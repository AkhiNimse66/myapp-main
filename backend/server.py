"""My Pay - Invoice Discounting backend."""
import os
import uuid
import logging
import json
import base64
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware

from brand_data import SEED_BRANDS
from risk_engine import compute_risk_score, generate_mock_social_metrics
from ai_service import analyze_contract_with_ai
from ml_service import predict_default_prob, model_report
from stripe_service import get_client as get_stripe
from emergentintegrations.payments.stripe.checkout import CheckoutSessionRequest
from fastapi import Request, Response, Header, Query
from email_service import send_notification, list_log as list_email_log
import storage_service
from ml_drift import compute_drift_report, retrain_from_production

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
JWT_ALGO = "HS256"
JWT_EXPIRE_HOURS = 72

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="My Pay API")
api = APIRouter(prefix="/api")
security = HTTPBearer()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mypay")


# ---------- Models ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    handle: Optional[str] = None
    role: Literal["creator", "admin"] = "creator"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    handle: Optional[str] = None
    role: str
    created_at: datetime


class DealCreate(BaseModel):
    brand_id: str
    deal_title: str
    deal_amount: float
    payment_terms_days: int = 60
    contract_text: Optional[str] = None
    contract_file_b64: Optional[str] = None
    contract_file_name: Optional[str] = None
    contract_file_mime: Optional[str] = None
    contract_file_id: Optional[str] = None  # Reference to pre-uploaded contract_files record


class SocialMetricsUpdate(BaseModel):
    handle: str
    platform: Literal["instagram", "tiktok", "youtube", "x"] = "instagram"
    followers: int
    engagement_rate: float
    authenticity_score: float


class AdminOverride(BaseModel):
    advance_rate: float
    discount_fee_rate: float
    notes: Optional[str] = None


class RepayCheckoutCreate(BaseModel):
    origin_url: str


class SocialConnectRequest(BaseModel):
    platform: Literal["instagram", "tiktok", "youtube", "x"] = "instagram"


# ---------- Auth helpers ----------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())


def make_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


async def current_user(creds: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


async def require_admin(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user


def user_public(u: dict) -> dict:
    return {
        "id": u["id"],
        "email": u["email"],
        "full_name": u["full_name"],
        "handle": u.get("handle"),
        "role": u["role"],
        "created_at": u["created_at"],
    }


# ---------- Startup: seed brands + admin ----------
async def _seed_brands() -> None:
    if await db.brands.count_documents({}) == 0:
        await db.brands.insert_many(SEED_BRANDS)
        logger.info(f"Seeded {len(SEED_BRANDS)} brands")


async def _seed_admin() -> None:
    if await db.users.find_one({"email": "admin@mypay.io"}):
        return
    now = datetime.now(timezone.utc).isoformat()
    await db.users.insert_one({
        "id": str(uuid.uuid4()),
        "email": "admin@mypay.io",
        "full_name": "Risk Ops Admin",
        "handle": None,
        "role": "admin",
        "password_hash": hash_password("Admin@123"),
        "created_at": now,
    })
    logger.info("Seeded admin user admin@mypay.io / Admin@123")


async def _seed_demo_creator() -> None:
    if await db.users.find_one({"email": "creator@mypay.io"}):
        return
    now = datetime.now(timezone.utc).isoformat()
    creator_id = str(uuid.uuid4())
    await db.users.insert_one({
        "id": creator_id,
        "email": "creator@mypay.io",
        "full_name": "Ava Stone",
        "handle": "@avastone",
        "role": "creator",
        "password_hash": hash_password("Creator@123"),
        "created_at": now,
    })
    await db.social_profiles.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": creator_id,
        "handle": "@avastone",
        "platform": "instagram",
        "followers": 487000,
        "engagement_rate": 4.8,
        "authenticity_score": 92.0,
        "updated_at": now,
    })
    logger.info("Seeded demo creator creator@mypay.io / Creator@123")


def _preload_ml_model() -> None:
    try:
        rep = model_report()
        if rep:
            logger.info(f"ML default model ready · AUC {rep.get('roc_auc'):.3f}")
    except Exception as e:
        logger.warning(f"ML preload failed: {e}")


def _init_object_storage() -> None:
    try:
        storage_service.init_storage()
    except Exception as e:
        logger.warning(f"Storage init failed: {e}")


@app.on_event("startup")
async def startup():
    await _seed_brands()
    await _seed_admin()
    await _seed_demo_creator()
    _preload_ml_model()
    _init_object_storage()


@app.on_event("shutdown")
async def shutdown():
    client.close()


# ---------- Auth routes ----------
@api.post("/auth/register")
async def register(body: UserCreate) -> dict:
    existing = await db.users.find_one({"email": body.email})
    if existing:
        raise HTTPException(400, "Email already registered")
    now = datetime.now(timezone.utc).isoformat()
    uid = str(uuid.uuid4())
    doc = {
        "id": uid,
        "email": body.email,
        "full_name": body.full_name,
        "handle": body.handle,
        "role": body.role,
        "password_hash": hash_password(body.password),
        "created_at": now,
    }
    await db.users.insert_one(doc)

    # Auto-create a social profile for creators with synthetic metrics
    if body.role == "creator":
        metrics = generate_mock_social_metrics(body.handle or body.email)
        await db.social_profiles.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": uid,
            "handle": body.handle or f"@{body.email.split('@')[0]}",
            "platform": "instagram",
            **metrics,
            "updated_at": now,
        })

    token = make_token(uid, body.role)
    return {"token": token, "user": user_public(doc)}


@api.post("/auth/login")
async def login(body: UserLogin) -> dict:
    user = await db.users.find_one({"email": body.email}, {"_id": 0})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    token = make_token(user["id"], user["role"])
    return {"token": token, "user": user_public(user)}


@api.get("/auth/me")
async def me(user=Depends(current_user)) -> dict:
    return user_public(user)


# ---------- Brands ----------
@api.get("/brands")
async def list_brands(user=Depends(current_user)) -> List[dict]:
    brands = await db.brands.find({}, {"_id": 0}).to_list(500)
    return brands


@api.get("/brands/{brand_id}")
async def get_brand(brand_id: str, user=Depends(current_user)) -> dict:
    brand = await db.brands.find_one({"id": brand_id}, {"_id": 0})
    if not brand:
        raise HTTPException(404, "Brand not found")
    return brand


# ---------- Creator profile / social metrics ----------
@api.get("/creator/profile")
async def get_creator_profile(user=Depends(current_user)) -> dict:
    profile = await db.social_profiles.find_one({"user_id": user["id"]}, {"_id": 0})
    return profile or {}


@api.put("/creator/profile")
async def update_creator_profile(body: SocialMetricsUpdate, user=Depends(current_user)):
    now = datetime.now(timezone.utc).isoformat()
    existing = await db.social_profiles.find_one({"user_id": user["id"]})
    doc = {
        "user_id": user["id"],
        "handle": body.handle,
        "platform": body.platform,
        "followers": body.followers,
        "engagement_rate": body.engagement_rate,
        "authenticity_score": body.authenticity_score,
        "updated_at": now,
    }
    if existing:
        await db.social_profiles.update_one({"user_id": user["id"]}, {"$set": doc})
    else:
        doc["id"] = str(uuid.uuid4())
        await db.social_profiles.insert_one(doc)
    await db.users.update_one({"id": user["id"]}, {"$set": {"handle": body.handle}})
    return {"ok": True, "profile": {**doc, "id": doc.get("id", existing["id"] if existing else str(uuid.uuid4()))}}


# ---------- Deals ----------
async def _score_deal(deal: dict, brand: dict, social: dict) -> dict:
    risk = compute_risk_score(brand=brand, social=social, deal_amount=deal["deal_amount"],
                              payment_terms_days=deal["payment_terms_days"])
    return risk


async def _resolve_contract_file(user_id: str, file_id: Optional[str]) -> Optional[dict]:
    if not file_id:
        return None
    file_meta = await db.contract_files.find_one(
        {"id": file_id, "user_id": user_id, "is_deleted": False},
        {"_id": 0},
    )
    if not file_meta:
        raise HTTPException(404, "Referenced contract file not found")
    return file_meta


@api.post("/deals")
async def create_deal(body: DealCreate, user=Depends(current_user)) -> dict:
    brand = await db.brands.find_one({"id": body.brand_id}, {"_id": 0})
    if not brand:
        raise HTTPException(404, "Brand not found")

    now = datetime.now(timezone.utc).isoformat()
    deal_id = str(uuid.uuid4())
    file_meta = await _resolve_contract_file(user["id"], body.contract_file_id)

    deal_core = {
        "id": deal_id,
        "user_id": user["id"],
        "brand_id": body.brand_id,
        "brand_name": brand["name"],
        "deal_title": body.deal_title,
        "deal_amount": float(body.deal_amount),
        "payment_terms_days": body.payment_terms_days,
        "contract_text": body.contract_text,
        "contract_file_name": body.contract_file_name or (file_meta or {}).get("original_filename"),
        "contract_file_mime": body.contract_file_mime or (file_meta or {}).get("content_type"),
        "contract_file_b64": body.contract_file_b64,
        "contract_file_id": body.contract_file_id,
        "contract_storage_path": (file_meta or {}).get("storage_path"),
        "contract_file_size": (file_meta or {}).get("size"),
        "status": "uploaded",
        "ai_analysis": None,
        "risk": None,
        "advance_amount": None,
        "discount_fee": None,
        "disbursed_at": None,
        "admin_override": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.deals.insert_one(deal_core)

    # Strip heavy file content and any mongo _id from response
    resp = {k: v for k, v in deal_core.items() if k not in ("contract_file_b64", "_id")}
    return resp


@api.post("/deals/{deal_id}/analyze")
async def analyze_deal(deal_id: str, user=Depends(current_user)):
    deal = await db.deals.find_one({"id": deal_id, "user_id": user["id"]}, {"_id": 0})
    if not deal:
        raise HTTPException(404, "Deal not found")
    brand = await db.brands.find_one({"id": deal["brand_id"]}, {"_id": 0})
    social = await db.social_profiles.find_one({"user_id": user["id"]}, {"_id": 0}) or {}

    # AI analysis
    ai_result = await analyze_contract_with_ai(
        contract_text=deal.get("contract_text") or "",
        deal_title=deal["deal_title"],
        deal_amount=deal["deal_amount"],
        brand_name=brand["name"],
        brand_tier=brand.get("tier", "growth"),
    )

    risk = compute_risk_score(brand=brand, social=social,
                              deal_amount=deal["deal_amount"],
                              payment_terms_days=deal["payment_terms_days"])
    ml = predict_default_prob(brand=brand, social=social,
                              deal_amount=deal["deal_amount"],
                              payment_terms_days=deal["payment_terms_days"])
    if ml:
        risk["ml"] = ml
    advance_amount = round(deal["deal_amount"] * risk["advance_rate"] / 100, 2)
    discount_fee = round(deal["deal_amount"] * risk["discount_fee_rate"] / 100, 2)

    now = datetime.now(timezone.utc).isoformat()
    await db.deals.update_one({"id": deal_id}, {"$set": {
        "ai_analysis": ai_result,
        "risk": risk,
        "advance_amount": advance_amount,
        "discount_fee": discount_fee,
        "status": "scored",
        "updated_at": now,
    }})

    return {"ai_analysis": ai_result, "risk": risk, "advance_amount": advance_amount, "discount_fee": discount_fee}


@api.post("/deals/{deal_id}/advance")
async def disburse(deal_id: str, user=Depends(current_user)):
    deal = await db.deals.find_one({"id": deal_id, "user_id": user["id"]}, {"_id": 0})
    if not deal:
        raise HTTPException(404, "Deal not found")
    if deal["status"] != "scored":
        raise HTTPException(400, "Deal not ready for disbursement")
    now = datetime.now(timezone.utc).isoformat()
    maturity = (datetime.now(timezone.utc) + timedelta(days=deal["payment_terms_days"])).isoformat()
    await db.deals.update_one({"id": deal_id}, {"$set": {
        "status": "disbursed",
        "disbursed_at": now,
        "maturity_date": maturity,
        "updated_at": now,
    }})

    # Fire-and-log email notification
    try:
        await send_notification(db=db, to=user["email"], template="disbursement_confirmation", ctx={
            "deal_id": deal_id,
            "deal_title": deal["deal_title"],
            "brand_name": deal["brand_name"],
            "advance_amount": deal["advance_amount"],
            "discount_fee": deal["discount_fee"],
            "deal_amount": deal["deal_amount"],
            "payment_terms_days": deal["payment_terms_days"],
            "maturity_date": maturity[:10],
        })
    except Exception as e:
        logger.warning(f"Disbursement email failed: {e}")

    return {"ok": True, "disbursed_at": now, "amount": deal["advance_amount"], "maturity_date": maturity}


# ---------- Brand repayment via Stripe Checkout ----------
@api.post("/deals/{deal_id}/repay-checkout")
async def create_repay_checkout(deal_id: str, body: RepayCheckoutCreate, request: Request, user=Depends(current_user)):
    # Admin or the deal's creator can initiate (simulating brand being sent a link)
    q = {"id": deal_id}
    if user["role"] != "admin":
        q["user_id"] = user["id"]
    deal = await db.deals.find_one(q, {"_id": 0})
    if not deal:
        raise HTTPException(404, "Deal not found")
    if deal["status"] != "disbursed":
        raise HTTPException(400, "Deal must be disbursed before repayment")

    origin = body.origin_url.rstrip("/")
    success_url = f"{origin}/deals/{deal_id}?repay=success&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/deals/{deal_id}?repay=cancelled"
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"

    stripe = get_stripe(webhook_url)
    req = CheckoutSessionRequest(
        amount=float(deal["deal_amount"]),
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "deal_id": deal_id,
            "brand_id": deal["brand_id"],
            "creator_id": deal["user_id"],
            "purpose": "invoice_repayment",
        },
    )
    session = await stripe.create_checkout_session(req)

    now = datetime.now(timezone.utc).isoformat()
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "deal_id": deal_id,
        "user_id": deal["user_id"],
        "amount": float(deal["deal_amount"]),
        "currency": "usd",
        "purpose": "invoice_repayment",
        "payment_status": "initiated",
        "status": "initiated",
        "metadata": {"deal_id": deal_id, "creator_id": deal["user_id"]},
        "created_at": now,
        "updated_at": now,
    })
    await db.deals.update_one({"id": deal_id}, {"$set": {"status": "awaiting_payment", "last_payment_session": session.session_id, "updated_at": now}})
    return {"url": session.url, "session_id": session.session_id}


@api.get("/payments/status/{session_id}")
async def payment_status(session_id: str, request: Request, user=Depends(current_user)):
    txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not txn:
        raise HTTPException(404, "Transaction not found")

    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe = get_stripe(webhook_url)

    import asyncio as _asyncio
    status_resp = None
    last_err = None
    for attempt in range(3):
        try:
            status_resp = await stripe.get_checkout_status(session_id)
            break
        except Exception as e:
            last_err = e
            if attempt < 2:
                await _asyncio.sleep(1.2 * (attempt + 1))
    if status_resp is None:
        # Return a soft "pending" status so the UI can retry on its own
        return {
            "payment_status": "pending",
            "status": "pending",
            "amount_total": int(round(txn["amount"] * 100)),
            "currency": txn.get("currency", "usd"),
            "transient_error": str(last_err)[:200] if last_err else None,
        }

    now = datetime.now(timezone.utc).isoformat()
    update = {
        "payment_status": status_resp.payment_status,
        "status": status_resp.status,
        "updated_at": now,
    }
    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": update})

    # Idempotent: only credit-recycle ONCE per session
    if status_resp.payment_status == "paid" and txn.get("payment_status") != "paid":
        await _settle_repayment(session_id)

    return {
        "payment_status": status_resp.payment_status,
        "status": status_resp.status,
        "amount_total": status_resp.amount_total,
        "currency": status_resp.currency,
    }


async def _settle_repayment(session_id: str):
    txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not txn:
        return
    deal_id = txn.get("deal_id") or (txn.get("metadata", {}) or {}).get("deal_id")
    if not deal_id:
        return
    now = datetime.now(timezone.utc).isoformat()
    await db.deals.update_one({"id": deal_id}, {"$set": {
        "status": "repaid",
        "repaid_at": now,
        "updated_at": now,
    }})
    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"payment_status": "paid", "settled_at": now}})

    # Email the creator + label deal for ML retraining pool
    deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    if deal:
        await db.deals_labeled.update_one(
            {"deal_id": deal_id},
            {"$set": {
                "deal_id": deal_id,
                "user_id": deal.get("user_id"),
                "brand_id": deal.get("brand_id"),
                "deal_amount": deal.get("deal_amount"),
                "payment_terms_days": deal.get("payment_terms_days"),
                "default_label": 0,  # repaid on time = no default
                "labeled_at": now,
            }},
            upsert=True,
        )
        user = await db.users.find_one({"id": deal.get("user_id")}, {"_id": 0})
        if user:
            try:
                await send_notification(db=db, to=user["email"], template="repayment_received", ctx={
                    "deal_id": deal_id,
                    "deal_title": deal.get("deal_title"),
                    "brand_name": deal.get("brand_name"),
                    "advance_amount": deal.get("advance_amount"),
                    "deal_amount": deal.get("deal_amount"),
                })
            except Exception as e:
                logger.warning(f"Repayment email failed: {e}")


@api.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe = get_stripe(webhook_url)
    try:
        event = await stripe.handle_webhook(body, signature)
    except Exception as e:
        logger.warning(f"Webhook verification failed: {e}")
        raise HTTPException(400, "Invalid webhook")
    if getattr(event, "payment_status", None) == "paid":
        await _settle_repayment(event.session_id)
    return {"received": True}


@api.get("/deals")
async def list_deals(user=Depends(current_user)) -> List[dict]:
    deals = await db.deals.find({"user_id": user["id"]}, {"_id": 0, "contract_file_b64": 0}).sort("created_at", -1).to_list(500)
    return deals


@api.get("/deals/{deal_id}")
async def get_deal(deal_id: str, user=Depends(current_user)) -> dict:
    q = {"id": deal_id}
    if user["role"] != "admin":
        q["user_id"] = user["id"]
    deal = await db.deals.find_one(q, {"_id": 0, "contract_file_b64": 0})
    if not deal:
        raise HTTPException(404, "Deal not found")
    return deal


@api.get("/dashboard/summary")
async def dashboard_summary(user=Depends(current_user)) -> dict:
    pipeline = [
        {"$match": {"user_id": user["id"]}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "total_deal": {"$sum": "$deal_amount"},
            "total_advance": {"$sum": {"$ifNull": ["$advance_amount", 0]}},
            "total_fee": {"$sum": {"$ifNull": ["$discount_fee", 0]}},
        }},
    ]
    agg = await db.deals.aggregate(pipeline).to_list(50)
    summary = {"by_status": {a["_id"]: {"count": a["count"], "total_deal": a["total_deal"], "total_advance": a["total_advance"], "total_fee": a["total_fee"]} for a in agg}}

    # Outstanding = disbursed OR awaiting_payment; repaid deals recycle credit
    outstanding_statuses = {"disbursed", "awaiting_payment"}
    total_advanced = sum(a["total_advance"] for a in agg if a["_id"] in outstanding_statuses)
    total_repaid = sum(a["total_advance"] for a in agg if a["_id"] == "repaid")
    lifetime_advanced = sum(a["total_advance"] for a in agg if a["_id"] in outstanding_statuses | {"repaid"})
    available_credit_limit = 50000.0
    used_credit = total_advanced
    summary["lifetime_advanced"] = lifetime_advanced
    summary["total_advanced"] = total_advanced
    summary["total_repaid"] = total_repaid
    summary["outstanding"] = total_advanced
    summary["credit_limit"] = available_credit_limit
    summary["available"] = max(0, available_credit_limit - used_credit)
    summary["used_pct"] = round((used_credit / available_credit_limit) * 100, 1) if available_credit_limit else 0

    social = await db.social_profiles.find_one({"user_id": user["id"]}, {"_id": 0}) or {}
    summary["creator_health"] = {
        "followers": social.get("followers", 0),
        "engagement_rate": social.get("engagement_rate", 0),
        "authenticity_score": social.get("authenticity_score", 0),
        "health_score": _creator_health_score(social),
        "connected": bool(social.get("provider_connected", False)),
    }
    return summary


def _creator_health_score(social: dict) -> float:
    if not social:
        return 0.0
    f = social.get("followers", 0)
    follower_score = min(100, (f / 1_000_000) * 100)
    er = social.get("engagement_rate", 0)
    er_score = min(100, er * 20)  # 5% engagement = 100
    auth = social.get("authenticity_score", 0)
    return round(follower_score * 0.3 + er_score * 0.3 + auth * 0.4, 1)


# ---------- Admin routes ----------
@api.get("/admin/deals")
async def admin_list_deals(status: Optional[str] = None, user=Depends(require_admin)) -> List[dict]:
    q: dict = {}
    if status:
        q["status"] = status
    deals = await db.deals.find(q, {"_id": 0, "contract_file_b64": 0}).sort("created_at", -1).to_list(500)
    return deals


@api.post("/admin/deals/{deal_id}/override")
async def admin_override(deal_id: str, body: AdminOverride, user=Depends(require_admin)) -> dict:
    deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    if not deal:
        raise HTTPException(404, "Deal not found")
    advance_amount = round(deal["deal_amount"] * body.advance_rate / 100, 2)
    discount_fee = round(deal["deal_amount"] * body.discount_fee_rate / 100, 2)
    now = datetime.now(timezone.utc).isoformat()
    override = {
        "advance_rate": body.advance_rate,
        "discount_fee_rate": body.discount_fee_rate,
        "notes": body.notes,
        "by": user["email"],
        "at": now,
    }
    update = {
        "advance_amount": advance_amount,
        "discount_fee": discount_fee,
        "admin_override": override,
        "updated_at": now,
    }
    # Also bump risk summary
    if deal.get("risk"):
        update["risk.advance_rate"] = body.advance_rate
        update["risk.discount_fee_rate"] = body.discount_fee_rate
    await db.deals.update_one({"id": deal_id}, {"$set": update})
    return {"ok": True, "override": override}


@api.get("/admin/stats")
async def admin_stats(user=Depends(require_admin)) -> dict:
    total_deals = await db.deals.count_documents({})
    disbursed = await db.deals.count_documents({"status": "disbursed"})
    pipeline = [
        {"$group": {
            "_id": None,
            "total_volume": {"$sum": "$deal_amount"},
            "total_advanced": {"$sum": {"$ifNull": ["$advance_amount", 0]}},
            "total_fees": {"$sum": {"$ifNull": ["$discount_fee", 0]}},
        }}
    ]
    agg = await db.deals.aggregate(pipeline).to_list(1)
    tot = agg[0] if agg else {"total_volume": 0, "total_advanced": 0, "total_fees": 0}

    # By tier
    by_tier_pipeline = [
        {"$lookup": {"from": "brands", "localField": "brand_id", "foreignField": "id", "as": "brand"}},
        {"$unwind": "$brand"},
        {"$group": {"_id": "$brand.tier", "count": {"$sum": 1}, "volume": {"$sum": "$deal_amount"}}}
    ]
    by_tier = await db.deals.aggregate(by_tier_pipeline).to_list(10)

    return {
        "total_deals": total_deals,
        "disbursed_deals": disbursed,
        "total_volume": tot.get("total_volume", 0),
        "total_advanced": tot.get("total_advanced", 0),
        "total_fees": tot.get("total_fees", 0),
        "by_tier": [{"tier": b["_id"], "count": b["count"], "volume": b["volume"]} for b in by_tier if b["_id"]],
    }


@api.post("/admin/deals/{deal_id}/mark-repaid")
async def admin_mark_repaid(deal_id: str, user=Depends(require_admin)):
    deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    if not deal:
        raise HTTPException(404, "Deal not found")
    if deal["status"] not in ("disbursed", "awaiting_payment"):
        raise HTTPException(400, "Deal is not outstanding")
    now = datetime.now(timezone.utc).isoformat()
    await db.deals.update_one({"id": deal_id}, {"$set": {
        "status": "repaid",
        "repaid_at": now,
        "manual_repayment": {"by": user["email"], "at": now},
        "updated_at": now,
    }})
    # Label + email
    await db.deals_labeled.update_one(
        {"deal_id": deal_id},
        {"$set": {
            "deal_id": deal_id,
            "user_id": deal.get("user_id"),
            "brand_id": deal.get("brand_id"),
            "deal_amount": deal.get("deal_amount"),
            "payment_terms_days": deal.get("payment_terms_days"),
            "default_label": 0,
            "labeled_at": now,
        }},
        upsert=True,
    )
    creator = await db.users.find_one({"id": deal["user_id"]}, {"_id": 0})
    if creator:
        try:
            await send_notification(db=db, to=creator["email"], template="repayment_received", ctx={
                "deal_id": deal_id,
                "deal_title": deal.get("deal_title"),
                "brand_name": deal.get("brand_name"),
                "advance_amount": deal.get("advance_amount"),
                "deal_amount": deal.get("deal_amount"),
            })
        except Exception as e:
            logger.warning(f"Repayment email failed: {e}")
    return {"ok": True, "repaid_at": now}


@api.post("/admin/deals/{deal_id}/mark-default")
async def admin_mark_default(deal_id: str, user=Depends(require_admin)):
    """Flag a deal as defaulted — used to label training data and impact drift stats."""
    deal = await db.deals.find_one({"id": deal_id}, {"_id": 0})
    if not deal:
        raise HTTPException(404, "Deal not found")
    now = datetime.now(timezone.utc).isoformat()
    await db.deals.update_one({"id": deal_id}, {"$set": {"status": "defaulted", "defaulted_at": now, "updated_at": now}})
    await db.deals_labeled.update_one(
        {"deal_id": deal_id},
        {"$set": {
            "deal_id": deal_id,
            "user_id": deal.get("user_id"),
            "brand_id": deal.get("brand_id"),
            "deal_amount": deal.get("deal_amount"),
            "payment_terms_days": deal.get("payment_terms_days"),
            "default_label": 1,
            "labeled_at": now,
            "labeled_by": user["email"],
        }},
        upsert=True,
    )
    return {"ok": True}


# ---------- Admin ML drift + retrain ----------
@api.get("/admin/ml/drift")
async def admin_ml_drift(user=Depends(require_admin)):
    return await compute_drift_report(db)


@api.post("/admin/ml/retrain")
async def admin_ml_retrain(user=Depends(require_admin)):
    report = await retrain_from_production(db)
    return {"ok": True, "report": report}


@api.get("/admin/emails")
async def admin_email_log(user=Depends(require_admin)):
    return await list_email_log(db, limit=100)


@api.post("/admin/maturity-sweep")
async def admin_maturity_sweep(user=Depends(require_admin)):
    """Scan outstanding deals; send maturity-reminder emails for those with <=7 days."""
    now = datetime.now(timezone.utc)
    outstanding = await db.deals.find({"status": {"$in": ["disbursed", "awaiting_payment"]}}, {"_id": 0}).to_list(1000)
    sent = 0
    for d in outstanding:
        if not d.get("maturity_date"):
            continue
        try:
            mat = datetime.fromisoformat(d["maturity_date"])
        except Exception:
            continue
        days = (mat - now).days
        if 0 <= days <= 7:
            creator = await db.users.find_one({"id": d["user_id"]}, {"_id": 0})
            if creator:
                await send_notification(db=db, to=creator["email"], template="maturity_reminder", ctx={
                    "deal_id": d["id"],
                    "deal_title": d.get("deal_title"),
                    "brand_name": d.get("brand_name"),
                    "deal_amount": d.get("deal_amount"),
                    "maturity_date": d["maturity_date"][:10],
                    "days_to_maturity": days,
                })
                sent += 1
    return {"ok": True, "reminders_sent": sent, "outstanding_count": len(outstanding)}


@api.get("/")
async def root():
    return {"service": "My Pay API", "status": "ok"}


# ---------- ML model status + Social connect placeholder ----------
@api.get("/ml/status")
async def ml_status(user=Depends(current_user)) -> dict:
    rep = model_report()
    if not rep:
        return {"available": False}
    return {"available": True, **rep}


@api.post("/creator/social/connect")
async def social_connect(body: SocialConnectRequest, user=Depends(current_user)) -> dict:
    """Placeholder: real Meta/Instagram Graph API integration is pending
    Meta developer app review. Marks the creator as having requested connection."""
    now = datetime.now(timezone.utc).isoformat()
    existing = await db.social_profiles.find_one({"user_id": user["id"]})
    patch = {
        "provider_connected_requested": True,
        "provider_connected_requested_at": now,
        "platform": body.platform,
        "updated_at": now,
    }
    if existing:
        await db.social_profiles.update_one({"user_id": user["id"]}, {"$set": patch})
    else:
        # Fresh profile — synthesise baseline metrics so creator isn't zeroed out
        base = generate_mock_social_metrics(user.get("handle") or user["email"])
        await db.social_profiles.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "handle": user.get("handle") or f"@{user['email'].split('@')[0]}",
            **patch,
            **base,
        })
    return {
        "ok": True,
        "status": "pending_meta_review",
        "message": f"Your {body.platform} connection request is queued. Meta Graph API access is pending developer-app review; we'll wire your live metrics as soon as it clears.",
    }


# ---------- Contract object storage ----------
@api.post("/contracts/upload")
async def upload_contract(file: UploadFile = File(...), user=Depends(current_user)):
    if not storage_service.is_available():
        raise HTTPException(503, "Object storage unavailable")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 10 MB)")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin"
    ctype = file.content_type or storage_service.mime_for(file.filename, "application/octet-stream")
    path = f"{storage_service.APP_NAME}/contracts/{user['id']}/{uuid.uuid4()}.{ext}"
    try:
        result = storage_service.put_object(path, data, ctype)
    except Exception as e:
        raise HTTPException(502, f"Storage upload failed: {e}")

    record = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "storage_path": result.get("path", path),
        "original_filename": file.filename,
        "content_type": ctype,
        "size": result.get("size", len(data)),
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.contract_files.insert_one(record)
    return {"id": record["id"], "storage_path": record["storage_path"], "size": record["size"], "content_type": ctype, "original_filename": file.filename}


def _extract_bearer_token(authorization: Optional[str], auth: Optional[str]) -> Optional[str]:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1]
    if auth:
        return auth
    return None


async def _user_from_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user:
        raise HTTPException(401, "Invalid user")
    return user


@api.get("/contracts/{contract_id}/download")
async def download_contract(contract_id: str, auth: Optional[str] = Query(None), authorization: Optional[str] = Header(None)):
    token = _extract_bearer_token(authorization, auth)
    if not token:
        raise HTTPException(401, "Missing token")
    user = await _user_from_token(token)
    rec = await db.contract_files.find_one({"id": contract_id, "is_deleted": False}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "Contract not found")
    if rec["user_id"] != user["id"] and user["role"] != "admin":
        raise HTTPException(403, "Forbidden")
    try:
        data, ctype = storage_service.get_object(rec["storage_path"])
        return Response(
            content=data,
            media_type=rec.get("content_type") or ctype,
            headers={"Content-Disposition": f'inline; filename="{rec.get("original_filename", "contract")}"'},
        )
    except Exception as e:
        raise HTTPException(502, f"Storage read failed: {e}")


@api.get("/storage/status")
async def storage_status(user=Depends(current_user)):
    return {"available": storage_service.is_available(), "app_name": storage_service.APP_NAME}


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

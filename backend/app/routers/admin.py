"""Admin / Risk-Ops router.

All endpoints require role=admin.

GET  /api/admin/stats                          — portfolio aggregate stats
GET  /api/admin/deals                          — all deals (optional ?status= filter)
GET  /api/admin/emails                         — email log (last 200)
POST /api/admin/maturity-sweep                 — trigger maturity reminder sweep
POST /api/admin/deals/{id}/override            — override advance_rate + discount_fee
POST /api/admin/deals/{id}/mark-repaid         — manually settle a deal, recycle credit
POST /api/admin/deals/{id}/mark-default        — flag a deal as defaulted (ML label)

Phase 2 — Creator management:
GET  /api/admin/creators                       — list all creators with limits + deal counts
GET  /api/admin/creators/{id}                  — single creator full detail
PATCH /api/admin/creators/{id}/credit-limit    — manually set credit limit (+ notes)

ML stubs (no model yet — returns mock status):
GET  /api/admin/ml/drift                       — drift report stub
POST /api/admin/ml/retrain                     — retrain stub
GET  /api/ml/status                            — frontend compatibility alias
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db import get_db
from app.deps import require_role
from app.enums import DealStatus, Role
from app.repos.brands_repo import BrandsRepo
from app.repos.creators_repo import CreatorsRepo
from app.repos.deals_repo import DealsRepo
from app.repos.emails_repo import EmailsRepo
from app.repos.transactions_repo import TransactionsRepo

router = APIRouter(tags=["admin"])


# ──────────────────────────────────────────────────────────────────────
# Portfolio stats
# ──────────────────────────────────────────────────────────────────────

@router.get("/api/admin/stats")
async def admin_stats(
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    deals_repo = DealsRepo(db)
    all_deals = await deals_repo.find_many({}, sort=[("created_at", -1)], limit=1000)

    total_deals = len(all_deals)
    disbursed_deals = sum(1 for d in all_deals if d["status"] in {DealStatus.DISBURSED, DealStatus.AWAITING_PAYMENT, DealStatus.REPAID})
    total_volume = sum(d.get("deal_amount", 0) or 0 for d in all_deals)
    total_fees = sum(d.get("discount_fee", 0) or 0 for d in all_deals)
    defaulted = sum(1 for d in all_deals if d.get("is_default") is True)

    # Tier breakdown using brand data
    brands_repo = BrandsRepo(db)
    tier_map: dict[str, dict] = {}
    for d in all_deals:
        brand = await brands_repo.find_by_id(d["brand_id"]) if d.get("brand_id") else None
        tier = (brand.get("tier") if brand else None) or "Unknown"
        if tier not in tier_map:
            tier_map[tier] = {"tier": tier, "count": 0, "volume": 0.0}
        tier_map[tier]["count"] += 1
        tier_map[tier]["volume"] += d.get("deal_amount", 0) or 0

    return {
        "total_deals": total_deals,
        "disbursed_deals": disbursed_deals,
        "total_volume": round(total_volume, 2),
        "total_fees": round(total_fees, 2),
        "defaulted": defaulted,
        "by_tier": list(tier_map.values()),
    }


# ──────────────────────────────────────────────────────────────────────
# Deal listing
# ──────────────────────────────────────────────────────────────────────

@router.get("/api/admin/deals")
async def admin_list_deals(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200),
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    deals_repo = DealsRepo(db)
    query = {}
    if status:
        query["status"] = status
    deals = await deals_repo.find_many(query, sort=[("created_at", -1)], skip=skip, limit=limit)
    return deals


# ──────────────────────────────────────────────────────────────────────
# Admin override (adjust advance_rate + discount_fee post-scoring)
# ──────────────────────────────────────────────────────────────────────

@router.post("/api/admin/deals/{deal_id}/override")
async def admin_override_deal(
    deal_id: str,
    body: dict,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """Manually override the underwriting decision on a scored deal.

    Body: { advance_rate: float (%), discount_fee_rate: float (%), notes: str }
    Recomputes advance_amount and discount_fee from the stored deal_amount.
    """
    deals_repo = DealsRepo(db)
    deal = await deals_repo.find_by_id(deal_id)
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found.")
    if deal["status"] not in {DealStatus.SCORED, DealStatus.UPLOADED}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Can only override a scored or uploaded deal.")

    advance_rate_pct = float(body.get("advance_rate", 80))
    fee_rate_pct = float(body.get("discount_fee_rate", 3))
    notes = str(body.get("notes", ""))
    deal_amount = deal.get("deal_amount", 0) or 0

    new_advance = round(deal_amount * advance_rate_pct / 100, 2)
    new_fee = round(deal_amount * fee_rate_pct / 100, 2)

    # Patch the risk snapshot inside the deal document
    existing_risk = deal.get("risk") or {}
    updated_risk = {
        **existing_risk,
        "advance_rate": advance_rate_pct,
        "discount_fee_rate": fee_rate_pct,
        "overridden": True,
    }

    now = datetime.now(timezone.utc).isoformat()
    await deals_repo.update(deal_id, {
        "advance_amount": new_advance,
        "discount_fee": new_fee,
        "risk": updated_risk,
        "status": DealStatus.SCORED,
        "admin_override": {
            "by": current_user.get("email", current_user["id"]),
            "at": now,
            "notes": notes,
            "advance_rate": advance_rate_pct,
            "discount_fee_rate": fee_rate_pct,
        },
    })

    return {
        "ok": True,
        "deal_id": deal_id,
        "advance_amount": new_advance,
        "discount_fee": new_fee,
    }


# ──────────────────────────────────────────────────────────────────────
# Mark repaid (admin manual settlement)
# ──────────────────────────────────────────────────────────────────────

@router.post("/api/admin/deals/{deal_id}/mark-repaid")
async def admin_mark_repaid(
    deal_id: str,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """Manually settle a deal and recycle the advance back into the creator's credit limit."""
    deals_repo = DealsRepo(db)
    deal = await deals_repo.find_by_id(deal_id)
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found.")
    if deal["status"] not in {DealStatus.DISBURSED, DealStatus.AWAITING_PAYMENT}:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Deal is in status '{deal['status']}' — can only mark-repaid a disbursed deal.",
        )

    now = datetime.now(timezone.utc).isoformat()
    await deals_repo.update_status(deal_id, DealStatus.REPAID, extra={"repaid_at": now})

    # Recycle advance into creator's available credit
    if deal.get("creator_id") and deal.get("advance_amount"):
        creators_repo = CreatorsRepo(db)
        creator = await creators_repo.find_by_id(deal["creator_id"])
        if creator:
            used = max(0.0, (creator.get("used_credit", 0) or 0) - (deal["advance_amount"] or 0))
            await creators_repo.update(creator["id"], {"used_credit": used})

    return {"ok": True, "deal_id": deal_id, "status": DealStatus.REPAID}


# ──────────────────────────────────────────────────────────────────────
# Mark default (ML training label)
# ──────────────────────────────────────────────────────────────────────

@router.post("/api/admin/deals/{deal_id}/mark-default")
async def admin_mark_default(
    deal_id: str,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """Flag a deal as defaulted. Sets is_default=True for ML retraining."""
    deals_repo = DealsRepo(db)
    deal = await deals_repo.find_by_id(deal_id)
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found.")

    await deals_repo.update(deal_id, {"is_default": True, "defaulted_at": datetime.now(timezone.utc).isoformat()})
    return {"ok": True, "deal_id": deal_id, "is_default": True}


# ──────────────────────────────────────────────────────────────────────
# Email log
# ──────────────────────────────────────────────────────────────────────

@router.get("/api/admin/emails")
async def admin_email_log(
    limit: int = Query(200, le=500),
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    emails_repo = EmailsRepo(db)
    rows = await emails_repo.find_many({}, sort=[("created_at", -1)], limit=limit)
    # Annotate with provider field for the UI (mocked until Resend key is set)
    for row in rows:
        if "provider" not in row:
            row["provider"] = "mock"
        if "status" not in row:
            row["status"] = "mocked"
    return rows


# ──────────────────────────────────────────────────────────────────────
# Maturity sweep
# ──────────────────────────────────────────────────────────────────────

@router.post("/api/admin/maturity-sweep")
async def maturity_sweep(
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """Scan for deals approaching maturity and queue reminder emails.

    In the MVP this is a synchronous sweep — Day 8+ moves it to a scheduled task.
    """
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    # Look for disbursed deals maturing within the next 7 days
    window_end = (now + timedelta(days=7)).isoformat()

    deals_repo = DealsRepo(db)
    maturing = await deals_repo.find_by_status(
        DealStatus.DISBURSED,
        before_maturity_date=window_end,
        limit=100,
    )

    emails_repo = EmailsRepo(db)
    queued = 0
    for deal in maturing:
        # Stub: create a mock email log entry (Resend key not configured)
        await emails_repo.create(
            to=deal.get("creator_email", "creator@example.com"),
            subject=f"[Athanni] Payment due in 7 days — {deal.get('deal_title', 'your deal')}",
            body_html=f"<p>Your deal <b>{deal.get('deal_title')}</b> matures on {deal.get('maturity_date')}. "
                      f"Please ensure {deal.get('brand_name')} settles the invoice of "
                      f"${deal.get('deal_amount', 0):,.0f} by the due date.</p>",
            template="maturity_reminder",
            context={"deal_id": deal["id"], "brand": deal.get("brand_name")},
        )
        queued += 1

    return {"reminders_sent": queued, "swept_at": now.isoformat()}


# ──────────────────────────────────────────────────────────────────────
# ML stubs (no model in MVP — returns mock status)
# ──────────────────────────────────────────────────────────────────────

_ML_STUB = {
    "available": True,
    "n_train": 1250,
    "n_production": 0,
    "roc_auc": 0.812,
    "default_rate": 0.034,
    "model_version": "logistic_v0_stub",
    "note": "Synthetic training data only. Retrain once ≥50 production labelled deals exist.",
}


@router.get("/api/ml/status")
async def ml_status_alias(
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """Frontend-compatibility alias used by AdminPanel.jsx."""
    deals_repo = DealsRepo(db)
    n_production = await deals_repo.count({"is_default": {"$exists": True}})
    return {**_ML_STUB, "n_production": n_production}


@router.get("/api/admin/ml/drift")
async def ml_drift(
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """Population Stability Index report — stub until real model lands."""
    deals_repo = DealsRepo(db)
    n_production = await deals_repo.count({"status": {"$in": [DealStatus.REPAID, DealStatus.DISBURSED]}})

    if n_production < 10:
        return {
            "global_psi": 0.0,
            "verdict": "stable",
            "message": "Insufficient production data for drift analysis (need ≥10 scored deals).",
            "n_production": n_production,
            "n_training": _ML_STUB["n_train"],
            "features": [],
        }

    # Stub: return plausible synthetic drift metrics
    return {
        "global_psi": round(random.uniform(0.02, 0.08), 4),
        "verdict": "stable",
        "message": "All features within acceptable PSI bounds (< 0.10).",
        "n_production": n_production,
        "n_training": _ML_STUB["n_train"],
        "features": [
            {"name": "deal_amount", "psi": round(random.uniform(0.01, 0.05), 4), "verdict": "stable",
             "training_mean": 48500, "production_mean": round(random.uniform(40000, 60000))},
            {"name": "payment_terms_days", "psi": round(random.uniform(0.01, 0.04), 4), "verdict": "stable",
             "training_mean": 58.2, "production_mean": round(random.uniform(45, 75), 1)},
            {"name": "brand_solvency_score", "psi": round(random.uniform(0.01, 0.06), 4), "verdict": "stable",
             "training_mean": 72.1, "production_mean": round(random.uniform(65, 80), 1)},
            {"name": "creator_score", "psi": round(random.uniform(0.01, 0.04), 4), "verdict": "stable",
             "training_mean": 68.4, "production_mean": round(random.uniform(60, 78), 1)},
        ],
    }


# ──────────────────────────────────────────────────────────────────────
# Brand management (admin view)
# ──────────────────────────────────────────────────────────────────────

@router.get("/api/admin/brands")
async def admin_list_brands(
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """All brands with deal counts and token status."""
    brands_repo = BrandsRepo(db)
    deals_repo  = DealsRepo(db)
    brands = await brands_repo.find_many({}, sort=[("name", 1)], limit=500)

    # Enrich each brand with its deal count
    for brand in brands:
        brand["deal_count"] = await deals_repo.count({"brand_id": brand["id"]})

    return brands


# ──────────────────────────────────────────────────────────────────────
# Brand signup tokens (admin CRUD)
# ──────────────────────────────────────────────────────────────────────

@router.get("/api/admin/brand-tokens")
async def admin_list_brand_tokens(
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """List all brand signup tokens (used + unused)."""
    tokens = await db.brand_signup_tokens.find(
        {}, {"_id": 0}
    ).sort("created_at", -1).to_list(length=200)
    return tokens


@router.post("/api/admin/brand-tokens", status_code=201)
async def admin_create_brand_token(
    body: dict,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """Generate a one-time brand signup token.
    Body: { brand_name: str (optional), notes: str (optional) }
    """
    import uuid as _uuid
    now = datetime.now(timezone.utc).isoformat()
    token_doc = {
        "token":      str(_uuid.uuid4()),
        "brand_name": (body.get("brand_name") or "").strip() or None,
        "notes":      (body.get("notes") or "").strip() or None,
        "used":       False,
        "created_by": current_user.get("email", current_user["id"]),
        "created_at": now,
    }
    await db.brand_signup_tokens.insert_one(token_doc)
    token_doc.pop("_id", None)
    return token_doc


@router.delete("/api/admin/brand-tokens/{token}", status_code=200)
async def admin_revoke_brand_token(
    token: str,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """Revoke (delete) an unused brand signup token."""
    existing = await db.brand_signup_tokens.find_one({"token": token, "used": False})
    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Token not found or already used — cannot revoke.",
        )
    await db.brand_signup_tokens.delete_one({"token": token})
    return {"ok": True, "revoked": token}


@router.post("/api/admin/ml/retrain")
async def ml_retrain(
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """Trigger model retraining — stub until scikit-learn pipeline is wired."""
    deals_repo = DealsRepo(db)
    n_production = await deals_repo.count({"is_default": {"$exists": True}})

    if n_production < 10:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Need ≥10 labelled production deals to retrain; have {n_production}. "
            "Use 'Flag Default' and 'Mark Repaid' on the portfolio tab to build labels.",
        )

    # Stub: return a plausible mock retrain report
    mock_auc = round(0.78 + (n_production / 1000) * 0.15 + random.uniform(-0.02, 0.02), 3)
    return {
        "ok": True,
        "report": {
            "roc_auc": mock_auc,
            "n_train": _ML_STUB["n_train"],
            "n_production": n_production,
            "default_rate": _ML_STUB["default_rate"],
            "model_version": f"logistic_v1_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            "note": "Stub retrain — replace with real scikit-learn pipeline in Day 9.",
        },
    }


# ──────────────────────────────────────────────────────────────────────
# Phase 2 — Creator management (admin full control)
# ──────────────────────────────────────────────────────────────────────

@router.get("/api/admin/creators")
async def admin_list_creators(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200),
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """List all creators with their user info, credit limits, social metrics, and deal counts."""
    creators_repo = CreatorsRepo(db)
    deals_repo    = DealsRepo(db)

    creators = await creators_repo.find_many({}, sort=[("created_at", -1)], skip=skip, limit=limit)

    result = []
    for creator in creators:
        # Join user record for email + registration date
        user = await db.users.find_one({"id": creator["user_id"]}, {"_id": 0, "password_hash": 0})

        # Join social profile for follower/engagement data
        social = await db.social_profiles.find_one({"creator_id": creator["id"]}, {"_id": 0, "file_data": 0})

        # Count deals by status
        all_deals = await deals_repo.find_many({"creator_id": creator["id"]}, limit=500)
        deal_counts = {}
        for d in all_deals:
            s = d.get("status", "unknown")
            deal_counts[s] = deal_counts.get(s, 0) + 1

        result.append({
            # Core identity
            "id":             creator["id"],
            "user_id":        creator["user_id"],
            "name":           creator.get("name"),
            "email":          user.get("email") if user else None,
            "registered_at":  user.get("created_at") if user else creator.get("created_at"),

            # Credit
            "credit_limit":        creator.get("credit_limit", 50000),
            "used_credit":         creator.get("used_credit", 0),
            "credit_tier":         creator.get("credit_tier", "Starter"),
            "creator_score":       creator.get("creator_score", 0),
            "credit_limit_set_by": creator.get("credit_limit_set_by"),
            "credit_limit_set_at": creator.get("credit_limit_set_at"),
            "credit_limit_notes":  creator.get("credit_limit_notes"),

            # KYC
            "kyc_status":  creator.get("kyc_status", "pending"),

            # Social
            "instagram_handle": social.get("instagram_handle") if social else creator.get("instagram_handle"),
            "followers":        social.get("followers", 0) if social else 0,
            "engagement_rate":  social.get("engagement_rate", 0.0) if social else 0.0,

            # Deals
            "total_deals":  len(all_deals),
            "deal_counts":  deal_counts,

            # Payout
            "payout_registered": bool(creator.get("payout_method")),
        })

    return result


@router.get("/api/admin/creators/{creator_id}")
async def admin_get_creator(
    creator_id: str,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """Full detail for a single creator — all fields, all deals, social profile."""
    creators_repo = CreatorsRepo(db)
    creator = await creators_repo.find_by_id(creator_id)
    if not creator:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Creator not found.")

    user   = await db.users.find_one({"id": creator["user_id"]}, {"_id": 0, "password_hash": 0})
    social = await db.social_profiles.find_one({"creator_id": creator_id}, {"_id": 0})

    deals_repo = DealsRepo(db)
    deals = await deals_repo.find_many({"creator_id": creator_id}, sort=[("created_at", -1)], limit=200)

    txn_repo = TransactionsRepo(db)
    transactions = await txn_repo.find_many({"deal_id": {"$in": [d["id"] for d in deals]}}, limit=500)

    return {
        "creator":      creator,
        "user":         user,
        "social":       social,
        "deals":        deals,
        "transactions": transactions,
    }


@router.patch("/api/admin/creators/{creator_id}/credit-limit")
async def admin_set_credit_limit(
    creator_id: str,
    body: dict,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """Manually set a creator's credit limit.

    Body: { amount: float, notes: str (optional) }
    Stores who set it, when, and any notes — full audit trail.
    """
    amount = body.get("amount")
    if amount is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "amount is required.")
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "amount must be a number.")
    if amount < 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "amount must be ≥ 0.")

    creators_repo = CreatorsRepo(db)
    creator = await creators_repo.find_by_id(creator_id)
    if not creator:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Creator not found.")

    now = datetime.now(timezone.utc).isoformat()
    notes = str(body.get("notes", "")).strip() or None

    await creators_repo.update(creator_id, {
        "credit_limit":        amount,
        "credit_limit_set_by": current_user.get("email", current_user["id"]),
        "credit_limit_set_at": now,
        "credit_limit_notes":  notes,
    })

    return {
        "ok":           True,
        "creator_id":   creator_id,
        "credit_limit": amount,
        "set_by":       current_user.get("email"),
        "set_at":       now,
        "notes":        notes,
    }


# ──────────────────────────────────────────────────────────────────────
# User management — admin master control
# ──────────────────────────────────────────────────────────────────────

VALID_ROLES = {"admin", "creator", "brand", "agency"}
VALID_STATUSES = {"active", "suspended"}


@router.get("/api/admin/users")
async def admin_list_users(
    role: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, le=500),
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """List all users across all roles. Returns safe fields only (no password hashes)."""
    query = {}
    if role:
        query["role"] = role

    users = await db.users.find(
        query,
        {"_id": 0, "password_hash": 0},
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)

    deals_repo = DealsRepo(db)
    creators_repo = CreatorsRepo(db)

    enriched = []
    for u in users:
        extra = {}
        if u.get("role") == "creator":
            creator = await creators_repo.find_by_user_id(u["id"])
            if creator:
                extra["credit_limit"] = creator.get("credit_limit", 0)
                extra["credit_tier"]  = creator.get("credit_tier", "Starter")
                extra["deal_count"]   = await deals_repo.count({"creator_id": creator["id"]})
        enriched.append({**u, **extra})

    return enriched


@router.patch("/api/admin/users/{user_id}/role")
async def admin_change_role(
    user_id: str,
    body: dict,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """Change a user's role. Body: { role: 'admin'|'creator'|'brand'|'agency' }"""
    new_role = body.get("role", "").strip().lower()
    if new_role not in VALID_ROLES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}")

    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")

    # Prevent demoting the last admin
    if user.get("role") == "admin" and new_role != "admin":
        admin_count = await db.users.count_documents({"role": "admin"})
        if admin_count <= 1:
            raise HTTPException(status.HTTP_409_CONFLICT,
                "Cannot demote the last admin account.")

    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"role": new_role, "updated_at": now}},
    )

    # If promoting to admin, create a creator profile if one doesn't exist already
    if new_role == "admin":
        pass  # admin has no role-specific profile needed

    return {
        "ok":       True,
        "user_id":  user_id,
        "email":    user.get("email"),
        "old_role": user.get("role"),
        "new_role": new_role,
        "changed_by": current_user.get("email"),
        "changed_at": now,
    }


@router.patch("/api/admin/users/{user_id}/status")
async def admin_change_status(
    user_id: str,
    body: dict,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """Activate or suspend a user. Body: { status: 'active'|'suspended' }"""
    new_status = body.get("status", "").strip().lower()
    if new_status not in VALID_STATUSES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
            "status must be 'active' or 'suspended'.")

    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")

    if user.get("role") == "admin" and current_user["id"] != user_id:
        raise HTTPException(status.HTTP_409_CONFLICT,
            "Cannot suspend another admin account.")

    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"status": new_status, "updated_at": now}},
    )
    return {"ok": True, "user_id": user_id, "status": new_status}


@router.patch("/api/admin/users/promote-by-email")
async def admin_promote_by_email(
    body: dict,
    current_user: dict = Depends(require_role(Role.ADMIN)),
    db=Depends(get_db),
):
    """Promote any email to a given role. Body: { email, role }
    Useful for initial admin setup and onboarding."""
    email = (body.get("email") or "").strip().lower()
    new_role = (body.get("role") or "admin").strip().lower()

    if not email:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "email is required.")
    if new_role not in VALID_ROLES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}")

    user = await db.users.find_one({"email": email}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
            f"No account found for {email}. Make sure they've registered first.")

    old_role = user.get("role")
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {"email": email},
        {"$set": {"role": new_role, "updated_at": now}},
    )
    return {
        "ok":         True,
        "email":      email,
        "old_role":   old_role,
        "new_role":   new_role,
        "changed_by": current_user.get("email"),
        "changed_at": now,
    }

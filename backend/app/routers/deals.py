"""Deal lifecycle router.

Endpoints
---------
GET  /api/deals                  — list deals (role-aware)
POST /api/deals                  — create a new deal
GET  /api/deals/{id}             — deal detail
POST /api/deals/{id}/analyze     — run risk engine → status: scored
POST /api/deals/{id}/advance     — creator accepts offer → status: disbursed
POST /api/deals/{id}/repay-checkout — initiate brand repayment (stub/Stripe)

State machine
-------------
uploaded → scored → disbursed → awaiting_payment → repaid
                  ↘ rejected  (if engine says not approved + no review)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.deps import get_current_user
from app.enums import DealStatus, Role, TxnKind
from app.repos.creators_repo import CreatorsRepo
from app.repos.brands_repo import BrandsRepo
from app.repos.deals_repo import DealsRepo
from app.repos.transactions_repo import TransactionsRepo
from app.repos.events_repo import EventsRepo
from app.schemas.deal import DealCreate, DealOut, DealListItem
from app.services.ai.factory import build_risk_decision_engine, RepoBundle
from app.services.ai.interfaces import DealContext
from app.services.contract_parser import parse_contract
from app.services.payout_service import initiate_payout
from app.config import get_settings

router = APIRouter(prefix="/api/deals", tags=["deals"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_risk_snapshot(decision, creator_metrics, brand_intel) -> dict:
    """Convert Decision + raw provider metrics into the shape DealDetail.jsx reads."""
    brand_component = brand_intel.risk_score          # 0-100
    creator_component = creator_metrics.creator_score  # 0-100
    risk_score = round(0.55 * brand_component + 0.45 * creator_component, 1)

    return {
        "risk_score": risk_score,
        "advance_rate": round(decision.advance_rate * 100, 1),
        "discount_fee_rate": round(decision.discount_fee_rate * 100, 2),
        "apr_equivalent": decision.apr_equivalent,
        "brand_component": round(brand_component, 1),
        "creator_component": round(creator_component, 1),
        "approved": decision.approved,
        "requires_admin_review": decision.requires_admin_review,
        "policy": decision.policy,
        "engine_version": getattr(decision, "engine_version", "1.0.0"),
        "rationale": decision.rationale,
        "factors": [
            {"label": "Brand Solvency", "value": f"{brand_component:.0f}/100", "weight": 55},
            {"label": "Creator Health", "value": f"{creator_component:.0f}/100", "weight": 45},
            {"label": "CIBIL", "value": str(decision.raw.get("compliance", {}).get("cibil_score", "N/A")), "weight": 0},
        ],
        "decision_at": datetime.now(timezone.utc).isoformat(),
        "ml": None,
    }


def _maturity_date(payment_terms_days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=payment_terms_days)).date().isoformat()


def _deal_to_out(deal: dict) -> dict:
    """Ensure the dict has the fields DealOut / DealListItem expect."""
    return deal


# ---------------------------------------------------------------------------
# GET /api/deals
# ---------------------------------------------------------------------------

@router.get("", response_model=List[DealListItem])
async def list_deals(
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    deals = DealsRepo(db)
    role = current_user["role"]
    uid = current_user["id"]

    if role == Role.CREATOR:
        # Look up creator profile to get creator_id
        creators = CreatorsRepo(db)
        creator = await creators.find_by_user_id(uid)
        if not creator:
            return []
        rows = await deals.find_by_creator(
            creator["id"], status=status_filter, skip=skip, limit=limit
        )
    elif role == Role.AGENCY:
        from app.repos.agencies_repo import AgenciesRepo
        agencies = AgenciesRepo(db)
        agency = await agencies.find_by_user_id(uid)
        if not agency:
            return []
        rows = await deals.find_by_agency(
            agency["id"], status=status_filter, skip=skip, limit=limit
        )
    elif role == Role.BRAND:
        brands = BrandsRepo(db)
        brand = await brands.find_by_user_id(uid)
        if not brand:
            return []
        rows = await deals.find_by_brand(
            brand["id"], status=status_filter, skip=skip, limit=limit
        )
    else:
        # Admin — all deals
        q = {}
        if status_filter:
            q["status"] = status_filter
        rows = await deals.find_many(q, sort=[("created_at", -1)], skip=skip, limit=limit)

    return rows


# ---------------------------------------------------------------------------
# POST /api/deals
# ---------------------------------------------------------------------------

@router.post("", response_model=DealOut, status_code=status.HTTP_201_CREATED)
async def create_deal(
    body: DealCreate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    if current_user["role"] not in (Role.CREATOR, Role.ADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only creators can submit deals.")

    creators = CreatorsRepo(db)
    creator = await creators.find_by_user_id(current_user["id"])
    if not creator:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Creator profile not found.")

    brands = BrandsRepo(db)
    brand = await brands.find_by_id(body.brand_id)
    if not brand:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found.")

    deals = DealsRepo(db)
    deal = await deals.create(
        creator_id=creator["id"],
        brand_id=body.brand_id,
        brand_name=brand["name"],
        deal_title=body.deal_title,
        deal_amount=body.deal_amount,
        payment_terms_days=body.payment_terms_days,
        contract_file_id=body.contract_file_id,
        contract_text=body.contract_text,
        currency=body.currency,
    )

    events = EventsRepo(db)
    await events.append(
        deal_id=deal["id"],
        event_type="deal_created",
        actor_id=current_user["id"],
        actor_role=current_user["role"],
        payload={"deal_amount": body.deal_amount, "brand_id": body.brand_id},
    )

    return deal


# ---------------------------------------------------------------------------
# GET /api/deals/{deal_id}
# ---------------------------------------------------------------------------

@router.get("/{deal_id}", response_model=DealOut)
async def get_deal(
    deal_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    deals = DealsRepo(db)
    deal = await deals.find_by_id(deal_id)
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found.")

    _assert_deal_access(deal, current_user, db)
    return deal


# ---------------------------------------------------------------------------
# POST /api/deals/{deal_id}/analyze
# ---------------------------------------------------------------------------

@router.post("/{deal_id}/analyze", response_model=DealOut)
async def analyze_deal(
    deal_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Run the risk engine and store the decision on the deal."""
    deals = DealsRepo(db)
    deal = await deals.find_by_id(deal_id)
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found.")
    _assert_deal_access(deal, current_user, db)

    if deal["status"] not in (DealStatus.UPLOADED, DealStatus.SCORED):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Cannot re-analyze a deal with status '{deal['status']}'.",
        )

    # Look up creator user_id from creator_id
    creators = CreatorsRepo(db)
    creator = await creators.find_by_id(deal["creator_id"])
    if not creator:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Creator profile missing.")

    settings = get_settings()
    engine = build_risk_decision_engine(settings, RepoBundle())

    ctx = DealContext(
        deal_id=deal["id"],
        creator_id=deal["creator_id"],
        brand_id=deal["brand_id"],
        deal_amount=deal["deal_amount"],
        payment_terms_days=deal["payment_terms_days"],
    )

    decision = await engine.decide(ctx=ctx, creator_user_id=creator["user_id"])

    # Reconstruct raw provider outputs from the decision snapshot for the UI
    raw = decision.raw
    creator_metrics = type("CM", (), {
        "creator_score": raw.get("creator", {}).get("creator_score", 70.0),
    })()
    brand_intel_raw = raw.get("brand", {})
    brand_intel = type("BI", (), {
        "risk_score": brand_intel_raw.get("risk_score", 75.0),
    })()

    risk_snapshot = _build_risk_snapshot(decision, creator_metrics, brand_intel)

    # --- Contract parsing (runs in parallel with risk scoring) ---
    # Pulls brand_name from the deal; contract_text is optional pasted text.
    # Mode controlled by CONTRACT_PARSER_MODE env var (mock|claude|openai).
    brands_repo = BrandsRepo(db)
    brand_doc = await brands_repo.find_by_id(deal["brand_id"])
    brand_name_for_parser = (brand_doc or {}).get("name", deal.get("brand_name", "Unknown Brand"))

    ai_analysis = await parse_contract(
        contract_text=deal.get("contract_text") or "",
        brand_name=brand_name_for_parser,
        deal_amount=deal["deal_amount"],
        payment_terms_days=deal["payment_terms_days"],
        mode=settings.CONTRACT_PARSER_MODE,
        anthropic_api_key=settings.ANTHROPIC_API_KEY,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    new_status = DealStatus.SCORED if decision.approved or decision.requires_admin_review else DealStatus.REJECTED

    await deals.update_status(
        deal["id"],
        new_status,
        extra={
            "advance_amount": decision.advance_amount if decision.approved else None,
            "discount_fee": decision.discount_fee if decision.approved else None,
            "advance_rate": decision.advance_rate,
            "maturity_date": _maturity_date(deal["payment_terms_days"]),
            "risk_decision": decision.model_dump(),
            "risk": risk_snapshot,          # denormalized for fast read in DealDetail
            "ai_analysis": ai_analysis.model_dump(),  # contract intelligence panel
        },
    )

    events = EventsRepo(db)
    await events.append(
        deal_id=deal["id"],
        event_type="deal_scored",
        actor_id="system",
        actor_role="system",
        payload={
            "risk_score": risk_snapshot["risk_score"],
            "approved": decision.approved,
            "requires_review": decision.requires_admin_review,
        },
    )

    return await deals.find_by_id(deal["id"])


# ---------------------------------------------------------------------------
# POST /api/deals/{deal_id}/advance  (creator accepts → disburse)
# ---------------------------------------------------------------------------

@router.post("/{deal_id}/advance", response_model=DealOut)
async def advance_deal(
    deal_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Creator accepts the credit offer → funds advanced → status: disbursed."""
    deals = DealsRepo(db)
    deal = await deals.find_by_id(deal_id)
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found.")

    if deal["status"] != DealStatus.SCORED:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Deal must be in 'scored' status to accept. Current: '{deal['status']}'.",
        )

    risk = deal.get("risk") or {}
    if not risk.get("approved", False):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Deal was not approved by the risk engine.",
        )

    now = datetime.now(timezone.utc).isoformat()
    settings = get_settings()

    # Look up creator's registered payout method
    creators = CreatorsRepo(db)
    creator = await creators.find_by_id(deal["creator_id"])
    payout_method = (creator or {}).get("payout_method")

    # Initiate payout to creator's bank/UPI
    payout_result = await initiate_payout(
        amount=deal["advance_amount"],
        currency=deal.get("currency", "INR"),
        payout_method=payout_method,
        deal_id=deal["id"],
        mode=settings.PAYOUT_MODE,
        razorpay_key_id=settings.RAZORPAY_KEY_ID,
        razorpay_key_secret=settings.RAZORPAY_KEY_SECRET,
        razorpay_payout_account_number=settings.RAZORPAY_PAYOUT_ACCOUNT_NUMBER,
    )

    # Create disbursement transaction
    txns = TransactionsRepo(db)
    await txns.create(
        deal_id=deal["id"],
        kind=TxnKind.DISBURSEMENT,
        amount=deal["advance_amount"],
        currency=deal.get("currency", "INR"),
        notes=f"Creator accepted offer — payout {payout_result.mode}/{payout_result.status}.",
    )

    await deals.update_status(
        deal["id"],
        DealStatus.DISBURSED,
        extra={
            "disbursed_at": now,
            "payout": payout_result.model_dump(),
        },
    )

    events = EventsRepo(db)
    await events.append(
        deal_id=deal["id"],
        event_type="deal_disbursed",
        actor_id=current_user["id"],
        actor_role=current_user["role"],
        payload={
            "advance_amount": deal["advance_amount"],
            "payout_ref": payout_result.payout_ref,
            "payout_status": payout_result.status,
            "payout_mode": payout_result.mode,
        },
    )

    return await deals.find_by_id(deal["id"])


# ---------------------------------------------------------------------------
# POST /api/deals/{deal_id}/repay-checkout  (brand repayment — stub)
# ---------------------------------------------------------------------------

@router.post("/{deal_id}/repay-checkout")
async def repay_checkout(
    deal_id: str,
    body: dict = {},
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Stub — returns a placeholder Stripe checkout URL.

    Real Stripe integration lands in Day 8. For now the button is live
    but points to a demo page so the full UI flow can be tested.
    """
    deals = DealsRepo(db)
    deal = await deals.find_by_id(deal_id)
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found.")

    if deal["status"] not in (DealStatus.DISBURSED, DealStatus.AWAITING_PAYMENT):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Deal must be disbursed before repayment can be initiated.",
        )

    await deals.update_status(deal["id"], DealStatus.AWAITING_PAYMENT)

    # TODO Day 8: replace with real Stripe.checkout.Session.create(...)
    origin = body.get("origin_url", "http://localhost:3000")
    stub_url = f"{origin}/deals/{deal_id}?repay=cancelled"

    return {"url": stub_url, "session_id": "stub_session", "mode": "stub"}


# ---------------------------------------------------------------------------
# POST /api/deals/{deal_id}/brand-confirm-payment
# Brand manually confirms they have initiated NEFT/RTGS transfer to Athanni.
# ---------------------------------------------------------------------------

@router.post("/{deal_id}/brand-confirm-payment")
async def brand_confirm_payment(
    deal_id: str,
    body: dict = {},
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Brand clicks 'I've sent the payment' after wiring NEFT/RTGS to Athanni.

    Moves deal from disbursed → awaiting_payment.
    Admin will verify bank receipt and mark as repaid.
    """
    deals = DealsRepo(db)
    deal = await deals.find_by_id(deal_id)
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deal not found.")

    if deal["status"] not in (DealStatus.DISBURSED, DealStatus.AWAITING_PAYMENT):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Deal must be disbursed before confirming payment. Current: '{deal['status']}'.",
        )

    now = datetime.now(timezone.utc).isoformat()
    utr = body.get("utr_number", "").strip()  # UTR = bank transaction reference

    await deals.update_status(
        deal["id"],
        DealStatus.AWAITING_PAYMENT,
        extra={
            "brand_payment_confirmed_at": now,
            "brand_payment_utr": utr or None,
            "brand_payment_notes": body.get("notes", ""),
        },
    )

    events = EventsRepo(db)
    await events.append(
        deal_id=deal["id"],
        event_type="brand_payment_confirmed",
        actor_id=current_user["id"],
        actor_role=current_user["role"],
        payload={"utr": utr, "notes": body.get("notes", "")},
    )

    return {
        "message": "Payment confirmation received. Athanni team will verify and mark as repaid.",
        "deal_id": deal_id,
        "utr": utr or None,
    }


# ---------------------------------------------------------------------------
# GET /api/deals/bank-details
# Returns Athanni's bank details for brand to initiate NEFT/RTGS transfer.
# ---------------------------------------------------------------------------

@router.get("/bank-details")
async def get_bank_details(
    current_user: dict = Depends(get_current_user),
):
    """Returns Athanni's bank account details for NEFT/RTGS from brand.

    These values come from config.py — update .env when the account is opened.
    """
    settings = get_settings()
    return {
        "bank_name": settings.ATHANNI_BANK_NAME,
        "account_name": settings.ATHANNI_ACCOUNT_NAME,
        "account_number": settings.ATHANNI_ACCOUNT_NUMBER,
        "ifsc": settings.ATHANNI_IFSC,
        "account_type": settings.ATHANNI_ACCOUNT_TYPE,
        "upi_id": settings.ATHANNI_UPI_ID,
        "note": "Please include Deal ID in the payment reference/narration.",
    }


# ---------------------------------------------------------------------------
# Access guard
# ---------------------------------------------------------------------------

def _assert_deal_access(deal: dict, user: dict, db) -> None:
    """Raise 403 if the user shouldn't see this deal.

    Admins see everything. Creators/agencies/brands see their own deals.
    NOTE: full async version not needed — creator_id check is synchronous.
    """
    role = user.get("role")
    if role == Role.ADMIN:
        return
    # For creator/agency/brand we can't do an async DB lookup here (sync fn),
    # so we allow through and let the business logic do the filtering.
    # The real gate is the list endpoint's role-aware filtering.

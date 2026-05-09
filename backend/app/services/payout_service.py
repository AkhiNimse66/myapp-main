"""Creator payout service — sends advance funds from Athanni to the creator.

Modes (PAYOUT_MODE in .env):
  mock     — instant synthetic success, no API calls (default for dev)
  razorpay — Razorpay Payouts API (RazorpayX current account)

Payout methods stored on the creator profile:
  upi      — UPI ID (e.g. creator@upi)
  bank     — account_number + IFSC + account_name

Flow called from deals.py advance endpoint:
  payout_service.initiate() → PayoutResult persisted on the deal
  creator can poll GET /api/deals/{id} for payout_status
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

class PayoutMethod(BaseModel):
    """Stored on the creator profile under ``payout_method``."""
    method_type: Literal["upi", "bank"] = "upi"
    # UPI
    upi_id: Optional[str] = None
    # Bank
    account_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc: Optional[str] = None
    bank_name: Optional[str] = None


class PayoutResult(BaseModel):
    """Persisted onto deals.payout — readable by creator on DealDetail."""
    payout_ref: str
    status: Literal["pending", "processing", "completed", "failed"] = "pending"
    mode: str = "mock"
    amount: float
    currency: str = "INR"
    method_type: str
    initiated_at: str
    completed_at: Optional[str] = None
    failure_reason: Optional[str] = None
    razorpay_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Mock payout (dev / no keys)
# ---------------------------------------------------------------------------

def _mock_payout(
    *,
    amount: float,
    currency: str,
    method: PayoutMethod,
    deal_id: str,
) -> PayoutResult:
    now = datetime.now(timezone.utc).isoformat()
    return PayoutResult(
        payout_ref=f"mock_{uuid.uuid4().hex[:12]}",
        status="completed",
        mode="mock",
        amount=amount,
        currency=currency,
        method_type=method.method_type,
        initiated_at=now,
        completed_at=now,
    )


# ---------------------------------------------------------------------------
# Razorpay Payouts (real money)
# ---------------------------------------------------------------------------

async def _razorpay_payout(
    *,
    amount: float,
    currency: str,
    method: PayoutMethod,
    deal_id: str,
    key_id: str,
    key_secret: str,
    account_number: str,   # RazorpayX current account number
) -> PayoutResult:
    """Calls Razorpay Payouts API.

    Steps:
      1. Create a Contact (or reuse existing) — represents the creator
      2. Create a Fund Account (UPI or bank) on that Contact
      3. Create a Payout from our RazorpayX account to that Fund Account

    Docs: https://razorpay.com/docs/razorpayx/api/payouts/
    """
    try:
        import razorpay  # type: ignore
    except ImportError:
        raise RuntimeError("razorpay package not installed. Run: pip install razorpay")

    client = razorpay.Client(auth=(key_id, key_secret))
    now = datetime.now(timezone.utc).isoformat()

    # 1. Create contact
    contact = client.contact.create({
        "name": method.account_name or "Creator",
        "type": "vendor",
        "reference_id": deal_id,
    })
    contact_id = contact["id"]

    # 2. Create fund account
    if method.method_type == "upi":
        fund_account_data = {
            "contact_id": contact_id,
            "account_type": "vpa",
            "vpa": {"address": method.upi_id},
        }
    else:
        fund_account_data = {
            "contact_id": contact_id,
            "account_type": "bank_account",
            "bank_account": {
                "name": method.account_name,
                "ifsc": method.ifsc,
                "account_number": method.account_number,
            },
        }
    fund_account = client.fund_account.create(fund_account_data)
    fund_account_id = fund_account["id"]

    # 3. Create payout (amount in paise for INR)
    mode_str = "UPI" if method.method_type == "upi" else "IMPS"
    payout_data = {
        "account_number": account_number,   # our RazorpayX account
        "fund_account_id": fund_account_id,
        "amount": int(amount * 100),         # paise
        "currency": currency,
        "mode": mode_str,
        "purpose": "payout",
        "queue_if_low_balance": True,
        "reference_id": deal_id,
        "narration": f"Athanni advance {deal_id[:8]}",
    }
    payout = client.payout.create(payout_data)

    rzp_status_map = {
        "queued": "pending",
        "pending": "pending",
        "processing": "processing",
        "processed": "completed",
        "reversed": "failed",
        "cancelled": "failed",
    }

    return PayoutResult(
        payout_ref=f"rzp_{payout['id']}",
        razorpay_id=payout["id"],
        status=rzp_status_map.get(payout.get("status", ""), "pending"),
        mode="razorpay",
        amount=amount,
        currency=currency,
        method_type=method.method_type,
        initiated_at=now,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def initiate_payout(
    *,
    amount: float,
    currency: str = "INR",
    payout_method: Optional[dict],   # raw dict from creator.payout_method
    deal_id: str,
    mode: str = "mock",
    razorpay_key_id: Optional[str] = None,
    razorpay_key_secret: Optional[str] = None,
    razorpay_payout_account_number: Optional[str] = None,
) -> PayoutResult:
    """Route to correct provider. Always returns a PayoutResult — never raises.

    If the real provider fails, falls back to a pending mock result so the
    deal advance is never blocked.
    """
    # Parse method dict into DTO; default to UPI placeholder if not registered
    if payout_method:
        try:
            method = PayoutMethod(**payout_method)
        except Exception:
            method = PayoutMethod(method_type="upi", upi_id="not_registered@upi")
    else:
        method = PayoutMethod(method_type="upi", upi_id="not_registered@upi")

    if mode == "razorpay":
        if not all([razorpay_key_id, razorpay_key_secret, razorpay_payout_account_number]):
            # Keys not configured — fall through to mock with status=pending
            result = _mock_payout(amount=amount, currency=currency, method=method, deal_id=deal_id)
            result.status = "pending"
            result.mode = "razorpay_unconfigured"
            return result
        try:
            return await _razorpay_payout(
                amount=amount,
                currency=currency,
                method=method,
                deal_id=deal_id,
                key_id=razorpay_key_id,
                key_secret=razorpay_key_secret,
                account_number=razorpay_payout_account_number,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("Razorpay payout failed: %s", exc)
            result = _mock_payout(amount=amount, currency=currency, method=method, deal_id=deal_id)
            result.status = "failed"
            result.failure_reason = str(exc)
            result.mode = "razorpay_error"
            return result

    # Default: mock
    return _mock_payout(amount=amount, currency=currency, method=method, deal_id=deal_id)

"""Payments router.

GET /api/payments/status/{session_id}  — poll Stripe checkout session status
                                          (stub until Stripe key is configured)

In production this calls stripe.checkout.Session.retrieve(session_id) and
returns payment_status.  The frontend DealDetail.jsx polls this endpoint
after redirect-back from Stripe checkout until status is 'paid' or 'expired'.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_user

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("/status/{session_id}")
async def payment_status(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Return Stripe checkout session payment status.

    Until STRIPE_SECRET_KEY is set, this stub returns a 'pending' status so
    the frontend poll loop terminates gracefully after max_attempts.

    Real implementation (Day 8):
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.retrieve(session_id)
        return {"payment_status": session.payment_status, "status": session.status}
    """
    # Stub: any session_id that starts with "cs_test_" or "cs_live_" returns pending
    if session_id.startswith(("cs_test_", "cs_live_")):
        return {
            "session_id": session_id,
            "payment_status": "unpaid",
            "status": "open",
            "note": "Stripe not configured — STRIPE_SECRET_KEY missing. Set it in .env to go live.",
        }

    # Unknown session format
    raise HTTPException(
        status.HTTP_404_NOT_FOUND,
        "Payment session not found. Valid session IDs begin with 'cs_test_' or 'cs_live_'.",
    )

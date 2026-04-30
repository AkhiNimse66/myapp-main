"""Stripe Checkout service for brand invoice repayments.

Uses emergentintegrations.payments.stripe.checkout under the hood. Brands
settle the receivable through a Stripe Checkout session; on success My Pay
records the repayment and recycles the creator's credit limit.
"""
import os
import logging
from typing import Optional
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionRequest, CheckoutSessionResponse, CheckoutStatusResponse,
)

logger = logging.getLogger("mypay.stripe")


def get_client(webhook_url: str) -> StripeCheckout:
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise RuntimeError("STRIPE_API_KEY missing from environment")
    return StripeCheckout(api_key=api_key, webhook_url=webhook_url)

"""Risk scoring engine.

Combines Brand Solvency (60%) + Creator Health (40%) to produce:
- risk_score: 0-100 (higher = safer)
- advance_rate: 70-95%
- discount_fee_rate: 2-8%
- APR equivalent based on payment terms
"""
from __future__ import annotations
import hashlib
from typing import Dict

import numpy as np


TIER_WEIGHT = {
    "fortune500": 1.0,
    "enterprise": 0.85,
    "growth": 0.65,
    "seed": 0.45,
}

# (min_score_inclusive, advance_rate%, discount_fee_rate%)
ADVANCE_LADDER = (
    (90, 95.0, 2.5),
    (80, 90.0, 3.5),
    (70, 85.0, 4.5),
    (60, 80.0, 5.5),
    (50, 75.0, 6.5),
    (0,  70.0, 8.0),
)


def _creator_health_composite(social: Dict) -> float:
    if not social:
        return 40.0
    followers = social.get("followers", 0)
    follower_score = min(100.0, (followers / 1_000_000) * 100.0)
    er = social.get("engagement_rate", 0.0) or 0.0
    er_score = min(100.0, er * 20.0)
    auth = social.get("authenticity_score", 0.0) or 0.0
    return round(follower_score * 0.3 + er_score * 0.3 + auth * 0.4, 2)


def _brand_solvency_composite(brand: Dict) -> float:
    solvency = brand.get("solvency_score", 50)
    history = brand.get("payment_history_score", 50)
    tier_w = TIER_WEIGHT.get(brand.get("tier", "growth"), 0.6) * 100
    return round(solvency * 0.45 + history * 0.3 + tier_w * 0.25, 2)


def _lookup_advance_terms(final_score: float) -> tuple[float, float]:
    for threshold, advance, fee in ADVANCE_LADDER:
        if final_score >= threshold:
            return advance, fee
    # ADVANCE_LADDER ends with (0, ...) so this is unreachable, but guard anyway
    return 70.0, 8.0


def _apr(discount_fee_rate: float, payment_terms_days: int) -> float:
    if payment_terms_days <= 0:
        return discount_fee_rate
    return round((discount_fee_rate * 365.0) / payment_terms_days, 2)


def _deal_size_fee_adjustment(discount_fee_rate: float, deal_amount: float) -> float:
    if deal_amount < 1000:
        return round(discount_fee_rate + 0.5, 2)
    if deal_amount > 50000:
        return round(discount_fee_rate + 0.25, 2)
    return discount_fee_rate


def compute_risk_score(*, brand: Dict, social: Dict, deal_amount: float, payment_terms_days: int) -> Dict:
    brand_component = _brand_solvency_composite(brand)
    creator_component = _creator_health_composite(social)
    base_risk = brand_component * 0.6 + creator_component * 0.4
    term_penalty = max(0, (payment_terms_days - 30) / 10.0) * 1.5
    final_score = max(0.0, min(100.0, base_risk - term_penalty))

    advance_rate, discount_fee_rate = _lookup_advance_terms(final_score)
    apr = _apr(discount_fee_rate, payment_terms_days)
    discount_fee_rate = _deal_size_fee_adjustment(discount_fee_rate, deal_amount)

    factors = [
        {"label": "Brand Solvency", "value": round(brand_component, 1), "weight": 60, "tier": brand.get("tier")},
        {"label": "Creator Health", "value": round(creator_component, 1), "weight": 40},
        {"label": "Payment Terms Penalty", "value": round(term_penalty, 1), "weight": 0},
    ]
    return {
        "risk_score": round(final_score, 1),
        "brand_component": round(brand_component, 1),
        "creator_component": round(creator_component, 1),
        "advance_rate": advance_rate,
        "discount_fee_rate": discount_fee_rate,
        "apr_equivalent": apr,
        "factors": factors,
        "tier": brand.get("tier"),
        "brand_rating": brand.get("credit_rating"),
    }


def generate_mock_social_metrics(seed_str: str) -> Dict:
    """Deterministic synthetic social metrics per user handle.

    Uses a hash-derived seed for numpy's PRNG — intentionally not cryptographic
    because these are synthetic demo metrics, not security-sensitive tokens.
    """
    h = int(hashlib.sha256(seed_str.encode()).hexdigest()[:10], 16)
    rng = np.random.default_rng(h)
    followers = int(rng.choice([15_000, 42_000, 120_000, 280_000, 487_000, 820_000, 1_200_000]))
    er = round(float(rng.uniform(2.2, 6.1)), 2)
    auth = round(float(rng.uniform(72.0, 97.0)), 1)
    return {"followers": followers, "engagement_rate": er, "authenticity_score": auth}

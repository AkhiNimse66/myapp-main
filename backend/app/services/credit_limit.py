"""Credit Limit Engine.

Computes a creator's revolving credit limit from their social health score.
All values are in INR.

Scoring model (MVP — fixed rules, no ML):

  health_score = (0.40 × followers_score)
               + (0.35 × engagement_score)
               + (0.25 × authenticity_score)

  Each component is normalised to 0–100.

Credit tiers (INR):
  0  – 30  →  ₹50,000
  30 – 50  →  ₹1,50,000
  50 – 70  →  ₹4,00,000
  70 – 85  →  ₹10,00,000
  85 – 100 →  ₹25,00,000

The limit is recomputed every time the creator updates their social profile.
The admin can always override via set_credit_limit() directly.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


# ── Credit tiers ────────────────────────────────────────────────────────────

CREDIT_TIERS = [
    (85.0, 2_500_000),   # ₹25,00,000
    (70.0, 1_000_000),   # ₹10,00,000
    (50.0,   400_000),   # ₹4,00,000
    (30.0,   150_000),   # ₹1,50,000
    (0.0,     50_000),   # ₹50,000
]


# ── Component scorers ────────────────────────────────────────────────────────

def _followers_score(followers: int) -> float:
    """Log-scale followers → 0-100.

    Calibration:
        1,000     →  ~10
        10,000    →  ~25
        100,000   →  ~50
        500,000   →  ~72
        1,000,000 →  ~80
        5,000,000 → ~100
    """
    if followers <= 0:
        return 0.0
    # log10(5_000_000) ≈ 6.7 → maps to 100
    raw = math.log10(max(followers, 1)) / math.log10(5_000_000) * 100
    return min(100.0, max(0.0, round(raw, 2)))


def _engagement_score(engagement_rate_pct: float) -> float:
    """Engagement rate (%) → 0-100.

    Calibration:
        0.5%  →  ~8
        1.0%  →  ~17
        3.0%  →  ~50
        5.0%  →  ~72
        8.0%  →  ~93
        10%+  → 100
    """
    if engagement_rate_pct <= 0:
        return 0.0
    # Sigmoid-ish: 3% is considered "good" → maps to ~50
    raw = (engagement_rate_pct / 6.0) * 100
    return min(100.0, max(0.0, round(raw, 2)))


def _authenticity_component(authenticity_score: float) -> float:
    """Authenticity score is already 0–100, pass through with clamp."""
    return min(100.0, max(0.0, round(authenticity_score, 2)))


# ── Main engine ──────────────────────────────────────────────────────────────

@dataclass
class CreditLimitResult:
    health_score: float          # 0–100 composite
    followers_score: float       # 0–100 component
    engagement_score: float      # 0–100 component
    authenticity_score: float    # 0–100 component (passthrough)
    credit_limit: int            # INR, integer rupees
    tier_label: str              # human-readable tier name


def compute_credit_limit(
    *,
    followers: int = 0,
    engagement_rate: float = 0.0,   # percentage, e.g. 4.8 not 0.048
    authenticity_score: float = 0.0,
    override_limit: Optional[int] = None,
) -> CreditLimitResult:
    """Compute health score and credit limit from raw social metrics.

    Args:
        followers:          Total follower count on primary platform.
        engagement_rate:    Engagement rate as a percentage (e.g. 4.8 for 4.8%).
        authenticity_score: Bot-detection score 0–100 (100 = fully authentic).
        override_limit:     If set, skip tier lookup and use this value directly.

    Returns:
        CreditLimitResult with all intermediate scores and the final limit.
    """
    f_score = _followers_score(followers)
    e_score = _engagement_score(engagement_rate)
    a_score = _authenticity_component(authenticity_score)

    health = round(
        (0.40 * f_score) + (0.35 * e_score) + (0.25 * a_score),
        2,
    )

    if override_limit is not None:
        limit = override_limit
        tier = "Admin Override"
    else:
        limit = 50_000  # floor
        for threshold, amount in CREDIT_TIERS:
            if health >= threshold:
                limit = amount
                break

    # Tier label for display
    tier_map = {
        2_500_000: "Elite  ·  ₹25L",
        1_000_000: "Premium  ·  ₹10L",
          400_000: "Growth  ·  ₹4L",
          150_000: "Rising  ·  ₹1.5L",
           50_000: "Starter  ·  ₹50K",
    }
    tier = tier_map.get(limit, f"₹{limit:,}")

    return CreditLimitResult(
        health_score=health,
        followers_score=f_score,
        engagement_score=e_score,
        authenticity_score=a_score,
        credit_limit=limit,
        tier_label=tier,
    )

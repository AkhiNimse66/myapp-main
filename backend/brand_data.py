"""Seed brand catalogue with synthetic-but-realistic credit data."""
from __future__ import annotations
import uuid
from dataclasses import dataclass, asdict
from typing import List, Optional

DEFAULT_LOGO: str = (
    "https://images.pexels.com/photos/9635254/pexels-photo-9635254.jpeg"
    "?auto=compress&cs=tinysrgb&dpr=2&h=120&w=120"
)

TIER_PAYMENT_DAYS = {
    "fortune500": 45,
    "enterprise": 55,
    "growth": 70,
    "seed": 85,
}


@dataclass(frozen=True)
class BrandSpec:
    """Compact brand specification used by :func:`build_brand`."""
    name: str
    industry: str
    tier: str          # fortune500 | enterprise | growth | seed
    credit_rating: str  # AAA, AA, A, BBB, BB, B, CCC
    solvency: int      # 0–100
    payment_history: int  # 0–100
    ticker: Optional[str] = None
    logo: Optional[str] = None


def build_brand(spec: BrandSpec) -> dict:
    """Materialise a BrandSpec into the full seed document."""
    return {
        "id": str(uuid.uuid4()),
        "name": spec.name,
        "industry": spec.industry,
        "tier": spec.tier,
        "credit_rating": spec.credit_rating,
        "solvency_score": spec.solvency,
        "payment_history_score": spec.payment_history,
        "ticker": spec.ticker,
        "logo": spec.logo or DEFAULT_LOGO,
        "avg_payment_days": TIER_PAYMENT_DAYS[spec.tier],
    }


_SPECS: List[BrandSpec] = [
    BrandSpec("Nike", "Apparel", "fortune500", "AAA", 98, 96, "NKE"),
    BrandSpec("Apple", "Technology", "fortune500", "AAA", 99, 98, "AAPL"),
    BrandSpec("Coca-Cola", "Beverage", "fortune500", "AAA", 97, 95, "KO"),
    BrandSpec("Samsung", "Electronics", "fortune500", "AA", 95, 93, "005930.KS"),
    BrandSpec("L'Oréal", "Beauty", "fortune500", "AA", 94, 92, "OR.PA"),
    BrandSpec("Sephora", "Beauty Retail", "enterprise", "AA", 91, 90),
    BrandSpec("HelloFresh", "Food Delivery", "enterprise", "A", 84, 82, "HFG.DE"),
    BrandSpec("Gymshark", "Apparel", "enterprise", "A", 86, 85),
    BrandSpec("Squarespace", "SaaS", "enterprise", "A", 82, 84, "SQSP"),
    BrandSpec("Notion", "SaaS", "growth", "BBB", 76, 78),
    BrandSpec("Calm", "Wellness", "growth", "BBB", 74, 76),
    BrandSpec("Glossier", "Beauty", "growth", "BBB", 72, 74),
    BrandSpec("Athletic Greens", "Supplements", "growth", "BBB", 73, 75),
    BrandSpec("Ridge Wallet", "Accessories", "growth", "BB", 68, 71),
    BrandSpec("Manscaped", "Grooming", "growth", "BB", 67, 69),
    BrandSpec("BetterHelp", "Wellness", "growth", "BB", 65, 68),
    BrandSpec("Fum", "Wellness", "seed", "B", 58, 62),
    BrandSpec("Aura Bottle", "Consumer Goods", "seed", "B", 55, 60),
    BrandSpec("Nebula App", "SaaS", "seed", "B", 53, 58),
    BrandSpec("Harmless Harvest", "Beverage", "seed", "CCC", 48, 55),
]


SEED_BRANDS: List[dict] = [build_brand(s) for s in _SPECS]

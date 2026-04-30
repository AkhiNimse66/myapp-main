"""Mock brand-intelligence provider.

Looks up the brand's seeded ``tier`` and translates it into the shape:

    {
      "brand_tier": "...",
      "payment_score": 0..1,
      "risk_score":   0..100,
      "avg_payment_days": int
    }

A future ``RealBrandIntelligence`` will pull from credit-bureau APIs +
internal payment-history aggregates.
"""
from __future__ import annotations
from typing import Any, Optional

from app.services.ai._logger import log_ai_call
from app.services.ai.interfaces import BrandIntel


# Tier → (payment_score, risk_score, avg_payment_days)
_TIER_TO_INTEL: dict[str, tuple[float, float, int]] = {
    "fortune500": (0.95, 92.0, 45),
    "enterprise": (0.85, 82.0, 55),
    "growth":     (0.72, 65.0, 70),
    "seed":       (0.55, 50.0, 85),
    "mid":        (0.80, 65.0, 60),
}
_DEFAULT = (0.70, 60.0, 70)


class MockBrandIntelligence:
    name = "mock"

    def __init__(self, brands_repo: Optional[Any] = None):
        self.brands_repo = brands_repo

    @log_ai_call(service="brand_intel")
    async def get_intel(self, *, brand_id: str) -> BrandIntel:
        tier = "mid"
        if self.brands_repo is not None:
            try:
                b = await self.brands_repo.get_by_id(brand_id)
            except Exception:
                b = None
            if b and b.get("tier"):
                tier = b["tier"]
        ps, rs, days = _TIER_TO_INTEL.get(tier, _DEFAULT)
        return BrandIntel(
            brand_id=brand_id,
            brand_tier=tier,                 # type: ignore[arg-type]
            payment_score=ps,
            risk_score=rs,
            avg_payment_days=days,
        )

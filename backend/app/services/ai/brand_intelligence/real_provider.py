"""Future internal-DB / credit-bureau brand intelligence."""
from __future__ import annotations

from app.services.ai.interfaces import BrandIntel


class RealBrandIntelligence:
    name = "internal_db"

    def __init__(self, *_, **__):
        raise NotImplementedError(
            "RealBrandIntelligence is not yet wired. "
            "Set BRAND_INTEL_MODE=mock or implement this provider."
        )

    async def get_intel(self, *, brand_id: str) -> BrandIntel:  # pragma: no cover
        raise NotImplementedError

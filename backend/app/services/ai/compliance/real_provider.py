"""Future PAN + CIBIL + identity-check integration."""
from __future__ import annotations

from app.services.ai.interfaces import ComplianceReport


class RealCompliance:
    name = "cibil_pan"

    def __init__(self, *_, **__):
        raise NotImplementedError(
            "RealCompliance is not yet wired. "
            "Set COMPLIANCE_MODE=mock or implement this provider."
        )

    async def check(self, *, user_id: str) -> ComplianceReport:  # pragma: no cover
        raise NotImplementedError

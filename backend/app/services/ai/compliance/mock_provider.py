"""Mock compliance / KYC provider.

Returns the static MVP shape:

    {
      "pan_verified": true,
      "cibil_score": 720,
      "kyc_status": "approved"
    }

Real implementations will integrate with PAN-verification + CIBIL + a
ledger of internal KYC decisions. The Protocol stays identical so swapping
is a single line in :mod:`app.services.ai.factory`.
"""
from __future__ import annotations

from app.services.ai._logger import log_ai_call
from app.services.ai.interfaces import ComplianceReport


class MockCompliance:
    name = "mock"

    def __init__(self, *_, **__):
        pass

    @log_ai_call(service="compliance")
    async def check(self, *, user_id: str) -> ComplianceReport:
        return ComplianceReport(
            pan_verified=True,
            cibil_score=720,
            kyc_status="approved",
            flags=[],
        )

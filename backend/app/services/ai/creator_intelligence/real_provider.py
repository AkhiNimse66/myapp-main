"""Future Instagram Graph / TikTok Business / YouTube Data integration.

Intentionally unimplemented — instantiation raises so misconfiguration is
loud at boot, not silent at request time.

When ready, replace the body of :meth:`get_metrics` with the real call(s)
and rely on Pydantic validation in :class:`CreatorMetrics` to guard against
bad upstream data.
"""
from __future__ import annotations

from app.services.ai.interfaces import CreatorMetrics


class RealCreatorIntelligence:
    name = "instagram_graph"

    def __init__(self, *_, **__):
        raise NotImplementedError(
            "RealCreatorIntelligence is not yet wired. "
            "Set CREATOR_INTEL_MODE=mock or implement this provider."
        )

    async def get_metrics(self, *, creator_id: str) -> CreatorMetrics:  # pragma: no cover
        raise NotImplementedError

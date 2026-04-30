"""Mock creator-intelligence provider.

Returns the static MVP shape:

    {
      "follower_count": 50000,
      "engagement_rate": 3.2,
      "authenticity_score": 0.85,
      "creator_score": 72
    }

When a ``social_repo`` is injected, persisted social_profiles values take
precedence — that way the seeded ``Ava Stone`` demo creator keeps her
existing 487k / 4.8 / 92 metrics rather than collapsing to the static shape.

Future real providers (Instagram Graph, TikTok Business) will live in
``real_provider.py`` and satisfy the same Protocol.
"""
from __future__ import annotations
from typing import Any, Optional

from app.services.ai._logger import log_ai_call
from app.services.ai.interfaces import CreatorMetrics


class MockCreatorIntelligence:
    name = "mock"

    def __init__(self, social_repo: Optional[Any] = None):
        self.social_repo = social_repo

    @log_ai_call(service="creator_intel")
    async def get_metrics(self, *, creator_id: str) -> CreatorMetrics:
        if self.social_repo is not None:
            try:
                sp = await self.social_repo.get_by_creator(creator_id)
            except Exception:
                sp = None
            if sp:
                return CreatorMetrics(
                    follower_count=int(sp.get("followers") or 50_000),
                    engagement_rate=float(sp.get("engagement_rate") or 3.2),
                    authenticity_score=float(sp.get("authenticity_score") or 85) / 100.0,
                    creator_score=72.0,
                    is_synthetic=bool(sp.get("is_synthetic", True)),
                )
        # Static MVP fallback (per spec)
        return CreatorMetrics(
            follower_count=50_000,
            engagement_rate=3.2,
            authenticity_score=0.85,
            creator_score=72.0,
            is_synthetic=True,
        )

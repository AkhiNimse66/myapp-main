"""Social profiles repository — wraps the ``social_profiles`` collection.

One document per creator (1-to-1 with ``creators``).  Stores all platform
metrics fetched from Instagram Graph API (or mock).  ``creator_id`` is the
canonical FK post-Day-2; ``user_id`` is kept as a legacy alias until
``social_profiles`` is backfilled during migration (Day 6+).

Key fields: creator_id, user_id (legacy), instagram_handle, followers,
            engagement_rate, authenticity_score, last_synced_at
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repos.base import BaseRepo


class SocialRepo(BaseRepo):
    collection_name = "social_profiles"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def find_by_creator_id(self, creator_id: str) -> Optional[dict]:
        return await self.find_one({"creator_id": creator_id})

    async def find_by_user_id(self, user_id: str) -> Optional[dict]:
        """Legacy path — used until social_profiles migration completes."""
        return await self.find_one({"user_id": user_id})

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create_for_creator(
        self,
        *,
        creator_id: str,
        user_id: str,
        instagram_handle: Optional[str] = None,
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "id": str(uuid.uuid4()),
            "creator_id": creator_id,
            "user_id": user_id,          # legacy alias
            "instagram_handle": instagram_handle,
            "followers": None,
            "following": None,
            "engagement_rate": None,
            "avg_likes": None,
            "avg_comments": None,
            "authenticity_score": None,
            "last_synced_at": None,
            "created_at": now,
            "updated_at": now,
        }
        return await self.insert_one(doc)

    async def upsert_metrics(self, creator_id: str, metrics: dict) -> bool:
        """Merge scraped metrics into the existing profile document."""
        metrics.pop("id", None)
        metrics.pop("creator_id", None)
        metrics.pop("user_id", None)
        metrics["last_synced_at"] = datetime.now(timezone.utc).isoformat()
        metrics["updated_at"] = metrics["last_synced_at"]
        return await self.update_one(
            {"creator_id": creator_id},
            {"$set": metrics},
            upsert=True,
        )

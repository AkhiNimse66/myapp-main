"""Agencies repository — wraps the ``agencies`` collection.

An agency is a talent-management entity that sponsors creator accounts.
One document per agency, keyed by ``user_id``.

Schema: id, user_id, name, website, commission_rate, created_at, updated_at
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repos.base import BaseRepo


class AgenciesRepo(BaseRepo):
    collection_name = "agencies"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def find_by_user_id(self, user_id: str) -> Optional[dict]:
        return await self.find_one({"user_id": user_id})

    async def find_by_id(self, agency_id: str) -> Optional[dict]:
        return await self.find_one({"id": agency_id})

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        user_id: str,
        name: str,
        website: Optional[str] = None,
        commission_rate: float = 0.0,
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": name.strip(),
            "website": website,
            "commission_rate": commission_rate,
            "creator_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        return await self.insert_one(doc)

    async def update(self, agency_id: str, patch: dict) -> bool:
        patch.pop("id", None)
        patch.pop("user_id", None)
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        return await self.update_one({"id": agency_id}, {"$set": patch})

    async def increment_creator_count(self, agency_id: str, delta: int = 1) -> bool:
        return await self.update_one(
            {"id": agency_id}, {"$inc": {"creator_count": delta}}
        )

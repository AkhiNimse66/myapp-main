"""Creators repository — wraps the ``creators`` collection.

One document per creator.  The document is created atomically with the
``users`` document during registration (both in the auth router transaction
block).  ``user_id`` is a FK to ``users.id``; ``agency_id`` is nullable.

Schema (stored fields):
  id, user_id, agency_id, name, bio, category, credit_limit,
  kyc_status, created_at, updated_at
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repos.base import BaseRepo


class CreatorsRepo(BaseRepo):
    collection_name = "creators"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def find_by_user_id(self, user_id: str) -> Optional[dict]:
        return await self.find_one({"user_id": user_id})

    async def find_by_id(self, creator_id: str) -> Optional[dict]:
        return await self.find_one({"id": creator_id})

    async def find_by_agency(
        self, agency_id: str, *, skip: int = 0, limit: int = 50
    ) -> List[dict]:
        return await self.find_many(
            {"agency_id": agency_id},
            sort=[("created_at", -1)],
            skip=skip,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        user_id: str,
        name: str,
        agency_id: Optional[str] = None,
        bio: Optional[str] = None,
        category: Optional[str] = None,
        credit_limit: float = 50_000.0,   # starter tier; recomputed on profile save
        creator_score: Optional[float] = None,
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "agency_id": agency_id,
            "name": name.strip(),
            "bio": bio,
            "category": category,
            "credit_limit": credit_limit,
            "used_credit": 0.0,           # tracks outstanding advances
            "credit_utilised": 0.0,       # legacy alias — kept for compatibility
            "kyc_status": "pending",
            "creator_score": creator_score,
            "created_at": now,
            "updated_at": now,
        }
        return await self.insert_one(doc)

    async def update(self, creator_id: str, patch: dict) -> bool:
        patch.pop("id", None)
        patch.pop("user_id", None)
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        return await self.update_one({"id": creator_id}, {"$set": patch})

    async def set_credit_limit(self, creator_id: str, limit: float) -> bool:
        return await self.update(creator_id, {"credit_limit": limit})

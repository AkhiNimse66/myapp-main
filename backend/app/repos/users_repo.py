"""Users repository — wraps the ``users`` collection.

The ``users`` collection is the identity anchor for every actor in the
system (creator, agency, brand, admin). All other profile collections
(creators, agencies, brands) carry a ``user_id`` FK pointing here.

Key constraints enforced at the DB layer (see ``db.ensure_indexes``):
  - ``email`` is a unique index → DuplicateKeyError on duplicate register
  - ``role`` is indexed for admin listing queries
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repos.base import BaseRepo


class UsersRepo(BaseRepo):
    collection_name = "users"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def find_by_email(self, email: str) -> Optional[dict]:
        """Case-sensitive lookup.  Callers normalise to lowercase before calling."""
        return await self.find_one({"email": email})

    async def find_by_id(self, user_id: str) -> Optional[dict]:
        return await self.find_one({"id": user_id})

    async def find_by_id_with_hash(self, user_id: str) -> Optional[dict]:
        """Includes ``password_hash`` — only for internal auth flows."""
        return await self.find_one({"id": user_id}, projection={"_id": 0})

    async def find_by_email_with_hash(self, email: str) -> Optional[dict]:
        """Includes ``password_hash`` — only for login verification."""
        return await self.find_one({"email": email}, projection={"_id": 0})

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        name: str,
        role: str,
    ) -> dict:
        """Insert a new user.  Raises ``pymongo.errors.DuplicateKeyError`` on
        duplicate email — the caller (auth router) catches this and returns 409.
        """
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "id": str(uuid.uuid4()),
            "email": email.lower().strip(),
            "password_hash": password_hash,
            "name": name.strip(),
            "role": role,
            "status": "active",
            "kyc_status": "pending",
            "created_at": now,
            "updated_at": now,
        }
        return await self.insert_one(doc)

    async def update(self, user_id: str, patch: dict) -> bool:
        """Partial update.  ``patch`` must NOT contain ``id`` or ``email``."""
        patch.pop("id", None)
        patch.pop("email", None)
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        return await self.update_one({"id": user_id}, {"$set": patch})

    async def set_status(self, user_id: str, status: str) -> bool:
        """``status`` should be one of: active | suspended | deleted."""
        return await self.update(user_id, {"status": status})

    async def set_kyc_status(self, user_id: str, kyc_status: str) -> bool:
        return await self.update(user_id, {"kyc_status": kyc_status})

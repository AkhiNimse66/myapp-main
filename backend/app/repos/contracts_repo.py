"""Contracts repository — wraps the ``contract_files`` collection.

Each row tracks a single uploaded contract document (PDF, image, etc.).
Actual file bytes live in object storage (S3/GCS); ``storage_key`` is the
reference.  Soft-delete is used so the AI audit trail remains intact even
if a user removes the file from their view.

Schema: id, user_id, creator_id, deal_id, filename, storage_key,
        mime_type, size_bytes, is_deleted, uploaded_at
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repos.base import BaseRepo


class ContractsRepo(BaseRepo):
    collection_name = "contract_files"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def find_by_id(self, file_id: str) -> Optional[dict]:
        return await self.find_one({"id": file_id, "is_deleted": False})

    async def find_by_user_id(
        self, user_id: str, *, include_deleted: bool = False
    ) -> List[dict]:
        q = {"user_id": user_id}
        if not include_deleted:
            q["is_deleted"] = False
        return await self.find_many(q, sort=[("uploaded_at", -1)])

    async def find_by_deal_id(self, deal_id: str) -> List[dict]:
        return await self.find_many(
            {"deal_id": deal_id, "is_deleted": False},
            sort=[("uploaded_at", -1)],
        )

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        user_id: str,
        filename: str,
        storage_key: str,
        creator_id: Optional[str] = None,
        deal_id: Optional[str] = None,
        mime_type: Optional[str] = None,
        size_bytes: Optional[int] = None,
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "creator_id": creator_id,
            "deal_id": deal_id,
            "filename": filename,
            "storage_key": storage_key,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "is_deleted": False,
            "uploaded_at": now,
        }
        return await self.insert_one(doc)

    async def soft_delete(self, file_id: str) -> bool:
        return await self.update_one(
            {"id": file_id}, {"$set": {"is_deleted": True}}
        )

    async def attach_to_deal(self, file_id: str, deal_id: str) -> bool:
        return await self.update_one(
            {"id": file_id}, {"$set": {"deal_id": deal_id}}
        )

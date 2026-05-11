"""Contracts repository — wraps the ``contract_files`` collection.

Each row tracks a single uploaded contract document (PDF, image, etc.).
MVP storage: file bytes stored as base64 in the ``file_data`` field — fully
persistent in MongoDB Atlas, zero data loss on Railway redeploys.
Phase 7 upgrade: replace file_data with a Cloudflare R2 presigned URL and
clear the base64 field to save Atlas storage.

Schema: id, user_id, creator_id, deal_id, filename, storage_key,
        mime_type, size_bytes, file_data (base64), is_deleted, uploaded_at
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
        file_data: Optional[str] = None,   # base64-encoded file bytes (MVP storage)
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
            "file_data": file_data,        # base64 string — persistent in Atlas
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

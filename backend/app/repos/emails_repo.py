"""Emails repository — wraps the ``email_log`` collection (transactional outbox).

The outbox pattern decouples email dispatch from request handlers.  A worker
polls for ``status=pending`` rows and hands them to the email provider
(Resend, SendGrid, etc.).  On failure the row is retried up to ``max_attempts``
with exponential backoff; ``next_attempt_at`` is the scheduler's cursor.

Key index: (status, next_attempt_at) — the worker's polling query.

Schema: id, to, subject, body_html, status, attempts, max_attempts,
        next_attempt_at, last_error, sent_at, created_at
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repos.base import BaseRepo


class EmailsRepo(BaseRepo):
    collection_name = "email_log"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def find_pending(self, *, limit: int = 50) -> List[dict]:
        """Fetch rows the worker should attempt right now."""
        now = datetime.now(timezone.utc).isoformat()
        return await self.find_many(
            {
                "status": "pending",
                "next_attempt_at": {"$lte": now},
                "$expr": {"$lt": ["$attempts", "$max_attempts"]},
            },
            sort=[("next_attempt_at", 1)],
            limit=limit,
        )

    async def find_by_id(self, email_id: str) -> Optional[dict]:
        return await self.find_one({"id": email_id})

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        to: str,
        subject: str,
        body_html: str,
        max_attempts: int = 3,
        template: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "id": str(uuid.uuid4()),
            "to": to,
            "subject": subject,
            "body_html": body_html,
            "template": template,
            "context": context or {},
            "status": "pending",
            "attempts": 0,
            "max_attempts": max_attempts,
            "next_attempt_at": now,   # eligible immediately
            "last_error": None,
            "sent_at": None,
            "created_at": now,
        }
        return await self.insert_one(doc)

    async def mark_sent(self, email_id: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        return await self.update_one(
            {"id": email_id},
            {"$set": {"status": "sent", "sent_at": now}, "$inc": {"attempts": 1}},
        )

    async def mark_failed(self, email_id: str, error: str) -> bool:
        return await self.update_one(
            {"id": email_id},
            {"$set": {"status": "failed", "last_error": error}, "$inc": {"attempts": 1}},
        )

    async def schedule_retry(self, email_id: str, next_attempt_at: str) -> bool:
        """Keep status=pending but push the next attempt forward."""
        return await self.update_one(
            {"id": email_id},
            {
                "$set": {"next_attempt_at": next_attempt_at},
                "$inc": {"attempts": 1},
            },
        )

"""Events repository — wraps the ``deal_events`` collection (append-only audit trail).

Every state transition, manual override, and system action on a deal writes
an event here.  No events are ever deleted.  The collection is the source of
truth for compliance audits and dispute resolution.

Key index: (deal_id, at DESC) — timeline queries are always deal-scoped.

Schema: id, deal_id, event_type, actor_id, actor_role,
        payload (arbitrary JSON), at (ISO timestamp)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repos.base import BaseRepo


class EventsRepo(BaseRepo):
    collection_name = "deal_events"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def find_by_deal(
        self, deal_id: str, *, limit: int = 200
    ) -> List[dict]:
        """Return events newest-first (descending ``at``)."""
        return await self.find_many(
            {"deal_id": deal_id},
            sort=[("at", -1)],
            limit=limit,
        )

    async def find_latest(self, deal_id: str) -> Optional[dict]:
        rows = await self.find_by_deal(deal_id, limit=1)
        return rows[0] if rows else None

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def append(
        self,
        *,
        deal_id: str,
        event_type: str,
        actor_id: str,
        actor_role: str = "system",
        payload: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Append a new event.  Never updates existing events."""
        doc = {
            "id": str(uuid.uuid4()),
            "deal_id": deal_id,
            "event_type": event_type,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "payload": payload or {},
            "at": datetime.now(timezone.utc).isoformat(),
        }
        return await self.insert_one(doc)

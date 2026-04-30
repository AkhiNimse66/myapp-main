"""Transactions repository — wraps the ``transactions`` collection.

The transactions collection is the unified financial ledger.  Every money
movement (disbursement, repayment, fee capture, refund) creates a row here.
``provider_session_id`` is the idempotency key from the payment rail
(Stripe, Razorpay, etc.) — unique sparse index prevents double-processing.

Schema: id, deal_id, kind, amount, currency, status,
        provider, provider_session_id, provider_ref,
        initiated_at, completed_at, notes
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.enums import TxnKind, TxnStatus
from app.repos.base import BaseRepo


class TransactionsRepo(BaseRepo):
    collection_name = "transactions"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def find_by_deal(
        self, deal_id: str, *, kind: Optional[str] = None
    ) -> List[dict]:
        q = {"deal_id": deal_id}
        if kind:
            q["kind"] = kind
        return await self.find_many(q, sort=[("initiated_at", 1)])

    async def find_by_id(self, txn_id: str) -> Optional[dict]:
        return await self.find_one({"id": txn_id})

    async def find_by_provider_session(self, session_id: str) -> Optional[dict]:
        """Idempotency lookup — returns existing txn if the session was already processed."""
        return await self.find_one({"provider_session_id": session_id})

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        deal_id: str,
        kind: str,
        amount: float,
        currency: str = "INR",
        provider: Optional[str] = None,
        provider_session_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "id": str(uuid.uuid4()),
            "deal_id": deal_id,
            "kind": kind,
            "amount": amount,
            "currency": currency,
            "status": TxnStatus.INITIATED,
            "provider": provider,
            "provider_session_id": provider_session_id,
            "provider_ref": None,
            "initiated_at": now,
            "completed_at": None,
            "notes": notes,
        }
        return await self.insert_one(doc)

    async def update_status(
        self,
        txn_id: str,
        status: str,
        *,
        provider_ref: Optional[str] = None,
    ) -> bool:
        patch: dict = {"status": status}
        if provider_ref:
            patch["provider_ref"] = provider_ref
        if status in (TxnStatus.PAID, TxnStatus.FAILED, TxnStatus.REFUNDED):
            patch["completed_at"] = datetime.now(timezone.utc).isoformat()
        return await self.update_one({"id": txn_id}, {"$set": patch})

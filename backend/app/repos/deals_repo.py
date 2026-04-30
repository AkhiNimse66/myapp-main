"""Deals repository — wraps the ``deals`` collection.

A deal represents a single brand-deal financing transaction from contract
upload through disbursement and repayment.  The status field is the primary
state machine driver — see ``enums.DealStatus`` for the full transition graph.

Key indexes (defined in db.ensure_indexes):
  - (creator_id, status)  — creator dashboard
  - (brand_id, status)    — brand dashboard
  - (agency_id, status)   — agency dashboard
  - (status, maturity_date) — collections sweep
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.enums import DealStatus
from app.repos.base import BaseRepo


class DealsRepo(BaseRepo):
    collection_name = "deals"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def find_by_id(self, deal_id: str) -> Optional[dict]:
        return await self.find_one({"id": deal_id})

    async def find_by_creator(
        self,
        creator_id: str,
        *,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[dict]:
        q: Dict[str, Any] = {"creator_id": creator_id}
        if status:
            q["status"] = status
        return await self.find_many(q, sort=[("created_at", -1)], skip=skip, limit=limit)

    async def find_by_brand(
        self,
        brand_id: str,
        *,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[dict]:
        q: Dict[str, Any] = {"brand_id": brand_id}
        if status:
            q["status"] = status
        return await self.find_many(q, sort=[("created_at", -1)], skip=skip, limit=limit)

    async def find_by_agency(
        self,
        agency_id: str,
        *,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[dict]:
        q: Dict[str, Any] = {"agency_id": agency_id}
        if status:
            q["status"] = status
        return await self.find_many(q, sort=[("created_at", -1)], skip=skip, limit=limit)

    async def find_by_status(
        self,
        status: str,
        *,
        before_maturity_date: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[dict]:
        """Used by the collections sweep job."""
        q: Dict[str, Any] = {"status": status}
        if before_maturity_date:
            q["maturity_date"] = {"$lte": before_maturity_date}
        return await self.find_many(q, sort=[("maturity_date", 1)], skip=skip, limit=limit)

    # ------------------------------------------------------------------
    # Writes
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        creator_id: str,
        brand_id: str,
        deal_amount: float,
        payment_terms_days: int,
        agency_id: Optional[str] = None,
        contract_file_id: Optional[str] = None,
        brand_name: Optional[str] = None,
        deal_title: Optional[str] = None,
        contract_text: Optional[str] = None,
        currency: str = "INR",
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "id": str(uuid.uuid4()),
            "creator_id": creator_id,
            "brand_id": brand_id,
            "brand_name": brand_name,
            "deal_title": deal_title,
            "agency_id": agency_id,
            "deal_amount": deal_amount,
            "payment_terms_days": payment_terms_days,
            "currency": currency,
            "contract_file_id": contract_file_id,
            "contract_text": contract_text,
            "status": DealStatus.UPLOADED,
            # Risk decision fields — populated after scoring
            "advance_amount": None,
            "discount_fee": None,
            "advance_rate": None,
            "risk_decision": None,
            "maturity_date": None,
            "disbursed_at": None,
            "repaid_at": None,
            "created_at": now,
            "updated_at": now,
        }
        return await self.insert_one(doc)

    async def update_status(
        self,
        deal_id: str,
        new_status: str,
        *,
        extra: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Atomic status transition.  ``extra`` merges additional fields
        (e.g. advance_amount after scoring, disbursed_at after payout).
        """
        patch = {"status": new_status}
        if extra:
            patch.update(extra)
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        return await self.update_one({"id": deal_id}, {"$set": patch})

    async def update(self, deal_id: str, patch: dict) -> bool:
        patch.pop("id", None)
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        return await self.update_one({"id": deal_id}, {"$set": patch})

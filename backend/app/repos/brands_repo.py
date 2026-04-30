"""Brands repository — wraps the ``brands`` collection.

Brands are counterparties on deal contracts.  A brand user account is
created via an admin-issued signup token; the brand profile stores the
additional commercial metadata needed for risk scoring.

Schema: id, user_id, name, website, industry, country, risk_score,
        payment_reliability, verified, created_at, updated_at
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.repos.base import BaseRepo


class BrandsRepo(BaseRepo):
    collection_name = "brands"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    async def find_by_id(self, brand_id: str) -> Optional[dict]:
        return await self.find_one({"id": brand_id})

    async def find_by_user_id(self, user_id: str) -> Optional[dict]:
        return await self.find_one({"user_id": user_id})

    async def find_by_name(self, name: str) -> Optional[dict]:
        """Case-insensitive exact match."""
        return await self.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})

    async def search_by_name(self, query: str, limit: int = 20) -> List[dict]:
        """Prefix search for autocomplete in the deal-upload flow."""
        return await self.find_many(
            {"name": {"$regex": f"^{query}", "$options": "i"}},
            sort=[("name", 1)],
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
        website: Optional[str] = None,
        industry: Optional[str] = None,
        country: Optional[str] = None,
        tier: Optional[str] = None,
        credit_rating: Optional[str] = None,
        solvency_score: Optional[float] = None,
        payment_history_score: Optional[float] = None,
        avg_payment_days: Optional[int] = None,
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "name": name.strip(),
            "website": website,
            "industry": industry,
            "country": country,
            "tier": tier,
            "credit_rating": credit_rating,
            "solvency_score": solvency_score,
            "payment_history_score": payment_history_score,
            "avg_payment_days": avg_payment_days,
            "risk_score": None,          # populated by BrandIntelligence
            "payment_reliability": None,  # 0.0–1.0 float
            "verified": False,
            "created_at": now,
            "updated_at": now,
        }
        return await self.insert_one(doc)

    async def update(self, brand_id: str, patch: dict) -> bool:
        patch.pop("id", None)
        patch.pop("user_id", None)
        patch["updated_at"] = datetime.now(timezone.utc).isoformat()
        return await self.update_one({"id": brand_id}, {"$set": patch})

    async def set_risk_score(
        self, brand_id: str, risk_score: str, payment_reliability: float
    ) -> bool:
        return await self.update(
            brand_id,
            {"risk_score": risk_score, "payment_reliability": payment_reliability},
        )

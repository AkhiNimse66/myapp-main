"""Risk Decision Engine — single entry point for any pricing decision.

Routers + deal services NEVER compute pricing themselves. They build a
:class:`DealContext` and call :meth:`RiskDecisionEngine.decide`. The engine
fans out to the configured intelligence providers, hands their DTOs to the
configured policy, and returns a frozen :class:`Decision`.

Swapping mock → real for any single dimension is a one-line change in
:mod:`app.services.ai.factory`.
"""
from __future__ import annotations
import logging

from app.services.ai.interfaces import (
    BrandIntelligence,
    Compliance,
    CreatorIntelligence,
    DealContext,
    Decision,
)
from app.services.ai.risk_decision.policies import Policy

logger = logging.getLogger("mypay.risk")


class RiskDecisionEngine:
    def __init__(
        self,
        *,
        creator_intel: CreatorIntelligence,
        brand_intel: BrandIntelligence,
        compliance: Compliance,
        policy: Policy,
        engine_version: str = "1.0.0",
    ):
        self.creator_intel = creator_intel
        self.brand_intel = brand_intel
        self.compliance = compliance
        self.policy = policy
        self.engine_version = engine_version

    async def decide(self, *, ctx: DealContext, creator_user_id: str) -> Decision:
        creator = await self.creator_intel.get_metrics(creator_id=ctx.creator_id)
        brand = await self.brand_intel.get_intel(brand_id=ctx.brand_id)
        comp = await self.compliance.check(user_id=creator_user_id)

        decision = self.policy.apply(ctx=ctx, creator=creator, brand=brand, comp=comp)
        decision.engine_version = self.engine_version

        logger.info(
            "risk.decide deal_id=%s policy=%s approved=%s review=%s advance=%.2f fee=%.2f",
            ctx.deal_id,
            self.policy.name,
            decision.approved,
            decision.requires_admin_review,
            decision.advance_amount,
            decision.discount_fee,
        )
        return decision

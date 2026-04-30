"""AI service Protocols + DTOs — the public contract.

Routers and deal services import only from this module. Concrete provider
classes live under ``services/ai/<service>/{mock,real}_provider.py`` and are
selected by :mod:`app.services.ai.factory` based on env-driven settings.

Three rules enforced everywhere:

1. **Routers never compute pricing.** They call services; services call the
   :class:`RiskDecisionEngine`; the engine fans out to providers.
2. **DTOs are Pydantic models.** Validation happens at the boundary so a
   misbehaving real provider cannot inject malformed numbers.
3. **Providers are interchangeable.** A real provider must satisfy the same
   Protocol as its mock; nothing else changes.
"""
from __future__ import annotations
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


# ===================================================================
# DTOs — wire shapes between providers, engine, and persistence
# ===================================================================
class CreatorMetrics(BaseModel):
    follower_count: int = Field(ge=0)
    engagement_rate: float = Field(
        ge=0.0, le=100.0,
        description="Percent (e.g. 3.2 → 3.2 %).",
    )
    authenticity_score: float = Field(ge=0.0, le=1.0)
    creator_score: float = Field(ge=0.0, le=100.0)
    is_synthetic: bool = True


class BrandIntel(BaseModel):
    brand_id: str
    brand_tier: Literal[
        "fortune500", "enterprise", "growth", "seed", "mid"
    ]
    payment_score: float = Field(ge=0.0, le=1.0)
    risk_score: float = Field(
        ge=0.0, le=100.0,
        description="Higher = safer.",
    )
    avg_payment_days: int = Field(ge=0)


class ComplianceReport(BaseModel):
    pan_verified: bool
    cibil_score: int = Field(ge=300, le=900)
    kyc_status: Literal["pending", "approved", "rejected"]
    flags: list[str] = []


class DealContext(BaseModel):
    deal_id: str
    creator_id: str
    brand_id: str
    deal_amount: float = Field(gt=0)
    payment_terms_days: int = Field(gt=0)
    currency: str = "usd"


class Decision(BaseModel):
    """Frozen output of the risk engine. Persisted onto ``deals.decision_snapshot``."""
    approved: bool
    requires_admin_review: bool = False

    advance_rate: float = Field(ge=0.0, le=1.0)
    discount_fee_rate: float = Field(ge=0.0, le=1.0)
    credit_limit: float = Field(ge=0.0)

    advance_amount: float = Field(ge=0.0)
    discount_fee: float = Field(ge=0.0)
    apr_equivalent: float = Field(ge=0.0)

    rationale: list[str] = []
    raw: dict = {}                          # full input snapshot for audit
    policy: str = "fixed_mvp"
    engine_version: str = "1.0.0"


# ===================================================================
# Protocols — the contract concrete providers must satisfy
# ===================================================================
@runtime_checkable
class CreatorIntelligence(Protocol):
    name: str
    async def get_metrics(self, *, creator_id: str) -> CreatorMetrics: ...


@runtime_checkable
class BrandIntelligence(Protocol):
    name: str
    async def get_intel(self, *, brand_id: str) -> BrandIntel: ...


@runtime_checkable
class Compliance(Protocol):
    name: str
    async def check(self, *, user_id: str) -> ComplianceReport: ...

"""Builder — turns ``Settings`` + repos into a ready-to-use RiskDecisionEngine.

This is the **only** module that picks concrete provider implementations.
Flipping any of these env vars at deploy time changes the providers without
touching any router, service, or repository:

    CREATOR_INTEL_MODE   = mock | instagram_graph
    BRAND_INTEL_MODE     = mock | internal_db
    COMPLIANCE_MODE      = mock | cibil_pan
    RISK_POLICY          = fixed_mvp | heuristic | ml
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional

from app.config import Settings
from app.services.ai.brand_intelligence.mock_provider import MockBrandIntelligence
from app.services.ai.brand_intelligence.real_provider import RealBrandIntelligence
from app.services.ai.compliance.mock_provider import MockCompliance
from app.services.ai.compliance.real_provider import RealCompliance
from app.services.ai.creator_intelligence.mock_provider import MockCreatorIntelligence
from app.services.ai.creator_intelligence.real_provider import RealCreatorIntelligence
from app.services.ai.interfaces import (
    BrandIntelligence,
    Compliance,
    CreatorIntelligence,
)
from app.services.ai.risk_decision.engine import RiskDecisionEngine
from app.services.ai.risk_decision.policies import POLICIES


@dataclass
class RepoBundle:
    """Minimum repository surface providers need.

    Fields stay ``Optional`` so the engine remains constructible during
    smoke-tests / unit tests without bringing up real Mongo.
    """
    social: Optional[Any] = None      # social_repo (Day 2)
    brands: Optional[Any] = None      # brands_repo (Day 2)


def build_creator_intel(settings: Settings, repos: RepoBundle) -> CreatorIntelligence:
    if settings.CREATOR_INTEL_MODE == "mock":
        return MockCreatorIntelligence(social_repo=repos.social)
    return RealCreatorIntelligence(social_repo=repos.social)


def build_brand_intel(settings: Settings, repos: RepoBundle) -> BrandIntelligence:
    if settings.BRAND_INTEL_MODE == "mock":
        return MockBrandIntelligence(brands_repo=repos.brands)
    return RealBrandIntelligence(brands_repo=repos.brands)


def build_compliance(settings: Settings) -> Compliance:
    if settings.COMPLIANCE_MODE == "mock":
        return MockCompliance()
    return RealCompliance()


def build_risk_decision_engine(
    settings: Settings,
    repos: Optional[RepoBundle] = None,
) -> RiskDecisionEngine:
    repos = repos or RepoBundle()
    if settings.RISK_POLICY not in POLICIES:
        raise ValueError(
            f"Unknown RISK_POLICY={settings.RISK_POLICY!r}; allowed: {list(POLICIES)}"
        )

    return RiskDecisionEngine(
        creator_intel=build_creator_intel(settings, repos),
        brand_intel=build_brand_intel(settings, repos),
        compliance=build_compliance(settings),
        policy=POLICIES[settings.RISK_POLICY],
        engine_version=settings.ENGINE_VERSION,
    )

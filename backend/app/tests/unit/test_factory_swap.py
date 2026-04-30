"""Prove that flipping env vars swaps providers without touching engine code."""
from __future__ import annotations
import pytest

from app.config import Settings
from app.services.ai.factory import (
    build_brand_intel,
    build_compliance,
    build_creator_intel,
    build_risk_decision_engine,
    RepoBundle,
)
from app.services.ai.brand_intelligence.mock_provider import MockBrandIntelligence
from app.services.ai.compliance.mock_provider import MockCompliance
from app.services.ai.creator_intelligence.mock_provider import MockCreatorIntelligence


def _mock_settings(**overrides) -> Settings:
    base = dict(
        MONGO_URL="mongodb://localhost:27017",
        DB_NAME="mypay_test",
        JWT_SECRET="unit-tests-only-jwt-secret-32-chars",
    )
    base.update(overrides)
    return Settings(**base)


def test_default_settings_select_all_mocks():
    s = _mock_settings()
    repos = RepoBundle()
    assert isinstance(build_creator_intel(s, repos), MockCreatorIntelligence)
    assert isinstance(build_brand_intel(s, repos), MockBrandIntelligence)
    assert isinstance(build_compliance(s), MockCompliance)


def test_real_creator_intel_raises_at_construction():
    s = _mock_settings(CREATOR_INTEL_MODE="instagram_graph")
    with pytest.raises(NotImplementedError):
        build_creator_intel(s, RepoBundle())


def test_real_brand_intel_raises_at_construction():
    s = _mock_settings(BRAND_INTEL_MODE="internal_db")
    with pytest.raises(NotImplementedError):
        build_brand_intel(s, RepoBundle())


def test_real_compliance_raises_at_construction():
    s = _mock_settings(COMPLIANCE_MODE="cibil_pan")
    with pytest.raises(NotImplementedError):
        build_compliance(s)


def test_unknown_risk_policy_rejected():
    # Pydantic Literal blocks invalid values at Settings construction time.
    with pytest.raises(Exception):
        _mock_settings(RISK_POLICY="lol-not-real")


def test_engine_built_with_default_settings():
    s = _mock_settings()
    eng = build_risk_decision_engine(s, RepoBundle())
    assert eng.policy.name == "fixed_mvp"
    assert eng.engine_version == s.ENGINE_VERSION

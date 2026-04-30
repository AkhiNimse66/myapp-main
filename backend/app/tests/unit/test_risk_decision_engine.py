"""Unit tests — RiskDecisionEngine + FixedMVPPolicy.

Hand-rolled provider stubs so the suite runs with **no DB**, **no network**,
and **no env beyond the conftest stubs**.
"""
from __future__ import annotations
import pytest

from app.services.ai.interfaces import (
    BrandIntel,
    ComplianceReport,
    CreatorMetrics,
    DealContext,
)
from app.services.ai.risk_decision.engine import RiskDecisionEngine
from app.services.ai.risk_decision.policies import FixedMVPPolicy


# ---------------------------------------------------------------------
# Stubs that satisfy the Protocols without touching the DB or _logger.
# ---------------------------------------------------------------------
class _StubCreator:
    name = "stub"
    def __init__(self, m): self._m = m
    async def get_metrics(self, *, creator_id: str): return self._m


class _StubBrand:
    name = "stub"
    def __init__(self, b): self._b = b
    async def get_intel(self, *, brand_id: str): return self._b


class _StubComp:
    name = "stub"
    def __init__(self, c): self._c = c
    async def check(self, *, user_id: str): return self._c


def _engine(*, creator=None, brand=None, comp=None):
    return RiskDecisionEngine(
        creator_intel=_StubCreator(creator or CreatorMetrics(
            follower_count=50_000, engagement_rate=3.2,
            authenticity_score=0.85, creator_score=72.0,
        )),
        brand_intel=_StubBrand(brand or BrandIntel(
            brand_id="b1", brand_tier="enterprise",
            payment_score=0.85, risk_score=82.0, avg_payment_days=55,
        )),
        compliance=_StubComp(comp or ComplianceReport(
            pan_verified=True, cibil_score=720, kyc_status="approved",
        )),
        policy=FixedMVPPolicy(),
    )


def _ctx(deal_amount=10_000.0, terms=60):
    return DealContext(
        deal_id="d1",
        creator_id="c1",
        brand_id="b1",
        deal_amount=deal_amount,
        payment_terms_days=terms,
    )


# ---------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------
@pytest.mark.asyncio
async def test_happy_path_returns_fixed_mvp_numbers():
    eng = _engine()
    d = await eng.decide(ctx=_ctx(), creator_user_id="u1")
    assert d.approved is True
    assert d.requires_admin_review is False
    assert d.advance_rate == 0.80
    assert d.discount_fee_rate == 0.03
    assert d.credit_limit == 50_000.0
    assert d.advance_amount == 8_000.0
    assert d.discount_fee == 300.0
    assert d.policy == "fixed_mvp"
    assert any("MVP fixed pricing" in r for r in d.rationale)


@pytest.mark.asyncio
async def test_kyc_rejected_blocks_approval():
    eng = _engine(comp=ComplianceReport(
        pan_verified=False, cibil_score=720, kyc_status="rejected",
    ))
    d = await eng.decide(ctx=_ctx(), creator_user_id="u1")
    assert d.approved is False
    assert any("KYC rejected" in r for r in d.rationale)


@pytest.mark.asyncio
async def test_low_cibil_triggers_review_but_still_approved():
    eng = _engine(comp=ComplianceReport(
        pan_verified=True, cibil_score=600, kyc_status="approved",
    ))
    d = await eng.decide(ctx=_ctx(), creator_user_id="u1")
    assert d.approved is True
    assert d.requires_admin_review is True
    assert any("CIBIL" in r for r in d.rationale)


@pytest.mark.asyncio
async def test_brand_payment_score_below_reject_threshold_blocks():
    eng = _engine(brand=BrandIntel(
        brand_id="b1", brand_tier="seed",
        payment_score=0.30, risk_score=40.0, avg_payment_days=85,
    ))
    d = await eng.decide(ctx=_ctx(terms=90), creator_user_id="u1")
    assert d.approved is False


@pytest.mark.asyncio
async def test_brand_payment_score_in_review_band_triggers_review():
    eng = _engine(brand=BrandIntel(
        brand_id="b1", brand_tier="growth",
        payment_score=0.50, risk_score=55.0, avg_payment_days=70,
    ))
    d = await eng.decide(ctx=_ctx(), creator_user_id="u1")
    assert d.approved is True
    assert d.requires_admin_review is True


@pytest.mark.asyncio
async def test_apr_calculated_from_terms():
    eng = _engine()
    d = await eng.decide(ctx=_ctx(terms=30), creator_user_id="u1")
    # 3% over 30 days → APR ≈ 36.5%
    assert 35.0 < d.apr_equivalent < 38.0


@pytest.mark.asyncio
async def test_decision_carries_engine_version():
    eng = _engine()
    eng.engine_version = "9.9.9"
    d = await eng.decide(ctx=_ctx(), creator_user_id="u1")
    assert d.engine_version == "9.9.9"


@pytest.mark.asyncio
async def test_raw_snapshot_is_replayable():
    eng = _engine()
    d = await eng.decide(ctx=_ctx(), creator_user_id="u1")
    assert set(d.raw.keys()) == {"creator", "brand", "compliance", "ctx"}
    assert d.raw["ctx"]["deal_amount"] == 10_000.0

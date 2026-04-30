"""Pricing / credit / approval policies.

The :class:`RiskDecisionEngine` plugs ONE policy in based on
``Settings.RISK_POLICY``. Policies are pure: they receive DTOs and return a
:class:`Decision`. They never touch the DB.

* :class:`FixedMVPPolicy` — MVP. Hard-coded 80 % advance / 3 % fee /
  ₹50 000 limit, but the **inputs are real DTOs** so KYC + brand
  payment-score + creator-score still gate approval and admin review.
* :class:`HeuristicPolicy` — Future. Wraps existing ``risk_engine.py``.
* :class:`MLPolicy` — Future. Wraps existing ``ml_service.py``.

Adding a new policy is two lines: a class implementing :meth:`apply` plus an
entry in :data:`POLICIES`. No router or service code changes.
"""
from __future__ import annotations
from typing import Protocol

from app.services.ai.interfaces import (
    BrandIntel,
    ComplianceReport,
    CreatorMetrics,
    DealContext,
    Decision,
)


class Policy(Protocol):
    name: str
    def apply(
        self,
        *,
        ctx: DealContext,
        creator: CreatorMetrics,
        brand: BrandIntel,
        comp: ComplianceReport,
    ) -> Decision: ...


# ===================================================================
# MVP policy
# ===================================================================
class FixedMVPPolicy:
    """Fixed advance / fee / limit per spec.

    ``raw`` on the returned :class:`Decision` includes the full input snapshot
    so audits can replay any decision deterministically.
    """
    name = "fixed_mvp"

    DEFAULT_ADVANCE_RATE = 0.80
    DEFAULT_DISCOUNT_FEE_RATE = 0.03
    DEFAULT_CREDIT_LIMIT = 50_000.0

    KYC_REJECT_STATES = {"rejected"}
    KYC_REVIEW_STATES = {"pending"}
    CIBIL_REVIEW_THRESHOLD = 650
    BRAND_PAYMENT_REVIEW_THRESHOLD = 0.6
    BRAND_PAYMENT_REJECT_THRESHOLD = 0.4
    CREATOR_SCORE_REVIEW_THRESHOLD = 50.0

    def apply(self, *, ctx, creator, brand, comp) -> Decision:
        rationale: list[str] = []
        approved = True
        requires_review = False

        # ---------- Hard rejections ----------
        if comp.kyc_status in self.KYC_REJECT_STATES:
            approved = False
            rationale.append(f"KYC rejected ({comp.kyc_status}).")
        if brand.payment_score < self.BRAND_PAYMENT_REJECT_THRESHOLD:
            approved = False
            rationale.append(
                f"Brand payment_score {brand.payment_score:.2f} below reject threshold "
                f"{self.BRAND_PAYMENT_REJECT_THRESHOLD:.2f}."
            )

        # ---------- Soft gates → admin review ----------
        if comp.kyc_status in self.KYC_REVIEW_STATES:
            requires_review = True
            rationale.append("KYC pending — admin review required.")
        if comp.cibil_score < self.CIBIL_REVIEW_THRESHOLD:
            requires_review = True
            rationale.append(
                f"CIBIL {comp.cibil_score} below review threshold "
                f"{self.CIBIL_REVIEW_THRESHOLD}."
            )
        if (
            brand.payment_score >= self.BRAND_PAYMENT_REJECT_THRESHOLD
            and brand.payment_score < self.BRAND_PAYMENT_REVIEW_THRESHOLD
        ):
            requires_review = True
            rationale.append(
                f"Brand payment_score {brand.payment_score:.2f} below review threshold "
                f"{self.BRAND_PAYMENT_REVIEW_THRESHOLD:.2f}."
            )
        if creator.creator_score < self.CREATOR_SCORE_REVIEW_THRESHOLD:
            requires_review = True
            rationale.append(
                f"Creator score {creator.creator_score:.0f} below review threshold "
                f"{self.CREATOR_SCORE_REVIEW_THRESHOLD:.0f}."
            )

        # ---------- Pricing (MVP fixed) ----------
        advance_rate = self.DEFAULT_ADVANCE_RATE
        fee_rate = self.DEFAULT_DISCOUNT_FEE_RATE
        limit = self.DEFAULT_CREDIT_LIMIT

        advance_amount = round(ctx.deal_amount * advance_rate, 2)
        discount_fee = round(ctx.deal_amount * fee_rate, 2)
        apr = round(fee_rate * 100 * 365 / max(ctx.payment_terms_days, 1), 2)

        rationale.append(
            f"MVP fixed pricing applied "
            f"(advance={advance_rate * 100:.0f}%, "
            f"fee={fee_rate * 100:.1f}%, "
            f"limit={limit:.0f})."
        )

        return Decision(
            approved=approved,
            requires_admin_review=requires_review,
            advance_rate=advance_rate,
            discount_fee_rate=fee_rate,
            credit_limit=limit,
            advance_amount=advance_amount,
            discount_fee=discount_fee,
            apr_equivalent=apr,
            rationale=rationale,
            raw={
                "creator": creator.model_dump(),
                "brand": brand.model_dump(),
                "compliance": comp.model_dump(),
                "ctx": ctx.model_dump(),
            },
            policy=self.name,
        )


# ===================================================================
# Future policy stubs
# ===================================================================
class HeuristicPolicy:
    """Future: wraps ``backend/risk_engine.py`` (heuristic blended score)."""
    name = "heuristic"

    def apply(self, *, ctx, creator, brand, comp) -> Decision:  # pragma: no cover
        raise NotImplementedError(
            "HeuristicPolicy is not yet wired — set RISK_POLICY=fixed_mvp."
        )


class MLPolicy:
    """Future: wraps ``backend/ml_service.py`` (LogReg default-prob model)."""
    name = "ml"

    def apply(self, *, ctx, creator, brand, comp) -> Decision:  # pragma: no cover
        raise NotImplementedError(
            "MLPolicy is not yet wired — set RISK_POLICY=fixed_mvp."
        )


POLICIES: dict[str, Policy] = {
    FixedMVPPolicy.name: FixedMVPPolicy(),
    HeuristicPolicy.name: HeuristicPolicy(),
    MLPolicy.name: MLPolicy(),
}

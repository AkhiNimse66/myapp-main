# Risk Decision Engine — rule book

This is the only place in the codebase that says "what advance / fee / limit
should this deal get?". Routers and deal services depend on it; nothing
computes pricing on its own.

## Inputs (resolved by the engine, not the caller)

| Source                | Provider Protocol     | DTO                |
|-----------------------|-----------------------|--------------------|
| Creator metrics       | `CreatorIntelligence` | `CreatorMetrics`   |
| Brand intelligence    | `BrandIntelligence`   | `BrandIntel`       |
| Compliance / KYC      | `Compliance`          | `ComplianceReport` |
| Deal context          | (caller-built)        | `DealContext`      |

## Output

A `Decision` containing:

- `approved` — hard verdict
- `requires_admin_review` — soft gate; deal moves to `pending_approval`
- `advance_rate` / `discount_fee_rate` / `credit_limit` (relative + absolute)
- `advance_amount` / `discount_fee` / `apr_equivalent` (precomputed money)
- `rationale[]` — human-readable explainability
- `raw` — full input snapshot for audit / replay
- `policy` + `engine_version` — provenance

## Policies

| name         | source                       | status |
|--------------|------------------------------|--------|
| `fixed_mvp`  | `FixedMVPPolicy`             | live   |
| `heuristic`  | wraps legacy `risk_engine.py`| stub   |
| `ml`         | wraps legacy `ml_service.py` | stub   |

Selected by `Settings.RISK_POLICY`.

## Decision rules (FixedMVPPolicy)

### Hard rejections — `approved = False`
- `compliance.kyc_status == "rejected"`
- `brand.payment_score < 0.40`

### Soft gates — `requires_admin_review = True`
- `compliance.kyc_status == "pending"`
- `compliance.cibil_score < 650`
- `0.40 ≤ brand.payment_score < 0.60`
- `creator.creator_score < 50`

### Pricing (always, when not hard-rejected)
- advance rate = **80 %**
- discount fee = **3 %**
- credit limit = **₹50 000**
- APR equivalent = `fee_rate × 365 / payment_terms_days`

## Swapping providers

Change one env var. No code edits anywhere else.

```env
CREATOR_INTEL_MODE=instagram_graph   # was: mock
BRAND_INTEL_MODE=internal_db         # was: mock
COMPLIANCE_MODE=cibil_pan            # was: mock
RISK_POLICY=heuristic                # was: fixed_mvp
```

The factory (`services/ai/factory.py`) is the only module that touches
those env vars. Routers, services, repositories, and tests all stay on
the Protocol types.

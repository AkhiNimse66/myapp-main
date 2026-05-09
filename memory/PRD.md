# My Pay — Product Requirement Document

## Original problem statement
Design an invoice-discounting platform for the creator economy. Influencers face 30-60 day payment delays from brands; My Pay provides immediate liquidity (minus a discount fee) once a signed brand deal is verified. Core modules: **Brand Verification Engine**, **Risk Scoring Algorithm**, **Automated Disbursement Workflow**.

## User personas
1. **Creator / Influencer** — uploads brand contract, receives credit offer, accepts advance, tracks repayment.
2. **Risk Ops Admin** — reviews flagged deals, overrides risk scores, monitors portfolio.

## Core requirements (static)
- JWT auth (email + bcrypt password) with role-based access (creator / admin).
- Brand catalogue with tier (fortune500 / enterprise / growth / seed), credit rating (AAA→CCC), solvency score, payment-history score.
- Creator health profile: followers, engagement rate, authenticity score (synthetic, deterministic).
- Deal lifecycle: **uploaded → scored → disbursed** (+ admin override).
- Risk math: `final_score = 0.6 * brand_solvency + 0.4 * creator_health − term_penalty`. Advance ladder 70-95%, fee 2-8%. APR-equivalent computed.
- AI-assisted contract analysis via Claude Sonnet 4.5 (emergentintegrations).
- Portfolio dashboards for both personas.

## Architecture / tasks done (2026-04-21)
### Backend (FastAPI + MongoDB)
- `server.py` — auth, brands, creator profile, deals CRUD, AI analyze, disburse, admin override, dashboard summary, admin stats.
- `brand_data.py` — 20 seeded brands across all 4 tiers.
- `risk_engine.py` — scoring math + synthetic social metric generator.
- `ai_service.py` — Claude Sonnet 4.5 via emergentintegrations, with heuristic fallback.
- Startup seed: admin@mypay.io / Admin@123 + creator@mypay.io / Creator@123 (Ava Stone · 487k followers · ER 4.8 · Auth 92).

### Frontend (React + Tailwind + shadcn primitives)
- Swiss high-contrast design system (Instrument Serif + Geist + JetBrains Mono, 1px borders, zero shadows).
- Pages: Landing, Login, Register, Dashboard, DealsList, DealNew, DealDetail, Profile, AdminPanel.
- SVG risk gauge, disbursement timeline, credit memo cards, admin override modal.
- `data-testid` on every interactive + data element.

## What's been implemented (2026-04-21)
- ✅ Full auth flow + 2 seeded roles
- ✅ 20 brands, creator health profile, risk scoring engine
- ✅ Contract upload (base64 inline, max 5 MB) + AI analysis (verified live)
- ✅ Credit offer with advance %, discount fee %, APR equivalent
- ✅ Manual disbursement (simulated wire)
- ✅ Admin portfolio stats, tier breakdown, override workflow
- ✅ 100% backend + frontend test pass (20 pytest tests)

## Phase 2 enhancements (2026-04-21)
- ✅ **Repayment workflow + revolving credit recycling**: `disbursed → awaiting_payment → repaid`, maturity dates, `_settle_repayment` idempotent, dashboard shows outstanding / lifetime-settled / available
- ✅ **Stripe Checkout for brand repayment** (using `STRIPE_API_KEY=sk_test_emergent` + `emergentintegrations.payments.stripe.checkout`): real `cs_test_*` sessions, polling endpoint with retry+backoff, webhook handler, `payment_transactions` collection
- ✅ **Admin "Mark Repaid"** action with audit trail; recycles credit immediately
- ✅ **Synthetic-data ML default model** (scikit-learn LogisticRegression, 1,000 synthetic deals, ROC-AUC 0.84 on held-out 200). `GET /api/ml/status` + `risk.ml` block on deal analysis (default_prob, survival_prob, ml_score, model_auc)
- ✅ **Social-connect placeholder** (Instagram / TikTok / YouTube / X) — `pending_meta_review` status; UI panel on Profile page
- ✅ Extended status chips, deals-list filters, admin ML status card, ML widget on Deal Detail, Repayment Ledger section
- ✅ 15/15 Phase 2 pytest pass + frontend verified end-to-end

## Phase 3 enhancements (2026-04-22)
- ✅ **Email notifications via Resend** — templates for `disbursement_confirmation`, `maturity_reminder`, `repayment_received`. MOCKED until `RESEND_API_KEY` is provided; emails persisted to `email_log` collection. Admin `maturity-sweep` endpoint queues reminders for deals maturing within 7 days.
- ✅ **Emergent-managed object storage** for contract files — `POST /api/contracts/upload` (multipart, 10 MB cap), `GET /api/contracts/{id}/download` (JWT header OR `?auth=` query), soft-delete pattern, `contract_files` collection. `contract_storage_path` linked on deals.
- ✅ **ML drift monitoring (PSI)** — `/api/admin/ml/drift` with per-feature Population Stability Index + global verdict (stable / watch / drift). `deals_labeled` collection populated automatically on Mark Repaid (default=0) / Flag Default (default=1).
- ✅ **ML retrain endpoint** — `/api/admin/ml/retrain` rebuilds the classifier blending synthetic + production labelled rows (weighted 0.3/0.7 once production data exists). Model artefact hot-reloaded in `ml_service`.
- ✅ **Admin UI overhaul** — 3-tab layout (Portfolio / ML Ops / Notifications) with Retrain button, PSI drift table, email log, maturity-sweep trigger, Flag Default action.
- ✅ 15/15 Phase 3 pytest pass; all earlier tests still green.

## Prioritized backlog
### P1 — shipping-ready enhancements
- Real contract OCR (send PDF bytes to a vision model) vs only text prompt
- File storage: move contract_file_b64 to object storage / GridFS
- Repayment tracking: mark brand payment received → credit recycles
- Email / SMS notifications on disbursement (Resend / Twilio)

### P2 — monetisation / growth
- Stripe Connect for ACH / wire payouts to creator bank
- Referral programme — creator invites earn 0.25% fee rebate
- Tier-based pricing (pro creators = discount on discount fee)
- Integration with real social API (Instagram Graph / TikTok Business) for authenticity scoring

### P3 — risk ops maturity
- Machine-learning default-rate model replacing heuristic risk_engine
- Dispute / clawback workflow
- KYC / KYB for brand counterparties
- Audit log of admin overrides

## Next tasks list
1. Pilot repayment workflow + credit recycling.
2. Integrate Stripe Connect for wire payouts.
3. Wire creator-health score to real Instagram Graph API.
4. Replace heuristic scoring with trained ML model after ~1k deal dataset is collected.

# Athanni — Master Progress & Session Continuity Doc

> **EVERY Claude session must read this file first, before touching any code.**
> Update the relevant section at the end of every session.
> Also read: CLAUDE_CONTEXT.md (architecture), ATHANNI_ROADMAP.md (product strategy)

---

## Project Identity

- **Product name:** Athanni (formerly My Pay — rebrand in progress)
- **What it is:** AR financing platform for Indian creators. Creators upload brand deal contracts, Athanni advances up to 80% instantly, collects from brand at maturity.
- **Primary market:** Indian creators + Indian/global brands. INR transactions.
- **Founder:** Akhi (animse66@gmail.com)
- **Repo location:** `/Users/wolfrag/Desktop/myapp-main/`
- **Domain (target):** athanni.co.in

---

## Current Stack (do not change without noting here)

| Layer | Tech |
|-------|------|
| Backend | FastAPI (Python 3.10), async, Motor (MongoDB) |
| Database | MongoDB (local dev). PostgreSQL planned for production. |
| Auth | JWT (PyJWT), bcrypt, RBAC: creator / brand / admin / agency |
| Frontend | React 19, Vite, Tailwind CSS v3, React Router v7 |
| Design | Luxury editorial — Instrument Serif + Geist + JetBrains Mono. NO rounded corners. 1px borders. No shadows. |
| Testing | pytest + pytest-asyncio. 35 unit tests. Must pass after every backend change. |

---

## Phase Overview (Restructured — Frontend First)

```
PHASE 0  →  Rebrand + Logo + Identity          ← START HERE
PHASE 1  →  Frontend UI Overhaul               ← Visual priority
PHASE 2  →  Admin Credit Limit Control         ← Simple backend
PHASE 3  →  Mock Document System               ← Full deal test run
PHASE 4  →  Social Media Metrics               ← Instagram + YouTube APIs
PHASE 5  →  KYC + Identity Verification        ← PAN, Aadhaar (no bank needed)
PHASE 6  →  eSign Integration                  ← Leegality / Digio
PHASE 7  →  Cloud Storage (R2)                 ← Replace /tmp
PHASE 8  →  Brand GST Verification             ← Surepass API
PHASE 9  →  Real Payments + Bank               ← NEEDS BANK ACCOUNT ← push to end
PHASE 10 →  Production Deployment              ← NEEDS BANK ACCOUNT ← push to end
```

**Bank account required for:** Phase 9 only (Razorpay disbursements, RazorpayX payouts, NEFT collection).
Everything before Phase 9 can be built and tested fully without a bank account.

---

## PHASE 0 — Rebrand + Logo + Visual Identity
**Goal:** Athanni brand is fully in place before any UI work begins.
**Status:** ✅ COMPLETE
**Needs bank account:** No

### Brand Identity Decisions
- **Name:** Athanni (Hindi/Urdu for 50 paise coin — a unit of value, perfectly on-brand for a financing product)
- **Domain:** athanni.co.in (purchase ASAP, park it)
- **Logo concept:** Minimal, typographic or coin-inspired. Must work in black on white and white on black. No gradients, no 3D. Consistent with luxury editorial design system.
- **Color palette (locked):** #0A0A0A ink · #002FA7 brand blue · #FAFAFA background · zinc scale grays
- **Typography (locked):** Instrument Serif (headers) · Geist (body) · JetBrains Mono (numbers/labels)

### Code Tasks
- [x] Find-and-replace all "My Pay", "mypay", "MyPay" across entire codebase
- [x] Update DB_NAME in .env: `mypay_dev` → `athanni_dev`
- [x] Update JWT_SECRET references
- [x] Update email sender: notifications@mypay.io → notifications@athanni.co.in
- [x] Update frontend meta tags, page `<title>` tags, Landing copy
- [x] Update README.md, CLAUDE_CONTEXT.md
- [x] Design + add Athanni logo (SVG) — used in AppShell nav + Landing
- [x] Favicon from logo
- [x] Confirm 35 tests still pass after rename

---

## PHASE 1 — Frontend UI Overhaul
**Goal:** Athanni looks and feels like a serious, premium Indian fintech product.
**Status:** 🔄 IN PROGRESS (Landing + Dashboard done; remaining pages pending)
**Needs bank account:** No

### Design Principles (non-negotiable)
- Instrument Serif for all page headers and large display text
- `rounded-none` everywhere — absolutely no border radius
- 1px borders (`border border-zinc-200` or `border-zinc-800`), zero shadows
- JetBrains Mono for all rupee amounts, percentages, numbers
- Dense information — this is a financial product not a marketing site
- Dark panels for auth (Login, Register) — already partially done, polish it
- Consistent spacing system: 4px base grid

### Pages — Priority Order

#### 1.1 Landing Page (`Landing.jsx`) — HIGHEST PRIORITY
- [x] Hero with Klein blue "sixty days" accent + trust signals (CheckCircle row)
- [x] Stats strip with Klein blue numbers
- [x] Live credit memo card with blue top accent + blue risk score bar
- [x] "How it works" 4-step grid with Klein blue active step indicator
- [x] "Why Athanni" pillars section with blue icons
- [x] Transparent fee ladder (4-tier pricing table)
- [x] Full-bleed Klein blue CTA footer section
- [x] Primary CTAs → btn-brand (Klein blue), secondary → btn-brand-ghost
- [x] AthanniLogo shared component wired in (replaces old inline AthanniMark)

#### 1.2 Dashboard (`Dashboard.jsx`) — CREATOR'S HOME
- [x] "New Deal" CTA → btn-brand (Klein blue)
- [x] Credit limit amount → Klein blue
- [x] Credit limit usage bar → Klein blue
- [x] Creator Health Index → Klein blue
- [x] Tier progression active dot → Klein blue
- [x] Tier progression bar → Klein blue
- [x] Pipeline stage bars → Klein blue
- [x] "Connect accounts" CTA when Phyllo disconnected → btn-brand

#### 1.3 Deal New (`DealNew.jsx`) — CORE PRODUCT FLOW
Current state: Form. Functional but feels like a form.
Goal: Guided submission experience. Creator feels confident, not confused.
- [ ] Step indicator (1. Upload contract → 2. Enter deal details → 3. Review)
- [ ] Contract upload zone — drag & drop, clear file preview
- [ ] Brand selector — clean dropdown with brand logo/name
- [ ] Amount + terms inputs — inline validation, formatted in ₹
- [ ] Review step — summary before submit

#### 1.4 Deal Detail (`DealDetail.jsx`) — DEAL VIEW + ACTION
Current state: Functional but information-heavy and unstructured
Goal: Clear decision page. Creator understands the offer and can act confidently.
- [ ] Offer card — advance amount, fee, net payout — all prominent, mono font
- [ ] Risk gauge — existing RiskGauge component, better placement
- [ ] Contract analysis panel — AI analysis output, readable format
- [ ] Action buttons — "Accept Offer" prominent, "Decline" secondary
- [ ] Status timeline — shows deal progression visually
- [ ] Repayment section — brand payment status, UTR entry

#### 1.5 Deals List (`DealsList.jsx`)
- [ ] Clean table with status chips
- [ ] Filter bar — by status, date range, amount
- [ ] Empty state — first deal prompt

#### 1.6 Profile Page (`Profile.jsx`)
- [ ] Social accounts section — connect Instagram, YouTube (OAuth buttons)
- [ ] Payout method — UPI / bank account entry
- [ ] Credit limit display — set by admin, not editable by creator
- [ ] KYC status indicator (future)

#### 1.7 Brand Portal (`BrandPortal.jsx`)
- [ ] Cleaner invoice table
- [ ] Athanni bank details card (NEFT/RTGS) — mock details for now
- [ ] UTR confirmation modal — cleaner flow
- [ ] NOA status per deal

#### 1.8 Admin Panel (`AdminPanel.jsx`)
- [ ] Creator management tab — list creators, set credit limits
- [ ] Deal oversight tab — pipeline view, override controls
- [ ] Brand management tab — already partially built
- [ ] Document log tab — all generated docs per deal
- [ ] Email log tab — already exists, polish it

#### 1.9 Login + Register
- [x] Shared AthanniLogo component wired in (coin-on-i wordmark) — Login, Register, BrandPortal, BrandRegister
- [x] Luxury dark right panel already in place
- [ ] Further polish if needed

#### 1.10 AppShell + Navigation
- [x] AthanniLogo shared component in nav (was done in Session 2)
- [ ] Mobile nav (hamburger menu)

---

## PHASE 2 — Admin Manual Credit Limit Control
**Goal:** Admin sets credit limits per creator. No auto-scoring.
**Status:** NOT STARTED
**Needs bank account:** No

Decision: Credit limit is manually assigned by Athanni admin. Admin has full control. Social score shown as reference only.

- [ ] Add `credit_limit_override` + `credit_limit_set_by` + `credit_limit_set_at` fields to creator document
- [ ] New endpoint: `PATCH /api/admin/creators/{id}/credit-limit` (body: amount, notes)
- [ ] New endpoint: `GET /api/admin/creators` — list all creators with their current limits
- [ ] Admin panel: "Creators" tab — table of creators, current limit, "Edit Limit" button
- [ ] Creator dashboard: shows limit (removed auto-compute language)
- [ ] Confirm tests pass

---

## PHASE 3 — Mock Document System (Full End-to-End Test Run)
**Goal:** Every document in the deal lifecycle exists and is generated. A complete deal runs end-to-end with real PDFs and real emails, all mock/template content.
**Status:** NOT STARTED
**Needs bank account:** No (disbursement is mock payout)

#### All 13 Documents to Build

| # | Document | Trigger | Recipient | Status |
|---|----------|---------|-----------|--------|
| 1 | Credit Facility Agreement | Creator onboarding | Creator signs | Not built |
| 2 | Credit Limit Letter | Admin sets limit | Creator (email) | Not built |
| 3 | Advance Offer Letter | Deal scored | Creator reviews | Not built |
| 4 | Financing Agreement (per deal) | Creator accepts | Creator signs | Not built |
| 5 | Notice of Assignment (NOA) | Creator accepts | Brand finance email | Not built |
| 6 | Invoice (creator → brand) | Creator accepts | Brand | Not built |
| 7 | Disbursement Confirmation | Advance sent | Creator (email) | Not built |
| 8 | NOA Acknowledgment | Brand acknowledges | Athanni records | Not built |
| 9 | Payment Reminder x3 | D-14, D-7, D-1 | Brand (email) | Not built |
| 10 | Payment Receipt | Brand pays | Brand (email) | Not built |
| 11 | Deal Closure Confirmation | Deal repaid | Creator (email) | Not built |
| 12 | Overdue Notice x3 | D+1, D+7, D+30 | Brand (email) | Not built |
| 13 | Creator Liability Notice | D+7 overdue | Creator (email) | Not built |

#### Backend Tasks
- [ ] Install `weasyprint` or `reportlab` for PDF generation
- [ ] Create `backend/app/services/document_generator.py`
- [ ] Build all 13 document templates (Athanni branded)
- [ ] Add `payment_due_date` to deal model (deal_date + payment_terms_days)
- [ ] Wire docs into deal lifecycle endpoints
- [ ] NOA delivery: email to brand contact on deal advance
- [ ] Brand portal: show NOA acknowledgment button
- [ ] Maturity sweep: check payment_due_date, trigger reminders
- [ ] Wire all emails through Resend (add RESEND_API_KEY to .env)

---

## PHASE 4 — Social Media Metrics
**Goal:** Real Instagram + YouTube metrics feed into creator profiles (reference data for admin).
**Status:** NOT STARTED
**Needs bank account:** No

#### Instagram
- API: Instagram Graph API (official Meta, free)
- Requires: Business/Creator IG account + connected Facebook Page
- Need: Meta Developer App registered for Athanni (1–2 week approval)
- We get: followers, media_count, engagement rate, reach, impressions
- [ ] Register Meta Developer App
- [ ] Build Instagram OAuth connect flow (frontend button → backend token exchange)
- [ ] Store tokens encrypted per creator
- [ ] Pull + display real metrics on Profile page
- [ ] Show metrics as reference on admin creator detail view

#### YouTube
- API: YouTube Data API v3 (official Google, free — 10K units/day quota)
- [ ] Register Google Cloud project for Athanni
- [ ] Build YouTube OAuth connect flow
- [ ] Pull: subscribers, view_count, video_count, channel_age
- [ ] Display on Profile page

---

## PHASE 5 — KYC + Identity Verification
**Goal:** Legal compliance before disbursement.
**Status:** NOT STARTED
**Needs bank account:** No (KYC is identity only)

Recommended provider: **IDfy** (evaluate pricing) or **Signzy**
- PAN verification: ~₹2–5/call
- Aadhaar eKYC (OTP): ~₹5–15/verification

- [ ] Choose and onboard KYC provider
- [ ] PAN verification on creator onboarding
- [ ] Aadhaar eKYC (OTP-based)
- [ ] Add `kyc_status` to creator document (pending / verified / failed)
- [ ] Gate deal advance on kyc_status = verified
- [ ] Admin: view KYC status per creator, manual override if needed

---

## PHASE 6 — eSign Integration
**Goal:** All agreements legally signed.
**Status:** NOT STARTED
**Needs bank account:** No

Provider: **Leegality** (India's most-used fintech eSign) or **Digio**
Cost: ~₹30–50 per signed document

- [ ] Choose provider, get API keys
- [ ] Credit Facility Agreement: creator signs at onboarding
- [ ] Financing Agreement: creator signs before each deal advance
- [ ] NOA: brand signs/acknowledges via emailed link
- [ ] Store signed document URLs on creator/deal records

---

## PHASE 7 — Cloud Storage
**Goal:** Contracts and generated documents off /tmp and into persistent cloud storage.
**Status:** NOT STARTED
**Needs bank account:** No

Provider: **Cloudflare R2** (S3-compatible, no egress fees — cheaper than AWS S3)

- [ ] Set up R2 bucket
- [ ] Update `routers/contracts.py` — replace /tmp with R2 `put_object()`
- [ ] Replace `FileResponse` with presigned URL (time-limited, secure)
- [ ] Store doc URLs on deal/contract records

---

## PHASE 8 — Brand Verification (GST + MCA)
**Goal:** Validate brands are real registered Indian companies.
**Status:** Mock only
**Needs bank account:** No

Provider: **Surepass** — GST + PAN + company verification
Cost: ~₹1–5/call

- [ ] GST number verification on brand registration
- [ ] Company registration lookup via MCA21
- [ ] Admin: brand solvency tier based on verification

---

## PHASE 9 — Real Payments ← NEEDS BANK ACCOUNT
**Goal:** Real money movement — disbursements to creators, collections from brands.
**Status:** Stubbed
**Needs bank account:** YES — do not start until Athanni bank account is open

- [ ] Open Athanni business bank account
- [ ] Register on Razorpay (business account required)
- [ ] Get Razorpay API keys (rzp_test_xxx for testing)
- [ ] Get RazorpayX Payouts API keys (for creator disbursements)
- [ ] Activate `repay-checkout` endpoint in `routers/deals.py`
- [ ] Set PAYOUT_MODE=razorpay in .env
- [ ] Add Razorpay Payment Link option for brand (alternative to NEFT)
- [ ] Bank account details in .env → replace XXXXX placeholders
- [ ] Bank account penny drop verification for creator onboarding (needs Razorpay)
- [ ] Test full money flow end-to-end in Razorpay test mode

---

## PHASE 10 — Production Deployment ← NEEDS BANK ACCOUNT
**Goal:** Live on athanni.co.in
**Status:** NOT STARTED
**Needs bank account:** YES (Razorpay integration required for production)

- [ ] Purchase athanni.co.in domain
- [ ] Railway account (backend hosting)
- [ ] Vercel account (frontend hosting)
- [ ] MongoDB Atlas (managed Mongo) or PostgreSQL migration
- [ ] Set all env vars in Railway/Vercel dashboards
- [ ] Point DNS: athanni.co.in → Vercel, api.athanni.co.in → Railway
- [ ] SSL (automatic on both platforms)
- [ ] Seed admin account on production
- [ ] Smoke test full flow on live URL

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| May 2026 | Rebrand My Pay → Athanni | Stronger brand — coin reference fits AR financing |
| May 2026 | Frontend-first build order | Visual progress is motivating + needed for any investor/test-user demos |
| May 2026 | Credit limit = manual admin control | No scoring algorithm yet. Admin sets per creator. Keeps Phase 2 simple. |
| May 2026 | All docs = mock/template for Phase 3 | Get full flow working before real legal APIs |
| May 2026 | Instagram = Graph API (official OAuth) | Basic Display API deprecated Dec 2024. Graph API is free + official. |
| May 2026 | Phyllo = skip for MVP | Enterprise pricing, overkill for early stage |
| May 2026 | eSign = Leegality | Most used in Indian fintech |
| May 2026 | KYC = IDfy (evaluate) | Good API, reasonable early-stage pricing |
| May 2026 | File storage = Cloudflare R2 | No egress fees, S3-compatible, cheaper than AWS |
| May 2026 | Hosting = Railway + Vercel | No Docker needed, fast deployment |
| May 2026 | Bank-dependent features pushed to Phase 9–10 | No bank account yet. Everything before Phase 9 is buildable now. |

---

## Session Log

### Session 3 — May 2026
**Work done:**
- Finished Task 4: Wired AthanniLogo shared component into all remaining pages (Login, Register, Landing, BrandPortal, BrandRegister) — removed all inline `AthanniMark` SVG functions. Zero remaining `AthanniMark` consumers outside of AthanniLogo.jsx itself.
- Added `btn-brand` and `btn-brand-ghost` utility classes to index.css (Klein blue #002FA7)
- Phase 1 Task 5: Full Landing page overhaul — Direction C palette (ink + Klein blue). Key elements: blue "sixty days" italic, blue stats numbers, blue CTA buttons, blue risk score bar on credit memo card, 4-step pipeline, fee ladder table, full-bleed blue CTA footer section
- Phase 1 Task 6: Dashboard overhaul — Klein blue on credit limit, health score, usage bar, tier dot, tier progress bar, pipeline bars, "Connect accounts" CTA

**Decisions made:**
- Primary CTAs across the whole app = btn-brand (Klein blue #002FA7), not btn-primary (ink)
- btn-primary (ink black) reserved for secondary actions inside the app shell

**Next session should start with:** Continue Phase 1 — remaining pages: DealNew, DealDetail, DealsList, Profile, AdminPanel. Then Phase 2 (Admin credit limit control).

---

### Session 2 — May 2026
**Work done:**
- Completed full Phase 0 rebrand
- Find-and-replaced all "My Pay" / "mypay" / "MyPay" / "MYPAY_" across all backend + frontend source files
- Updated backend/.env: DB_NAME → athanni_dev, APP_NAME → athanni, bank fields → ATHANNI_*, SENDER_EMAIL → notifications@athanni.co.in
- Updated backend/app/config.py: all field names and defaults
- Updated backend/app/main.py, __init__.py, db.py: logger names, API title, boot message
- Updated backend/app/routers/deals.py, admin.py: bank details endpoint + email subject
- Updated backend/seed_admin.py: all defaults
- Updated backend/app/services/payout_service.py: narration string
- Updated frontend/index.html: title + meta description + favicon link
- Updated frontend/src/context/AuthContext.jsx + AuthContext.js: mypay_token → athanni_token
- Updated frontend/src/lib/api.js: token key
- Updated all 8 frontend pages: all "My Pay" → "Athanni" text references
- Updated CLAUDE_CONTEXT.md: all references
- Designed Athanni SVG logo: double-ring coin mark with italic ₹, + "athanni" wordmark in Instrument Serif
- Created frontend/public/athanni-logo.svg (black), athanni-logo-white.svg (white), favicon.svg (coin mark only)
- Wired AthanniMark inline SVG component into AppShell, Landing, Login, Register, BrandPortal, BrandRegister
- Confirmed 35/35 unit tests pass

**Decisions made:** None new — all Phase 0 decisions were already logged

**Next session should start with:** Phase 1 — Frontend UI Overhaul (start with Landing page, then Dashboard)

---

### Session 1 — May 2026
**Work done:**
- Full codebase audit and architecture review
- Brainstormed: rebrand, domain, UI redesign, Instagram API
- Mapped complete 9-phase deal lifecycle — all gaps identified
- Identified all 13 missing documents
- Researched social media APIs — Instagram Graph API chosen (Basic Display deprecated)
- Researched Phyllo pricing (custom/enterprise — skip for MVP)
- Created ATHANNI_ROADMAP.md
- Created MASTER_PROGRESS.md (this file)
- Restructured phases: frontend-first, bank-dependent features pushed to Phase 9–10

**Decisions made:** See Decisions Log above

**Next session should start with:** Phase 1 — Frontend UI Overhaul (start with Landing page, then Dashboard)

---

## How To Use This File (instructions for Claude)

1. Read this entire file before starting any work in this repo
2. Read CLAUDE_CONTEXT.md for full technical architecture + API reference
3. Find the first phase with incomplete tasks `[ ]` — that is where to start
4. Mark tasks `[x]` as you complete them
5. Add a new entry to Session Log at the end of every session
6. Add new decisions to Decisions Log as they are made
7. Never delete old entries — only add and update
8. If Akhi gives new instructions that change a phase, update that phase and log the decision

---

## Quick Reference — Where Things Live

| Thing | File/Location |
|-------|--------------|
| FastAPI app entry | `backend/app/main.py` |
| All routes | `backend/app/routers/` |
| Database repos | `backend/app/repos/` |
| Risk engine | `backend/app/services/ai/risk_decision/engine.py` |
| Credit limit logic | `backend/app/services/credit_limit.py` |
| Contract parser | `backend/app/services/contract_parser.py` |
| Payout service | `backend/app/services/payout_service.py` |
| Frontend pages | `frontend/src/pages/` |
| Auth context | `frontend/src/context/AuthContext.jsx` |
| API client | `frontend/src/lib/api.js` |
| Design system | `frontend/src/index.css` + `tailwind.config.js` |
| Backend env vars | `backend/.env` |
| Frontend env vars | `frontend/.env` |
| Run tests | `cd backend && pytest app/tests/unit/ -q` |

# Athanni — Master Progress & Session Continuity Doc

> **EVERY Claude session must read this file first, before touching any code.**
> Update the relevant section at the end of every session.
> Also read: CLAUDE_CONTEXT.md (architecture), ATHANNI_ROADMAP.md (product strategy)

---

## Project Identity

- **Product name:** Athanni (formerly My Pay — rebrand complete)
- **What it is:** AR financing platform for Indian creators. Creators upload brand deal invoices, Athanni advances 80% of invoice value immediately, collects 100% from the brand on the due date, and returns the remaining 20% to the creator minus fees and interest.
- **Primary market:** Indian creators + Indian/global brands. INR transactions.
- **Founder:** Akhi (animse66@gmail.com) — admin master account
- **Repo location (iCloud):** `/Users/wolfrag/Library/Mobile Documents/com~apple~CloudDocs/Desktop/myapp-main/`
- **Git remote:** `https://github.com/AkhiNimse66/myapp-main.git`
- **Domain (target):** athanni.co.in
- **Live deployment:** Frontend → https://myapp-main-xi.vercel.app · Backend → https://myapp-main-production.up.railway.app

> ⚠️ **Git note for Claude:** iCloud mount breaks git file locking. NEVER run git directly on the iCloud mount path. Always:
> 1. `git clone https://github.com/AkhiNimse66/myapp-main.git /tmp/myapp-local`
> 2. Edit files on iCloud mount via file tools
> 3. `cp` changed files into `/tmp/myapp-local`
> 4. Commit and push from `/tmp/myapp-local` using the GitHub token

---

## Current Stack

| Layer | Tech | Status |
|-------|------|--------|
| Backend | FastAPI (Python 3.10), async, Motor (MongoDB) | ✅ Live on Railway |
| Database | MongoDB Atlas (production) | ✅ Live |
| Auth | JWT (PyJWT), bcrypt, RBAC: creator / brand / admin / agency | ✅ Working |
| Frontend | React 19, Vite, Tailwind CSS v3, React Router v7 | ✅ Live on Vercel |
| Design | Luxury editorial — Instrument Serif + Geist + JetBrains Mono. NO rounded corners. 1px borders. No shadows. | ✅ Locked |
| Testing | pytest + pytest-asyncio. 35 unit tests. Must pass after every backend change. | ✅ 35/35 |

---

## Palette (locked — do not change)

| Token | Hex | Usage |
|-------|-----|-------|
| Navy | `#0D1B3E` | Nav background, page headers, primary buttons |
| Blue | `#2646B0` | Numbers, label accents, progress bars, active states |
| Copper | `#B87333` | Logo coin dot, premium CTAs, pricing highlights |
| White | `#FFFFFF` | Body background |
| Off-white | `#F7F8FC` | Card/panel backgrounds |

---

## The Business Model (critical context for every feature decision)

**Athanni is an invoice discounting / AR financing platform.**

```
CREATOR                    ATHANNI                    BRAND
   │                          │                          │
   │  Uploads brand invoice   │                          │
   │─────────────────────────▶│                          │
   │                          │  Verifies brand + deal   │
   │                          │  Scores creator health   │
   │                          │  Calculates advance rate │
   │                          │                          │
   │  Receives offer:         │                          │
   │  80% advance of invoice  │                          │
   │◀─────────────────────────│                          │
   │                          │                          │
   │  Signs docs + accepts    │                          │
   │─────────────────────────▶│                          │
   │                          │  Sends NOA to brand      │
   │                          │─────────────────────────▶│
   │                          │                          │
   │  Receives 80% wire       │                          │
   │  within 24 hours         │                          │
   │◀─────────────────────────│                          │
   │                          │                          │
   │  Creator delivers        │                          │
   │  content to brand        │                          │
   │─────────────────────────────────────────────────────▶│
   │                          │                          │
   │                          │  Brand pays 100%         │
   │                          │  on invoice due date     │
   │                          │◀─────────────────────────│
   │                          │                          │
   │  Athanni returns 20%     │                          │
   │  minus fees + interest   │                          │
   │◀─────────────────────────│                          │
```

**Key numbers (initial defaults until evaluated):**
- Advance rate: **80%** of invoice
- Wire ETA: **24 hours** (fixed, always displayed)
- Credit limit: standard placeholder → evaluated after underwriting docs reviewed
- Creator health score: placeholder → evaluated after underwriting docs reviewed
- Athanni fee: deducted from the 20% retained when brand pays

---

## Full Creator Journey (Product Flow — source of truth)

### Stage 1: Registration + Onboarding

1. Creator lands on homepage → clicks "Open account"
2. Fills basic registration (name, email, handle, password)
3. Account created → immediately enters **multi-step onboarding wizard** (not a wall, seamlessly integrated)

**Onboarding wizard collects (in order, with progress indicator):**

| Step | What we collect | Purpose |
|------|----------------|---------|
| 1 | Social handle + platform (Instagram/YouTube) | Creator identity |
| 2 | First invoice (PDF/image upload) | Underwriting anchor |
| 3 | Professional dashboard screenshot | Follower/engagement proof |
| 4 | Past brand collabs with brands (names + amounts) | Track record |
| 5 | Proof of income — last 3 months brand collab payments | Income verification |
| 6 | PAN card copy (upload) | KYC identity |
| 7 | CIBIL check consent + basic details | Credit history |
| 8 | Bank account details (account number + IFSC) | Disbursement setup |

**After wizard:**
- Creator lands on dashboard with **initial placeholder values**:
  - Credit limit: ₹50,000 (default placeholder)
  - Creator health: "Pending review"
  - Wire ETA: 24 hours (always fixed)
  - Advance rate: 80% (displayed as standard)
- Dashboard shows status: "Your documents are under review — we'll update your profile within 48 hours"
- Timeline tracker step 1 is active: **Profile submitted**

---

### Stage 2: Athanni Underwriting Review (Admin side)

1. Admin sees new creator in admin panel with "Docs pending review" status
2. Admin reviews all submitted documents
3. Admin sets:
   - **Credit limit** (₹ amount — how much total exposure Athanni takes with this creator)
   - **Creator health score** (0–100 composite score)
   - **Advance rate** (80% standard, can vary by risk)
   - **KYC status** (verified / pending / failed)
4. Creator dashboard updates with real evaluated values
5. Creator receives email: "Your Athanni profile is ready — here's your credit facility"
6. Creator receives: **Credit Facility Agreement** to sign

---

### Stage 3: Creator Submits a Deal

1. Creator goes to "New Deal"
2. Uploads the brand deal contract/invoice
3. Fills: brand name, invoice amount, payment terms (days), content due date
4. Submits → timeline tracker activates:

```
● Contract uploaded  ──  ● Brand verified  ──  ● Offer ready  ──  ○ Funded
```

---

### Stage 4: Athanni Evaluates & Makes Offer

1. System (+ admin) verifies the brand:
   - Is this brand real? (GST lookup, Phase 9)
   - Brand solvency score
   - Brand payment history with Athanni
2. System scores the deal and generates offer:
   - Advance amount = invoice amount × advance rate
   - Fee calculation
   - Net payout to creator
3. Dashboard updated: **Offer ready** milestone lights up
4. Creator sees offer card with:
   - Advance amount (₹)
   - Fee (% + ₹)
   - Net payout to you
   - Wire ETA: 24 hours
   - Brand score
   - Creator health score

---

### Stage 5: Creator Reviews + Accepts Offer

Documents generated and shown to creator **before** they accept:

| Doc | Purpose | Needs eSign? |
|-----|---------|-------------|
| MOU (Memorandum of Understanding) | Framework of the relationship | Yes — creator signs |
| NOA (Notice of Assignment) | Assigns invoice payment right to Athanni | Yes — creator + brand acknowledge |
| Master Sales Agreement | Governs all future deals | Yes — creator signs once |
| Term Sheet (per invoice) | Specific terms for this invoice | Yes — creator signs |
| Modified Invoice | Invoice reissued in Athanni's name as assignee | Creator receives |

Creator action: **Accept Offer** button (primary) or **Decline** (secondary, tracked but rare)

---

### Stage 6: Disbursement

1. Creator accepts → Athanni team is notified
2. Athanni initiates wire transfer (80% of invoice) to creator's bank account
3. Creator receives email: **Disbursement Confirmation** with UTR/reference number
4. Timeline: **Funded** milestone lights up
5. NOA sent to brand finance email: "Please remit invoice payment to Athanni's account on [due date]"

---

### Stage 7: Brand Pays Athanni

1. Brand receives NOA — knows to pay Athanni (not creator) on due date
2. Brand portal: brand can log in, see NOA, confirm payment, upload UTR
3. Athanni receives 100% of invoice on due date
4. Brand receives: **Payment Receipt** (email)

---

### Stage 8: Creator Collects Remaining 20%

1. Creator logs back into Athanni after invoice due date
2. Dashboard shows: "Your invoice has been paid — collect your remaining balance"
3. Creator sees:
   - Invoice total: ₹X
   - Already advanced: 80% = ₹Y
   - Remaining: 20% = ₹Z
   - Athanni fee: ₹F (interest + service charge)
   - **Net payout to you: ₹Z − ₹F**
4. Creator triggers collection → Athanni wires the balance
5. Deal status: **Closed**. Creator receives: **Deal Closure Confirmation** (email)

---

### Overdue Flow (if brand doesn't pay)

- D-14, D-7, D-1: Payment reminder emails to brand
- D+1: Overdue notice to brand
- D+7: Escalated overdue notice to brand + Creator Liability Notice to creator
- D+30: Final escalation

---

## Phase Overview

```
PHASE 0  →  Rebrand + Logo + Identity              ✅ COMPLETE
PHASE 1  →  Frontend UI Overhaul                   🔄 IN PROGRESS
PHASE 2  →  Admin Credit Limit Control             ✅ COMPLETE
PHASE 3  →  Creator Onboarding Wizard              ❌ NOT STARTED
PHASE 4  →  Deal Lifecycle + Document System       ❌ NOT STARTED
PHASE 5  →  Social Media Metrics                   ❌ NOT STARTED
PHASE 6  →  KYC + Identity Verification            ❌ NOT STARTED
PHASE 7  →  eSign Integration                      ❌ NOT STARTED
PHASE 8  →  Cloud Storage (R2)                     ❌ NOT STARTED
PHASE 9  →  Brand Verification (GST + MCA)         ❌ NOT STARTED
PHASE 10 →  Real Payments + Bank                   ❌ NEEDS BANK ACCOUNT
```

---

## PHASE 0 — Rebrand + Logo + Visual Identity
**Status:** ✅ COMPLETE

- [x] Find-and-replace all "My Pay" / "mypay" / "MyPay" across entire codebase
- [x] Updated DB_NAME: `mypay_dev` → `athanni_dev`
- [x] JWT_SECRET, email sender, all references updated
- [x] Frontend meta tags, page titles, Landing copy updated
- [x] README.md, CLAUDE_CONTEXT.md updated
- [x] AthanniLogo shared component (CSS coin-on-i wordmark with metallic radial gradient)
- [x] Favicon
- [x] 35/35 tests passing after rename

---

## PHASE 1 — Frontend UI Overhaul
**Status:** 🔄 IN PROGRESS
**Needs bank account:** No

### Design Principles (non-negotiable)
- Instrument Serif for all page headers and large display text
- `rounded-none` everywhere — absolutely no border radius
- 1px borders (`border border-zinc-200` or `border-zinc-800`), zero shadows
- JetBrains Mono for all rupee amounts, percentages, numbers
- Dense information — this is a financial product not a marketing site
- Palette: Navy + Blue + Copper (see locked palette above)

### Pages

#### 1.1 Landing Page (`Landing.jsx`) ✅ COMPLETE
- [x] Hero: "Get paid today. *Not in 90 days.*"
- [x] Subhead: "...wire up to **90%** of invoice value — same day"
- [x] Redesigned hero card: navy header, progress timeline (4 steps), brand + creator score bars, offer breakdown grid
- [x] Stats strip: ₹18.4Cr funded
- [x] Nav: "Open account" ghost button (removed "Get funded" copper button)
- [x] "How it works" 4-step grid
- [x] Fee ladder table
- [x] Navy CTA footer: "Get paid within 24 hours"
- [x] TrendingUp icon in pillars

#### 1.2 Login Page (`Login.jsx`) ✅ COMPLETE
- [x] Show/hide password toggle (Eye/EyeOff icon)
- [x] Right panel quote: "Stop waiting *90 days* for the wire."
- [x] Right panel stats: 90% Max advance · 24 hr Median wire · 2.5% Floor fee

#### 1.3 Register Page (`Register.jsx`) ✅ COMPLETE
- [x] Show/hide password toggle (Eye/EyeOff icon)

#### 1.4 Admin Panel (`AdminPanel.jsx`) ✅ COMPLETE
- [x] Users tab: search by name/email, filter by role, role change (with confirm), suspend/activate toggle
- [x] Creators tab: table with KYC/limit/tier/score/deal counts, expandable row with social metrics + deal breakdown + audit trail, "Set Limit" modal

#### 1.5 Dashboard (`Dashboard.jsx`) ✅ COMPLETE
- [x] Credit limit amount in blue
- [x] Credit limit usage bar in blue
- [x] Creator Health Index in blue
- [x] Tier progression — active dot + bar in blue
- [x] Pipeline stage bars in blue
- [x] "New Deal" CTA — btn-brand

#### 1.6 AppShell + Navigation ✅ COMPLETE
- [x] Dark navy header
- [x] AthanniLogo in nav
- [ ] Mobile nav (hamburger menu) — PENDING

#### 1.7 Deal New (`DealNew.jsx`) ❌ PENDING
Goal: Guided multi-step submission experience (not a bare form).
- [ ] Step indicator (1. Upload invoice → 2. Deal details → 3. Review & submit)
- [ ] Invoice/contract upload zone — drag & drop, file preview
- [ ] Brand selector — dropdown (existing brands) + "new brand" option
- [ ] Amount + terms inputs — inline validation, formatted in ₹
- [ ] Payment due date field (invoice date + N days)
- [ ] Review step — full summary before submit

#### 1.8 Deal Detail (`DealDetail.jsx`) ❌ PENDING
Goal: Clear offer page — creator understands and can act confidently.
- [ ] Offer card — advance amount (₹), fee, net payout — mono font, prominent
- [ ] Timeline tracker (matches screenshot: Contract → Brand verified → Offer ready → Funded)
- [ ] Brand score display
- [ ] Creator health display
- [ ] Document list (MOU, NOA, MSA, Term Sheet, Modified Invoice) with download/sign buttons
- [ ] "Accept Offer" (primary, navy/blue) + "Decline" (secondary, ghost) action buttons
- [ ] Repayment section (shown after funded): brand payment status, "Collect balance" trigger

#### 1.9 Deals List (`DealsList.jsx`) ❌ PENDING
- [ ] Table with status chips (Submitted / Brand verified / Offer ready / Funded / Repaid / Overdue)
- [ ] Filter bar — by status, date range, amount
- [ ] Empty state — prompt to submit first deal

#### 1.10 Profile Page (`Profile.jsx`) ❌ PENDING
- [ ] Social accounts section — connect Instagram, YouTube (OAuth buttons) — Phase 5 dependency
- [ ] KYC status indicator (Pending review / Verified / Action required)
- [ ] Payout method — UPI / bank account display (entered during onboarding)
- [ ] Credit limit display — set by admin, read-only for creator
- [ ] Advance rate — set by admin, read-only for creator
- [ ] Uploaded documents log (onboarding docs submitted)

#### 1.11 Brand Portal (`BrandPortal.jsx`) ❌ PENDING
- [ ] Deals assigned to this brand (NOA received)
- [ ] Invoice table — amount, due date, status
- [ ] Athanni bank details card (NEFT/RTGS — mock for now, real after Phase 10)
- [ ] UTR confirmation input — cleaner flow
- [ ] NOA acknowledgment button per deal
- [ ] Payment receipt download

---

## PHASE 2 — Admin Manual Credit Limit Control
**Status:** ✅ COMPLETE

### Backend ✅
- [x] `PATCH /api/admin/creators/{id}/credit-limit` — set limit with audit trail (credit_limit_set_by, credit_limit_set_at, credit_limit_notes)
- [x] `GET /api/admin/creators` — list all creators with limits + scores + deal counts
- [x] `GET /api/admin/creators/{id}` — full detail with deals + transactions
- [x] `GET /api/admin/users` — all users across all roles
- [x] `PATCH /api/admin/users/{user_id}/role` — with last-admin guard
- [x] `PATCH /api/admin/users/{user_id}/status` — activate/suspend
- [x] `PATCH /api/admin/users/promote-by-email` — promote any email to any role (used to make animse66@gmail.com admin)

### Frontend ✅
- [x] AdminPanel: Users tab (search, filter, role change, suspend/activate)
- [x] AdminPanel: Creators tab (expandable rows, Set Limit modal, audit trail)

---

## PHASE 3 — Creator Onboarding Wizard
**Status:** ❌ NOT STARTED
**Needs bank account:** No
**Priority:** HIGH — this is the core of the creator funnel

### Goal
After basic registration, creator is guided through a seamless 8-step document collection wizard. UX must feel like a modern fintech onboarding (Cred / Zepto-style steps) — not a form dump. Progress bar at top, one step at a time, each step has a clear purpose explained to the creator.

### Backend Tasks
- [ ] New model: `OnboardingDocument` — track each doc type, upload status, admin review status
- [ ] New endpoint: `POST /api/creators/onboarding/upload` — accepts doc_type + file
- [ ] New endpoint: `GET /api/creators/onboarding/status` — returns step completion status
- [ ] New endpoint: `PATCH /api/admin/creators/{id}/underwriting` — admin sets credit_limit, health_score, advance_rate, kyc_status after reviewing docs
- [ ] Add to creator model: `onboarding_complete: bool`, `onboarding_step: int`, `kyc_status`, `advance_rate`, `underwriting_reviewed_at`, `underwriting_reviewed_by`
- [ ] Email trigger: when admin completes underwriting → creator receives "Your profile is ready" email with Credit Facility Agreement

### Frontend Tasks
- [ ] New page: `Onboarding.jsx` — wizard with 8 steps
- [ ] Step 1: Social handle + platform selector
- [ ] Step 2: First invoice upload (PDF/JPG/PNG, drag & drop)
- [ ] Step 3: Professional dashboard screenshot upload (with explainer text: "Screenshot of your Instagram/YouTube analytics")
- [ ] Step 4: Past brand collabs — simple list (brand name + amount + date, add multiple)
- [ ] Step 5: Proof of income — last 3 months collab payment proofs (multi-file upload)
- [ ] Step 6: PAN card upload (with PAN number field for auto-verification in Phase 6)
- [ ] Step 7: CIBIL consent checkbox + basic details (name, DOB, mobile — for CIBIL pull in Phase 6)
- [ ] Step 8: Bank account details (account number, IFSC, account holder name)
- [ ] After wizard: redirect to dashboard showing "Under review" state
- [ ] Dashboard banner: "Documents under review · Typically 48 hours" with progress indicator
- [ ] Route guard: if onboarding not complete, redirect to wizard before any deal submission

### Onboarding Documents Reference

| Step | Document / Data | Format | Auto-verify? |
|------|----------------|--------|-------------|
| 1 | Social handle + platform | Text | Phase 5 (OAuth) |
| 2 | First invoice | PDF/Image | OCR (Phase 4) |
| 3 | Professional dashboard screenshot | Image | Manual review |
| 4 | Past brand collabs | Structured form | Manual review |
| 5 | Proof of income (3 months) | PDF/Image (multi) | Manual review |
| 6 | PAN card | Image/PDF | IDfy API (Phase 6) |
| 7 | CIBIL consent + details | Form | CIBIL API (Phase 6) |
| 8 | Bank account | Form | Penny drop (Phase 10) |

---

## PHASE 4 — Deal Lifecycle + Document System
**Status:** ❌ NOT STARTED
**Needs bank account:** No (disbursement is mock for now)

### Goal
Every step of the deal lifecycle — from invoice upload to final collection — is tracked, documented, and communicated. A complete deal runs end-to-end with real PDFs and real emails.

### Deal Status State Machine

```
submitted → brand_verified → offer_ready → accepted → funded → repaid → closed
                                              └──────→ declined → closed
                                                                    
(overdue track: funded → overdue → escalated → legal)
```

### Timeline Tracker UI (reference: screenshot)
```
● Contract ── ● Brand verified ── ● Offer ready ── ○ Funded
```
All 4 steps shown on DealDetail page header, with active/complete/pending states.

### All 13 Documents to Build

| # | Document | Trigger | Recipient | Needs eSign? | Status |
|---|----------|---------|-----------|-------------|--------|
| 1 | Credit Facility Agreement | Admin completes underwriting | Creator signs | Yes | Not built |
| 2 | Credit Limit Letter | Admin sets credit limit | Creator (email) | No | Not built |
| 3 | Advance Offer Letter | Deal scored, offer ready | Creator reviews | No | Not built |
| 4 | MOU (Memorandum of Understanding) | Offer accepted | Creator signs | Yes | Not built |
| 5 | NOA (Notice of Assignment) | Offer accepted | Creator signs + Brand receives | Yes | Not built |
| 6 | Master Sales Agreement | First deal (once only) | Creator signs | Yes | Not built |
| 7 | Term Sheet (per invoice) | Offer accepted | Creator signs | Yes | Not built |
| 8 | Modified Invoice | Offer accepted | Creator receives | No | Not built |
| 9 | Disbursement Confirmation | Advance wired | Creator (email) | No | Not built |
| 10 | Payment Reminder ×3 | D-14, D-7, D-1 | Brand (email) | No | Not built |
| 11 | Payment Receipt | Brand pays | Brand (email) | No | Not built |
| 12 | Deal Closure Confirmation | Creator collects balance | Creator (email) | No | Not built |
| 13 | Overdue Notice ×3 | D+1, D+7, D+30 | Brand + Creator | No | Not built |

### Backend Tasks
- [ ] Install `weasyprint` or `reportlab` for PDF generation
- [ ] Create `backend/app/services/document_generator.py`
- [ ] Build all 13 document templates (Athanni-branded)
- [ ] Add `payment_due_date` to deal model (deal_date + payment_terms_days)
- [ ] Add `brand_score` to deal model (from brand verification)
- [ ] Add deal status transitions with timestamps
- [ ] New endpoint: `POST /api/deals/{id}/accept` — creator accepts offer, triggers doc generation + NOA email to brand
- [ ] New endpoint: `POST /api/deals/{id}/decline` — creator declines, deal closed
- [ ] New endpoint: `POST /api/deals/{id}/collect-balance` — creator triggers final 20% collection
- [ ] Maturity sweep: cron/scheduler checks payment_due_date, triggers reminders
- [ ] Wire all emails through Resend (add RESEND_API_KEY to .env)
- [ ] NOA email delivery to brand finance contact on deal acceptance

### Frontend Tasks
- [ ] DealDetail.jsx — see Phase 1.8 above
- [ ] Deal acceptance modal — shows all docs, confirm button
- [ ] Document viewer — inline PDF preview or download links
- [ ] "Collect balance" flow — shows breakdown (invoice total, advanced, fee, net)

---

## PHASE 5 — Social Media Metrics
**Status:** ❌ NOT STARTED
**Needs bank account:** No

### Instagram
- API: Instagram Graph API (official Meta, free)
- Requires: Business/Creator IG account + connected Facebook Page + Meta Developer App for Athanni
- Approval timeline: 1–2 weeks
- Data: followers, media_count, engagement rate, reach, impressions

- [ ] Register Meta Developer App for Athanni
- [ ] Build Instagram OAuth connect flow (frontend button → backend token exchange)
- [ ] Store access tokens encrypted per creator
- [ ] Pull + display real metrics on Profile page
- [ ] Show metrics as reference on admin creator detail view
- [ ] Refresh tokens on schedule (long-lived tokens last 60 days)

### YouTube
- API: YouTube Data API v3 (free — 10K units/day quota)
- [ ] Register Google Cloud project for Athanni
- [ ] Build YouTube OAuth connect flow
- [ ] Pull: subscribers, view_count, video_count, channel_age
- [ ] Display on Profile page

---

## PHASE 6 — KYC + Identity Verification
**Status:** ❌ NOT STARTED
**Needs bank account:** No
**Note:** Integrated into onboarding wizard (Phase 3). This phase adds real API verification.

Recommended provider: **IDfy** (evaluate pricing) or **Signzy**
- PAN verification: ~₹2–5/call
- CIBIL check: per pull pricing

- [ ] Choose and onboard KYC provider (IDfy preferred)
- [ ] PAN verification API — called when creator submits PAN in onboarding step 6
- [ ] CIBIL check — pulled from onboarding step 7 details
- [ ] Add `pan_verified`, `cibil_score`, `kyc_status` to creator document
- [ ] Gate deal advance on `kyc_status = verified`
- [ ] Admin: view KYC status per creator, manual override if needed
- [ ] Show KYC status on creator dashboard + admin panel

---

## PHASE 7 — eSign Integration
**Status:** ❌ NOT STARTED
**Needs bank account:** No

Provider: **Leegality** (India's most-used fintech eSign) or **Digio**
Cost: ~₹30–50 per signed document

Documents requiring eSign (from Phase 4):
- Credit Facility Agreement (creator, at onboarding completion)
- MOU (creator, per deal)
- NOA (creator signs; brand acknowledges via emailed link)
- Master Sales Agreement (creator, first deal only)
- Term Sheet (creator, per deal)

- [ ] Choose provider, get API keys
- [ ] Build eSign request flow: generate doc → send signing request → webhook on completion
- [ ] Store signed document URLs on creator/deal records
- [ ] Block deal progression until required docs are signed
- [ ] Admin: view signing status per deal

---

## PHASE 8 — Cloud Storage
**Status:** ❌ NOT STARTED (partial workaround in place)
**Needs bank account:** No

**Current state:** Contract files stored as base64 in MongoDB (works, not ideal for large files)
**Target:** Cloudflare R2 (S3-compatible, no egress fees)

- [ ] Set up R2 bucket on Cloudflare
- [ ] Update `routers/contracts.py` — replace base64-in-MongoDB with R2 `put_object()`
- [ ] Replace base64 serving with presigned URL (time-limited, secure)
- [ ] Store R2 object keys on contract/deal records
- [ ] Also store generated PDFs (Phase 4) and signed docs (Phase 7) in R2

---

## PHASE 9 — Brand Verification (GST + MCA)
**Status:** Mock only (seed data has mock brands)
**Needs bank account:** No

Provider: **Surepass** — GST + PAN + company verification API
Cost: ~₹1–5/call

- [ ] GST number field on brand registration
- [ ] GST verification API on brand registration submit
- [ ] Company registration lookup via MCA21
- [ ] Add `gst_verified`, `mca_verified`, `solvency_tier` to brand document
- [ ] Brand solvency tier feeds into deal brand score (admin reference)
- [ ] Admin: view brand verification status per brand
- [ ] Show brand score on DealDetail page for creator

---

## PHASE 10 — Real Payments ← NEEDS BANK ACCOUNT
**Status:** Stubbed / mock
**Needs bank account:** YES — do not start until Athanni business bank account is open

- [ ] Open Athanni business bank account (mandatory prerequisite)
- [ ] Register on Razorpay (business account required)
- [ ] Get Razorpay API keys (rzp_test_xxx first)
- [ ] Get RazorpayX Payouts API keys (for creator disbursements)
- [ ] Activate `repay-checkout` endpoint in `routers/deals.py`
- [ ] Set PAYOUT_MODE=razorpay in .env
- [ ] Add Razorpay Payment Link option for brand (alternative to NEFT)
- [ ] Bank account details in .env → replace XXXXX placeholders
- [ ] Bank account penny drop verification for creator onboarding bank details
- [ ] Test full money flow end-to-end in Razorpay test mode
- [ ] athanni.co.in domain purchased + DNS pointed

---

## Deployment Reference (current live setup)

| Service | URL / Config |
|---------|-------------|
| Frontend | https://myapp-main-xi.vercel.app (Vercel auto-deploys from main branch) |
| Backend | https://myapp-main-production.up.railway.app (Railway auto-deploys from main branch) |
| Database | MongoDB Atlas (cluster connected via MONGO_URI in Railway env) |
| Backend env vars | MONGO_URI, JWT_SECRET, CORS_ORIGINS, SEED_KEY, RESEND_API_KEY (pending) |
| Frontend env vars | VITE_BACKEND_URL=https://myapp-main-production.up.railway.app |
| Admin account | animse66@gmail.com (promoted to admin via /api/admin/users/promote-by-email) |

**Seed endpoint (use carefully):**
- `GET /api/seed-demo?key={SEED_KEY}` — seeds demo data (safe, does not wipe)
- `GET /api/seed-demo?key={SEED_KEY}&force=true&confirm_wipe=yes` — wipes + reseeds (DESTRUCTIVE)

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| May 2026 | Rebrand My Pay → Athanni | Stronger brand — coin reference fits AR financing |
| May 2026 | Frontend-first build order | Visual progress needed for investor/user demos |
| May 2026 | Credit limit = manual admin control | No scoring algorithm yet. Admin sets per creator. |
| May 2026 | All docs = template/mock for Phase 4 | Get full flow working before real legal APIs |
| May 2026 | Instagram = Graph API (official OAuth) | Basic Display API deprecated Dec 2024 |
| May 2026 | Phyllo = skip for MVP | Enterprise pricing, overkill for early stage |
| May 2026 | eSign = Leegality | Most used in Indian fintech |
| May 2026 | KYC = IDfy (evaluate) | Good API, reasonable early-stage pricing |
| May 2026 | File storage = Cloudflare R2 | No egress fees, S3-compatible |
| May 2026 | Hosting = Railway + Vercel | No Docker needed, fast deployment |
| May 2026 | Bank-dependent features → Phase 10 only | No bank account yet. Everything before is buildable now. |
| May 2026 | Palette = Navy + Blue + Copper | White #FFF + Navy #0D1B3E + Blue #2646B0 + Copper #B87333 |
| May 2026 | Logo = CSS-based coin-on-i wordmark | SVG text-metric approach was fragile. CSS absolute positioning is reliable. |
| May 2026 | railway.toml = pip install over uv sync | uv sync --frozen has cross-platform lockfile risks on Railway Linux |
| May 2026 | VITE_BACKEND_URL for frontend env var | Vite uses import.meta.env.VITE_* not process.env.REACT_APP_* |
| May 2026 | Contract files = base64 in MongoDB | Eliminates /tmp data loss on Railway redeploy. R2 migration in Phase 8. |
| May 2026 | Advance rate = 80% (standard) | Industry standard for invoice discounting. Adjustable per creator by admin. |
| May 2026 | Wire ETA = 24 hours (fixed marketing claim) | Achievable with manual ops. Fixed in all UI copy. |
| May 2026 | Hero copy = "Not in 90 days" | 90 days = industry standard brand payment terms. The pain point we solve. |
| May 2026 | Onboarding = seamless wizard (Phase 3) | Document collection must feel like Cred/fintech onboarding, not a form dump |
| May 2026 | Git workflow = clone to /tmp, never run git on iCloud mount | iCloud FUSE filesystem breaks git file locking. /tmp clone → copy → push is reliable. |

---

## Session Log

### Session 5 — May 2026
**Work done:**

*UI Polish (all pushed to GitHub → Vercel live):*
- `Landing.jsx` — full rewrite: hero "Not in 90 days" (90 days = industry pain, we solve it), redesigned hero card with navy header / progress timeline / brand+creator score bars / offer breakdown grid, stats → ₹18.4Cr, nav → ghost "Open account" (removed copper "Get funded" btn), fee ladder best rate 90%, CTA "Get paid within 24 hours"
- `Login.jsx` — show/hide password toggle (Eye/EyeOff from lucide-react), right panel: "Stop waiting *90 days* for the wire", stats: 90% max advance / 24hr median wire / 2.5% floor fee
- `Register.jsx` — show/hide password toggle (Eye/EyeOff from lucide-react)

*Git infrastructure fix:*
- Diagnosed: iCloud Drive mount breaks git file locking (FUSE limitation → "Resource deadlock avoided" bus error)
- Established permanent workaround: `git clone` to `/tmp/myapp-local` → copy files → commit → push with GitHub token. This is now the standard workflow for all sessions.
- Pushed all three files successfully from /tmp clone

*Product flow clarification (from Akhi):*
- Confirmed business model: Athanni advances 80% → brand pays 100% to Athanni → creator collects remaining 20% minus fees
- Hero contrast = "today vs 90 days" (industry wait time), wire stat = 24hr
- Onboarding wizard: 8-step document collection during account creation
- Deal lifecycle: 4-step timeline tracker (Contract → Brand verified → Offer ready → Funded)
- 5 documents generated on deal acceptance: MOU, NOA, Master Sales Agreement, Term Sheet, Modified Invoice
- Creator collects remaining 20% after brand pays Athanni

*Master doc:*
- Full rewrite: updated phase statuses, added business model flow diagram, full creator journey, new Phase 3 (Onboarding Wizard), restructured Phase 4 (Deal Lifecycle + Documents), updated all decisions

**Decisions made:**
- Hero copy = "Not in 90 days" (90 days is the industry pain point)
- Wire ETA = 24 hours (fixed in all UI copy)
- Advance rate = 80% displayed as standard
- Onboarding = Phase 3 (seamless 8-step wizard, not a form wall)
- Git = always use /tmp clone workflow (never run git on iCloud mount)

**Next session:**
- Brainstorm approach to Phase 3 (Creator Onboarding Wizard) with Akhi
- Then build Phase 3 backend + frontend
- Remaining Phase 1 pages: DealNew, DealDetail, DealsList, Profile, BrandPortal

---

### Session 4 — May 2026
**Work done:**

*Deployment:*
- Fixed `backend/railway.toml`: `uv sync --frozen` → `pip install -r requirements.txt`, added healthcheckTimeout=30
- Fixed `frontend/vercel.json`: added `"framework":"vite"`, `npm install --legacy-peer-deps`
- Deployed: Frontend → Vercel (myapp-main-xi.vercel.app), Backend → Railway, DB → MongoDB Atlas
- Diagnosed and fixed "invalid login" — missing seed data in production; ran `/api/seed-demo`
- Confirmed admin + creator logins working via curl

*Phase 2 — Admin Credit Control:*
- Built `PATCH /api/admin/creators/{id}/credit-limit` with full audit trail
- Built `GET /api/admin/creators`, `GET /api/admin/creators/{id}`
- Built `GET /api/admin/users`, `PATCH /api/admin/users/{id}/role`, `PATCH /api/admin/users/{id}/status`
- Built `PATCH /api/admin/users/promote-by-email` — promoted animse66@gmail.com to admin
- Built AdminPanel Users tab and Creators tab in React

*Data persistence:*
- Moved contract file storage from `/tmp` (ephemeral on Railway) to base64 in MongoDB — zero data loss on redeploy
- Hardened seed endpoint: SEED_KEY from env var + `confirm_wipe=yes` guard

**Next session:** UI polish → then Phase 3 (Onboarding Wizard)

---

### Session 3 — May 2026
**Work done:**
- AthanniLogo shared component wired into all pages
- CSS coin-on-i wordmark with metallic radial gradient (reliable cross font-load)
- Palette locked: Navy #0D1B3E + Blue #2646B0 + Copper #B87333
- Landing.jsx — full first overhaul
- Dashboard.jsx — blue colour pass
- AppShell.jsx — dark navy header
- index.css — palette tokens, btn-copper, btn-brand-ghost, chip-copper
- 35/35 tests passing

---

### Session 2 — May 2026
**Work done:**
- Full Phase 0 rebrand — all "My Pay" → "Athanni" across entire codebase
- AthanniLogo SVG component created
- Confirmed 35/35 tests pass

---

### Session 1 — May 2026
**Work done:**
- Full codebase audit + architecture review
- Mapped 9-phase deal lifecycle, all gaps identified
- Identified all 13 missing documents
- Researched social media APIs
- Created ATHANNI_ROADMAP.md + MASTER_PROGRESS.md
- Restructured phases: frontend-first, bank-dependent features pushed to end

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
| Document generator | `backend/app/services/document_generator.py` (Phase 4 — not built yet) |
| Frontend pages | `frontend/src/pages/` |
| Auth context | `frontend/src/context/AuthContext.jsx` |
| API client | `frontend/src/lib/api.js` |
| Design system | `frontend/src/index.css` + `tailwind.config.js` |
| Backend env vars | `backend/.env` (local) · Railway dashboard (production) |
| Frontend env vars | `frontend/.env` (local) · Vercel dashboard (production) |
| Run tests | `cd backend && pytest app/tests/unit/ -q` |
| Seed demo data | `GET /api/seed-demo?key={SEED_KEY}` |
| Promote to admin | `PATCH /api/admin/users/promote-by-email` body: `{"email":"...","role":"admin"}` |

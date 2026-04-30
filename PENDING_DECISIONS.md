# My Pay — Pending Decisions & Integration Stubs

This file tracks every architectural decision that is deferred, every
third-party integration that is stubbed, and where exactly in the codebase
to go when the decision is made.  Update this file when a decision lands.

---

## 1. Payment Architecture — Two Separate Flows (decided)

### 1a. Brand → My Pay (Manual Bank Transfer)
**Decision:** NEFT / RTGS / IMPS manual transfer. No payment gateway needed.
**Status:** ✅ Built. Brand sees My Pay bank details in DealDetail, clicks "I've transferred", deal moves to `awaiting_payment`. Admin marks repaid.

**To go live:** Update `backend/.env` with real account details:
```
MYPAY_BANK_NAME=HDFC Bank
MYPAY_ACCOUNT_NAME=My Pay Technologies Pvt Ltd
MYPAY_ACCOUNT_NUMBER=50200012345678
MYPAY_IFSC=HDFC0001234
MYPAY_ACCOUNT_TYPE=Current
MYPAY_UPI_ID=mypay@hdfcbank
```

### 1b. My Pay → Creator (Payout Service)
**Decision:** Razorpay Payouts API (RazorpayX current account). Mock mode active now.
**Status:** ✅ Built. `backend/app/services/payout_service.py`. Creator registers UPI/bank on Profile. On deal advance, payout initiates automatically.

**To activate real payouts:**
```
PAYOUT_MODE=razorpay
RAZORPAY_KEY_ID=rzp_live_xxx
RAZORPAY_KEY_SECRET=xxx
RAZORPAY_PAYOUT_ACCOUNT_NUMBER=<RazorpayX account number>
```
Also: `pip install razorpay`

### 1c. Gateway (future — for international or brand online payment)
**Decision:** Razorpay payment gateway for online brand payments (future).
**Status:** Stub in place. Waiting for Razorpay API keys.

**What to do when key arrives:**
- Get keys from https://dashboard.razorpay.com
- Add to `backend/.env`:
  ```
  RAZORPAY_KEY_ID=rzp_test_xxx
  RAZORPAY_KEY_SECRET=xxx
  ```
- Edit: `backend/app/routers/deals.py`
  - Find: `POST /api/deals/{id}/repay-checkout`
  - Replace stub with real Razorpay order creation:
    ```python
    import razorpay
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    order = client.order.create({"amount": int(deal_amount * 100), "currency": "INR", ...})
    ```
- Edit: `backend/app/routers/payments.py`
  - Replace stub `GET /api/payments/status/{session_id}` with real Razorpay order fetch
- Edit: `frontend/src/pages/DealDetail.jsx`
  - The repay button and poll loop are already wired — just update the checkout URL handling

**Stripe (international, future):**
- Add `STRIPE_SECRET_KEY` to `.env`
- Same files above — add currency check: INR → Razorpay, USD/EUR → Stripe

---

## 2. LLM for Contract Parsing — ✅ Shipped in mock mode

**Decision:** Anthropic Claude (claude-sonnet-4-6) — recommended.
**Status:** Parser built and wired in. Running in mock mode. One env var flip to go live.

**File:** `backend/app/services/contract_parser.py`
**Called by:** `POST /api/deals/{id}/analyze` — result stored as `deal.ai_analysis`
**Renders in:** `DealDetail.jsx` ai_analysis panel (already built)

**To activate real Claude parsing:**
```
# backend/.env
CONTRACT_PARSER_MODE=claude
ANTHROPIC_API_KEY=sk-ant-xxx
```
Run: `pip install anthropic`

**To activate OpenAI instead:**
```
CONTRACT_PARSER_MODE=openai
OPENAI_API_KEY=sk-xxx
```
Run: `pip install openai`

**Next extension — PDF OCR (text extraction from uploaded PDFs):**
- The parser already handles pasted text. For PDFs:
- Install: `pip install pypdf2` (or `pdfminer.six` for better layout preservation)
- Edit: `backend/app/routers/contracts.py` — after saving file, extract text:
  ```python
  from pypdf import PdfReader
  import io
  reader = PdfReader(io.BytesIO(file_bytes))
  extracted = " ".join(p.extract_text() or "" for p in reader.pages)
  # save extracted to contract record, pass to parse_contract(contract_text=extracted)
  ```
- Then pass the extracted text when creating the deal

---

## 3. Social Media Data — Phyllo API (decided) / Direct Instagram (rejected)

**Decision:** Phyllo (usephyllo.com) for Instagram, TikTok, YouTube, X metrics.
Direct Instagram Graph API rejected — Meta App Review too slow for MVP.
**Status:** Mock scoring in place. Creator manually enters metrics on Profile page.

**What to do when key arrives:**
- Sign up at https://usephyllo.com (sandbox tier available)
- Add to `backend/.env`:
  ```
  PHYLLO_CLIENT_ID=xxx
  PHYLLO_SECRET=xxx
  PHYLLO_ENV=sandbox   # switch to production when live
  ```
- Edit: `backend/app/services/ai/providers/creator_intel.py`
  - Find `CreatorIntelMode.MOCK` block
  - Add `CreatorIntelMode.PHYLLO` that calls Phyllo SDK
  - Set `CREATOR_INTEL_MODE=phyllo` in `.env` to activate
- Edit: `backend/app/routers/creator.py`
  - `POST /api/creator/social/connect` → initiate Phyllo OAuth SDK flow
  - Add `GET /api/creator/social/sync` → pull latest metrics from Phyllo and write to social_profiles
- The Profile page connect buttons are already wired and waiting

---

## 4. Database — PostgreSQL for Production (decided, deferred)

**Decision:** MongoDB for local/MVP. Migrate to PostgreSQL before production launch.
**Status:** All data logic is behind repository classes — migration is isolated.

**What to do when ready to migrate:**
- All DB logic lives in `backend/app/repos/` — swap Motor calls for SQLAlchemy async
- Key repos: users_repo, deals_repo, creators_repo, transactions_repo, events_repo
- Use Supabase (easiest) or AWS RDS PostgreSQL
- Add `pgAudit` extension for financial audit trail
- Enable Row Level Security on deals and transactions tables
- Column-level encryption via `pgcrypto` for: contract values, personal identifiers
- The `BaseRepo` in `backend/app/repos/base.py` is the only file that needs
  the Motor→SQLAlchemy swap; all other repos inherit from it

---

## 5. File Storage — S3 / Cloudflare R2 (undecided)

**Decision:** Pending. S3 for AWS-hosted, R2 for cheaper egress if on Cloudflare.
**Status:** Contracts stored in `/tmp/mypay_uploads` (disappears on restart).

**What to do when decided:**
- Add to `backend/.env`:
  ```
  AWS_ACCESS_KEY_ID=xxx
  AWS_SECRET_ACCESS_KEY=xxx
  S3_BUCKET_NAME=mypay-contracts
  S3_REGION=ap-south-1
  # OR for R2:
  R2_ACCOUNT_ID=xxx
  R2_ACCESS_KEY=xxx
  R2_SECRET_KEY=xxx
  R2_BUCKET=mypay-contracts
  ```
- Edit: `backend/app/routers/contracts.py`
  - Find comment `# Temp storage dir — in production this is replaced by S3 pre-signed upload`
  - Replace `open(local_path, "wb")` write with `boto3 s3.put_object()`
  - Replace `FileResponse` download with `s3.generate_presigned_url()`
- The contract metadata (id, filename, mime, size) is already stored in MongoDB —
  only the binary storage location changes

---

## 6. Email Provider — Resend (decided, pending key)

**Decision:** Resend (resend.com) — already integrated in mock mode.
**Status:** Emails are mocked and logged to `email_log` collection.

**What to do when key arrives:**
- Add to `backend/.env`:
  ```
  RESEND_API_KEY=re_xxx
  SENDER_EMAIL=notifications@mypay.io
  ```
- The email worker will automatically switch from mock to live sends
- No code changes needed — the `RESEND_API_KEY` check is already in the email service
- Templates to build: deal_scored, disbursement_sent, maturity_reminder, repayment_confirmed

---

## 7. Docker / Deployment (deferred)

**Decision:** Skip Docker for local development. Add before first production deploy.
**Status:** Not started.

**When ready:**
- Add `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`
- Services: fastapi, react (nginx), mongodb (dev only — use Atlas in prod)
- MongoDB Atlas for production DB (or RDS PostgreSQL after migration #4)
- Target platforms: Railway (easiest), Fly.io, DigitalOcean App Platform, AWS ECS

---

---

## 8. Brand Signup Flow — Model B (Self-Initiated, future)

**Decision:** Model A (admin-pushed tokens) is the current approach — admin generates a token in the UI and manually sends it to the brand rep. This is sufficient for MVP.

**Model B (future — brand-initiated onboarding):**
Brand rep fills in an interest/onboarding form on a public page (`/brand/apply`).
Admin reviews the application in the Admin panel → Brands tab.
On approval, system automatically emails the signup token via Resend.
Brand clicks the link in the email, lands on `/brand/register?token=xxx` with the token pre-filled.

**Why this matters:** Model A requires admin intervention for every brand. At scale, Model B is needed for self-serve onboarding without bottlenecking on admin.

**What to build when ready:**
- New public route: `frontend/src/pages/BrandApply.jsx` — interest form (company name, contact, website, GST, note)
- New backend endpoint: `POST /api/brands/apply` (no auth) — creates a `brand_applications` collection entry with status `pending`
- New Admin panel feature: Applications sub-tab under Brands tab — shows pending applications, approve/reject
- On approve: auto-call `POST /api/auth/admin/brand-token` internally + trigger Resend email with the token link
- Email template needed: `brand_invite` — "You've been approved, here's your signup link"
- Requires: `RESEND_API_KEY` configured (see decision #6)

**Files to edit when ready:**
- `backend/app/routers/brands.py` — add `/apply` endpoint
- `backend/app/routers/auth.py` — approve endpoint that issues token + fires email
- `frontend/src/pages/AdminPanel.jsx` — Applications sub-tab
- `frontend/src/pages/BrandApply.jsx` — new file
- `backend/app/repos/` — new `brand_applications_repo.py`

---

## Summary Table

| # | Decision | Status | Blocker |
|---|----------|--------|---------|
| 1 | Payment gateway | Razorpay ✓ | API keys |
| 2 | LLM / contract parsing | ✅ Shipped (mock) | ANTHROPIC_API_KEY to go live |
| 3 | Social data | Phyllo ✓ | API keys |
| 4 | Database (production) | PostgreSQL ✓ | Deploy time |
| 5 | File storage | S3 or R2 | Decision + keys |
| 6 | Email | Resend ✓ | API key |
| 7 | Docker / deploy | Deferred | Deploy time |
| 8 | PDF OCR (text extraction) | Not started | pypdf install + contracts.py edit |
| 9 | Brand onboarding Model B (self-initiated) | Deferred | Resend API key + admin UI build |

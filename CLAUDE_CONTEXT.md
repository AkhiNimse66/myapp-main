# Athanni — Complete Project Context for New Claude Sessions

Read this entire file before doing anything. It is the single source of truth
for the project state, architecture, decisions made, and what to build next.

---

## What Is Athanni

A creator financing platform — AR (Accounts Receivable) financing for
influencers. Creators upload brand deal contracts, Athanni advances them up to
80% of the deal value instantly, and collects from the brand when the invoice
matures. Similar to invoice discounting / factoring but for the creator economy.

**Core flow:**
1. Creator registers → gets a revolving credit limit based on social metrics
2. Creator uploads a brand deal contract (PDF/image)
3. System scores the deal (brand solvency + creator health → risk score)
4. Creator accepts the offer → receives advance (minus discount fee) instantly
5. Brand pays Athanni on maturity → creator's credit limit is recycled

**Primary market:** Indian creators + Indian/global brands (INR transactions)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.10), async, Motor (MongoDB) |
| Database | MongoDB (local dev), PostgreSQL planned for production |
| Auth | JWT (PyJWT), bcrypt passwords, role-based (creator/brand/admin/agency) |
| Frontend | React 19, Vite, Tailwind CSS v3, React Router v7 |
| Design | Luxury editorial — Instrument Serif + Geist + JetBrains Mono |
| Testing | pytest + pytest-asyncio, 35 unit tests passing |

---

## Repository Structure

```
myapp-main/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory, mounts all routers
│   │   ├── config.py            # Pydantic settings (reads .env)
│   │   ├── db.py                # Motor client + index bootstrap
│   │   ├── deps.py              # FastAPI dependencies (get_current_user, require_role)
│   │   ├── enums.py             # DealStatus, Role, TxnKind enums
│   │   ├── security.py          # hash_password, verify_password, make_token
│   │   ├── repos/               # Repository pattern — one class per collection
│   │   │   ├── base.py          # BaseRepo — all Motor logic here
│   │   │   ├── users_repo.py
│   │   │   ├── creators_repo.py
│   │   │   ├── deals_repo.py
│   │   │   ├── brands_repo.py
│   │   │   ├── social_repo.py
│   │   │   ├── contracts_repo.py
│   │   │   ├── transactions_repo.py
│   │   │   ├── events_repo.py
│   │   │   ├── emails_repo.py
│   │   │   └── agencies_repo.py
│   │   ├── routers/             # One file per domain
│   │   │   ├── auth.py          # POST /register, /login, GET /me
│   │   │   ├── deals.py         # Full deal lifecycle
│   │   │   ├── brands.py        # Brand list + seed
│   │   │   ├── creator.py       # Creator profile + social connect
│   │   │   ├── dashboard.py     # Rich dashboard summary
│   │   │   ├── contracts.py     # File upload/download
│   │   │   ├── admin.py         # Admin ops + ML stubs
│   │   │   └── payments.py      # Stripe/Razorpay stub
│   │   ├── schemas/             # Pydantic v2 request/response schemas
│   │   │   ├── auth.py
│   │   │   ├── deal.py
│   │   │   └── user.py
│   │   ├── services/
│   │   │   ├── credit_limit.py  # Credit limit engine (health score → INR tiers)
│   │   │   └── ai/              # Risk decision engine
│   │   │       ├── factory.py
│   │   │       ├── interfaces.py
│   │   │       ├── engine.py
│   │   │       └── providers/   # mock/fixed_mvp implementations
│   │   └── tests/unit/          # 35 passing tests
│   ├── .env                     # Local dev config (see below)
│   └── requirements.txt         # Cleaned — no emergentintegrations
│
├── frontend/
│   ├── src/
│   │   ├── App.js               # Routes: /, /login, /register, /dashboard,
│   │   │                        #   /deals, /deals/new, /deals/:id,
│   │   │                        #   /profile, /admin
│   │   ├── index.js             # Vite entry point
│   │   ├── context/
│   │   │   └── AuthContext.js   # JWT auth state, login/register/logout
│   │   ├── lib/
│   │   │   └── api.js           # Axios instance + money/pct/compact helpers
│   │   ├── components/
│   │   │   ├── AppShell.jsx     # Nav + layout wrapper
│   │   │   └── RiskGauge.jsx    # SVG risk score gauge
│   │   └── pages/
│   │       ├── Landing.jsx      # Public marketing page
│   │       ├── Login.jsx        # Luxury dark right panel
│   │       ├── Register.jsx     # Luxury dark right panel
│   │       ├── Dashboard.jsx    # 4 stats + tier progression + pipeline + social
│   │       ├── DealNew.jsx      # Contract submission form
│   │       ├── DealDetail.jsx   # Full deal view + risk + repayment
│   │       ├── DealsList.jsx    # Filterable deals table
│   │       ├── Profile.jsx      # Social metrics + live credit preview
│   │       └── AdminPanel.jsx   # Risk ops + ML ops + email log
│   ├── index.html               # Vite root HTML (clean, no Emergent junk)
│   ├── vite.config.js           # Vite config, @ alias → src/
│   ├── .env                     # VITE_BACKEND_URL=http://localhost:8000
│   ├── tailwind.config.js
│   └── package.json             # Vite-based, no react-scripts/craco
│
├── PENDING_DECISIONS.md         # All deferred integrations with exact edit locations
├── CLAUDE_CONTEXT.md            # This file
└── HOW_TO_RUN.md               # Step-by-step local setup guide
```

---

## Backend .env (exact contents needed to run)

```
MONGO_URL=mongodb://localhost:27017
DB_NAME=athanni_dev
JWT_SECRET=athanni-super-secret-key-change-in-production-32c
JWT_ALGO=HS256
JWT_EXPIRE_HOURS=72
APP_NAME=athanni
CORS_ORIGINS=http://localhost:3000
CREATOR_INTEL_MODE=mock
BRAND_INTEL_MODE=mock
COMPLIANCE_MODE=mock
RISK_POLICY=fixed_mvp
ENGINE_VERSION=1.0.0
STRIPE_API_KEY=
RESEND_API_KEY=
SENDER_EMAIL=notifications@athanni.co.in
```

---

## Key Architectural Decisions

### Motor import guards (CRITICAL — do not remove)
All Motor/pymongo imports are wrapped in `TYPE_CHECKING` guards:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase
```
This prevents pyOpenSSL breaking at import time in tests. Production is fine.
`import pymongo.errors` is deferred inside function bodies, not at module scope.

### Repository pattern
All DB logic is in `repos/`. Nothing outside `repos/` touches MongoDB directly.
`BaseRepo` in `repos/base.py` is the only file with Motor calls.
When migrating to PostgreSQL, only `BaseRepo` needs to change.

### Risk engine (fixed MVP policy, no ML)
`RISK_POLICY=fixed_mvp` → `FixedMVPPolicy`: 80% advance rate, 3% fee, ₹10L max.
All ML tabs in AdminPanel are stubs — they show plausible mock data.
`CREATOR_INTEL_MODE=mock` and `BRAND_INTEL_MODE=mock` use synthetic scores.

### Credit limit tiers (INR)
Computed by `services/credit_limit.py`. Tiers:
- Score 0–30:  Starter  → ₹50,000
- Score 30–50: Rising   → ₹1,50,000
- Score 50–70: Growth   → ₹4,00,000
- Score 70–85: Premium  → ₹10,00,000
- Score 85–100: Elite   → ₹25,00,000
Recomputed every time creator saves social metrics on Profile page.
Initial limit on registration: ₹50,000 (starter).

### Authentication flow
- POST /api/auth/register → returns `{ access_token, user_id, role, name }`
- POST /api/auth/login → same shape
- Token stored in `localStorage` as `athanni_token`
- GET /api/auth/me → returns full user + role profile
- Frontend: `AuthContext.js` calls /login then /me, stores token, sets user state

### Deal state machine
uploaded → scored → disbursed → awaiting_payment → repaid
                              ↘ rejected (at scoring stage)

### Frontend env vars
Vite uses `import.meta.env.VITE_*` not `process.env.REACT_APP_*`.
The only env var needed: `VITE_BACKEND_URL=http://localhost:8000`

---

## API Endpoints Reference

### Auth
- POST /api/auth/register
- POST /api/auth/login
- GET  /api/auth/me
- POST /api/auth/admin/brand-token  (admin only)

### Deals
- GET  /api/deals
- POST /api/deals
- GET  /api/deals/{id}
- GET  /api/deals/bank-details        (Athanni's bank account for NEFT/RTGS from brand)
- POST /api/deals/{id}/analyze        (runs risk engine + contract parser)
- POST /api/deals/{id}/advance        (creator accepts → disburse → payout to creator)
- POST /api/deals/{id}/repay-checkout (stub → Razorpay gateway when key arrives)
- POST /api/deals/{id}/brand-confirm-payment  (brand says they've wired NEFT/RTGS)

### Brands
- GET  /api/brands
- GET  /api/brands/{id}
- POST /api/brands/seed             (no auth — seeds 5 demo brands)

### Creator
- GET   /api/creator/profile
- PATCH /api/creator/profile        (recomputes credit limit)
- GET   /api/creator/payout-method  (returns masked payout method)
- PATCH /api/creator/payout-method  (register UPI ID or bank account)
- POST  /api/creator/social/connect (Phyllo stub)

### Dashboard
- GET /api/dashboard/summary        (rich payload with pipeline + tier progression)

### Contracts
- POST /api/contracts/upload
- GET  /api/contracts/{id}/download

### Admin
- GET  /api/admin/stats
- GET  /api/admin/deals
- GET  /api/admin/emails
- POST /api/admin/maturity-sweep
- POST /api/admin/deals/{id}/override
- POST /api/admin/deals/{id}/mark-repaid
- POST /api/admin/deals/{id}/mark-default
- GET  /api/admin/ml/drift
- POST /api/admin/ml/retrain
- GET  /api/ml/status

### Payments
- GET /api/payments/status/{session_id}  (Razorpay stub)

---

## Design System

**Fonts:** Instrument Serif (headers), Geist (body), JetBrains Mono (labels/numbers)
**Palette:** #0A0A0A ink, #002FA7 brand blue, #FAFAFA background, zinc scale for grays
**Style rules:**
- `rounded-none` everywhere — no border radius
- 1px borders (`hair` class) not shadows
- `label-xs` = uppercase tracking-wider text-xs
- `serif` = Instrument Serif class
- `mono` = JetBrains Mono class
- `btn-primary` = filled black button
- `btn-ghost` = outlined button
- `card-flat` = flat bordered card
- `input-hair` = 1px border input
- `chip`, `chip-ok`, `chip-warn`, `chip-bad`, `chip-brand` = status badges
- `dense` = compact table class
- `row-hover` = table row hover

---

## Pending Integrations (see PENDING_DECISIONS.md for exact edit locations)

| Integration | Status | Files to edit when ready |
|-------------|--------|--------------------------|
| Razorpay payments | Needs API key | `routers/deals.py`, `routers/payments.py`, `DealDetail.jsx` |
| LLM contract parsing | Needs API key (Claude recommended) | Create `services/ai/providers/contract_parser.py`, edit `routers/deals.py` |
| Phyllo social data | Needs API key | `services/ai/providers/creator_intel.py`, `routers/creator.py` |
| S3/R2 file storage | Decision pending | `routers/contracts.py` (replace /tmp with boto3) |
| Resend email | Needs API key | Already wired, just add RESEND_API_KEY to .env |
| PostgreSQL migration | Before production | Only `repos/base.py` needs changing |
| Docker | Before production | Not started |

---

## What Has Been Built (completed)

- [x] Full repository layer (10 repos, BaseRepo pattern)
- [x] Auth + RBAC (creator/brand/admin/agency roles, JWT, brand signup tokens)
- [x] Deal lifecycle (create → analyze → advance → repay-checkout)
- [x] Risk engine (FixedMVPPolicy: 80% advance, 3% fee, mock scoring)
- [x] Credit limit engine (health score → INR tiers, live preview on Profile)
- [x] Dashboard (stats, tier progression visualiser, deal pipeline, social intel card)
- [x] Admin panel (portfolio, override, mark-repaid, mark-default, ML stubs, email log)
- [x] Contract upload (local /tmp storage, metadata in DB)
- [x] Brand management (seed endpoint, dropdown for deal form)
- [x] Frontend auth (Login, Register with luxury dark panels)
- [x] Profile page (social metrics, live credit preview, connect accounts stub)
- [x] 35 unit tests passing
- [x] Vite migration (removed react-scripts/craco, works on Node 22)
- [x] Cleaned all Emergent AI artifacts from codebase
- [x] Vite JSX config fully resolved — app runs at localhost:3000
      - Created src/index.jsx, src/App.jsx, src/context/AuthContext.jsx (proper .jsx extensions)
      - Old .js stubs contain only comments; resolve.extensions puts .jsx before .js
      - postcss.config.js and tailwind.config.js converted to ESM (export default)
      - public/index.html replaced with comment-only placeholder (was old Emergent CRA file)
      - index.html entry point updated to /src/index.jsx
      - vite.config.js: plain react(), resolve.extensions [.jsx before .js], optimizeDeps loader
- [x] INR currency formatting — money() now returns ₹ with en-IN locale; moneyCompact() added
- [x] Payment architecture (two flows):
      - Brand → Athanni: manual bank transfer (NEFT/RTGS/IMPS). Brand sees Athanni account details
        in DealDetail, clicks "I've transferred ₹X", enters UTR, deal moves to awaiting_payment.
        Admin marks repaid. Bank details are XXXXX placeholders in .env — update when account opens.
        New endpoint: POST /api/deals/{id}/brand-confirm-payment
        New endpoint: GET /api/deals/bank-details
      - Athanni → Creator: Payout service `backend/app/services/payout_service.py`.
        PAYOUT_MODE=mock (instant synthetic) or razorpay (RazorpayX Payouts API).
        Creator registers UPI ID or bank account on Profile page → stored as payout_method on creator doc.
        On advance accept, payout initiates automatically; payout result stored on deal.payout.
        New endpoints: PATCH/GET /api/creator/payout-method
- [x] Contract parser service — `backend/app/services/contract_parser.py`
      - mock mode: deterministic synthetic analysis (no API key needed)
      - claude mode: Anthropic claude-sonnet-4-6 (set ANTHROPIC_API_KEY + CONTRACT_PARSER_MODE=claude)
      - openai mode: gpt-4o fallback (set OPENAI_API_KEY + CONTRACT_PARSER_MODE=openai)
      - Wired into POST /api/deals/{id}/analyze — ai_analysis stored on deal, shown in DealDetail.jsx
      - Graceful degradation: if API key missing or LLM errors, falls back to mock silently

---

## What Has Been Built (continued)

- [x] Admin seed script — `backend/seed_admin.py`
      Run once: `cd backend && python seed_admin.py`
      Creates admin@athanni.co.in (or override via ADMIN_EMAIL/ADMIN_PASSWORD env vars). Idempotent.
      After running, log in at /login — routes to /admin automatically.
- [x] Admin Brands tab — full brand management in AdminPanel.jsx
      - Token generation form (brand name + notes → one-time UUID token)
      - Tokens list with copy button + revoke (DELETE /api/admin/brand-tokens/{token})
      - All registered brands table (name, industry, tier, solvency, deal count, verified status)
      - New backend endpoints: GET/POST /api/admin/brands, GET/POST/DELETE /api/admin/brand-tokens
- [x] Brand registration page — `frontend/src/pages/BrandRegister.jsx` at `/brand/register`
      - 2-step form: Step 1 (token + credentials), Step 2 (company details)
      - Fields: signup_token, contact_name, email, password, company_name, website,
        industry (dropdown), company_type (dropdown), GST number, PAN number, phone, billing_email
      - Token can be pre-filled via ?token= query param (for when we send invite links)
      - Luxury dark right panel matching creator register design
- [x] Extended brand schema — `backend/app/schemas/auth.py` + `routers/auth.py`
      New fields on RegisterRequest: brand_company_name, brand_industry, brand_company_type,
      brand_gst_number, brand_pan_number, brand_phone, brand_billing_email
      All stored on the brands collection document after registration.
- [x] Role-aware routing — `frontend/src/App.jsx`
      admin  → /admin (after login)
      brand  → /brand-portal (after login)
      creator → /dashboard (after login)
      RoleRedirect on /login and /register: logged-in users skip auth forms.
      Protected component accepts role= prop or legacy adminOnly=.
- [x] Brand portal — `frontend/src/pages/BrandPortal.jsx` at `/brand-portal`
      - Summary stats: open invoices, outstanding amount, total deals
      - Athanni bank details card (NEFT/RTGS wire info, dark panel)
      - Open invoices table with "Confirm payment" button → UTR modal
      - Settled deals history table
      - Standalone layout (no AppShell — brand has its own header with logout)
      - Backend: GET /api/brands/my-deals (returns brand profile + all their deals)

---

## What To Build Next (priority order)

### 1. ✅ Contract parser — DONE
Built in `backend/app/services/contract_parser.py`. Running in mock mode.
To activate real LLM parsing: add ANTHROPIC_API_KEY to backend/.env and set CONTRACT_PARSER_MODE=claude.
If you have a PDF contract (not just pasted text), the next step is OCR:
- Install `pypdf2` or `pdfminer.six`, extract text in `routers/contracts.py` upload endpoint
- Store extracted text on the contract record, pass to `parse_contract()` via `contract_text`

### 2. Razorpay payment integration (HIGH — closes the money loop)
- Needs: Razorpay API keys (rzp_test_xxx)
- Edit: `backend/app/routers/deals.py` → repay-checkout endpoint
- Edit: `backend/app/routers/payments.py` → status polling endpoint
- Frontend: DealDetail.jsx repay flow is already wired

### 3. Phyllo social data integration (MEDIUM)
- Needs: Phyllo API keys
- Edit: `backend/app/services/ai/providers/creator_intel.py`
- Edit: `backend/app/routers/creator.py` → social/connect endpoint
- The Profile page connect buttons are already built

### 4. Admin brand management UI (MEDIUM)
- Currently brands are only created via POST /api/brands/seed
- Need: Admin UI to create/edit individual brands with proper solvency data
- Edit: `frontend/src/pages/AdminPanel.jsx` — add a Brands tab

### 5. S3/R2 file storage (MEDIUM — needed before production)
- Edit: `backend/app/routers/contracts.py`
- Replace /tmp writes with boto3 s3.put_object()
- Replace FileResponse with presigned URL

### 6. Stripe/Razorpay webhook (after payment integration)
- Needed to auto-mark deals as repaid when brand pays
- Create: `backend/app/routers/webhooks.py`

### 7. PostgreSQL migration (before production launch)
- Edit: `backend/app/repos/base.py` → swap Motor for SQLAlchemy async
- All other repos inherit BaseRepo → zero changes needed elsewhere

---

## How To Run Locally

```bash
# Terminal 1 — MongoDB
brew services start mongodb-community
# or: docker run -d -p 27017:27017 --name athanni-mongo mongo:7

# Terminal 2 — Backend
cd ~/Desktop/myapp-main/backend
source .venv/bin/activate   # create with: python3 -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 3 — Seed brands (once, after backend starts)
curl -X POST http://localhost:8000/api/brands/seed

# Terminal 4 — Frontend
cd ~/Desktop/myapp-main/frontend
npm install --legacy-peer-deps   # first time only
npm start
# Opens at http://localhost:3000
```

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `NotImplementedError: Database objects do not implement truth value` | `db or get_db()` in db.py | Use `if db is None: db = get_db()` |
| `Cannot find module 'ajv/dist/compile/codegen'` | react-scripts incompatible with Node 22 | Migrated to Vite — resolved |
| `emergentintegrations not found` | Legacy Emergent AI package | Removed from requirements.txt |
| `@emergentbase/visual-edits not found` | Legacy Emergent AI devDep | Removed from package.json |
| `Address already in use (port 8000)` | Old backend process running | `lsof -ti:8000 \| xargs kill -9` |
| `403 on /api/brands/seed` | Was admin-only | Removed auth requirement |
| `X509_V_FLAG_NOTIFY_POLICY AttributeError` | pyOpenSSL 21 + cryptography 46 | TYPE_CHECKING guards on Motor imports |

---

## Notes for Next Claude Session

- The user's name is Akhi
- The repo is at `/Users/wolfrag/Desktop/myapp-main/`
- Always read this file + PENDING_DECISIONS.md before starting work
- The design system is non-negotiable — luxury editorial, no rounded corners,
  no shadows, 1px borders, Instrument Serif for headings
- Currency is INR for the Indian market (the money() helper uses USD display
  currently — this needs updating to INR formatting when convenient)
- The ML tabs in admin are intentional stubs — do not try to wire real ML
- All 35 tests must pass after any backend change: `pytest app/tests/unit/ -q`
- Motor imports must always be under TYPE_CHECKING — never at module scope

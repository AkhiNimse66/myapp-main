"""
Athanni — Demo Seed Script
===========================
Seeds mock admin, creator, brand logins, and invoices for demos.

Run from backend/ folder with venv active:
    python seed_demo.py

Reads MONGO_URL and DB_NAME from backend/.env automatically.
Override via env vars if needed:
    MONGO_URL="mongodb+srv://..." DB_NAME="athanni_prod" python seed_demo.py
"""

import os
import uuid
import bcrypt
from datetime import datetime, timezone, timedelta
from pathlib import Path
from pymongo import MongoClient

# ── Load .env from backend/ directory ────────────────────────────────────────
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _, _val = _line.partition("=")
            os.environ.setdefault(_key.strip(), _val.strip())

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME   = os.environ.get("DB_NAME",   "athanni_dev")

client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=8_000)
db     = client[DB_NAME]

def now(offset_days=0):
    return (datetime.now(timezone.utc) + timedelta(days=offset_days)).isoformat()

def hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(12)).decode()

def uid():
    return str(uuid.uuid4())

print(f"\n  Athanni — Seeding demo data into [{DB_NAME}]...\n")

# ── Wipe all demo data ────────────────────────────────────────────────────────
DEMO_EMAILS = [
    "admin@athanni.co.in",
    "demo.creator@athanni.co.in",
    "demo.brand@nykaa.com",
    # legacy emails (clean up if they exist from old My Pay seed)
    "admin@mypay.io",
    "demo.creator@mypay.io",
]
for email in DEMO_EMAILS:
    user = db.users.find_one({"email": email})
    if user:
        db.creators.delete_many({"user_id": user["id"]})
        db.social_profiles.delete_many({"user_id": user["id"]})
        db.deals.delete_many({"creator_id": {"$exists": True}})

db.users.delete_many({"email": {"$in": DEMO_EMAILS}})
db.brands.delete_many({})
db.transactions.delete_many({})
db.deal_events.delete_many({})
db.brand_signup_tokens.delete_many({})
print("  Cleared previous demo data")

# ── 1. Brands ─────────────────────────────────────────────────────────────────
brands = [
    {
        "id": "gymshark",
        "name": "Gymshark",
        "brand_risk_score": 88,
        "payment_reliability": "high",
        "industry": "fitness",
        "verified": True,
        "contact_email": "finance@gymshark.com",
        "created_at": now(),
    },
    {
        "id": "nykaa",
        "name": "Nykaa",
        "brand_risk_score": 85,
        "payment_reliability": "high",
        "industry": "beauty",
        "verified": True,
        "contact_email": "finance@nykaa.com",
        "created_at": now(),
    },
    {
        "id": "boat",
        "name": "boAt",
        "brand_risk_score": 79,
        "payment_reliability": "medium",
        "industry": "consumer electronics",
        "verified": True,
        "contact_email": "finance@boat-lifestyle.com",
        "created_at": now(),
    },
    {
        "id": "mamaearth",
        "name": "Mamaearth",
        "brand_risk_score": 81,
        "payment_reliability": "high",
        "industry": "personal care",
        "verified": True,
        "contact_email": "finance@mamaearth.in",
        "created_at": now(),
    },
    {
        "id": "sugar",
        "name": "Sugar Cosmetics",
        "brand_risk_score": 76,
        "payment_reliability": "medium",
        "industry": "cosmetics",
        "verified": True,
        "contact_email": "finance@sugarcosmetics.com",
        "created_at": now(),
    },
]
db.brands.insert_many(brands)
print(f"  Seeded {len(brands)} brands")

# ── 2. Admin user ─────────────────────────────────────────────────────────────
admin_id = uid()
db.users.insert_one({
    "id": admin_id,
    "email": "admin@athanni.co.in",
    "password_hash": hash_pw("athanni-admin-2024"),
    "name": "Akhi — Athanni Admin",
    "role": "admin",
    "status": "active",
    "kyc_status": "verified",
    "created_at": now(-30),
    "updated_at": now(),
})
print("  Admin    →  admin@athanni.co.in  /  athanni-admin-2024")

# ── 3. Demo Creator — Priya Sharma ────────────────────────────────────────────
creator_user_id = uid()
creator_id      = uid()

db.users.insert_one({
    "id": creator_user_id,
    "email": "demo.creator@athanni.co.in",
    "password_hash": hash_pw("Demo1234!"),
    "name": "Priya Sharma",
    "role": "creator",
    "status": "active",
    "kyc_status": "verified",
    "created_at": now(-60),
    "updated_at": now(),
})

db.creators.insert_one({
    "id": creator_id,
    "user_id": creator_user_id,
    "name": "Priya Sharma",
    "handle": "@priyasharmalifestyle",
    "agency_id": None,
    "credit_limit": 500000,
    "creator_score": 78.4,
    "credit_tier": "Premium",
    "kyc_status": "verified",
    "pan_number": "ABCDE1234F",
    "bank_account": {
        "account_number": "XXXX XXXX 4521",
        "ifsc": "HDFC0001234",
        "bank_name": "HDFC Bank",
    },
    "created_at": now(-60),
    "updated_at": now(),
})

db.social_profiles.insert_one({
    "id": uid(),
    "creator_id": creator_id,
    "user_id": creator_user_id,
    "instagram_handle": "@priyasharmalifestyle",
    "followers": 248000,
    "following": 1200,
    "engagement_rate": 4.7,
    "authenticity_score": 82,
    "last_synced_at": now(-1),
    "platform": "instagram",
})
print("  Creator  →  demo.creator@athanni.co.in  /  Demo1234!")

# ── 4. Mock Deals (invoices) ──────────────────────────────────────────────────

# Deal 1 — AWAITING_PAYMENT (funded, brand owes Athanni)
deal1_id = uid()
db.deals.insert_one({
    "id": deal1_id,
    "creator_id": creator_id,
    "user_id": creator_user_id,
    "brand_id": "gymshark",
    "brand_name": "Gymshark",
    "deal_title": "Gymshark Q2 Fitness Campaign",
    "deal_amount": 200000.0,
    "advance_amount": 170000.0,
    "discount_fee": 6000.0,
    "advance_rate": 0.85,
    "currency": "INR",
    "status": "awaiting_payment",
    "payment_terms_days": 30,
    "maturity_date": now(22),
    "disbursed_at": now(-8),
    "risk_decision": {
        "approved": True,
        "score": 81,
        "engine_version": "1.0.0",
        "reasons": [
            "High brand risk score (88)",
            "Strong creator engagement (4.7%)",
            "Verified KYC",
        ],
    },
    "created_at": now(-8),
    "updated_at": now(-8),
})
db.transactions.insert_one({
    "id": uid(),
    "deal_id": deal1_id,
    "kind": "disbursement",
    "amount": 170000,
    "currency": "INR",
    "provider": "mock",
    "status": "paid",
    "note": "Advance disbursed to creator bank account — mock payout",
    "created_at": now(-8),
})
db.deal_events.insert_many([
    {"deal_id": deal1_id, "event_type": "uploaded",  "actor_id": creator_user_id, "at": now(-9)},
    {"deal_id": deal1_id, "event_type": "approved",  "actor_id": admin_id, "at": now(-8), "note": "Risk score 81 — auto-approved"},
    {"deal_id": deal1_id, "event_type": "disbursed", "actor_id": admin_id, "at": now(-8), "note": "INR 1,70,000 sent to HDFC Bank"},
])

# Deal 2 — REPAID (fully completed with Nykaa)
deal2_id = uid()
db.deals.insert_one({
    "id": deal2_id,
    "creator_id": creator_id,
    "user_id": creator_user_id,
    "brand_id": "nykaa",
    "brand_name": "Nykaa",
    "deal_title": "Nykaa Beauty Spring Collection",
    "deal_amount": 120000.0,
    "advance_amount": 102000.0,
    "discount_fee": 3600.0,
    "advance_rate": 0.85,
    "currency": "INR",
    "status": "repaid",
    "payment_terms_days": 30,
    "maturity_date": now(-15),
    "disbursed_at": now(-55),
    "repaid_at": now(-15),
    "risk_decision": {
        "approved": True,
        "score": 79,
        "engine_version": "1.0.0",
        "reasons": [
            "Established brand (Nykaa)",
            "Creator score 78.4",
            "Clean history",
        ],
    },
    "created_at": now(-55),
    "updated_at": now(-15),
})
db.transactions.insert_many([
    {
        "id": uid(), "deal_id": deal2_id,
        "kind": "disbursement", "amount": 102000, "currency": "INR",
        "provider": "mock", "status": "paid",
        "note": "Advance disbursed — mock payout",
        "created_at": now(-55),
    },
    {
        "id": uid(), "deal_id": deal2_id,
        "kind": "repayment", "amount": 120000, "currency": "INR",
        "provider": "neft", "status": "paid",
        "note": "Full repayment received from Nykaa",
        "created_at": now(-15),
    },
    {
        "id": uid(), "deal_id": deal2_id,
        "kind": "fee_capture", "amount": 3600, "currency": "INR",
        "provider": "internal", "status": "paid",
        "note": "Athanni discount fee — 3% of advance",
        "created_at": now(-15),
    },
])

# Deal 3 — UPLOADED (just submitted, pending underwriting)
deal3_id = uid()
db.deals.insert_one({
    "id": deal3_id,
    "creator_id": creator_id,
    "user_id": creator_user_id,
    "brand_id": "mamaearth",
    "brand_name": "Mamaearth",
    "deal_title": "Mamaearth Skincare — YouTube + Reels Pack",
    "deal_amount": 85000.0,
    "advance_amount": None,
    "discount_fee": None,
    "advance_rate": None,
    "currency": "INR",
    "status": "uploaded",
    "payment_terms_days": 30,
    "maturity_date": now(30),
    "risk_decision": None,
    "created_at": now(-1),
    "updated_at": now(-1),
})

print("  Seeded 3 mock deals  (awaiting_payment, repaid, uploaded)")

# ── 5. Brand signup tokens (for brand portal demo) ────────────────────────────
db.brand_signup_tokens.insert_many([
    {
        "token": "NYKAA-DEMO-2026",
        "brand_id": "nykaa",
        "brand_name": "Nykaa",
        "used": False,
        "created_at": now(),
        "notes": "Demo token for Nykaa brand portal login",
    },
    {
        "token": "GYMSHARK-DEMO-2026",
        "brand_id": "gymshark",
        "brand_name": "Gymshark",
        "used": False,
        "created_at": now(),
        "notes": "Demo token for Gymshark brand portal login",
    },
])
print("  Seeded 2 brand signup tokens")

# ── Done ──────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("  Athanni — Demo seed complete!")
print("=" * 60)
print()
print("  ADMIN LOGIN")
print("  Email    :  admin@athanni.co.in")
print("  Password :  athanni-admin-2024")
print()
print("  CREATOR LOGIN (mock — Priya Sharma)")
print("  Email    :  demo.creator@athanni.co.in")
print("  Password :  Demo1234!")
print()
print("  BRAND PORTAL SIGNUP TOKENS")
print("  Nykaa    :  NYKAA-DEMO-2026")
print("  Gymshark :  GYMSHARK-DEMO-2026")
print()
print("  App URL  :  https://myapp-main-xi.vercel.app")
print()

client.close()

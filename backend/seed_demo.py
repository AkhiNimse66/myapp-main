"""
My Pay — Production Demo Seed Script
=====================================
Run from backend/ folder with venv active:
    python seed_demo.py
"""

import uuid
import bcrypt
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

MONGO_URL = "mongodb+srv://myapp_admin:Wolfrag66@myapp.1o0ae3n.mongodb.net/mypay_prod?appName=myapp"
DB_NAME   = "mypay_prod"

client = MongoClient(MONGO_URL)
db     = client[DB_NAME]

def now(offset_days=0):
    return (datetime.now(timezone.utc) + timedelta(days=offset_days)).isoformat()

def hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(12)).decode()

def uid():
    return str(uuid.uuid4())

print("\n🌱 My Pay — Seeding production demo data...\n")

# ── Wipe all demo data ────────────────────────────────────────────────────────
DEMO_EMAILS = ["admin@mypay.io", "demo.creator@mypay.io"]
for email in DEMO_EMAILS:
    user = db.users.find_one({"email": email})
    if user:
        db.creators.delete_many({"user_id": user["id"]})
        db.social_profiles.delete_many({"user_id": user["id"]})
        db.deals.delete_many({"user_id": user["id"]})

db.users.delete_many({"email": {"$in": DEMO_EMAILS}})
db.brands.delete_many({})
db.transactions.delete_many({})
db.deal_events.delete_many({})
db.brand_signup_tokens.delete_many({})
print("  ✓ Cleared previous demo data")

# ── 1. Brands ─────────────────────────────────────────────────────────────────
brands = [
    {"id": "gymshark",  "name": "Gymshark",        "brand_risk_score": 88, "payment_reliability": "high",   "industry": "fitness",             "verified": True, "created_at": now()},
    {"id": "nykaa",     "name": "Nykaa",            "brand_risk_score": 85, "payment_reliability": "high",   "industry": "beauty",              "verified": True, "created_at": now()},
    {"id": "boat",      "name": "boAt",             "brand_risk_score": 79, "payment_reliability": "medium", "industry": "consumer electronics","verified": True, "created_at": now()},
    {"id": "mamaearth", "name": "Mamaearth",        "brand_risk_score": 81, "payment_reliability": "high",   "industry": "personal care",       "verified": True, "created_at": now()},
    {"id": "sugar",     "name": "Sugar Cosmetics",  "brand_risk_score": 76, "payment_reliability": "medium", "industry": "cosmetics",           "verified": True, "created_at": now()},
]
db.brands.insert_many(brands)
print(f"  ✓ Seeded {len(brands)} brands")

# ── 2. Admin user ─────────────────────────────────────────────────────────────
admin_id = uid()
db.users.insert_one({
    "id": admin_id,
    "email": "admin@mypay.io",
    "password_hash": hash_pw("mypay-admin-2024"),
    "name": "Akhi — Admin",
    "role": "admin",
    "status": "active",
    "kyc_status": "verified",
    "created_at": now(-30),
    "updated_at": now(),
})
print("  ✓ Admin  →  admin@mypay.io / mypay-admin-2024")

# ── 3. Demo Creator — Priya Sharma ────────────────────────────────────────────
creator_user_id = uid()
creator_id      = uid()

db.users.insert_one({
    "id": creator_user_id,
    "email": "demo.creator@mypay.io",
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
    "engagement_rate": 4.7,           # correct field name
    "authenticity_score": 82,
    "last_synced_at": now(-1),        # correct field name
    "platform": "instagram",
})
print("  ✓ Creator  →  demo.creator@mypay.io / Demo1234!")

# ── 4. Deals (correct status values from DealStatus enum) ─────────────────────

# Deal 1 — AWAITING_PAYMENT (funded, brand owes My Pay)
deal1_id = uid()
db.deals.insert_one({
    "id": deal1_id,
    "creator_id": creator_id,
    "user_id": creator_user_id,
    "brand_id": "gymshark",
    "brand_name": "Gymshark",
    "deal_amount": 200000,         # correct field name (contract value)
    "advance_amount": 170000,
    "discount_fee": 30000,
    "discount_rate": 15.0,
    "status": "awaiting_payment",  # correct enum value
    "maturity_date": now(22),
    "payment_terms": "NET-30",
    "deliverables": "2x Reels + 4x Stories",
    "risk_decision": {
        "approved": True,
        "score": 81,
        "engine_version": "1.0.0",
        "reasons": ["High brand risk score (88)", "Strong creator engagement (4.7%)", "Verified KYC"],
    },
    "created_at": now(-8),
    "updated_at": now(-8),
})
db.transactions.insert_one({
    "id": uid(), "deal_id": deal1_id,
    "kind": "disbursement", "amount": 170000, "currency": "INR",
    "provider": "razorpay", "status": "paid",
    "note": "Advance disbursed to creator bank account",
    "created_at": now(-8),
})
db.deal_events.insert_many([
    {"deal_id": deal1_id, "event_type": "uploaded",  "actor_id": creator_user_id, "at": now(-9)},
    {"deal_id": deal1_id, "event_type": "approved",  "actor_id": admin_id, "at": now(-8), "note": "Risk score 81 — auto-approved"},
    {"deal_id": deal1_id, "event_type": "disbursed", "actor_id": admin_id, "at": now(-8), "note": "₹1,70,000 sent to HDFC Bank"},
])

# Deal 2 — REPAID (fully completed with Nykaa)
deal2_id = uid()
db.deals.insert_one({
    "id": deal2_id,
    "creator_id": creator_id,
    "user_id": creator_user_id,
    "brand_id": "nykaa",
    "brand_name": "Nykaa",
    "deal_amount": 120000,
    "advance_amount": 102000,
    "discount_fee": 18000,
    "discount_rate": 15.0,
    "status": "repaid",            # correct enum value
    "maturity_date": now(-15),
    "payment_terms": "NET-30",
    "deliverables": "3x Reels",
    "risk_decision": {
        "approved": True,
        "score": 79,
        "engine_version": "1.0.0",
        "reasons": ["Established brand (Nykaa)", "Creator score 78.4", "Clean history"],
    },
    "created_at": now(-55),
    "updated_at": now(-15),
})
db.transactions.insert_many([
    {"id": uid(), "deal_id": deal2_id, "kind": "disbursement", "amount": 102000, "currency": "INR", "provider": "razorpay", "status": "paid",  "created_at": now(-55)},
    {"id": uid(), "deal_id": deal2_id, "kind": "repayment",    "amount": 120000, "currency": "INR", "provider": "neft",     "status": "paid",  "note": "Full repayment from Nykaa", "created_at": now(-15)},
    {"id": uid(), "deal_id": deal2_id, "kind": "fee_capture",  "amount": 18000,  "currency": "INR", "provider": "internal", "status": "paid",  "note": "My Pay discount fee", "created_at": now(-15)},
])

# Deal 3 — UPLOADED (just submitted, not yet scored)
deal3_id = uid()
db.deals.insert_one({
    "id": deal3_id,
    "creator_id": creator_id,
    "user_id": creator_user_id,
    "brand_id": "mamaearth",
    "brand_name": "Mamaearth",
    "deal_amount": 85000,
    "advance_amount": None,
    "discount_fee": None,
    "status": "uploaded",          # correct enum value
    "maturity_date": now(30),
    "payment_terms": "NET-30",
    "deliverables": "1x YouTube Video + 2x Reels",
    "risk_decision": None,
    "created_at": now(-1),
    "updated_at": now(-1),
})
print("  ✓ Seeded 3 deals  (awaiting_payment, repaid, uploaded)")

# ── 5. Brand signup token ─────────────────────────────────────────────────────
db.brand_signup_tokens.insert_one({
    "token": "GYMSHARK-DEMO-2026",
    "brand_name": "Gymshark",
    "used": False,
    "created_at": now(),
    "notes": "Demo token",
})

# ── Done ──────────────────────────────────────────────────────────────────────
print("\n" + "═"*55)
print("  🎉 Demo data seeded!")
print("═"*55)
print("\n  👤 Creator  →  demo.creator@mypay.io  /  Demo1234!")
print("  🔑 Admin    →  admin@mypay.io         /  mypay-admin-2024")
print("\n  🌐 https://myapp-main-xi.vercel.app\n")

client.close()

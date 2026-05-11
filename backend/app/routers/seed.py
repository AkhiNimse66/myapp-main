"""
POST /api/seed-demo?key=athanni-seed-2026

One-shot demo data seeder — runs inside Railway, no external connection needed.
Protected by a secret key query param. Safe to leave deployed (won't re-seed
if data already exists unless ?force=true is passed).
"""
from __future__ import annotations

import uuid
import bcrypt
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db

router = APIRouter(prefix="/api", tags=["seed"])

SEED_KEY = "athanni-seed-2026"


def _now(offset_days: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=offset_days)).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(12)).decode()


@router.post("/seed-demo")
async def seed_demo(
    key: str = Query(..., description="Seed secret key"),
    force: bool = Query(False, description="Re-seed even if data exists"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Seed demo users, brands, deals into the live database."""

    if key != SEED_KEY:
        raise HTTPException(status_code=403, detail="Invalid seed key.")

    # ── Idempotency check ─────────────────────────────────────────────────────
    existing = await db.users.find_one({"email": "admin@athanni.co.in"})
    if existing and not force:
        return {
            "status": "already_seeded",
            "message": "Demo data already exists. Pass ?force=true to re-seed.",
            "logins": {
                "admin":   {"email": "admin@athanni.co.in",           "password": "athanni-admin-2024"},
                "creator": {"email": "demo.creator@athanni.co.in",    "password": "Demo1234!"},
                "brand_tokens": {"nykaa": "NYKAA-DEMO-2026", "gymshark": "GYMSHARK-DEMO-2026"},
            },
        }

    # ── Wipe old demo data ────────────────────────────────────────────────────
    demo_emails = [
        "admin@athanni.co.in", "demo.creator@athanni.co.in",
        "admin@mypay.io", "demo.creator@mypay.io",
    ]
    for email in demo_emails:
        user = await db.users.find_one({"email": email})
        if user:
            await db.creators.delete_many({"user_id": user["id"]})
            await db.social_profiles.delete_many({"user_id": user["id"]})

    await db.users.delete_many({"email": {"$in": demo_emails}})
    await db.brands.delete_many({})
    await db.deals.delete_many({})
    await db.transactions.delete_many({})
    await db.deal_events.delete_many({})
    await db.brand_signup_tokens.delete_many({})

    # ── 1. Brands ─────────────────────────────────────────────────────────────
    brands = [
        {"id": "gymshark",  "name": "Gymshark",       "brand_risk_score": 88, "payment_reliability": "high",   "industry": "fitness",             "verified": True, "contact_email": "finance@gymshark.com",        "created_at": _now()},
        {"id": "nykaa",     "name": "Nykaa",           "brand_risk_score": 85, "payment_reliability": "high",   "industry": "beauty",              "verified": True, "contact_email": "finance@nykaa.com",           "created_at": _now()},
        {"id": "boat",      "name": "boAt",            "brand_risk_score": 79, "payment_reliability": "medium", "industry": "consumer electronics","verified": True, "contact_email": "finance@boat-lifestyle.com",  "created_at": _now()},
        {"id": "mamaearth", "name": "Mamaearth",       "brand_risk_score": 81, "payment_reliability": "high",   "industry": "personal care",       "verified": True, "contact_email": "finance@mamaearth.in",        "created_at": _now()},
        {"id": "sugar",     "name": "Sugar Cosmetics", "brand_risk_score": 76, "payment_reliability": "medium", "industry": "cosmetics",           "verified": True, "contact_email": "finance@sugarcosmetics.com",  "created_at": _now()},
    ]
    await db.brands.insert_many(brands)

    # ── 2. Admin ──────────────────────────────────────────────────────────────
    admin_id = _uid()
    await db.users.insert_one({
        "id": admin_id, "email": "admin@athanni.co.in",
        "password_hash": _hash("athanni-admin-2024"),
        "name": "Akhi — Athanni Admin", "role": "admin",
        "status": "active", "kyc_status": "verified",
        "created_at": _now(-30), "updated_at": _now(),
    })

    # ── 3. Demo Creator — Priya Sharma ────────────────────────────────────────
    creator_user_id = _uid()
    creator_id      = _uid()

    await db.users.insert_one({
        "id": creator_user_id, "email": "demo.creator@athanni.co.in",
        "password_hash": _hash("Demo1234!"),
        "name": "Priya Sharma", "role": "creator",
        "status": "active", "kyc_status": "verified",
        "created_at": _now(-60), "updated_at": _now(),
    })
    await db.creators.insert_one({
        "id": creator_id, "user_id": creator_user_id,
        "name": "Priya Sharma", "handle": "@priyasharmalifestyle",
        "agency_id": None, "credit_limit": 500000,
        "creator_score": 78.4, "credit_tier": "Premium",
        "kyc_status": "verified", "pan_number": "ABCDE1234F",
        "bank_account": {"account_number": "XXXX XXXX 4521", "ifsc": "HDFC0001234", "bank_name": "HDFC Bank"},
        "created_at": _now(-60), "updated_at": _now(),
    })
    await db.social_profiles.insert_one({
        "id": _uid(), "creator_id": creator_id, "user_id": creator_user_id,
        "instagram_handle": "@priyasharmalifestyle",
        "followers": 248000, "following": 1200,
        "engagement_rate": 4.7, "authenticity_score": 82,
        "last_synced_at": _now(-1), "platform": "instagram",
    })

    # ── 4. Deals ──────────────────────────────────────────────────────────────
    deal1_id = _uid()
    await db.deals.insert_one({
        "id": deal1_id, "creator_id": creator_id, "user_id": creator_user_id,
        "brand_id": "gymshark", "brand_name": "Gymshark",
        "deal_title": "Gymshark Q2 Fitness Campaign",
        "deal_amount": 200000.0, "advance_amount": 170000.0,
        "discount_fee": 6000.0, "advance_rate": 0.85, "currency": "INR",
        "status": "awaiting_payment", "payment_terms_days": 30,
        "maturity_date": _now(22), "disbursed_at": _now(-8),
        "risk_decision": {"approved": True, "score": 81, "engine_version": "1.0.0",
            "reasons": ["High brand risk score (88)", "Strong creator engagement (4.7%)", "Verified KYC"]},
        "created_at": _now(-8), "updated_at": _now(-8),
    })
    await db.transactions.insert_one({
        "id": _uid(), "deal_id": deal1_id, "kind": "disbursement",
        "amount": 170000, "currency": "INR", "provider": "mock", "status": "paid",
        "note": "Advance disbursed — mock payout", "created_at": _now(-8),
    })

    deal2_id = _uid()
    await db.deals.insert_one({
        "id": deal2_id, "creator_id": creator_id, "user_id": creator_user_id,
        "brand_id": "nykaa", "brand_name": "Nykaa",
        "deal_title": "Nykaa Beauty Spring Collection",
        "deal_amount": 120000.0, "advance_amount": 102000.0,
        "discount_fee": 3600.0, "advance_rate": 0.85, "currency": "INR",
        "status": "repaid", "payment_terms_days": 30,
        "maturity_date": _now(-15), "disbursed_at": _now(-55), "repaid_at": _now(-15),
        "risk_decision": {"approved": True, "score": 79, "engine_version": "1.0.0",
            "reasons": ["Established brand (Nykaa)", "Creator score 78.4", "Clean history"]},
        "created_at": _now(-55), "updated_at": _now(-15),
    })

    deal3_id = _uid()
    await db.deals.insert_one({
        "id": deal3_id, "creator_id": creator_id, "user_id": creator_user_id,
        "brand_id": "mamaearth", "brand_name": "Mamaearth",
        "deal_title": "Mamaearth Skincare — YouTube + Reels Pack",
        "deal_amount": 85000.0, "advance_amount": None,
        "discount_fee": None, "advance_rate": None, "currency": "INR",
        "status": "uploaded", "payment_terms_days": 30,
        "maturity_date": _now(30), "risk_decision": None,
        "created_at": _now(-1), "updated_at": _now(-1),
    })

    # ── 5. Brand signup tokens ─────────────────────────────────────────────────
    await db.brand_signup_tokens.insert_many([
        {"token": "NYKAA-DEMO-2026",     "brand_id": "nykaa",     "brand_name": "Nykaa",     "used": False, "created_at": _now()},
        {"token": "GYMSHARK-DEMO-2026",  "brand_id": "gymshark",  "brand_name": "Gymshark",  "used": False, "created_at": _now()},
    ])

    return {
        "status": "seeded",
        "seeded": {"brands": 5, "users": 2, "deals": 3, "brand_tokens": 2},
        "logins": {
            "admin":   {"email": "admin@athanni.co.in",        "password": "athanni-admin-2024"},
            "creator": {"email": "demo.creator@athanni.co.in", "password": "Demo1234!"},
            "brand_tokens": {"nykaa": "NYKAA-DEMO-2026", "gymshark": "GYMSHARK-DEMO-2026"},
        },
    }

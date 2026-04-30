"""Brands router.

GET  /api/brands          — list all brands (for deal creation dropdown)
GET  /api/brands/{id}     — brand detail (for DealDetail sidebar)
POST /api/brands/seed     — admin: seed demo brands
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_db
from app.deps import get_current_user, require_role
from app.enums import Role
from app.repos.brands_repo import BrandsRepo
from app.repos.deals_repo import DealsRepo

router = APIRouter(prefix="/api/brands", tags=["brands"])


@router.get("/my-deals")
async def brand_my_deals(
    current_user: dict = Depends(require_role(Role.BRAND)),
    db=Depends(get_db),
):
    """All deals where this brand is the counterparty.
    Used by the Brand Portal dashboard.
    """
    brands = BrandsRepo(db)
    deals_repo = DealsRepo(db)

    brand = await brands.find_by_user_id(current_user["id"])
    if not brand:
        return []

    # Deals can be linked by brand_id (registered brand) or brand_name (seeded brand)
    deals = await deals_repo.find_many(
        {"brand_id": brand["id"]},
        sort=[("created_at", -1)],
        limit=200,
    )
    return {"brand": brand, "deals": deals}


@router.get("")
async def list_brands(
    q: str = "",
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    brands = BrandsRepo(db)
    if q:
        rows = await brands.search_by_name(q, limit=limit)
    else:
        rows = await brands.find_many({}, sort=[("name", 1)], limit=limit)
    return rows


@router.get("/{brand_id}")
async def get_brand(
    brand_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    brands = BrandsRepo(db)
    brand = await brands.find_by_id(brand_id)
    if not brand:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Brand not found.")
    return brand


@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def seed_demo_brands(
    db=Depends(get_db),
):
    """Seed demo brands — no auth required (dev/setup utility)."""

    brands = BrandsRepo(db)
    demo = [
        {"name": "Gymshark", "tier": "Enterprise", "credit_rating": "AA",
         "industry": "Fitness & Apparel", "country": "UK",
         "solvency_score": 91.0, "payment_history_score": 94.0, "avg_payment_days": 38},
        {"name": "Nykaa", "tier": "Enterprise", "credit_rating": "A",
         "industry": "Beauty & Wellness", "country": "IN",
         "solvency_score": 84.0, "payment_history_score": 87.0, "avg_payment_days": 45},
        {"name": "boAt Lifestyle", "tier": "Growth", "credit_rating": "A",
         "industry": "Consumer Electronics", "country": "IN",
         "solvency_score": 78.0, "payment_history_score": 82.0, "avg_payment_days": 52},
        {"name": "Mamaearth", "tier": "Growth", "credit_rating": "B+",
         "industry": "D2C Personal Care", "country": "IN",
         "solvency_score": 71.0, "payment_history_score": 75.0, "avg_payment_days": 60},
        {"name": "Sugar Cosmetics", "tier": "Mid", "credit_rating": "B",
         "industry": "Beauty", "country": "IN",
         "solvency_score": 65.0, "payment_history_score": 69.0, "avg_payment_days": 65},
    ]

    created = []
    for b in demo:
        existing = await brands.find_by_name(b["name"])
        if existing:
            created.append({"name": b["name"], "action": "skipped (exists)"})
            continue
        doc = await brands.create(
            user_id="system",
            name=b["name"],
            industry=b.get("industry"),
            country=b.get("country"),
            tier=b.get("tier"),
            credit_rating=b.get("credit_rating"),
            solvency_score=b.get("solvency_score"),
            payment_history_score=b.get("payment_history_score"),
            avg_payment_days=b.get("avg_payment_days"),
        )
        created.append({"name": doc["name"], "id": doc["id"], "action": "created"})

    return {"seeded": created}

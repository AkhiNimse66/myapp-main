"""Auth + RBAC router.

Endpoints
---------
POST /api/auth/register  — role-aware registration
POST /api/auth/login     — credential exchange for JWT
GET  /api/auth/me        — current user + role profile

Registration flow
-----------------
creator  → users + creators + social_profiles (atomic; email uniqueness via DuplicateKeyError)
agency   → users + agencies
brand    → validate one-time signup_token → users + brands (token consumed atomically)
admin    → not self-serviceable; seeded via management script

Brand signup tokens live in the ``brand_signup_tokens`` collection.  An admin
creates them via the internal endpoint (or the seed script).  Each token is
a UUIDv4 string and is marked ``used=True`` on first use — prevents replays.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, Depends, HTTPException, status

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db import get_db
from app.deps import get_current_user
from app.enums import Role
from app.repos.users_repo import UsersRepo
from app.repos.creators_repo import CreatorsRepo
from app.repos.agencies_repo import AgenciesRepo
from app.repos.brands_repo import BrandsRepo
from app.repos.social_repo import SocialRepo
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, SignupTokenCreate
from app.schemas.user import UserOut
from app.security import hash_password, verify_password, make_token
from app.services.credit_limit import compute_credit_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _consume_brand_token(db: AsyncIOMotorDatabase, token: str) -> dict:
    """Validate and atomically consume a brand signup token.

    Returns the token document on success.
    Raises HTTP 422 if the token is invalid or already used.
    """
    result = await db.brand_signup_tokens.find_one_and_update(
        {"token": token, "used": False},
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc).isoformat()}},
        projection={"_id": 0},
        return_document=True,  # return the updated doc
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid or already-used signup token.",
        )
    return result


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    """Create a user + role-specific profile in one logical transaction.

    Email uniqueness is enforced by the MongoDB unique index — a
    ``DuplicateKeyError`` is caught and surfaced as HTTP 409.
    """
    users = UsersRepo(db)

    # ---- Brand: validate + consume signup token before touching users ----
    brand_token_doc: Optional[dict] = None
    if body.role == Role.BRAND:
        brand_token_doc = await _consume_brand_token(db, body.signup_token)

    # ---- Create user (may raise DuplicateKeyError) ----
    import pymongo.errors  # deferred — avoids broken pyOpenSSL at import time in tests
    try:
        user = await users.create(
            email=body.email,
            password_hash=hash_password(body.password),
            name=body.name,
            role=body.role.value,
        )
    except pymongo.errors.DuplicateKeyError:
        # Roll back consumed brand token so it can be reused
        if brand_token_doc:
            await db.brand_signup_tokens.update_one(
                {"token": body.signup_token},
                {"$set": {"used": False}, "$unset": {"used_at": ""}},
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    # ---- Create role-specific profile ----
    user_id: str = user["id"]

    if body.role == Role.CREATOR:
        creators = CreatorsRepo(db)
        # Compute initial credit limit from zero metrics (starter tier ₹50k)
        # Recomputed when creator fills in social profile on Profile page
        initial = compute_credit_limit(followers=0, engagement_rate=0.0, authenticity_score=0.0)
        creator = await creators.create(
            user_id=user_id,
            name=body.name,
            credit_limit=initial.credit_limit,
            creator_score=initial.health_score,
        )
        social = SocialRepo(db)
        await social.create_for_creator(
            creator_id=creator["id"],
            user_id=user_id,
            instagram_handle=body.instagram_handle,
        )

    elif body.role == Role.AGENCY:
        agencies = AgenciesRepo(db)
        await agencies.create(
            user_id=user_id,
            name=body.agency_name or body.name,
        )

    elif body.role == Role.BRAND:
        brands = BrandsRepo(db)
        brand_doc = await brands.create(
            user_id=user_id,
            name=body.brand_company_name or brand_token_doc.get("brand_name") or body.name,
            website=body.brand_website,
            industry=body.brand_industry,
        )
        # Store extended KYC/business fields via immediate patch
        extra: dict = {}
        if body.brand_company_type:  extra["company_type"]    = body.brand_company_type
        if body.brand_gst_number:    extra["gst_number"]      = body.brand_gst_number
        if body.brand_pan_number:    extra["pan_number"]      = body.brand_pan_number
        if body.brand_phone:         extra["phone"]           = body.brand_phone
        if body.brand_billing_email: extra["billing_email"]   = body.brand_billing_email
        if body.name:                extra["contact_name"]    = body.name
        if extra:
            await brands.update(brand_doc["id"], extra)

    token = make_token(user_id=user_id, role=user["role"])
    return TokenResponse(
        access_token=token,
        user_id=user_id,
        role=user["role"],
        name=user["name"],
    )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    users = UsersRepo(db)
    user = await users.find_by_email_with_hash(body.email.lower().strip())

    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if user.get("status") == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Contact support.",
        )

    token = make_token(user_id=user["id"], role=user["role"])
    return TokenResponse(
        access_token=token,
        user_id=user["id"],
        role=user["role"],
        name=user["name"],
    )


# ---------------------------------------------------------------------------
# Me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserOut)
async def me(
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Return the caller's user document + role-specific profile."""
    role = current_user.get("role")
    user_id = current_user["id"]
    profile: Optional[dict] = None

    if role == Role.CREATOR:
        creators = CreatorsRepo(db)
        profile = await creators.find_by_user_id(user_id)
    elif role == Role.AGENCY:
        agencies = AgenciesRepo(db)
        profile = await agencies.find_by_user_id(user_id)
    elif role == Role.BRAND:
        brands = BrandsRepo(db)
        profile = await brands.find_by_user_id(user_id)

    return UserOut(**{**current_user, "profile": profile})


# ---------------------------------------------------------------------------
# Admin: issue brand signup token
# ---------------------------------------------------------------------------

@router.post(
    "/admin/brand-token",
    status_code=status.HTTP_201_CREATED,
    summary="Issue a brand signup token (admin only)",
)
async def issue_brand_token(
    body: SignupTokenCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    if current_user.get("role") != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only.")

    now = datetime.now(timezone.utc).isoformat()
    token_doc = {
        "token": str(uuid.uuid4()),
        "brand_name": body.brand_name,
        "notes": body.notes,
        "used": False,
        "created_by": current_user["id"],
        "created_at": now,
    }
    await db.brand_signup_tokens.insert_one(token_doc)
    token_doc.pop("_id", None)
    return token_doc

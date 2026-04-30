"""Creator profile router.

GET   /api/creator/profile        — current creator's social profile (used in DealDetail)
PATCH /api/creator/profile        — update metrics / handle / platform
POST  /api/creator/social/connect — queue a social account connection (stub; Meta review pending)
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.db import get_db
from app.deps import get_current_user, require_role
from app.enums import Role
from app.repos.creators_repo import CreatorsRepo
from app.repos.social_repo import SocialRepo
from app.services.credit_limit import compute_credit_limit

router = APIRouter(prefix="/api/creator", tags=["creator"])

# Fields the frontend sends in PATCH /profile that map to social_profiles
_SOCIAL_FIELDS = {"handle", "platform", "followers", "engagement_rate", "authenticity_score", "instagram_handle"}

# Fields that map to the creators collection
_CREATOR_FIELDS = {"bio", "category", "agency_id"}

# Allowed payout method fields (nested under payout_method on the creator doc)
_PAYOUT_FIELDS = {"method_type", "upi_id", "account_name", "account_number", "ifsc", "bank_name"}


@router.get("/profile")
async def get_creator_profile(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Returns the social profile for the logged-in creator.

    DealDetail.jsx and Dashboard.jsx use this to show followers / engagement / authenticity.
    """
    user_id = current_user["id"]

    creators = CreatorsRepo(db)
    creator = await creators.find_by_user_id(user_id)
    if not creator:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Creator profile not found.")

    social = SocialRepo(db)
    profile = await social.find_by_creator_id(creator["id"])
    if not profile:
        # Return minimal placeholder so the UI doesn't break on new accounts
        return {
            "creator_id": creator["id"],
            "handle": creator.get("instagram_handle"),
            "instagram_handle": creator.get("instagram_handle"),
            "followers": 0,
            "engagement_rate": 0.0,
            "authenticity_score": 0.0,
            "platform": "instagram",
            "health_score": creator.get("creator_score", 0.0),
            "provider_connected_requested": creator.get("provider_connected_requested"),
            "provider_connected_requested_at": creator.get("provider_connected_requested_at"),
        }

    return {
        **profile,
        # Alias: Profile.jsx reads `handle`; the DB stores `instagram_handle`
        "handle": profile.get("instagram_handle"),
        "platform": profile.get("platform", "instagram"),
        "health_score": creator.get("creator_score", 0.0),
        "provider_connected_requested": creator.get("provider_connected_requested"),
        "provider_connected_requested_at": creator.get("provider_connected_requested_at"),
    }


@router.patch("/profile")
async def update_creator_profile(
    body: dict,
    current_user: dict = Depends(require_role(Role.CREATOR)),
    db=Depends(get_db),
):
    """Update creator metrics and social handle.

    Profile.jsx sends: handle, platform, followers, engagement_rate, authenticity_score
    plus optional: bio, category.
    """
    creators = CreatorsRepo(db)
    creator = await creators.find_by_user_id(current_user["id"])
    if not creator:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Creator profile not found.")

    # Update creators collection fields
    creator_patch = {k: v for k, v in body.items() if k in _CREATOR_FIELDS}
    if creator_patch:
        await creators.update(creator["id"], creator_patch)

    # Build social_profiles patch — normalise `handle` → `instagram_handle`
    social_patch: dict = {}
    for k, v in body.items():
        if k in _SOCIAL_FIELDS:
            if k == "handle":
                social_patch["instagram_handle"] = v
            else:
                social_patch[k] = v

    if social_patch:
        social = SocialRepo(db)
        await social.upsert_metrics(creator["id"], social_patch)

        # Recompute credit limit whenever social metrics change.
        # Pull the full current profile to get any fields not in this patch.
        updated_profile = await social.find_by_creator_id(creator["id"]) or {}
        merged = {**updated_profile, **social_patch}

        result = compute_credit_limit(
            followers=int(merged.get("followers") or 0),
            engagement_rate=float(merged.get("engagement_rate") or 0.0),
            authenticity_score=float(merged.get("authenticity_score") or 0.0),
        )
        await creators.update(creator["id"], {
            "credit_limit": result.credit_limit,
            "creator_score": result.health_score,
            "credit_tier": result.tier_label,
        })

    return {
        "ok": True,
        "credit_limit": (
            compute_credit_limit(
                followers=int(social_patch.get("followers") or 0),
                engagement_rate=float(social_patch.get("engagement_rate") or 0.0),
                authenticity_score=float(social_patch.get("authenticity_score") or 0.0),
            ).credit_limit if social_patch else None
        ),
    }


@router.patch("/payout-method")
async def update_payout_method(
    body: dict,
    current_user: dict = Depends(require_role(Role.CREATOR)),
    db=Depends(get_db),
):
    """Register or update the creator's payout method (UPI or bank account).

    Profile.jsx payout section sends:
      { method_type: "upi",  upi_id: "creator@upi" }
      { method_type: "bank", account_name: "...", account_number: "...", ifsc: "...", bank_name: "..." }
    """
    creators = CreatorsRepo(db)
    creator = await creators.find_by_user_id(current_user["id"])
    if not creator:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Creator profile not found.")

    method_type = body.get("method_type", "upi")
    if method_type not in ("upi", "bank"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "method_type must be 'upi' or 'bank'.")

    # Validate required fields per method
    if method_type == "upi":
        if not body.get("upi_id"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "upi_id is required for UPI method.")
    else:
        for f in ("account_name", "account_number", "ifsc"):
            if not body.get(f):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{f} is required for bank method.")

    payout_method = {k: v for k, v in body.items() if k in _PAYOUT_FIELDS}
    await creators.update(creator["id"], {"payout_method": payout_method})

    return {"ok": True, "payout_method": payout_method}


@router.get("/payout-method")
async def get_payout_method(
    current_user: dict = Depends(require_role(Role.CREATOR)),
    db=Depends(get_db),
):
    """Returns the registered payout method (masked for security)."""
    creators = CreatorsRepo(db)
    creator = await creators.find_by_user_id(current_user["id"])
    if not creator:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Creator profile not found.")

    pm = creator.get("payout_method")
    if not pm:
        return {"registered": False}

    # Mask sensitive fields before returning
    masked = dict(pm)
    if masked.get("account_number"):
        n = masked["account_number"]
        masked["account_number"] = "•••• •••• " + n[-4:]
    if masked.get("upi_id"):
        upi = masked["upi_id"]
        at = upi.find("@")
        if at > 2:
            masked["upi_id"] = upi[:2] + "•••" + upi[at:]

    return {"registered": True, **masked}


@router.post("/social/connect")
async def connect_social_account(
    body: dict,
    current_user: dict = Depends(require_role(Role.CREATOR)),
    db=Depends(get_db),
):
    """Queue a social account connection request.

    In production this initiates the OAuth handshake with Meta / TikTok.
    Currently stubbed — logs the request and returns a pending status.
    """
    platform = body.get("platform", "instagram")
    allowed_platforms = {"instagram", "tiktok", "youtube", "x"}
    if platform not in allowed_platforms:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Unknown platform: {platform}")

    creators = CreatorsRepo(db)
    creator = await creators.find_by_user_id(current_user["id"])
    if not creator:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Creator profile not found.")

    # Persist the request timestamp so the UI can show the pending banner
    now = datetime.now(timezone.utc).isoformat()
    await creators.update(creator["id"], {
        "provider_connected_requested": platform,
        "provider_connected_requested_at": now,
    })

    return {
        "status": "pending_meta_review",
        "platform": platform,
        "message": (
            f"{platform.capitalize()} connection queued. "
            "Meta / TikTok developer-app review typically takes 5–10 business days. "
            "Synthetic scoring remains active in the meantime."
        ),
    }

"""Dashboard summary router.

GET /api/dashboard/summary — rich creator dashboard payload.

Shape returned (matches Dashboard.jsx):
{
  credit_limit, credit_tier, credit_tier_key,
  next_tier: { label, limit, health_needed, gap, progress_pct },
  tier_path: [ { key, label, limit, min_score, active, achieved } ],
  used_pct, available, total_advanced, total_repaid,
  pipeline: {
    uploaded:         { count, value },
    scored:           { count, value },
    disbursed:        { count, value },
    awaiting_payment: { count, value },
    repaid:           { count, value },
    rejected:         { count, value },
  },
  monthly_volume: [ { month, advanced, deals } ],  # last 6 months
  creator_health: {
    health_score, followers, engagement_rate, authenticity_score,
    platform, social_connected, last_synced,
  },
}
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends

from app.db import get_db
from app.deps import get_current_user
from app.enums import DealStatus
from app.repos.creators_repo import CreatorsRepo
from app.repos.deals_repo import DealsRepo
from app.repos.social_repo import SocialRepo
from app.services.credit_limit import CREDIT_TIERS, compute_credit_limit

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# ── Tier metadata for the progression visualiser ────────────────────────────

TIER_PATH = [
    {"key": "starter",  "label": "Starter",  "limit": 50_000,    "min_score": 0.0,  "display": "₹50K"},
    {"key": "rising",   "label": "Rising",   "limit": 150_000,   "min_score": 30.0, "display": "₹1.5L"},
    {"key": "growth",   "label": "Growth",   "limit": 400_000,   "min_score": 50.0, "display": "₹4L"},
    {"key": "premium",  "label": "Premium",  "limit": 1_000_000, "min_score": 70.0, "display": "₹10L"},
    {"key": "elite",    "label": "Elite",    "limit": 2_500_000, "min_score": 85.0, "display": "₹25L"},
]


def _tier_for_score(score: float) -> dict:
    for t in reversed(TIER_PATH):
        if score >= t["min_score"]:
            return t
    return TIER_PATH[0]


def _next_tier(current_tier: dict) -> dict | None:
    idx = next((i for i, t in enumerate(TIER_PATH) if t["key"] == current_tier["key"]), 0)
    return TIER_PATH[idx + 1] if idx + 1 < len(TIER_PATH) else None


def _build_tier_path(health_score: float) -> list[dict]:
    result = []
    for t in TIER_PATH:
        achieved = health_score >= t["min_score"]
        active = _tier_for_score(health_score)["key"] == t["key"]
        result.append({**t, "achieved": achieved, "active": active})
    return result


def _tier_progression(health_score: float, social: dict) -> dict:
    """Compute what the creator needs to do to reach the next tier."""
    current = _tier_for_score(health_score)
    nxt = _next_tier(current)
    if not nxt:
        return {"label": "Elite — maximum tier reached", "limit": None,
                "health_needed": 85.0, "gap": 0.0, "progress_pct": 100.0, "hints": []}

    gap = max(0.0, nxt["min_score"] - health_score)
    span = nxt["min_score"] - current["min_score"]
    progress_pct = round(min(100, ((health_score - current["min_score"]) / span * 100)), 1) if span > 0 else 0.0

    # Compute what single-metric improvements would tip them over
    hints = []
    followers = int(social.get("followers") or 0)
    er = float(social.get("engagement_rate") or 0)
    auth = float(social.get("authenticity_score") or 0)

    # Try bumping followers
    for target_f in [50_000, 100_000, 250_000, 500_000, 750_000, 1_000_000, 2_000_000, 5_000_000]:
        if target_f > followers:
            r = compute_credit_limit(followers=target_f, engagement_rate=er, authenticity_score=auth)
            if r.health_score >= nxt["min_score"]:
                hints.append({"metric": "followers", "label": "Followers",
                               "current": followers, "needed": target_f,
                               "formatted": f"{target_f:,}"})
                break

    # Try bumping ER
    for target_er in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0]:
        if target_er > er:
            r = compute_credit_limit(followers=followers, engagement_rate=target_er, authenticity_score=auth)
            if r.health_score >= nxt["min_score"]:
                hints.append({"metric": "engagement_rate", "label": "Engagement Rate",
                               "current": er, "needed": target_er,
                               "formatted": f"{target_er}%"})
                break

    return {
        "label": f"{nxt['label']} · {nxt['display']}",
        "limit": nxt["limit"],
        "health_needed": nxt["min_score"],
        "gap": round(gap, 1),
        "progress_pct": progress_pct,
        "hints": hints[:2],  # max 2 hints — keep it actionable
    }


def _build_pipeline(deals: list[dict]) -> dict:
    pipeline: dict = {s: {"count": 0, "value": 0.0} for s in
                      ["uploaded", "scored", "disbursed", "awaiting_payment", "repaid", "rejected"]}
    for d in deals:
        s = d.get("status", "uploaded")
        if s in pipeline:
            pipeline[s]["count"] += 1
            pipeline[s]["value"] += d.get("deal_amount") or 0
    return pipeline


def _build_monthly_volume(deals: list[dict]) -> list[dict]:
    """Last 6 calendar months of deal activity."""
    now = datetime.now(timezone.utc)
    months = []
    for i in range(5, -1, -1):
        dt = now - timedelta(days=i * 30)
        months.append(dt.strftime("%b"))

    buckets: dict[str, dict] = {m: {"month": m, "advanced": 0.0, "deals": 0} for m in months}

    for d in deals:
        try:
            created = datetime.fromisoformat(d["created_at"].replace("Z", "+00:00"))
            label = created.strftime("%b")
            if label in buckets:
                buckets[label]["advanced"] += d.get("advance_amount") or 0
                buckets[label]["deals"] += 1
        except Exception:
            pass

    return list(buckets.values())


# ── Route ────────────────────────────────────────────────────────────────────

@router.get("/summary")
async def summary(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    user_id = current_user["id"]

    creators = CreatorsRepo(db)
    creator = await creators.find_by_user_id(user_id)

    if not creator:
        # Non-creator roles — minimal payload
        deals_repo = DealsRepo(db)
        all_deals = await deals_repo.find_many({}, limit=1000)
        disbursed = [d for d in all_deals if d["status"] in (DealStatus.DISBURSED, DealStatus.AWAITING_PAYMENT)]
        repaid = [d for d in all_deals if d["status"] == DealStatus.REPAID]
        return {
            "credit_limit": 0, "credit_tier": "—", "credit_tier_key": "starter",
            "next_tier": None, "tier_path": _build_tier_path(0),
            "used_pct": 0, "available": 0,
            "total_advanced": sum(d.get("advance_amount") or 0 for d in disbursed),
            "total_repaid": sum(d.get("deal_amount") or 0 for d in repaid),
            "pipeline": _build_pipeline([]),
            "monthly_volume": _build_monthly_volume([]),
            "creator_health": {"health_score": 0, "followers": 0, "engagement_rate": 0,
                               "authenticity_score": 0, "platform": "instagram",
                               "social_connected": False, "last_synced": None},
        }

    creator_id = creator["id"]
    credit_limit = float(creator.get("credit_limit") or 50_000)
    health_score = float(creator.get("creator_score") or 0)

    deals_repo = DealsRepo(db)
    all_creator_deals = await deals_repo.find_by_creator(creator_id, limit=0)

    outstanding = [d for d in all_creator_deals
                   if d["status"] in (DealStatus.DISBURSED, DealStatus.AWAITING_PAYMENT)]
    total_advanced = sum(d.get("advance_amount") or 0 for d in outstanding)
    total_repaid = sum(d.get("deal_amount") or 0
                       for d in all_creator_deals if d["status"] == DealStatus.REPAID)

    used_pct = round(min(100, total_advanced / credit_limit * 100), 1) if credit_limit > 0 else 0.0
    available = max(0.0, credit_limit - total_advanced)

    social_repo = SocialRepo(db)
    social = await social_repo.find_by_creator_id(creator_id) or {}

    current_tier = _tier_for_score(health_score)

    creator_health = {
        "health_score": health_score,
        "followers": social.get("followers") or 0,
        "engagement_rate": social.get("engagement_rate") or 0.0,
        "authenticity_score": social.get("authenticity_score") or 0.0,
        "platform": social.get("platform", "instagram"),
        # Phyllo integration flag — false until PHYLLO keys are configured
        "social_connected": bool(creator.get("provider_connected_requested")),
        "last_synced": social.get("last_synced_at"),
    }

    return {
        "credit_limit": credit_limit,
        "credit_tier": creator.get("credit_tier", current_tier["label"]),
        "credit_tier_key": current_tier["key"],
        "next_tier": _tier_progression(health_score, social),
        "tier_path": _build_tier_path(health_score),
        "used_pct": used_pct,
        "available": available,
        "total_advanced": total_advanced,
        "total_repaid": total_repaid,
        "pipeline": _build_pipeline(all_creator_deals),
        "monthly_volume": _build_monthly_volume(all_creator_deals),
        "creator_health": creator_health,
    }

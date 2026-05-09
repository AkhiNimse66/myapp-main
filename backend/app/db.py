"""Motor (async Mongo) client + index bootstrap.

Single global client is intentional: Motor pools connections internally,
and re-creating clients across requests defeats that pool. Tests can call
:func:`close` between cases for hygiene.
"""
from __future__ import annotations
import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

logger = logging.getLogger("athanni.db")

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(get_settings().MONGO_URL)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        _db = get_client()[get_settings().DB_NAME]
    return _db


async def ensure_indexes(db: Optional[AsyncIOMotorDatabase] = None) -> None:
    """Idempotent. Safe to run on every boot.

    Add new indexes here when introducing collections. Mongo deduplicates
    by name, so re-running is a no-op when the index already exists.
    """
    if db is None:
        db = get_db()

    # users — email uniqueness is the linchpin against duplicate-account races
    await db.users.create_index("email", unique=True)
    await db.users.create_index("role")

    # creators / agencies / brands
    await db.creators.create_index("user_id", unique=True)
    await db.creators.create_index("agency_id")
    await db.agencies.create_index("user_id", unique=True)
    await db.brands.create_index("id", unique=True)
    await db.brands.create_index("name")

    # social_profiles — keyed off creators.id (not user_id) post-Day-2 refactor
    await db.social_profiles.create_index("creator_id", unique=True, sparse=True)
    await db.social_profiles.create_index("user_id", sparse=True)  # legacy field, kept until Day 2 migration

    # deals — every dashboard query is covered
    await db.deals.create_index("id", unique=True)
    await db.deals.create_index([("creator_id", 1), ("status", 1)])
    await db.deals.create_index([("brand_id", 1), ("status", 1)])
    await db.deals.create_index([("agency_id", 1), ("status", 1)])
    await db.deals.create_index([("user_id", 1), ("status", 1)])  # legacy alias
    await db.deals.create_index([("status", 1), ("maturity_date", 1)])

    # deal_events — append-only audit trail
    await db.deal_events.create_index([("deal_id", 1), ("at", -1)])

    # transactions — the unified ledger
    await db.transactions.create_index([("deal_id", 1), ("kind", 1)])
    await db.transactions.create_index(
        "provider_session_id", unique=True, sparse=True
    )
    # Legacy collection from phase-2 — kept until Day 8 migrates it into transactions
    await db.payment_transactions.create_index("session_id", unique=True, sparse=True)

    # contracts
    await db.contract_files.create_index([("user_id", 1), ("is_deleted", 1)])

    # outbox
    await db.email_log.create_index([("status", 1), ("next_attempt_at", 1)])

    # AI ops — every provider call is logged here for audit
    await db.ai_call_log.create_index([("service", 1), ("called_at", -1)])
    await db.ai_call_log.create_index([("provider", 1), ("called_at", -1)])

    logger.info("Indexes ensured on db=%s", db.name)


async def close() -> None:
    """Closes the Motor client and clears the cached references."""
    global _client, _db
    if _client is not None:
        _client.close()
    _client, _db = None, None

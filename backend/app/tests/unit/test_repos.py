"""Unit tests for the repository layer.

We mock the Motor collection with ``AsyncMock`` so these tests run without
a live MongoDB.  We verify:
  - BaseRepo methods call the underlying Motor APIs with correct arguments
  - UsersRepo.create builds the correct document shape
  - CreatorsRepo.create initialises credit fields to 0.0
  - DealsRepo.update_status merges extra fields correctly
  - EventsRepo.append never overwrites existing events (insert_one only)
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.repos.base import BaseRepo
from app.repos.users_repo import UsersRepo
from app.repos.creators_repo import CreatorsRepo
from app.repos.deals_repo import DealsRepo
from app.repos.events_repo import EventsRepo
from app.repos.transactions_repo import TransactionsRepo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(collection_mock=None):
    """Return a minimal Motor DB mock."""
    db = MagicMock()
    col = collection_mock or _make_collection()
    db.__getitem__ = MagicMock(return_value=col)
    return db, col


def _make_collection():
    col = MagicMock()
    col.find_one = AsyncMock(return_value=None)
    col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="fake"))
    col.update_one = AsyncMock(
        return_value=MagicMock(modified_count=1, upserted_id=None)
    )
    col.delete_one = AsyncMock(return_value=MagicMock(deleted_count=1))
    col.count_documents = AsyncMock(return_value=0)
    # find() returns a cursor-like object
    cursor = MagicMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.skip = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=[])
    col.find = MagicMock(return_value=cursor)
    return col


# ---------------------------------------------------------------------------
# BaseRepo
# ---------------------------------------------------------------------------

class TestBaseRepo:
    def _repo(self):
        db, col = _make_db()
        repo = BaseRepo.__new__(BaseRepo)
        repo._col = col
        return repo, col

    @pytest.mark.asyncio
    async def test_find_one_strips_id_by_default(self):
        repo, col = self._repo()
        col.find_one = AsyncMock(return_value={"_id": "x", "id": "1", "name": "a"})
        result = await repo.find_one({"id": "1"})
        col.find_one.assert_awaited_once_with({"id": "1"}, {"_id": 0})
        assert result == {"_id": "x", "id": "1", "name": "a"}  # Motor strips at DB level

    @pytest.mark.asyncio
    async def test_insert_one_strips_internal_id(self):
        repo, col = self._repo()
        doc = {"id": "abc", "name": "test"}
        result = await repo.insert_one(doc)
        col.insert_one.assert_awaited_once()
        assert "_id" not in result

    @pytest.mark.asyncio
    async def test_update_one_returns_true_on_modify(self):
        repo, col = self._repo()
        result = await repo.update_one({"id": "x"}, {"$set": {"name": "y"}})
        assert result is True

    @pytest.mark.asyncio
    async def test_update_one_returns_false_when_nothing_matched(self):
        repo, col = self._repo()
        col.update_one = AsyncMock(
            return_value=MagicMock(modified_count=0, upserted_id=None)
        )
        result = await repo.update_one({"id": "missing"}, {"$set": {"x": 1}})
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_one_returns_true(self):
        repo, col = self._repo()
        result = await repo.delete_one({"id": "z"})
        assert result is True


# ---------------------------------------------------------------------------
# UsersRepo
# ---------------------------------------------------------------------------

class TestUsersRepo:
    @pytest.mark.asyncio
    async def test_create_generates_uuid_and_timestamps(self):
        db, col = _make_db()
        repo = UsersRepo(db)
        col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="x"))
        user = await repo.create(
            email="alice@example.com",
            password_hash="$2b$hash",
            name="Alice",
            role="creator",
        )
        assert user["email"] == "alice@example.com"
        assert user["role"] == "creator"
        assert user["status"] == "active"
        assert user["kyc_status"] == "pending"
        assert len(user["id"]) == 36  # UUIDv4
        assert "created_at" in user
        assert "updated_at" in user
        assert "password_hash" in user

    @pytest.mark.asyncio
    async def test_create_lowercases_email(self):
        db, col = _make_db()
        repo = UsersRepo(db)
        col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="x"))
        user = await repo.create(
            email="Alice@Example.COM",
            password_hash="hash",
            name="Alice",
            role="creator",
        )
        assert user["email"] == "alice@example.com"

    @pytest.mark.asyncio
    async def test_find_by_email_queries_correctly(self):
        db, col = _make_db()
        repo = UsersRepo(db)
        col.find_one = AsyncMock(return_value={"id": "1", "email": "a@b.com"})
        result = await repo.find_by_email("a@b.com")
        col.find_one.assert_awaited_once_with({"email": "a@b.com"}, {"_id": 0})
        assert result["id"] == "1"


# ---------------------------------------------------------------------------
# CreatorsRepo
# ---------------------------------------------------------------------------

class TestCreatorsRepo:
    @pytest.mark.asyncio
    async def test_create_initialises_credit_fields(self):
        db, col = _make_db()
        repo = CreatorsRepo(db)
        col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="x"))
        creator = await repo.create(user_id="u1", name="Bob")
        assert creator["credit_limit"] == 50_000.0   # starter tier default
        assert creator["credit_utilised"] == 0.0
        assert creator["used_credit"] == 0.0
        assert creator["creator_score"] is None
        assert creator["agency_id"] is None

    @pytest.mark.asyncio
    async def test_create_with_agency(self):
        db, col = _make_db()
        repo = CreatorsRepo(db)
        col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="x"))
        creator = await repo.create(user_id="u2", name="Carol", agency_id="ag1")
        assert creator["agency_id"] == "ag1"


# ---------------------------------------------------------------------------
# DealsRepo
# ---------------------------------------------------------------------------

class TestDealsRepo:
    @pytest.mark.asyncio
    async def test_create_sets_uploaded_status(self):
        db, col = _make_db()
        repo = DealsRepo(db)
        col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="x"))
        deal = await repo.create(
            creator_id="c1",
            brand_id="b1",
            deal_amount=50_000.0,
            payment_terms_days=60,
        )
        assert deal["status"] == "uploaded"
        assert deal["advance_amount"] is None
        assert deal["creator_id"] == "c1"

    @pytest.mark.asyncio
    async def test_update_status_with_extra_fields(self):
        db, col = _make_db()
        repo = DealsRepo(db)
        await repo.update_status(
            "deal1",
            "scored",
            extra={"advance_amount": 40_000.0, "discount_fee": 1_500.0},
        )
        call_args = col.update_one.call_args
        update_doc = call_args[0][1]
        assert update_doc["$set"]["status"] == "scored"
        assert update_doc["$set"]["advance_amount"] == 40_000.0


# ---------------------------------------------------------------------------
# EventsRepo — append-only audit trail
# ---------------------------------------------------------------------------

class TestEventsRepo:
    @pytest.mark.asyncio
    async def test_append_only_inserts(self):
        db, col = _make_db()
        repo = EventsRepo(db)
        col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="x"))
        event = await repo.append(
            deal_id="d1",
            event_type="status_changed",
            actor_id="system",
            payload={"from": "uploaded", "to": "scored"},
        )
        assert event["event_type"] == "status_changed"
        assert event["deal_id"] == "d1"
        assert event["payload"]["from"] == "uploaded"
        # Ensure we ONLY called insert, never update
        col.update_one.assert_not_called()


# ---------------------------------------------------------------------------
# TransactionsRepo
# ---------------------------------------------------------------------------

class TestTransactionsRepo:
    @pytest.mark.asyncio
    async def test_create_sets_initiated_status(self):
        db, col = _make_db()
        repo = TransactionsRepo(db)
        col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="x"))
        txn = await repo.create(
            deal_id="d1",
            kind="disbursement",
            amount=40_000.0,
        )
        assert txn["status"] == "initiated"
        assert txn["kind"] == "disbursement"
        assert txn["completed_at"] is None

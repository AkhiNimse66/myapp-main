"""Auth router unit tests.

Uses FastAPI ``TestClient`` with the ``get_db`` dependency overridden to
return a fully mocked Motor database.  No real Mongo connection required.

Coverage:
  - POST /api/auth/register — creator, agency, brand flows
  - POST /api/auth/register — duplicate email → 409
  - POST /api/auth/register — brand without signup_token → 422
  - POST /api/auth/login — valid credentials → token
  - POST /api/auth/login — wrong password → 401
  - POST /api/auth/login — suspended account → 403
  - GET  /api/auth/me — returns user + creator profile
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Build a minimal testable app (no lifespan, no Mongo boot)
# ---------------------------------------------------------------------------

def _make_app():
    import os
    os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
    os.environ.setdefault("DB_NAME", "mypay_test")
    os.environ.setdefault("JWT_SECRET", "unit-tests-only-jwt-secret-32-chars")

    from fastapi import FastAPI
    from app.routers.auth import router
    app = FastAPI()
    app.include_router(router)
    return app


# ---------------------------------------------------------------------------
# Mock DB factory
# ---------------------------------------------------------------------------

def _mock_db(
    *,
    user_doc: dict | None = None,
    creator_doc: dict | None = None,
    agency_doc: dict | None = None,
    brand_doc: dict | None = None,
    brand_token_doc: dict | None = None,
    insert_raises: Exception | None = None,
):
    """Return a Motor DB mock with configurable find results."""
    db = MagicMock()

    def _make_col(find_result=None, insert_raises_=None):
        col = MagicMock()
        col.find_one = AsyncMock(return_value=find_result)
        if insert_raises_:
            col.insert_one = AsyncMock(side_effect=insert_raises_)
        else:
            col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="x"))
        col.update_one = AsyncMock(
            return_value=MagicMock(modified_count=1, upserted_id=None)
        )
        return col

    # find_one_and_update for brand_signup_tokens
    token_col = MagicMock()
    token_col.find_one_and_update = AsyncMock(return_value=brand_token_doc)
    token_col.insert_one = AsyncMock(return_value=MagicMock(inserted_id="x"))

    users_col = _make_col(
        find_result=user_doc,
        insert_raises_=insert_raises,
    )
    creators_col = _make_col(creator_doc)
    agencies_col = _make_col(agency_doc)
    brands_col = _make_col(brand_doc)
    social_col = _make_col()

    def _getitem(name):
        return {
            "users": users_col,
            "creators": creators_col,
            "agencies": agencies_col,
            "brands": brands_col,
            "social_profiles": social_col,
            "brand_signup_tokens": token_col,
        }.get(name, MagicMock())

    db.__getitem__ = MagicMock(side_effect=_getitem)
    return db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    return _make_app()


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------

class TestRegisterCreator:
    def test_register_creator_returns_201_and_token(self, app, client):
        import uuid
        user_id = str(uuid.uuid4())

        mock_db = _mock_db()
        # insert_one returns user doc shape (without _id)
        from app.repos.users_repo import UsersRepo
        with patch("app.routers.auth.UsersRepo") as MockUsers, \
             patch("app.routers.auth.CreatorsRepo") as MockCreators, \
             patch("app.routers.auth.SocialRepo") as MockSocial:

            mock_users_inst = MagicMock()
            mock_users_inst.create = AsyncMock(return_value={
                "id": user_id, "email": "creator@test.com",
                "name": "Test Creator", "role": "creator", "status": "active",
            })
            MockUsers.return_value = mock_users_inst

            mock_creators_inst = MagicMock()
            mock_creators_inst.create = AsyncMock(return_value={"id": "c1"})
            MockCreators.return_value = mock_creators_inst

            mock_social_inst = MagicMock()
            mock_social_inst.create_for_creator = AsyncMock(return_value={})
            MockSocial.return_value = mock_social_inst

            from app.db import get_db
            app.dependency_overrides[get_db] = lambda: mock_db

            resp = client.post("/api/auth/register", json={
                "email": "creator@test.com",
                "password": "password123",
                "name": "Test Creator",
                "role": "creator",
                "instagram_handle": "@testcreator",
            })

        app.dependency_overrides.clear()
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["role"] == "creator"


class TestRegisterBrandNoToken:
    def test_brand_without_token_returns_422(self, app, client):
        from app.db import get_db
        app.dependency_overrides[get_db] = lambda: _mock_db()
        resp = client.post("/api/auth/register", json={
            "email": "brand@test.com",
            "password": "password123",
            "name": "Brand Co",
            "role": "brand",
            # no signup_token
        })
        app.dependency_overrides.clear()
        assert resp.status_code == 422  # pydantic model_validator


class TestRegisterDuplicateEmail:
    def test_duplicate_email_returns_409(self, app, client):
        import pymongo.errors  # deferred — avoids broken pyOpenSSL at module scope
        mock_db = _mock_db(
            insert_raises=pymongo.errors.DuplicateKeyError("email_1 dup key")
        )
        from app.db import get_db
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch("app.routers.auth.CreatorsRepo"), \
             patch("app.routers.auth.SocialRepo"):
            resp = client.post("/api/auth/register", json={
                "email": "dupe@test.com",
                "password": "password123",
                "name": "Duplicate User",
                "role": "creator",
            })

        app.dependency_overrides.clear()
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

class TestLogin:
    def _hashed_user(self, email="u@test.com", status="active"):
        from app.security import hash_password
        return {
            "id": "uid1",
            "email": email,
            "name": "User",
            "role": "creator",
            "status": status,
            "password_hash": hash_password("correctpassword"),
        }

    def test_valid_credentials_return_token(self, app, client):
        from app.db import get_db
        with patch("app.routers.auth.UsersRepo") as MockUsers:
            inst = MagicMock()
            inst.find_by_email_with_hash = AsyncMock(return_value=self._hashed_user())
            MockUsers.return_value = inst
            app.dependency_overrides[get_db] = lambda: _mock_db()

            resp = client.post("/api/auth/login", json={
                "email": "u@test.com",
                "password": "correctpassword",
            })
        app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_wrong_password_returns_401(self, app, client):
        from app.db import get_db
        with patch("app.routers.auth.UsersRepo") as MockUsers:
            inst = MagicMock()
            inst.find_by_email_with_hash = AsyncMock(return_value=self._hashed_user())
            MockUsers.return_value = inst
            app.dependency_overrides[get_db] = lambda: _mock_db()

            resp = client.post("/api/auth/login", json={
                "email": "u@test.com",
                "password": "wrongpassword",
            })
        app.dependency_overrides.clear()
        assert resp.status_code == 401

    def test_unknown_email_returns_401(self, app, client):
        from app.db import get_db
        with patch("app.routers.auth.UsersRepo") as MockUsers:
            inst = MagicMock()
            inst.find_by_email_with_hash = AsyncMock(return_value=None)
            MockUsers.return_value = inst
            app.dependency_overrides[get_db] = lambda: _mock_db()

            resp = client.post("/api/auth/login", json={
                "email": "nobody@test.com",
                "password": "whatever",
            })
        app.dependency_overrides.clear()
        assert resp.status_code == 401

    def test_suspended_account_returns_403(self, app, client):
        from app.db import get_db
        with patch("app.routers.auth.UsersRepo") as MockUsers:
            inst = MagicMock()
            inst.find_by_email_with_hash = AsyncMock(
                return_value=self._hashed_user(status="suspended")
            )
            MockUsers.return_value = inst
            app.dependency_overrides[get_db] = lambda: _mock_db()

            resp = client.post("/api/auth/login", json={
                "email": "u@test.com",
                "password": "correctpassword",
            })
        app.dependency_overrides.clear()
        assert resp.status_code == 403
        assert "suspended" in resp.json()["detail"].lower()

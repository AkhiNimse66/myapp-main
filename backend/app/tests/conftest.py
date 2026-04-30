"""Shared pytest configuration."""
import os
import pytest

# Make sure unit tests don't accidentally hit the real Mongo if env is loaded.
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "mypay_test")
os.environ.setdefault("JWT_SECRET", "unit-tests-only-jwt-secret-32-chars")


@pytest.fixture
def anyio_backend():
    return "asyncio"

"""FastAPI application factory.

Replaces ``backend/server.py``. Routers are mounted incrementally as Day 3+
work lands; for now the only live endpoint is the health check, plus the
risk-engine health probe so we can verify wiring end-to-end.

Run with::

    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from starlette.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import get_db, ensure_indexes, close as close_db
from app.routers import auth as auth_router
from app.routers import deals as deals_router
from app.routers import brands as brands_router
from app.routers import creator as creator_router
from app.routers import dashboard as dashboard_router
from app.routers import contracts as contracts_router
from app.routers import admin as admin_router
from app.routers import payments as payments_router
from app.routers import seed as seed_router
from app.services.ai.factory import build_risk_decision_engine, RepoBundle
from app.services.ai.interfaces import DealContext

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("athanni")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    db = get_db()
    await ensure_indexes(db)
    logger.info(
        "Athanni API booted · db=%s · risk_policy=%s · creator_intel=%s · brand_intel=%s · compliance=%s",
        settings.DB_NAME,
        settings.RISK_POLICY,
        settings.CREATOR_INTEL_MODE,
        settings.BRAND_INTEL_MODE,
        settings.COMPLIANCE_MODE,
    )
    yield
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Athanni API",
        version=settings.ENGINE_VERSION,
        lifespan=lifespan,
    )

    origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    if "*" in origins and len(origins) > 1:
        raise ValueError("CORS_ORIGINS cannot mix '*' with explicit origins.")
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routers (mounted incrementally; add new ones here as days land) ---
    app.include_router(auth_router.router)
    app.include_router(deals_router.router)
    app.include_router(brands_router.router)
    app.include_router(creator_router.router)
    app.include_router(dashboard_router.router)
    app.include_router(contracts_router.router)
    app.include_router(admin_router.router)
    app.include_router(payments_router.router)
    app.include_router(seed_router.router)

    @app.get("/")
    async def root():
        return {
            "service": "Athanni API",
            "status": "ok",
            "version": settings.ENGINE_VERSION,
        }

    @app.get("/api/health/risk")
    async def risk_health():
        """Smoke-test the risk engine wiring without touching real DB rows."""
        engine = build_risk_decision_engine(settings, RepoBundle())
        ctx = DealContext(
            deal_id="probe",
            creator_id="probe-creator",
            brand_id="probe-brand",
            deal_amount=10_000.0,
            payment_terms_days=60,
        )
        decision = await engine.decide(ctx=ctx, creator_user_id="probe-user")
        return {
            "ok": True,
            "policy": decision.policy,
            "engine_version": decision.engine_version,
            "approved": decision.approved,
            "advance_amount": decision.advance_amount,
            "discount_fee": decision.discount_fee,
        }

    return app


app = create_app()

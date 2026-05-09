"""Centralised settings — fail-fast on missing required secrets.

The legacy code scattered ``os.environ[...]`` across five modules and silently
defaulted ``JWT_SECRET`` to ``"dev-secret"``. This module is the single source
of truth: missing or invalid secrets crash the process at boot rather than
producing a misconfigured-but-running server.
"""
from __future__ import annotations
from typing import Literal, Optional
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration; loaded from .env + process env."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- Required infra ----------
    MONGO_URL: str
    DB_NAME: str
    JWT_SECRET: str = Field(
        min_length=16,
        description="Must be ≥16 chars; never falls back to a default.",
    )

    # ---------- Auth ----------
    JWT_ALGO: str = "HS256"
    JWT_EXPIRE_HOURS: int = 72

    # ---------- App / CORS ----------
    APP_NAME: str = "athanni"
    CORS_ORIGINS: str = "http://localhost:3000"

    # ---------- External providers (optional; mock fallbacks exist) ----------
    STRIPE_API_KEY: Optional[str] = None
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    EMERGENT_LLM_KEY: Optional[str] = None
    RESEND_API_KEY: Optional[str] = None
    SENDER_EMAIL: str = "notifications@athanni.co.in"

    # ---------- Athanni bank details (shown to brands for manual NEFT/RTGS) ----------
    # Leave as XXXXX until the business account is opened.
    ATHANNI_BANK_NAME: str = "XXXXX Bank"
    ATHANNI_ACCOUNT_NAME: str = "Athanni Technologies Pvt Ltd"
    ATHANNI_ACCOUNT_NUMBER: str = "XXXXXXXXXXXX"
    ATHANNI_IFSC: str = "XXXX0000000"
    ATHANNI_ACCOUNT_TYPE: str = "Current"
    ATHANNI_UPI_ID: str = "athanni@XXXXX"

    # ---------- Creator payout service ----------
    # PAYOUT_MODE=mock    → instant synthetic payout (default, no keys needed)
    # PAYOUT_MODE=razorpay → real Razorpay Payouts API
    #   Requires: RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET (same keys as gateway)
    #   Also set: RAZORPAY_PAYOUT_ACCOUNT_NUMBER (the RazorpayX current account)
    PAYOUT_MODE: str = "mock"
    RAZORPAY_PAYOUT_ACCOUNT_NUMBER: Optional[str] = None

    # ---------- LLM / Contract parser ----------
    # CONTRACT_PARSER_MODE=mock  →  returns realistic synthetic analysis (no API key needed)
    # CONTRACT_PARSER_MODE=claude →  calls Anthropic claude-sonnet-4-6 (set ANTHROPIC_API_KEY)
    # CONTRACT_PARSER_MODE=openai →  calls gpt-4o (set OPENAI_API_KEY)
    CONTRACT_PARSER_MODE: Literal["mock", "claude", "openai"] = "mock"
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # ---------- AI / Risk modes ----------
    # MVP defaults select mocks everywhere — flip these when a real
    # provider is implemented; nothing else in the codebase changes.
    CREATOR_INTEL_MODE: Literal["mock", "instagram_graph"] = "mock"
    BRAND_INTEL_MODE: Literal["mock", "internal_db"] = "mock"
    COMPLIANCE_MODE: Literal["mock", "cibil_pan"] = "mock"
    RISK_POLICY: Literal["fixed_mvp", "heuristic", "ml"] = "fixed_mvp"

    # Stamped onto every Decision.engine_version for audit traceability
    ENGINE_VERSION: str = "1.0.0"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor. Tests can call ``get_settings.cache_clear()`` to refresh."""
    return Settings()

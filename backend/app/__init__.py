"""Athanni — production-grade backend (modular rewrite).

The legacy `server.py` monolith is being incrementally replaced by:
    app.config        — pydantic-settings, fail-fast on missing secrets
    app.db            — Motor client + index bootstrap
    app.security      — bcrypt + JWT primitives
    app.deps          — FastAPI dependencies (current_user, require_role)
    app.main          — application factory
    app.services.ai   — pluggable creator/brand/compliance intelligence + risk engine
    app.repositories  — pure Mongo I/O (Day 2)
    app.routers       — thin controllers (Day 3+)
"""
__version__ = "1.0.0"

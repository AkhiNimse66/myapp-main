"""Auth primitives — password hashing + JWT issue/decode.

Pulled out of the legacy ``server.py`` so multiple routers can reuse them
without circular imports. ``JWT_SECRET`` is read from :func:`get_settings`
which fails the boot if it is missing — no silent ``"dev-secret"`` fallback.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt

from app.config import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        # Malformed hash on the user record — treat as failed login.
        return False


def make_token(*, user_id: str, role: str) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=s.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, s.JWT_SECRET, algorithm=s.JWT_ALGO)


def decode_token(token: str) -> dict:
    """Raises ``jwt.PyJWTError`` on any failure (expired, malformed, bad signature)."""
    s = get_settings()
    return jwt.decode(token, s.JWT_SECRET, algorithms=[s.JWT_ALGO])

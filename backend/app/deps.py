"""FastAPI dependencies — current_user + RBAC gates.

Routers depend on these instead of recreating auth logic. ``require_role`` is
a factory: ``Depends(require_role("admin"))`` or ``Depends(require_role("creator", "agency"))``.
"""
from __future__ import annotations
from typing import Iterable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.db import get_db
from app.enums import Role
from app.security import decode_token

security = HTTPBearer(auto_error=True)


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Resolves the bearer token to the user document.

    Strips ``_id`` and ``password_hash`` so callers cannot accidentally leak them.
    """
    try:
        payload = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    db = get_db()
    user = await db.users.find_one(
        {"id": payload["sub"]},
        {"_id": 0, "password_hash": 0},
    )
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    if user.get("status") == "suspended":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account suspended")
    return user


def require_role(*roles: str | Role):
    """Returns a dependency that 403s if the caller's role isn't in the allow-list."""
    allowed = {r.value if isinstance(r, Role) else r for r in roles}

    async def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Requires role: {', '.join(sorted(allowed))}",
            )
        return user

    _checker.__name__ = f"require_role_{'_'.join(sorted(allowed))}"
    return _checker

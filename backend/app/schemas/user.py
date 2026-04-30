"""User response schemas."""
from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    """Public user representation — no password_hash, no _id."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    role: str
    status: str
    kyc_status: str
    created_at: str

    # Profile hydrated by /auth/me based on role
    profile: Optional[Dict[str, Any]] = None

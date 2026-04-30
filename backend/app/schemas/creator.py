"""Creator profile schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class CreatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    agency_id: Optional[str] = None
    name: str
    bio: Optional[str] = None
    category: Optional[str] = None
    credit_limit: float
    credit_utilised: float
    kyc_status: str
    creator_score: Optional[float] = None
    created_at: str


class CreatorUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    bio: Optional[str] = None
    category: Optional[str] = None
    agency_id: Optional[str] = None

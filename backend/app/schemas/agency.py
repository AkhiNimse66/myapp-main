"""Agency profile schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class AgencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    website: Optional[str] = None
    commission_rate: float
    creator_count: int
    created_at: str


class AgencyUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Optional[str] = None
    website: Optional[str] = None
    commission_rate: Optional[float] = None

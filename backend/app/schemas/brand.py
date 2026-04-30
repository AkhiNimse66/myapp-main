"""Brand profile schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    risk_score: Optional[str] = None
    payment_reliability: Optional[float] = None
    verified: bool
    created_at: str


class BrandUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    website: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None

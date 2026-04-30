"""Deal request/response schemas."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DealCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    brand_id: str
    deal_title: str = Field(min_length=1, max_length=200)
    deal_amount: float = Field(gt=0)
    payment_terms_days: int = Field(gt=0, le=365)
    contract_text: Optional[str] = None
    contract_file_id: Optional[str] = None
    contract_file_name: Optional[str] = None
    contract_file_mime: Optional[str] = None
    currency: str = "INR"


class RiskFactor(BaseModel):
    label: str
    value: str
    weight: float


class RiskSnapshot(BaseModel):
    """Stored on the deal after scoring. Shape mirrors what DealDetail.jsx reads."""
    risk_score: float           # 0-100 composite
    advance_rate: float         # e.g., 80.0 → "80%"
    discount_fee_rate: float    # e.g., 3.0  → "3%"
    apr_equivalent: float       # e.g., 18.25 → "18.25%"
    brand_component: float      # 0-100 brand solvency score
    creator_component: float    # 0-100 creator health score
    approved: bool
    requires_admin_review: bool
    policy: str
    engine_version: str
    rationale: List[str]
    factors: List[RiskFactor]
    decision_at: str
    ml: Optional[Dict[str, Any]] = None


class DealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    creator_id: str
    brand_id: str
    brand_name: Optional[str] = None
    deal_title: Optional[str] = None
    deal_amount: float
    advance_amount: Optional[float] = None
    discount_fee: Optional[float] = None
    payment_terms_days: int
    currency: str
    status: str
    contract_file_id: Optional[str] = None
    contract_file_name: Optional[str] = None
    contract_file_size: Optional[int] = None
    contract_text: Optional[str] = None
    maturity_date: Optional[str] = None
    disbursed_at: Optional[str] = None
    repaid_at: Optional[str] = None
    created_at: str
    risk: Optional[Dict[str, Any]] = None     # RiskSnapshot as dict


class DealListItem(BaseModel):
    """Lightweight row for the deals table."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    brand_id: str
    brand_name: Optional[str] = None
    deal_title: Optional[str] = None
    deal_amount: float
    advance_amount: Optional[float] = None
    discount_fee: Optional[float] = None
    payment_terms_days: int
    status: str
    created_at: str
    risk: Optional[Dict[str, Any]] = None

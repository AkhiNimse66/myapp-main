"""Auth request/response schemas.

``RegisterRequest`` is intentionally flat (no nested objects) to keep the
mobile client simple.  Role-specific fields (instagram_handle, agency_name,
brand_website, signup_token) are optional at the schema level; the router
validates presence based on the selected role.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.enums import Role


class RegisterRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters")
    name: str = Field(min_length=1, max_length=100)
    role: Role

    # --- Creator-specific ---
    instagram_handle: Optional[str] = Field(None, max_length=50)

    # --- Agency-specific ---
    agency_name: Optional[str] = Field(None, max_length=100)

    # --- Brand-specific ---
    signup_token: Optional[str] = None           # admin-issued one-time token (required for brands)
    brand_website: Optional[str] = Field(None, max_length=200)
    brand_company_name: Optional[str] = Field(None, max_length=150)   # legal entity name
    brand_industry: Optional[str] = Field(None, max_length=100)
    brand_company_type: Optional[str] = Field(None, max_length=50)    # startup/SME/enterprise/MNC
    brand_gst_number: Optional[str] = Field(None, max_length=20)
    brand_pan_number: Optional[str] = Field(None, max_length=15)
    brand_phone: Optional[str] = Field(None, max_length=20)
    brand_billing_email: Optional[str] = Field(None, max_length=200)

    @model_validator(mode="after")
    def _role_fields(self) -> "RegisterRequest":
        if self.role == Role.BRAND and not self.signup_token:
            raise ValueError("Brand registration requires a signup_token issued by an admin.")
        return self


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    name: str


class SignupTokenCreate(BaseModel):
    """Admin endpoint: pre-issue a brand signup token."""
    brand_name: Optional[str] = None   # optional pre-association
    notes: Optional[str] = None

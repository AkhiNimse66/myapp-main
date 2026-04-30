"""Enums shared across services. ``str`` subclassing keeps them JSON-safe."""
from __future__ import annotations
from enum import Enum


class Role(str, Enum):
    CREATOR = "creator"
    AGENCY = "agency"
    BRAND = "brand"
    ADMIN = "admin"


class DealStatus(str, Enum):
    UPLOADED = "uploaded"
    SCORED = "scored"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISBURSED = "disbursed"
    AWAITING_PAYMENT = "awaiting_payment"
    REPAID = "repaid"
    DEFAULTED = "defaulted"


class TxnKind(str, Enum):
    DISBURSEMENT = "disbursement"
    REPAYMENT = "repayment"
    FEE_CAPTURE = "fee_capture"
    REFUND = "refund"


class TxnStatus(str, Enum):
    INITIATED = "initiated"
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class KycStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

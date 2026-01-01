"""Payment schemas for provider communication."""

from decimal import Decimal
from enum import IntEnum
from uuid import UUID

from pydantic import BaseModel, Field


class PaymentInitParams(BaseModel):
    """Parameters for payment initiation (matches Robokassa format)."""

    merchant_login: str = Field(..., description="Merchant login")
    out_sum: Decimal = Field(..., description="Payment amount in RUB")
    inv_id: int = Field(..., ge=1, description="Invoice ID (1-9223372036854775807)")
    description: str = Field(..., max_length=100, description="Payment description")
    signature: str = Field(..., description="MD5 signature")

    # Optional parameters
    culture: str = Field(default="ru", description="Interface language")
    email: str | None = Field(default=None, description="Customer email")
    is_test: bool = Field(default=False, description="Test mode flag")

    # Custom Shp_* parameters
    shp_invoice_id: UUID = Field(..., description="Our invoice UUID")
    shp_user_id: int = Field(..., description="Telegram user ID")


class WebhookData(BaseModel):
    """ResultURL callback data (matches Robokassa format)."""

    out_sum: Decimal = Field(..., description="Payment amount")
    inv_id: int = Field(..., description="Invoice ID")
    signature: str = Field(..., description="Signature for verification")

    # Optional from Robokassa
    fee: Decimal | None = Field(default=None, description="Payment fee")
    email: str | None = Field(default=None, description="Customer email")
    payment_method: str | None = Field(default=None, description="Payment method used")

    # Custom Shp_* parameters
    shp_invoice_id: UUID = Field(..., description="Our invoice UUID")
    shp_user_id: int = Field(..., description="Telegram user ID")


class PaymentStatus(IntEnum):
    """OpStateExt status codes from Robokassa."""

    INITIALIZED = 5
    CANCELLED = 10
    RESERVED = 50  # Hold
    CANCELLED_AFTER_RESERVE = 60
    TRANSFERRED = 80
    COMPLETED = 100

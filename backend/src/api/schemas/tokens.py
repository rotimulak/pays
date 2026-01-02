"""Token API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TokenBalanceResponse(BaseModel):
    """Response for balance check."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    token_balance: int = Field(..., ge=0)
    subscription_active: bool
    subscription_end: datetime | None
    can_spend: bool
    reason: str | None = None


class SpendTokensRequest(BaseModel):
    """Request to spend tokens."""

    amount: int = Field(..., gt=0, le=10000, description="Amount to spend")
    description: str = Field(..., min_length=1, max_length=500)
    idempotency_key: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Unique key to prevent duplicate spending",
    )
    metadata: dict | None = Field(None, description="Additional data")


class SpendTokensResponse(BaseModel):
    """Response after spending tokens."""

    success: bool = True
    transaction_id: UUID
    tokens_spent: int
    balance_before: int
    balance_after: int


class ErrorResponse(BaseModel):
    """Error response."""

    error: str  # Error code
    message: str  # Human-readable message
    details: dict | None = None


class TokenErrorCode:
    """Error codes for token operations."""

    INSUFFICIENT_BALANCE = "insufficient_balance"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    USER_NOT_FOUND = "user_not_found"
    USER_BLOCKED = "user_blocked"
    INVALID_AMOUNT = "invalid_amount"
    RATE_LIMITED = "rate_limited"
    CONCURRENT_MODIFICATION = "concurrent_modification"

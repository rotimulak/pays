"""User DTOs for service layer."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, computed_field


class SubscriptionStatus(str, Enum):
    """Subscription status enum."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRING_TODAY = "expiring_today"
    EXPIRED = "expired"


class UserProfile(BaseModel):
    """DTO for user profile display."""

    id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    token_balance: int
    subscription_end: datetime | None
    subscription_status: SubscriptionStatus
    subscription_status_text: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_name(self) -> str:
        """Return first_name or default."""
        return self.first_name or "Пользователь"

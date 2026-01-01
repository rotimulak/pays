"""Tariff DTOs for service layer."""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, computed_field


class TariffDTO(BaseModel):
    """DTO for tariff display."""

    id: UUID
    slug: str
    name: str
    description: str | None
    price: Decimal
    tokens: int
    subscription_days: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def price_display(self) -> str:
        """Format price with currency symbol."""
        # Remove trailing zeros and format
        price_str = f"{self.price:.2f}".rstrip("0").rstrip(".")
        return f"{price_str} ₽"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def benefits(self) -> str:
        """Format benefits as a string."""
        parts: list[str] = []

        if self.tokens > 0:
            parts.append(f"{self.tokens} токенов")

        if self.subscription_days > 0:
            parts.append(f"{self.subscription_days} дней подписки")

        return " + ".join(parts) if parts else "—"

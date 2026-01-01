"""Promo code DTOs for service layer."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, computed_field

from src.db.models.promo_code import DiscountType


class PromoCodeDTO(BaseModel):
    """DTO for promo code display."""

    id: UUID
    code: str
    discount_type: DiscountType
    discount_value: Decimal
    max_uses: int | None
    uses_count: int
    valid_from: datetime | None
    valid_until: datetime | None
    tariff_id: UUID | None
    is_active: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def discount_display(self) -> str:
        """Format discount for display."""
        match self.discount_type:
            case DiscountType.PERCENT:
                return f"{int(self.discount_value)}%"
            case DiscountType.FIXED:
                return f"{self.discount_value:.0f} ₽"
            case DiscountType.BONUS_TOKENS:
                return f"+{int(self.discount_value)} токенов"
            case _:
                return str(self.discount_value)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def uses_left(self) -> int | None:
        """Calculate remaining uses."""
        if self.max_uses is None:
            return None
        return max(0, self.max_uses - self.uses_count)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_valid(self) -> bool:
        """Check if promo code can be used right now."""
        if not self.is_active:
            return False

        now = datetime.utcnow()

        if self.valid_from and self.valid_from > now:
            return False

        if self.valid_until and self.valid_until < now:
            return False

        if self.max_uses and self.uses_count >= self.max_uses:
            return False

        return True


class PromoValidationResult(BaseModel):
    """Result of promo code validation."""

    valid: bool
    error: str | None = None
    promo: PromoCodeDTO | None = None


class DiscountPreviewDTO(BaseModel):
    """Preview of discount before applying."""

    original_amount: Decimal
    final_amount: Decimal
    discount_amount: Decimal
    bonus_tokens: int
    promo_code: str
    promo_description: str  # "Скидка 20% по промокоду SALE20"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def original_amount_display(self) -> str:
        """Format original amount."""
        return f"{self.original_amount:.0f} ₽"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def final_amount_display(self) -> str:
        """Format final amount."""
        return f"{self.final_amount:.0f} ₽"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def discount_display(self) -> str:
        """Format discount for display."""
        if self.discount_amount > 0:
            return f"-{self.discount_amount:.0f} ₽"
        return ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_discount(self) -> bool:
        """Check if there's any discount or bonus."""
        return self.final_amount < self.original_amount or self.bonus_tokens > 0

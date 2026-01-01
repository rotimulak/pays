"""Promo code service for business logic."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ValidationError
from src.db.models.promo_code import DiscountType, PromoCode
from src.db.repositories.promo_code_repository import PromoCodeRepository


@dataclass
class DiscountResult:
    """Result of discount calculation."""

    original_amount: Decimal
    final_amount: Decimal
    discount_amount: Decimal
    bonus_tokens: int
    promo_code: PromoCode
    description: str  # "Скидка 20%" or "50 ₽ скидка" or "+50 бонусных токенов"


class PromoService:
    """Service for promo code operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.promo_repo = PromoCodeRepository(session)

    async def validate_promo(
        self,
        code: str,
        tariff_id: UUID | None = None,
    ) -> PromoCode:
        """Validate promo code and return it.

        Args:
            code: Promo code string
            tariff_id: Optional tariff to validate against

        Returns:
            Valid PromoCode

        Raises:
            ValidationError: If promo code is invalid
        """
        promo, error = await self.promo_repo.can_use(code, tariff_id)

        if error:
            raise ValidationError(message=error)

        if promo is None:
            raise ValidationError(message="Промокод не найден")

        return promo

    async def calculate_discount(
        self,
        code: str,
        original_amount: Decimal,
        tariff_id: UUID | None = None,
    ) -> DiscountResult:
        """Calculate discount for promo code.

        Args:
            code: Promo code string
            original_amount: Original price
            tariff_id: Tariff ID for validation

        Returns:
            DiscountResult with calculated values

        Raises:
            ValidationError: If promo code is invalid
        """
        promo = await self.validate_promo(code, tariff_id)

        final_amount, bonus_tokens, description = self._apply_discount(
            promo, original_amount
        )

        return DiscountResult(
            original_amount=original_amount,
            final_amount=final_amount,
            discount_amount=original_amount - final_amount,
            bonus_tokens=bonus_tokens,
            promo_code=promo,
            description=description,
        )

    def _apply_discount(
        self,
        promo: PromoCode,
        amount: Decimal,
    ) -> tuple[Decimal, int, str]:
        """Apply discount to amount.

        Returns:
            (final_amount, bonus_tokens, description)
        """
        bonus_tokens = 0

        match promo.discount_type:
            case DiscountType.PERCENT:
                discount = amount * promo.discount_value / 100
                final = amount - discount
                description = f"Скидка {int(promo.discount_value)}%"

            case DiscountType.FIXED:
                # Minimum amount is 1 ruble
                final = max(amount - promo.discount_value, Decimal("1.00"))
                actual_discount = amount - final
                description = f"Скидка {actual_discount:.0f} ₽"

            case DiscountType.BONUS_TOKENS:
                final = amount
                bonus_tokens = int(promo.discount_value)
                description = f"+{bonus_tokens} бонусных токенов"

            case _:
                final = amount
                description = ""

        # Round to 2 decimal places
        final = final.quantize(Decimal("0.01"))

        return final, bonus_tokens, description

    async def use_promo(self, promo_id: UUID) -> int:
        """Mark promo code as used.

        Returns:
            New uses_count
        """
        return await self.promo_repo.increment_uses(promo_id)

    async def get_by_code(self, code: str) -> PromoCode | None:
        """Get promo code by code string."""
        return await self.promo_repo.get_by_code(code)

    async def get_active(self) -> list[PromoCode]:
        """Get all active promo codes."""
        return await self.promo_repo.get_active()

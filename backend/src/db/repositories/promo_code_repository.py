"""Repository for PromoCode model operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.promo_code import PromoCode


class PromoCodeRepository:
    """Repository for promo code operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, promo_id: UUID) -> PromoCode | None:
        """Get promo code by ID."""
        result = await self.session.execute(
            select(PromoCode).where(PromoCode.id == promo_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> PromoCode | None:
        """Get promo code by code string (case-insensitive).

        Args:
            code: Promo code string

        Returns:
            PromoCode or None if not found
        """
        result = await self.session.execute(
            select(PromoCode).where(PromoCode.code.ilike(code))
        )
        return result.scalar_one_or_none()

    async def create(self, promo: PromoCode) -> PromoCode:
        """Create new promo code."""
        self.session.add(promo)
        await self.session.flush()
        await self.session.refresh(promo)
        return promo

    async def update(self, promo: PromoCode) -> PromoCode:
        """Update promo code."""
        promo.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(promo)
        return promo

    async def increment_uses(self, promo_id: UUID) -> int:
        """Increment uses_count atomically.

        Returns:
            New uses_count value
        """
        result = await self.session.execute(
            update(PromoCode)
            .where(PromoCode.id == promo_id)
            .values(
                uses_count=PromoCode.uses_count + 1,
                updated_at=datetime.utcnow(),
            )
            .returning(PromoCode.uses_count)
        )
        return result.scalar_one()

    async def get_all(self) -> list[PromoCode]:
        """Get all promo codes."""
        result = await self.session.execute(
            select(PromoCode).order_by(PromoCode.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active(self) -> list[PromoCode]:
        """Get all currently active promo codes.

        Filters by:
        - is_active = True
        - valid_from <= now (or null)
        - valid_until >= now (or null)
        """
        now = datetime.utcnow()
        result = await self.session.execute(
            select(PromoCode)
            .where(PromoCode.is_active.is_(True))
            .where(
                (PromoCode.valid_from <= now) | (PromoCode.valid_from.is_(None))
            )
            .where(
                (PromoCode.valid_until >= now) | (PromoCode.valid_until.is_(None))
            )
            .order_by(PromoCode.created_at.desc())
        )
        return list(result.scalars().all())

    async def deactivate(self, promo_id: UUID) -> PromoCode | None:
        """Deactivate promo code.

        Args:
            promo_id: Promo code UUID

        Returns:
            Deactivated promo code or None if not found
        """
        result = await self.session.execute(
            update(PromoCode)
            .where(PromoCode.id == promo_id)
            .values(
                is_active=False,
                updated_at=datetime.utcnow(),
            )
            .returning(PromoCode)
        )
        return result.scalar_one_or_none()

    async def is_valid(
        self,
        promo: PromoCode,
        tariff_id: UUID | None = None,
    ) -> tuple[bool, str | None]:
        """Check if promo code is valid for use.

        Args:
            promo: PromoCode to validate
            tariff_id: Optional tariff to check restriction

        Returns:
            (is_valid, error_message)
        """
        now = datetime.utcnow()

        # Check if active
        if not promo.is_active:
            return False, "Промокод неактивен"

        # Check valid_from
        if promo.valid_from and promo.valid_from > now:
            return False, "Промокод ещё не активен"

        # Check valid_until
        if promo.valid_until and promo.valid_until < now:
            return False, "Срок действия промокода истёк"

        # Check uses limit
        if promo.max_uses and promo.uses_count >= promo.max_uses:
            return False, "Лимит использований промокода исчерпан"

        # Check tariff restriction
        if promo.tariff_id and tariff_id and promo.tariff_id != tariff_id:
            return False, "Промокод не применим к этому тарифу"

        return True, None

    async def can_use(
        self,
        code: str,
        tariff_id: UUID | None = None,
    ) -> tuple[PromoCode | None, str | None]:
        """Check if promo code can be used and return it.

        Args:
            code: Promo code string
            tariff_id: Optional tariff ID

        Returns:
            (promo_code, error_message)
            If valid: (PromoCode, None)
            If invalid: (None, "error message")
        """
        promo = await self.get_by_code(code)

        if not promo:
            return None, "Промокод не найден"

        is_valid, error = await self.is_valid(promo, tariff_id)

        if not is_valid:
            return None, error

        return promo, None

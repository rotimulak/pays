"""Repository for PromoActivation model operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.promo_activation import PromoActivation


class PromoActivationRepository:
    """Repository for promo activation operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, activation: PromoActivation) -> PromoActivation:
        """Create new activation record.

        Args:
            activation: PromoActivation instance to create

        Returns:
            Created activation record
        """
        self.session.add(activation)
        await self.session.flush()
        await self.session.refresh(activation)
        return activation

    async def has_activated_tariff(self, user_id: int, tariff_id: UUID) -> bool:
        """Check if user has already activated this tariff.

        Args:
            user_id: User's Telegram ID
            tariff_id: Tariff UUID

        Returns:
            True if user has activated this tariff before
        """
        result = await self.session.execute(
            select(PromoActivation.id)
            .where(PromoActivation.user_id == user_id)
            .where(PromoActivation.tariff_id == tariff_id)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_user_activations(self, user_id: int) -> list[PromoActivation]:
        """Get all activations for user.

        Args:
            user_id: User's Telegram ID

        Returns:
            List of activation records for user
        """
        result = await self.session.execute(
            select(PromoActivation)
            .where(PromoActivation.user_id == user_id)
            .order_by(PromoActivation.activated_at.desc())
        )
        return list(result.scalars().all())

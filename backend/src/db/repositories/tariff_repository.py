from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundError
from src.db.models.tariff import Tariff


class TariffRepository:
    """Repository for Tariff model operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, tariff_id: UUID) -> Tariff | None:
        """Get tariff by ID."""
        result = await self.session.execute(
            select(Tariff).where(Tariff.id == tariff_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Tariff | None:
        """Get tariff by slug."""
        result = await self.session.execute(
            select(Tariff).where(Tariff.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_active(self) -> list[Tariff]:
        """Get all active tariffs sorted by sort_order."""
        result = await self.session.execute(
            select(Tariff)
            .where(Tariff.is_active.is_(True))
            .order_by(Tariff.sort_order)
        )
        return list(result.scalars().all())

    async def create(self, tariff: Tariff) -> Tariff:
        """Create new tariff."""
        self.session.add(tariff)
        await self.session.flush()
        await self.session.refresh(tariff)
        return tariff

    async def update(self, tariff: Tariff) -> Tariff:
        """Update tariff."""
        tariff.updated_at = datetime.utcnow()
        await self.session.flush()
        await self.session.refresh(tariff)
        return tariff

    async def deactivate(self, tariff_id: UUID) -> Tariff:
        """Set is_active=False (soft delete).

        Args:
            tariff_id: Tariff UUID

        Returns:
            Deactivated tariff

        Raises:
            NotFoundError: If tariff not found
        """
        stmt = (
            update(Tariff)
            .where(Tariff.id == tariff_id)
            .values(
                is_active=False,
                updated_at=datetime.utcnow(),
            )
            .returning(Tariff)
        )

        result = await self.session.execute(stmt)
        tariff = result.scalar_one_or_none()

        if tariff is None:
            raise NotFoundError(
                message=f"Tariff {tariff_id} not found",
                details={"tariff_id": str(tariff_id)},
            )

        return tariff

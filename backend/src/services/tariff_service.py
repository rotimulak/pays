"""Tariff service for business logic."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.tariff import Tariff
from src.db.repositories.tariff_repository import TariffRepository
from src.services.dto.tariff import TariffDTO


class TariffService:
    """Service for tariff-related operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.tariff_repo = TariffRepository(session)

    async def get_active_tariffs(self) -> list[TariffDTO]:
        """Get all active tariffs sorted by sort_order.

        Returns:
            List of TariffDTO for display.
        """
        tariffs = await self.tariff_repo.get_active()
        return [self._to_dto(t) for t in tariffs]

    async def get_tariff_by_id(self, tariff_id: UUID) -> TariffDTO | None:
        """Get tariff by ID."""
        tariff = await self.tariff_repo.get_by_id(tariff_id)
        return self._to_dto(tariff) if tariff else None

    async def get_tariff_by_slug(self, slug: str) -> TariffDTO | None:
        """Get tariff by slug."""
        tariff = await self.tariff_repo.get_by_slug(slug)
        return self._to_dto(tariff) if tariff else None

    def format_tariff_for_display(self, tariff: TariffDTO) -> str:
        """Format tariff for Telegram message.

        Example:
            💎 Premium
            100 токенов + 30 дней подписки
            💰 499 ₽
        """
        lines = [
            f"<b>{tariff.name}</b>",
        ]

        if tariff.description:
            lines.append(f"<i>{tariff.description}</i>")

        lines.append(tariff.benefits)
        lines.append(f"💰 {tariff.price_display}")

        return "\n".join(lines)

    def format_tariffs_list(self, tariffs: list[TariffDTO]) -> str:
        """Format list of tariffs for Telegram message."""
        if not tariffs:
            return "Нет доступных тарифов."

        header = "💰 <b>Доступные тарифы</b>\n\nВыбери подходящий тариф:"
        tariff_texts = [self.format_tariff_for_display(t) for t in tariffs]

        return header + "\n\n" + "\n\n".join(tariff_texts)

    @staticmethod
    def _to_dto(tariff: Tariff) -> TariffDTO:
        """Convert Tariff model to DTO."""
        return TariffDTO(
            id=tariff.id,
            slug=tariff.slug,
            name=tariff.name,
            description=tariff.description,
            price=tariff.price,
            tokens=tariff.tokens,
            subscription_days=tariff.subscription_days,
        )

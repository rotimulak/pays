"""Invoice DTOs for service layer."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, computed_field

from src.db.models.invoice import InvoiceStatus


class InvoiceDTO(BaseModel):
    """DTO for invoice display."""

    id: UUID
    inv_id: int
    amount: Decimal
    original_amount: Decimal
    tokens: int
    subscription_days: int
    status: InvoiceStatus
    tariff_name: str
    created_at: datetime
    expires_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def amount_display(self) -> str:
        """Format amount with currency symbol."""
        amount_str = f"{self.amount:.2f}".rstrip("0").rstrip(".")
        return f"{amount_str} ₽"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def discount(self) -> Decimal | None:
        """Calculate discount amount if promo applied."""
        if self.original_amount > self.amount:
            return self.original_amount - self.amount
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def status_display(self) -> str:
        """Format status for display."""
        status_map: dict[InvoiceStatus, str] = {
            InvoiceStatus.PENDING: "⏳ Ожидает оплаты",
            InvoiceStatus.PAID: "✅ Оплачен",
            InvoiceStatus.EXPIRED: "⌛ Истёк",
            InvoiceStatus.CANCELLED: "❌ Отменён",
            InvoiceStatus.REFUNDED: "↩️ Возвращён",
        }
        return status_map.get(self.status, self.status.value)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_expired(self) -> bool:
        """Check if invoice is expired."""
        if self.status != InvoiceStatus.PENDING:
            return False

        now = datetime.now(UTC)
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        return expires_at < now

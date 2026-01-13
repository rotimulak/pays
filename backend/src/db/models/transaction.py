import enum
import uuid
from datetime import datetime

from typing import Any

from sqlalchemy import BigInteger, Enum, Float, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base


class TransactionType(enum.Enum):
    """Token transaction type."""

    TOPUP = "topup"
    SPEND = "spend"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"
    SUBSCRIPTION = "subscription"


class Transaction(Base):
    """Token transaction model."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Transaction UUID",
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="User who owns the transaction",
    )
    type: Mapped[TransactionType] = mapped_column(
        Enum(
            TransactionType,
            name="transaction_type",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        comment="Transaction type",
    )
    tokens_delta: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Token change (positive or negative)",
    )
    balance_after: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Token balance after transaction",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Transaction description",
    )
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        comment="Related invoice for topup/refund",
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        comment="Additional transaction data",
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
        comment="Transaction time",
    )

    # Relationships
    user: Mapped["User"] = relationship(  # type: ignore[name-defined] # noqa: F821
        back_populates="transactions",
        lazy="selectin",
    )
    invoice: Mapped["Invoice | None"] = relationship(  # type: ignore[name-defined] # noqa: F821
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_transactions_user_id", "user_id"),
        Index("idx_transactions_created_at", "created_at"),
        Index("idx_transactions_type", "type"),
    )

    def __repr__(self) -> str:
        return (
            f"Transaction(id={self.id}, type={self.type.value}, "
            f"delta={self.tokens_delta:+.2f})"
        )

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base


class InvoiceStatus(enum.Enum):
    """Invoice payment status."""

    PENDING = "pending"
    PAID = "paid"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Invoice(Base):
    """Invoice (payment order) model."""

    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Invoice UUID",
    )
    inv_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        comment="Robokassa invoice ID",
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="User who created the invoice",
    )
    tariff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tariffs.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Purchased tariff",
    )
    promo_code_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("promo_codes.id", ondelete="SET NULL"),
        nullable=True,
        comment="Applied promo code",
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Amount to pay after discount",
    )
    original_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Original amount before discount",
    )
    tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Tokens to credit on payment",
    )
    subscription_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Subscription days to add on payment",
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status", create_constraint=True),
        default=InvoiceStatus.PENDING,
        nullable=False,
        comment="Payment status",
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="Idempotency key to prevent duplicates",
    )
    payment_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Payment gateway URL",
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Payment completion time",
    )
    expires_at: Mapped[datetime] = mapped_column(
        nullable=False,
        comment="Invoice expiration time",
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
        comment="Record creation time",
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        comment="Record update time",
    )

    # Relationships
    user: Mapped["User"] = relationship(  # type: ignore[name-defined] # noqa: F821
        back_populates="invoices",
        lazy="selectin",
    )
    tariff: Mapped["Tariff"] = relationship(  # type: ignore[name-defined] # noqa: F821
        lazy="selectin",
    )
    promo_code: Mapped["PromoCode | None"] = relationship(  # type: ignore[name-defined] # noqa: F821
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("idx_invoices_user_id", "user_id"),
        Index("idx_invoices_status", "status"),
        Index("idx_invoices_idempotency_key", "idempotency_key"),
        Index("idx_invoices_inv_id", "inv_id"),
        Index(
            "idx_invoices_expires_at_pending",
            "expires_at",
            postgresql_where="status = 'pending'",
        ),
    )

    def __repr__(self) -> str:
        return f"Invoice(id={self.id}, inv_id={self.inv_id}, status={self.status.value})"

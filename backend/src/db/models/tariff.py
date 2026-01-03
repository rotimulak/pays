import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.session import Base


class PeriodUnit(str, Enum):
    """Period unit for subscription duration."""

    HOUR = "hour"  # for testing
    DAY = "day"
    MONTH = "month"


class Tariff(Base):
    """Tariff (pricing plan) model."""

    __tablename__ = "tariffs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Tariff UUID",
    )
    slug: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="URL-friendly identifier",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Display name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Tariff description",
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Price in RUB",
    )
    tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of tokens included",
    )
    subscription_days: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Subscription duration in days (legacy, use period_unit/period_value)",
    )
    # M11: New period fields
    period_unit: Mapped[PeriodUnit] = mapped_column(
        SQLEnum(PeriodUnit, name="period_unit", create_constraint=True),
        default=PeriodUnit.MONTH,
        nullable=False,
        comment="Period unit: hour/day/month",
    )
    period_value: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Number of period units",
    )
    subscription_fee: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
        comment="Subscription fee in tokens per period",
    )
    min_payment: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("200.00"),
        nullable=False,
        comment="Minimum payment amount in RUB",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Display order",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Tariff is available for purchase",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Tariff version for history tracking",
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

    __table_args__ = (
        CheckConstraint("price > 0", name="price_positive"),
        CheckConstraint("tokens >= 0", name="tokens_non_negative"),
        CheckConstraint("subscription_days >= 0", name="subscription_days_non_negative"),
        CheckConstraint("period_value > 0", name="period_value_positive"),
        CheckConstraint("subscription_fee >= 0", name="subscription_fee_non_negative"),
        CheckConstraint("min_payment > 0", name="min_payment_positive"),
    )

    def __repr__(self) -> str:
        return f"Tariff(id={self.id}, slug={self.slug!r}, price={self.price})"

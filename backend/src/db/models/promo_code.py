import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base


class DiscountType(enum.Enum):
    """Discount type for promo codes."""

    PERCENT = "percent"
    FIXED = "fixed"


class PromoCode(Base):
    """Promo code model."""

    __tablename__ = "promo_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Promo code UUID",
    )
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="Promo code string",
    )
    discount_type: Mapped[DiscountType] = mapped_column(
        Enum(DiscountType, name="discount_type", create_constraint=True),
        nullable=False,
        comment="Type of discount",
    )
    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Discount amount (% or fixed RUB)",
    )
    max_uses: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum number of uses (null = unlimited)",
    )
    uses_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Current usage count",
    )
    valid_from: Mapped[datetime] = mapped_column(
        nullable=False,
        comment="Start of validity period",
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="End of validity period (null = no expiry)",
    )
    tariff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tariffs.id", ondelete="SET NULL"),
        nullable=True,
        comment="Limit to specific tariff (null = all tariffs)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Promo code is usable",
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
    tariff: Mapped["Tariff | None"] = relationship(  # type: ignore[name-defined] # noqa: F821
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("discount_value > 0", name="discount_value_positive"),
        CheckConstraint("uses_count >= 0", name="uses_count_non_negative"),
        CheckConstraint(
            "max_uses IS NULL OR max_uses > 0",
            name="max_uses_positive_or_null",
        ),
    )

    def __repr__(self) -> str:
        return f"PromoCode(id={self.id}, code={self.code!r})"

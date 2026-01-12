"""Promo code activation history model."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base


class PromoActivation(Base):
    """Promo code activation history."""

    __tablename__ = "promo_activations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Activation UUID",
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who activated the promo",
    )
    tariff_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tariffs.id", ondelete="CASCADE"),
        nullable=False,
        comment="Activated tariff",
    )
    promo_code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("promo_codes.id", ondelete="CASCADE"),
        nullable=False,
        comment="Used promo code",
    )
    activated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
        comment="Activation time",
    )
    tokens_credited: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of tokens credited",
    )
    subscription_days_added: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of subscription days added",
    )

    # Relationships
    user: Mapped["User"] = relationship(lazy="selectin")  # type: ignore[name-defined]  # noqa: F821
    tariff: Mapped["Tariff"] = relationship(lazy="selectin")  # type: ignore[name-defined]  # noqa: F821
    promo_code: Mapped["PromoCode"] = relationship(lazy="selectin")  # type: ignore[name-defined]  # noqa: F821

    __table_args__ = (
        CheckConstraint("tokens_credited >= 0", name="tokens_credited_non_negative"),
        CheckConstraint(
            "subscription_days_added >= 0", name="subscription_days_non_negative"
        ),
        Index(
            "idx_promo_activations_user_tariff",
            "user_id",
            "tariff_id",
            unique=True,
        ),
        Index("idx_promo_activations_user_id", "user_id"),
        Index("idx_promo_activations_promo_code_id", "promo_code_id"),
    )

    def __repr__(self) -> str:
        return f"PromoActivation(id={self.id}, user_id={self.user_id}, tariff_id={self.tariff_id})"

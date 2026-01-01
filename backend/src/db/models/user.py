from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base

if TYPE_CHECKING:
    from src.db.models.invoice import Invoice
    from src.db.models.transaction import Transaction


class User(Base):
    """Telegram user model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        comment="Telegram user_id",
    )
    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Telegram username",
    )
    first_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User first name",
    )
    last_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User last name",
    )
    token_balance: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Token balance",
    )
    balance_version: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Version for optimistic locking",
    )
    subscription_end: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Subscription end date",
    )
    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="User is blocked",
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
    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="user",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("token_balance >= 0", name="token_balance_non_negative"),
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, username={self.username!r})"

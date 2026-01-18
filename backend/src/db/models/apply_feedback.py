"""Apply feedback model for user reactions on generated responses."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base


class FeedbackRating(str, enum.Enum):
    """User feedback rating for generated apply response."""

    BAD = "bad"  # 🤮
    OK = "ok"  # 😐
    GREAT = "great"  # 🤩


class ApplyFeedback(Base):
    """User feedback on generated apply response."""

    __tablename__ = "apply_feedbacks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Feedback UUID",
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who gave feedback",
    )
    rating: Mapped[FeedbackRating] = mapped_column(
        Enum(
            FeedbackRating,
            name="feedback_rating",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        comment="User rating (bad/ok/great)",
    )
    vacancy_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="URL of the vacancy",
    )
    task_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Runner task ID",
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        nullable=False,
        comment="Feedback time",
    )

    # Relationships
    user: Mapped["User"] = relationship(  # type: ignore[name-defined] # noqa: F821
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_apply_feedbacks_user_id", "user_id"),
        Index("idx_apply_feedbacks_rating", "rating"),
        Index("idx_apply_feedbacks_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"ApplyFeedback(id={self.id}, rating={self.rating.value})"

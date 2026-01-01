"""Transaction DTOs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.db.models.transaction import TransactionType


class TransactionDTO(BaseModel):
    """Transaction data transfer object."""

    id: UUID
    type: TransactionType
    type_display: str
    tokens_delta: int
    tokens_delta_display: str  # "+100" or "-50"
    balance_after: int
    description: str | None
    invoice_id: UUID | None
    created_at: datetime
    created_at_display: str  # "01.02.2024 15:30"

    model_config = {"from_attributes": True}


class TransactionListDTO(BaseModel):
    """Paginated list of transactions."""

    items: list[TransactionDTO]
    total: int
    limit: int
    offset: int
    has_more: bool

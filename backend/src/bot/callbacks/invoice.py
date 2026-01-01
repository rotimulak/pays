"""Callback data for invoice actions."""

from uuid import UUID

from aiogram.filters.callback_data import CallbackData


class InvoiceCallback(CallbackData, prefix="invoice"):
    """Callback data for invoice actions.

    Examples:
        invoice:cancel:550e8400-e29b-41d4-a716-446655440000
        invoice:check:550e8400-e29b-41d4-a716-446655440000
    """

    action: str  # "cancel", "check"
    invoice_id: UUID

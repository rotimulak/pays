"""Callback data classes for inline keyboards."""

from src.bot.callbacks.feedback import FeedbackCallback
from src.bot.callbacks.invoice import InvoiceCallback
from src.bot.callbacks.pagination import PaginationCallback
from src.bot.callbacks.promo import PromoCallback
from src.bot.callbacks.tariff import TariffCallback

__all__ = [
    "FeedbackCallback",
    "InvoiceCallback",
    "PaginationCallback",
    "PromoCallback",
    "TariffCallback",
]

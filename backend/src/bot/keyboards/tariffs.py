"""Tariffs inline keyboard."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.callbacks.tariff import TariffCallback
from src.services.dto.tariff import TariffDTO


def get_tariffs_keyboard(tariffs: list[TariffDTO]) -> InlineKeyboardMarkup:
    """Create inline keyboard with tariff buttons.

    Each button:
    - Text: "Выбрать {name}"
    - Callback: TariffCallback(action="select", tariff_id=id)

    Args:
        tariffs: List of tariffs to display

    Returns:
        InlineKeyboardMarkup with tariff buttons
    """
    builder = InlineKeyboardBuilder()

    for tariff in tariffs:
        builder.button(
            text=f"Выбрать {tariff.name}",
            callback_data=TariffCallback(
                action="select",
                tariff_id=tariff.id,
            ),
        )

    builder.adjust(1)  # One button per row
    return builder.as_markup()


def get_empty_tariffs_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown when no tariffs available."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить", callback_data="refresh_tariffs")
    return builder.as_markup()

"""Promo code keyboards."""

from uuid import UUID

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.callbacks.promo import PromoCallback


def get_promo_input_keyboard(
    tariff_id: UUID,
    show_skip: bool = False,
) -> InlineKeyboardMarkup:
    """Keyboard for promo code input state.

    Args:
        tariff_id: Tariff UUID for callbacks
        show_skip: Show "Skip" button

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    if show_skip:
        builder.button(
            text="⏭ Продолжить без промокода",
            callback_data=PromoCallback(action="skip", tariff_id=tariff_id),
        )

    builder.button(
        text="❌ Отмена",
        callback_data=PromoCallback(action="cancel", tariff_id=tariff_id),
    )

    builder.adjust(1)
    return builder.as_markup()


def get_promo_result_keyboard(
    tariff_id: UUID,
    has_promo: bool = False,
) -> InlineKeyboardMarkup:
    """Keyboard after promo code validation.

    Args:
        tariff_id: Tariff UUID for callbacks
        has_promo: Whether a promo code is applied

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="💳 Перейти к оплате",
        callback_data=PromoCallback(action="confirm", tariff_id=tariff_id),
    )

    if has_promo:
        builder.button(
            text="🔄 Другой промокод",
            callback_data=PromoCallback(action="apply", tariff_id=tariff_id),
        )
        builder.button(
            text="❌ Убрать промокод",
            callback_data=PromoCallback(action="remove", tariff_id=tariff_id),
        )

    builder.button(
        text="💰 Баланс",
        callback_data="balance",
    )

    builder.adjust(1)
    return builder.as_markup()


def get_tariff_with_promo_keyboard(tariff_id: UUID) -> InlineKeyboardMarkup:
    """Keyboard showing promo code option for tariff.

    Args:
        tariff_id: Tariff UUID

    Returns:
        InlineKeyboardMarkup with promo and back buttons
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="🎟 Ввести промокод",
        callback_data=PromoCallback(action="apply", tariff_id=tariff_id),
    )

    builder.button(
        text="⏭ Продолжить без промокода",
        callback_data=PromoCallback(action="skip", tariff_id=tariff_id),
    )

    builder.button(
        text="💰 Баланс",
        callback_data="balance",
    )

    builder.adjust(1)
    return builder.as_markup()

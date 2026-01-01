"""Promo code handlers."""

import logging
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.callbacks.promo import PromoCallback
from src.bot.keyboards.payment import get_payment_keyboard
from src.bot.keyboards.promo import (
    get_promo_input_keyboard,
    get_promo_result_keyboard,
    get_tariff_with_promo_keyboard,
)
from src.bot.keyboards.tariffs import get_tariffs_keyboard
from src.bot.states.promo import PromoStates
from src.core.exceptions import NotFoundError, ValidationError
from src.db.models.user import User
from src.services.dto.invoice import InvoicePreviewDTO
from src.services.invoice_service import InvoiceService
from src.services.payment_service import PaymentService
from src.services.tariff_service import TariffService

logger = logging.getLogger(__name__)

router = Router(name="promo")


def format_promo_result(preview: InvoicePreviewDTO, code: str) -> str:
    """Format promo code result message.

    Args:
        preview: Invoice preview with applied promo
        code: Applied promo code

    Returns:
        Formatted message text
    """
    lines = [f"✅ Промокод <b>{code}</b> применён!\n"]

    if preview.has_discount:
        lines.append(
            f"💰 Цена: <s>{preview.original_amount_display}</s> → "
            f"<b>{preview.final_amount_display}</b>"
        )

        if preview.discount_info:
            lines.append(f"🎁 {preview.discount_info}")

        if preview.bonus_tokens > 0:
            lines.append(f"🎫 +{preview.bonus_tokens} бонусных токенов")

    lines.append(f"\n📦 {preview.tariff_name}")
    lines.append(f"🎫 {preview.tokens} токенов")

    if preview.subscription_days > 0:
        lines.append(f"📅 {preview.subscription_days} дней подписки")

    return "\n".join(lines)


@router.callback_query(PromoCallback.filter(F.action == "apply"))
async def start_promo_input(
    callback: CallbackQuery,
    callback_data: PromoCallback,
    state: FSMContext,
) -> None:
    """Start promo code input flow."""
    message = callback.message
    if message is None or not isinstance(message, Message):
        await callback.answer()
        return

    await state.update_data(tariff_id=str(callback_data.tariff_id))
    await state.set_state(PromoStates.waiting_for_code)

    await message.edit_text(
        "🎟 <b>Введите промокод</b>\n\n"
        "Отправьте промокод сообщением или нажмите «Отмена»",
        reply_markup=get_promo_input_keyboard(callback_data.tariff_id),
    )
    await callback.answer()


@router.message(PromoStates.waiting_for_code)
async def process_promo_code(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Process entered promo code."""
    if message.text is None:
        await message.answer(
            "❌ Пожалуйста, введите промокод текстом",
        )
        return

    code = message.text.strip().upper()
    data = await state.get_data()
    tariff_id_str = data.get("tariff_id")

    if not tariff_id_str:
        await state.clear()
        await message.answer("❌ Ошибка. Попробуйте снова через /buy")
        return

    tariff_id = UUID(tariff_id_str)
    invoice_service = InvoiceService(session)

    try:
        # Validate and preview
        preview = await invoice_service.preview_invoice(
            user_id=user.id,
            tariff_id=tariff_id,
            promo_code=code,
        )

        # Check if promo actually applied
        if not preview.has_discount:
            await message.answer(
                f"❌ Промокод <b>{code}</b> не найден или не применим к этому тарифу.\n\n"
                "Попробуйте другой промокод или продолжите без скидки.",
                reply_markup=get_promo_input_keyboard(tariff_id, show_skip=True),
            )
            return

        # Save promo code in state
        await state.update_data(promo_code=code)
        await state.set_state(PromoStates.confirming_purchase)

        # Show result
        text = format_promo_result(preview, code)
        keyboard = get_promo_result_keyboard(tariff_id, has_promo=True)

        await message.answer(text, reply_markup=keyboard)

        logger.info(
            "Promo code applied: code=%s, user=%d, tariff=%s",
            code,
            user.id,
            tariff_id,
        )

    except ValidationError as e:
        # Invalid promo code
        await message.answer(
            f"❌ {e.message}\n\n"
            "Попробуйте другой промокод или продолжите без скидки.",
            reply_markup=get_promo_input_keyboard(tariff_id, show_skip=True),
        )

    except NotFoundError as e:
        logger.warning("Promo validation error: %s", e.message)
        await state.clear()
        await message.answer(f"❌ {e.message}")


@router.callback_query(PromoCallback.filter(F.action == "cancel"))
async def cancel_promo_input(
    callback: CallbackQuery,
    callback_data: PromoCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Cancel promo code input."""
    message = callback.message
    if message is None or not isinstance(message, Message):
        await callback.answer()
        return

    await state.clear()

    # Show tariffs list
    tariff_service = TariffService(session)
    tariffs = await tariff_service.get_active_tariffs()

    if tariffs:
        text = "Ввод промокода отменён.\n\n"
        text += tariff_service.format_tariffs_list(tariffs)
        await message.edit_text(text, reply_markup=get_tariffs_keyboard(tariffs))
    else:
        await message.edit_text("Ввод промокода отменён.")

    await callback.answer()


@router.callback_query(PromoCallback.filter(F.action == "skip"))
async def skip_promo(
    callback: CallbackQuery,
    callback_data: PromoCallback,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Continue without promo code - go directly to payment."""
    message = callback.message
    if message is None or not isinstance(message, Message):
        await callback.answer()
        return

    await state.clear()

    tariff_id = callback_data.tariff_id
    invoice_service = InvoiceService(session)
    payment_service = PaymentService(session)

    try:
        # Create invoice without promo
        invoice, created = await invoice_service.get_or_create_invoice(
            user_id=user.id,
            tariff_id=tariff_id,
        )

        # Generate payment URL
        payment_url = await payment_service.create_payment_url(invoice.id)

        # Get invoice DTO for display
        invoice_dto = await invoice_service.get_invoice_for_payment(invoice.id)
        if invoice_dto is None:
            await callback.answer("❌ Ошибка создания счёта", show_alert=True)
            return

        # Format message
        text = invoice_service.format_invoice_for_display(invoice_dto)

        await message.edit_text(
            text,
            reply_markup=get_payment_keyboard(
                payment_url=payment_url,
                amount=invoice_dto.amount_display,
                invoice_id=invoice.id,
            ),
        )

        logger.info(
            "Invoice created without promo: inv_id=%d, user=%d",
            invoice.inv_id,
            user.id,
        )

    except (NotFoundError, ValidationError) as e:
        logger.warning("Skip promo error: %s", e.message)
        await callback.answer(f"❌ {e.message}", show_alert=True)

    await callback.answer()


@router.callback_query(PromoCallback.filter(F.action == "remove"))
async def remove_promo(
    callback: CallbackQuery,
    callback_data: PromoCallback,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Remove applied promo code."""
    message = callback.message
    if message is None or not isinstance(message, Message):
        await callback.answer()
        return

    # Clear promo from state
    await state.update_data(promo_code=None)

    tariff_id = callback_data.tariff_id
    invoice_service = InvoiceService(session)

    try:
        # Preview without promo
        preview = await invoice_service.preview_invoice(
            user_id=user.id,
            tariff_id=tariff_id,
            promo_code=None,
        )

        text = (
            "❌ Промокод удалён.\n\n"
            f"📦 {preview.tariff_name}\n"
            f"💰 Цена: <b>{preview.final_amount_display}</b>\n"
            f"🎫 {preview.tokens} токенов"
        )

        if preview.subscription_days > 0:
            text += f"\n📅 {preview.subscription_days} дней подписки"

        await message.edit_text(
            text,
            reply_markup=get_tariff_with_promo_keyboard(tariff_id),
        )

    except NotFoundError as e:
        await callback.answer(f"❌ {e.message}", show_alert=True)

    await callback.answer()


@router.callback_query(PromoCallback.filter(F.action == "confirm"))
async def confirm_promo_purchase(
    callback: CallbackQuery,
    callback_data: PromoCallback,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Confirm purchase with promo code."""
    message = callback.message
    if message is None or not isinstance(message, Message):
        await callback.answer()
        return

    data = await state.get_data()
    promo_code = data.get("promo_code")
    tariff_id = callback_data.tariff_id

    await state.clear()

    invoice_service = InvoiceService(session)
    payment_service = PaymentService(session)

    try:
        # Create invoice with promo code
        invoice = await invoice_service.create_invoice(
            user_id=user.id,
            tariff_id=tariff_id,
            promo_code=promo_code,
        )

        # Generate payment URL
        payment_url = await payment_service.create_payment_url(invoice.id)

        # Get invoice DTO for display
        invoice_dto = await invoice_service.get_invoice_for_payment(invoice.id)
        if invoice_dto is None:
            await callback.answer("❌ Ошибка создания счёта", show_alert=True)
            return

        # Format message
        text = invoice_service.format_invoice_for_display(invoice_dto)

        if promo_code:
            text = f"✅ Промокод <b>{promo_code}</b> применён!\n\n" + text

        await message.edit_text(
            text,
            reply_markup=get_payment_keyboard(
                payment_url=payment_url,
                amount=invoice_dto.amount_display,
                invoice_id=invoice.id,
            ),
        )

        logger.info(
            "Invoice created with promo: inv_id=%d, user=%d, promo=%s",
            invoice.inv_id,
            user.id,
            promo_code,
        )

    except ValidationError as e:
        logger.warning("Promo confirm error: %s", e.message)
        await callback.answer(f"❌ {e.message}", show_alert=True)
    except NotFoundError as e:
        logger.warning("Promo confirm error: %s", e.message)
        await callback.answer(f"❌ {e.message}", show_alert=True)

    await callback.answer()

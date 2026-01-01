"""Buy/payment handler for tariff selection."""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.callbacks.invoice import InvoiceCallback
from src.bot.callbacks.tariff import TariffCallback
from src.bot.keyboards.payment import get_payment_keyboard
from src.bot.keyboards.tariffs import get_tariffs_keyboard
from src.core.config import settings
from src.core.exceptions import NotFoundError, ValidationError
from src.db.models.user import User
from src.services.invoice_service import InvoiceService
from src.services.tariff_service import TariffService

logger = logging.getLogger(__name__)

router = Router(name="buy")


def generate_mock_payment_url(inv_id: int) -> str:
    """Generate mock payment URL for testing.

    In M4+ this will be replaced with real Robokassa URL.
    """
    base_url = settings.webhook_base_url.rstrip("/")
    return f"{base_url}/mock-pay/{inv_id}"


@router.callback_query(TariffCallback.filter(F.action == "select"))
async def process_tariff_selection(
    callback: CallbackQuery,
    callback_data: TariffCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Process tariff selection callback.

    1. Get tariff by ID from callback_data
    2. Create or get existing pending invoice
    3. Generate payment URL (mock for now)
    4. Show invoice details with "Pay" button
    """
    message = callback.message
    if message is None or not isinstance(message, Message):
        await callback.answer()
        return

    tariff_service = TariffService(session)
    invoice_service = InvoiceService(session)

    try:
        # Get tariff details
        tariff = await tariff_service.get_tariff_by_id(callback_data.tariff_id)
        if tariff is None:
            await callback.answer("❌ Тариф не найден", show_alert=True)
            return

        # Create or get existing invoice
        invoice, created = await invoice_service.get_or_create_invoice(
            user_id=user.id,
            tariff_id=callback_data.tariff_id,
        )

        # Generate mock payment URL
        payment_url = generate_mock_payment_url(invoice.inv_id)

        # Update invoice with payment URL if needed
        if invoice.payment_url != payment_url:
            invoice.payment_url = payment_url
            await session.flush()

        # Get invoice DTO for display
        invoice_dto = await invoice_service.get_invoice_for_payment(invoice.id)
        if invoice_dto is None:
            await callback.answer("❌ Ошибка создания счёта", show_alert=True)
            return

        # Format message
        text = invoice_service.format_invoice_for_display(invoice_dto)

        if not created:
            text += "\n\n<i>ℹ️ У вас уже есть неоплаченный счёт на этот тариф</i>"

        await message.edit_text(
            text,
            reply_markup=get_payment_keyboard(
                payment_url=payment_url,
                amount=invoice_dto.amount_display,
                invoice_id=invoice.id,
            ),
        )

        if created:
            logger.info(
                "Invoice created: inv_id=%d, user=%d, tariff=%s",
                invoice.inv_id,
                user.id,
                tariff.slug,
            )

    except (NotFoundError, ValidationError) as e:
        logger.warning("Tariff selection error: %s", e.message)
        await callback.answer(f"❌ {e.message}", show_alert=True)

    await callback.answer()


@router.callback_query(InvoiceCallback.filter(F.action == "cancel"))
async def cancel_invoice_callback(
    callback: CallbackQuery,
    callback_data: InvoiceCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Handle invoice cancellation."""
    message = callback.message
    if message is None or not isinstance(message, Message):
        await callback.answer()
        return

    invoice_service = InvoiceService(session)
    tariff_service = TariffService(session)

    try:
        # Get invoice to verify ownership
        invoice_dto = await invoice_service.get_invoice_for_payment(
            callback_data.invoice_id
        )

        if invoice_dto is None:
            await callback.answer("❌ Счёт не найден", show_alert=True)
            return

        # Cancel invoice
        await invoice_service.cancel_invoice(callback_data.invoice_id)

        # Show tariffs again
        tariffs = await tariff_service.get_active_tariffs()
        text = "✅ Счёт отменён.\n\n"

        if tariffs:
            text += tariff_service.format_tariffs_list(tariffs)
            await message.edit_text(
                text,
                reply_markup=get_tariffs_keyboard(tariffs),
            )
        else:
            await message.edit_text(
                text + "Нет доступных тарифов.",
            )

        logger.info(
            "Invoice cancelled: inv_id=%d, user=%d",
            invoice_dto.inv_id,
            user.id,
        )

    except (NotFoundError, ValidationError) as e:
        logger.warning("Invoice cancel error: %s", e.message)
        await callback.answer(f"❌ {e.message}", show_alert=True)

    await callback.answer()


@router.callback_query(InvoiceCallback.filter(F.action == "check"))
async def check_invoice_status_callback(
    callback: CallbackQuery,
    callback_data: InvoiceCallback,
    user: User,
    session: AsyncSession,
) -> None:
    """Handle invoice status check."""
    invoice_service = InvoiceService(session)

    invoice_dto = await invoice_service.get_invoice_for_payment(
        callback_data.invoice_id
    )

    if invoice_dto is None:
        await callback.answer("❌ Счёт не найден", show_alert=True)
        return

    # Show current status
    await callback.answer(
        f"Статус: {invoice_dto.status_display}",
        show_alert=True,
    )

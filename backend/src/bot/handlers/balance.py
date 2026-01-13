"""Balance handler for M11 simplified UX."""

from datetime import datetime
from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.balance import (
    get_balance_keyboard,
    get_cancel_keyboard,
    get_payment_keyboard,
)
from src.bot.states.payment import PaymentStates
from src.db.models.user import User
from src.db.repositories.tariff_repository import TariffRepository
from src.services.invoice_service import InvoiceService
from src.services.payment_service import PaymentService

router = Router()

# ========== Message Templates ==========

BALANCE_ACTIVE_TEMPLATE = """
📊 <b>Ваш профиль</b>

🆔 ID: <code>{user_id}</code>
👤 Username: {username}

💳 Баланс: <b>{balance}</b> токенов
📅 Подписка активна до: <b>{subscription_end}</b>

━━━━━━━━━━━━━━━━━━━━━
ℹ️ Абонплата: {subscription_fee} токенов/мес.
Токены расходуются на запросы.
Минимальное пополнение: {min_payment}₽
"""

BALANCE_INACTIVE_TEMPLATE = """
📊 <b>Ваш профиль</b>

🆔 ID: <code>{user_id}</code>
👤 Username: {username}

💳 Баланс: <b>{balance}</b> токенов
⚠️ Подписка неактивна

━━━━━━━━━━━━━━━━━━━━━
ℹ️ Для активации пополните минимум {min_payment}₽.
{subscription_fee} токенов — абонплата,
остальное — на баланс.
"""

ENTER_AMOUNT_TEMPLATE = """
✏️ <b>Введите сумму пополнения</b>

Минимальная сумма: {min_payment}₽

Отправьте число (только цифры):
"""

PAYMENT_READY_TEMPLATE = """
💳 <b>Пополнение на {amount}₽</b>

Нажмите кнопку для перехода к оплате:
"""


# ========== Helpers ==========


async def _get_balance_text(user: User, session: AsyncSession) -> tuple[str, Decimal]:
    """Get formatted balance text and min_payment.

    Returns:
        Tuple of (formatted_text, min_payment)
    """
    tariff_repo = TariffRepository(session)
    tariff = await tariff_repo.get_default_tariff()

    if tariff is None:
        # Fallback values if no tariff configured
        min_payment = Decimal("200.00")
        subscription_fee = 100
    else:
        min_payment = tariff.min_payment
        subscription_fee = tariff.subscription_fee

    now = datetime.utcnow()
    is_active = user.subscription_end is not None and user.subscription_end > now
    username_display = f"@{user.username}" if user.username else "не указан"

    if is_active:
        text = BALANCE_ACTIVE_TEMPLATE.format(
            user_id=user.id,
            username=username_display,
            balance=user.token_balance,
            subscription_end=user.subscription_end.strftime("%d.%m.%Y"),
            subscription_fee=subscription_fee,
            min_payment=int(min_payment),
        )
    else:
        text = BALANCE_INACTIVE_TEMPLATE.format(
            user_id=user.id,
            username=username_display,
            balance=user.token_balance,
            subscription_fee=subscription_fee,
            min_payment=int(min_payment),
        )

    return text.strip(), min_payment


# ========== Handlers ==========


@router.message(Command("balance"))
@router.message(F.text == "💰 Баланс")
async def cmd_balance(
    message: Message,
    user: User,
    session: AsyncSession,
) -> None:
    """Show balance screen."""
    text, min_payment = await _get_balance_text(user, session)
    await message.answer(text, reply_markup=get_balance_keyboard(min_payment))


@router.callback_query(F.data == "balance")
async def on_balance_callback(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Show balance screen (callback)."""
    # Clear any FSM state when returning to balance
    await state.clear()

    if callback.message is None:
        await callback.answer()
        return

    try:
        text, min_payment = await _get_balance_text(user, session)
        await callback.message.edit_text(text, reply_markup=get_balance_keyboard(min_payment))
        await callback.answer()
    except Exception:
        # Message not modified (same content) or other error
        # Always answer callback to prevent "loading" state on button
        await callback.answer()


@router.callback_query(F.data.startswith("pay:"))
async def on_pay_callback(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Handle payment button clicks."""
    if callback.message is None:
        await callback.answer()
        return

    # Extract amount from callback data
    _, amount_str = callback.data.split(":", 1)

    if amount_str == "custom":
        # Show custom amount input
        tariff_repo = TariffRepository(session)
        tariff = await tariff_repo.get_default_tariff()
        min_payment = int(tariff.min_payment) if tariff else 200

        await state.set_state(PaymentStates.waiting_for_amount)
        await state.update_data(min_payment=min_payment)

        text = ENTER_AMOUNT_TEMPLATE.format(min_payment=min_payment)
        await callback.message.edit_text(text, reply_markup=get_cancel_keyboard())
        await callback.answer()
        return

    # Quick payment with fixed amount
    amount = int(amount_str)
    await _create_payment(callback, user, session, amount)


async def _create_payment(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    amount: int,
) -> None:
    """Create invoice and show payment link."""
    tariff_repo = TariffRepository(session)
    tariff = await tariff_repo.get_default_tariff()

    if tariff is None:
        await callback.answer("Ошибка: тариф не настроен", show_alert=True)
        return

    # Validate minimum payment
    if amount < int(tariff.min_payment):
        await callback.answer(
            f"Минимальная сумма: {int(tariff.min_payment)}₽",
            show_alert=True,
        )
        return

    # Create invoice
    invoice_service = InvoiceService(session)
    invoice = await invoice_service.create_invoice(
        user_id=user.id,
        tariff_id=tariff.id,
    )

    # Override invoice amount with user's amount
    # Note: In real implementation, you might want a separate method for M11 invoices
    invoice.amount = Decimal(amount)
    invoice.tokens = amount  # 1:1 ratio

    # Get payment URL
    payment_service = PaymentService(session)
    payment_url = await payment_service.create_payment_url(invoice.id)

    text = PAYMENT_READY_TEMPLATE.format(amount=amount)
    await callback.message.edit_text(
        text,
        reply_markup=get_payment_keyboard(amount, payment_url),
    )
    await callback.answer()


@router.message(PaymentStates.waiting_for_amount)
async def on_amount_input(
    message: Message,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Handle custom amount input."""
    data = await state.get_data()
    min_payment = data.get("min_payment", 200)

    # Validate input
    text = message.text.strip() if message.text else ""

    try:
        amount = int(text)
    except ValueError:
        await message.answer(
            f"❌ Введите число (только цифры).\nМинимум: {min_payment}₽"
        )
        return

    if amount < min_payment:
        await message.answer(
            f"❌ Минимальная сумма: {min_payment}₽\nВы ввели: {amount}₽"
        )
        return

    # Clear FSM state
    await state.clear()

    # Get tariff for invoice creation
    tariff_repo = TariffRepository(session)
    tariff = await tariff_repo.get_default_tariff()

    if tariff is None:
        await message.answer("Ошибка: тариф не настроен")
        return

    # Create invoice
    invoice_service = InvoiceService(session)
    invoice = await invoice_service.create_invoice(
        user_id=user.id,
        tariff_id=tariff.id,
    )

    # Override invoice amount
    invoice.amount = Decimal(amount)
    invoice.tokens = amount

    # Get payment URL
    payment_service = PaymentService(session)
    payment_url = await payment_service.create_payment_url(invoice.id)

    text = PAYMENT_READY_TEMPLATE.format(amount=amount)
    await message.answer(
        text,
        reply_markup=get_payment_keyboard(amount, payment_url),
    )

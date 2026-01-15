"""Trial promo code handlers."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.keyboards.balance import get_balance_keyboard, get_trial_promo_keyboard
from src.bot.states.trial import TrialStates
from src.core.exceptions import ValidationError
from src.db.models.user import User
from src.db.repositories.tariff_repository import TariffRepository
from src.services.trial_service import TrialService

logger = logging.getLogger(__name__)

router = Router(name="trial")

ENTER_PROMO_CODE_TEXT = """
🎟 <b>Введите промокод</b>

Отправьте промокод сообщением или нажмите «Отмена»
"""

SUCCESS_TEMPLATE = """
✅ <b>Промокод активирован!</b>

🎁 Получено:
• {tokens} токенов
• Подписка до {subscription_end}

💳 Ваш баланс: {balance} токенов (~{generations} генераций)
"""


@router.callback_query(F.data == "promo_trial")
async def on_promo_trial_button(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Start trial promo code input."""
    if callback.message is None:
        await callback.answer()
        return

    await state.set_state(TrialStates.waiting_for_code)
    await callback.message.edit_text(
        ENTER_PROMO_CODE_TEXT,
        reply_markup=get_trial_promo_keyboard(),
    )
    await callback.answer()


@router.message(TrialStates.waiting_for_code)
async def on_promo_code_input(
    message: Message,
    user: User,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Process trial promo code input."""
    if message.text is None:
        await message.answer("❌ Пожалуйста, введите промокод текстом")
        return

    code = message.text.strip().upper()
    trial_service = TrialService(session)

    try:
        result = await trial_service.activate_trial(user.id, code)

        await state.clear()

        # Show success message
        balance_rounded = round(float(result["new_balance"]), 2)
        generations = int(balance_rounded / 2)
        text = SUCCESS_TEMPLATE.format(
            tokens=result["tokens_credited"],
            subscription_end=result["subscription_end"].strftime("%d.%m.%Y"),
            balance=balance_rounded,
            generations=generations,
        )

        # Get updated keyboard
        tariff_repo = TariffRepository(session)
        tariff = await tariff_repo.get_default_tariff()
        min_payment = tariff.min_payment if tariff else 200

        await message.answer(text, reply_markup=get_balance_keyboard(min_payment))

        logger.info("Trial activated: user=%d, code=%s", user.id, code)

    except ValidationError as e:
        await message.answer(f"❌ {e.message}")
        logger.warning(
            "Trial activation failed: user=%d, code=%s, error=%s",
            user.id,
            code,
            e.message,
        )

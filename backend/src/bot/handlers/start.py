"""Start command handler."""

import os

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.healthcheck import check_runner_health
from src.bot.keyboards.main_menu import get_main_menu, get_main_menu_inline, get_start_menu_inline
from src.bot.states.cv import CVStates
from src.bot.states.skills import SkillsStates
from src.bot.states.apply import ApplyStates
from src.core.config import settings
from src.db.models.user import User
from src.services.cv_service import CV_ANALYSIS_COST
from src.services.skills_service import SKILLS_COST
from src.services.apply_service import APPLY_COST
from src.services.token_service import TokenService

router = Router(name="start")

# Версия билда (устанавливается при деплое)
BUILD_VERSION = os.getenv("BUILD_VERSION", "dev")

# URL для юридических документов
OFERTA_URL = f"{settings.webhook_base_url}/legal/oferta"


@router.message(CommandStart())
async def cmd_start(message: Message, user: User) -> None:
    """Handle /start command."""
    first_name = user.first_name or "друг"

    # Check runner health
    try:
        is_healthy, status_msg = await check_runner_health()
    except Exception:
        is_healthy = False

    if is_healthy:
        text = (
            f"Привет, {first_name}!\n\n"
            "Я помогу пользоваться сервисом и управлять своей подпиской.\n\n"
            "Выбери действие:\n\n"
            f'<a href="{OFERTA_URL}">Публичная оферта</a>\n\n'
            f"<i>v{BUILD_VERSION}</i>"
        )
    else:
        text = (
            f"Привет, {first_name}!\n\n"
            "⚠️ <b>К сожалению, сервис временно недоступен.</b>\n\n"
            "Мы уже работаем над восстановлением. "
            "Пожалуйста, попробуйте позже.\n\n"
            f'<a href="{OFERTA_URL}">Публичная оферта</a>\n\n'
            f"<i>v{BUILD_VERSION}</i>"
        )

    # Send reply keyboard
    await message.answer(
        text,
        reply_markup=get_main_menu() if is_healthy else None,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

    # Send inline buttons for quick actions
    if is_healthy:
        await message.answer(
            "👇 Быстрые действия:",
            reply_markup=get_start_menu_inline(),
        )


@router.callback_query(F.data == "main_menu")
async def on_main_menu(callback: CallbackQuery) -> None:
    """Return to main menu (inline navigation)."""
    if callback.message is None:
        await callback.answer()
        return

    try:
        text = "Главное меню\n\nВыбери действие:"
        await callback.message.edit_text(text, reply_markup=get_main_menu_inline())
        await callback.answer()
    except Exception:
        await callback.answer()


@router.callback_query(F.data == "cmd_cv")
async def on_cmd_cv(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Handle CV button - start CV analysis flow."""
    token_service = TokenService(session)
    can_spend, reason = await token_service.can_spend(user.telegram_id, CV_ANALYSIS_COST)

    if not can_spend:
        await callback.answer(f"❌ {reason}", show_alert=True)
        return

    await state.set_state(CVStates.waiting_for_file)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            f"📄 <b>Анализ CV</b>\n\n"
            f"Загрузите ваше резюме в формате <b>PDF</b> или <b>TXT</b>.\n\n"
            f"⚠️ Максимальный размер файла: <b>1 МБ</b>\n"
            f"💰 Стоимость: <b>{CV_ANALYSIS_COST} токен</b>\n\n"
            f"Отправьте файл прямо в этот чат."
        )


@router.callback_query(F.data == "cmd_skills")
async def on_cmd_skills(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Handle Skills button - start skills analysis flow."""
    token_service = TokenService(session)
    can_spend, reason = await token_service.can_spend(user.telegram_id, SKILLS_COST)

    if not can_spend:
        await callback.answer(f"❌ {reason}", show_alert=True)
        return

    await state.set_state(SkillsStates.waiting_for_urls)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            f"💪 <b>Усилить резюме</b>\n\n"
            f"Отправьте список ссылок на вакансии с hh.ru (до 20 штук).\n\n"
            f"Я проанализирую требования и подскажу, какие ключевые слова "
            f"и навыки добавить в резюме для повышения релевантности.\n\n"
            f"💰 Стоимость: <b>{SKILLS_COST} токен</b>\n\n"
            f"Пример:\nhttps://hh.ru/vacancy/123456789\nhttps://hh.ru/vacancy/987654321"
        )


@router.callback_query(F.data == "cmd_apply")
async def on_cmd_apply(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Handle Apply button - start apply flow."""
    token_service = TokenService(session)
    can_spend, reason = await token_service.can_spend(user.telegram_id, APPLY_COST)

    if not can_spend:
        await callback.answer(f"❌ {reason}", show_alert=True)
        return

    await state.set_state(ApplyStates.waiting_for_url)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            f"💼 <b>Отклик на вакансию</b>\n\n"
            f"Отправьте ссылку на вакансию с hh.ru.\n\n"
            f"⚠️ Требования:\n"
            f"• У вас должно быть загружено резюме (команда /cv)\n"
            f"• Ссылка должна быть с hh.ru\n\n"
            f"💰 Стоимость: <b>{APPLY_COST} токен</b>\n\n"
            f"Пример: https://hh.ru/vacancy/123456789"
        )

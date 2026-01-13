"""Start command handler."""

import asyncio
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
from src.services.skills_service import SKILLS_COST
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

    if not is_healthy:
        text = (
            f"Привет, {first_name}!\n\n"
            "⚠️ <b>К сожалению, сервис временно недоступен.</b>\n\n"
            "Мы уже работаем над восстановлением. "
            "Пожалуйста, попробуйте позже.\n\n"
            f'<a href="{OFERTA_URL}">Публичная оферта</a>\n\n'
            f"<i>v{BUILD_VERSION}</i>"
        )
        await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)
        return

    # Intro message 1 - Overview
    intro_1 = (
        f"🚀 Привет, {first_name}! Мы поможем тебе с поиском работы на hh.ru:\n\n"
        "✅ Проанализируем резюме и дадим рекомендации\n"
        "✅ Подскажем, какие навыки добавить под рынок\n"
        "✅ Сгенерируем персональный отклик на вакансию\n\n"
        "❌ <b>Важно понимать:</b>\n"
        "Мы НЕ предлагаем работу\n"
        "Мы НЕ правим ваше резюме автоматически, мы выдаем рекомендации \n"
        "Мы НЕ откликаемся и не ведем переписку\n\n"
        "Shit in - Shit out: модели покажут хороший результат с реальным резюме, в котором уже проведена ваша подготовительная работа\n\n"
        "💡 <b>Рекомендуемый порядок:</b>\n"
        "Загрузить CV → Усилить компетенциями из целевых вакансий → Писать отклики\n\n"
        f'<a href="{OFERTA_URL}">Публичная оферта</a> · <i>v{BUILD_VERSION}</i>\n'
        f'<i>API: {settings.webhook_base_url} | Runner: {settings.runner_base_url}</i>'
    )

    # Intro message 2 - CV
    intro_2 = (
        "1. Сначала загрузи резюме для анализ\n\n"
        "<b>Вход:</b> файл резюме из Headhunter в PDF или TXT\n\n"
        "<b>Что получишь:</b>\n"
        "• Анализ по критериям HR и ключевикам, чтобы пройти ИИ фильтрацию (ATS-системы)\n"
        "• Рекомендации по улучшению\n"
        "• Формируется файл «Конструктор откликов» — шаблон для будущих писем"
    )

    # Intro message 3 - Skills
    intro_3 = (
        "2. Усиливаем резюме, проанализировав, что требуется в целевых вакансиях\n\n"
        "Выберите вакансии, на которые вы хотели бы претендовать, мы проанализируем требования и сделаем рекомендации, что добавить в резюме\n"
        "<b>Вход:</b> список ссылок на вакансии hh.ru, до 8 штук, и ранее загруженное резюме\n\n"
        "<b>Что получишь:</b>\n"
        "• Анализ требований по всем вакансиям\n"
        "• Топ навыков с частотой упоминания (например: «Excel — 4/8 вакансий»)\n"
        "• Готовые формулировки ctrl+c ctrl+v и места из резюме, в которых они могут быть правдой\n\n"
        f"<i>Runner API: {settings.runner_base_url}</i>"
    )

    # Intro message 4 - Apply
    intro_4 = (
        "3. Создаем текст отклика на вакансию\n\n"
        "Формируем отклик по формуле, чтобы запомнится (эмоциональный хук вначале, наиболее релевантный опыт под вакансию, ответы на вопросы, если есть и тд)\n"
        "<b>Вход:</b> ссылка на 1 вакансию hh.ru и ранее загруженное резюме\n\n"
        "<b>Что получишь:</b>\n"
        "• Персонализированное сопроводительное письмо\n"
        "• Учёт требований вакансии и твоего опыта\n"
        "• Готовый текст отклика"
    )

    # Send all intro messages with delays
    await message.answer(intro_1, parse_mode="HTML", disable_web_page_preview=True)
    await asyncio.sleep(2)
    await message.answer(intro_2, parse_mode="HTML")
    await asyncio.sleep(2)
    await message.answer(intro_3, parse_mode="HTML")
    await asyncio.sleep(2)
    await message.answer(intro_4, parse_mode="HTML")

    # Send reply keyboard + inline buttons
    await message.answer(
        "Выбери действие:",
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
        await callback.message.edit_text(text, reply_markup=get_start_menu_inline())
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
    balance = await token_service.check_balance(user.id)

    if not balance.can_spend:
        await callback.answer(f"❌ {balance.reason}", show_alert=True)
        return

    await state.set_state(CVStates.waiting_for_file)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            f"📄 <b>Анализ CV</b>\n\n"
            f"Загрузите ваше резюме в формате <b>PDF</b> или <b>TXT</b>.\n\n"
            f"⚠️ Максимальный размер файла: <b>1 МБ</b>\n"
            f"💰 Стоимость списывается автоматически после выполнения\n\n"
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
    can_spend, reason = await token_service.can_spend(user.id, SKILLS_COST)

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
            f"💰 Стоимость: <b>{SKILLS_COST} токен</b>"
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
    balance = await token_service.check_balance(user.id)

    if not balance.can_spend:
        await callback.answer(f"❌ {balance.reason}", show_alert=True)
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
            f"💰 Стоимость списывается автоматически после выполнения"
        )

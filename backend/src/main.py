"""Bot entry point."""

import asyncio

from aiogram import Bot
from aiogram.types import BotCommand

from src.bot import create_bot, create_dispatcher
from src.bot.handlers import apply, balance, buy, constructor, cv, healthcheck, help, skills, start, trial
from src.bot.middlewares import AuthMiddleware, CommandResetMiddleware, DbSessionMiddleware
from src.core.config import settings
from src.core.logging import get_logger, setup_logging

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def set_commands(bot: Bot) -> None:
    """Set bot commands for menu."""
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="cv", description="Анализ CV"),
        BotCommand(command="apply", description="Отклик на вакансию"),
        BotCommand(command="skills", description="Усилить резюме"),
        BotCommand(command="constructor", description="Обновить конструктор"),
        BotCommand(command="balance", description="Баланс"),
    ]
    await bot.set_my_commands(commands)


async def set_bot_description(bot: Bot) -> None:
    """Set bot description shown before /start."""
    # Description shown in empty chat (up to 512 chars)
    description = (
        "AI-помощник для поиска работы на hh.ru\n\n"
        "Что умеет бот:\n"
        "• Анализ резюме с рекомендациями по улучшению\n"
        "• Подбор навыков под целевые вакансии\n"
        "• Генерация персональных откликов\n\n"
        "Нажмите /start чтобы начать"
    )
    await bot.set_my_description(description=description, language_code="ru")

    # Short description for profile/sharing (up to 120 chars)
    short_description = "AI-помощник для поиска работы: анализ CV, усиление резюме, генерация откликов на hh.ru"
    await bot.set_my_short_description(short_description=short_description, language_code="ru")


async def on_startup(bot: Bot) -> None:
    """Startup hook."""
    try:
        await set_commands(bot)
        await set_bot_description(bot)
    except Exception as e:
        logger.warning(f"Failed to set bot config: {e}")
    logger.info("Bot started")


async def on_shutdown(bot: Bot) -> None:
    """Shutdown hook."""
    logger.info("Bot stopped")


async def main() -> None:
    """Entry point."""
    bot = create_bot(settings.telegram_bot_token)
    dp = create_dispatcher()

    # Register middlewares (order matters: db_session → auth → command_reset)
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.message.middleware(CommandResetMiddleware())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(buy.router)
    dp.include_router(balance.router)
    dp.include_router(trial.router)
    dp.include_router(help.router)
    dp.include_router(healthcheck.router)
    dp.include_router(cv.router)
    dp.include_router(apply.router)
    dp.include_router(skills.router)
    dp.include_router(constructor.router)

    # Register hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start polling
    logger.info("Starting bot in polling mode...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

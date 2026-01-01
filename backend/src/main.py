"""Bot entry point."""

import asyncio
import logging
import sys

from aiogram import Bot
from aiogram.types import BotCommand

from src.bot import create_bot, create_dispatcher
from src.bot.handlers import balance, buy, help, history, profile, promo, start, tariffs
from src.bot.middlewares import AuthMiddleware, DbSessionMiddleware
from src.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def set_commands(bot: Bot) -> None:
    """Set bot commands for menu."""
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="profile", description="Мой профиль"),
        BotCommand(command="tariffs", description="Тарифы"),
        BotCommand(command="balance", description="Баланс"),
        BotCommand(command="history", description="История"),
        BotCommand(command="promo", description="Ввести промокод"),
        BotCommand(command="help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)


async def on_startup(bot: Bot) -> None:
    """Startup hook."""
    await set_commands(bot)
    logger.info("Bot started")


async def on_shutdown(_bot: Bot) -> None:
    """Shutdown hook."""
    logger.info("Bot stopped")


async def main() -> None:
    """Entry point."""
    bot = create_bot(settings.telegram_bot_token)
    dp = create_dispatcher()

    # Register middlewares (order matters: db_session before auth)
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Register routers
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(tariffs.router)
    dp.include_router(buy.router)
    dp.include_router(balance.router)
    dp.include_router(history.router)
    dp.include_router(promo.router)
    dp.include_router(help.router)

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

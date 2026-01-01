"""Telegram bot initialization module."""

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.core.config import settings

# Global bot instance for use in webhooks
_bot_instance: Bot | None = None


def create_bot(token: str) -> Bot:
    """Create Bot instance with default properties."""
    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Create Dispatcher instance."""
    return Dispatcher()


def get_bot() -> Bot:
    """Get or create global Bot instance.

    Used for sending notifications from webhook handlers.
    """
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = create_bot(settings.telegram_bot_token)
    return _bot_instance


def set_bot(bot: Bot) -> None:
    """Set global Bot instance.

    Call this during bot startup to share the same instance.
    """
    global _bot_instance
    _bot_instance = bot


__all__ = ["create_bot", "create_dispatcher", "get_bot", "set_bot"]

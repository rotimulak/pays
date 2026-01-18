"""Robotest configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """E2E test settings."""

    # Telegram API (from my.telegram.org)
    telegram_api_id: int
    telegram_api_hash: str

    # Robotest account
    robotest_phone: str
    robotest_session: str = "robotest"

    # Target bot
    bot_username: str = "smartheadhunterbot"

    # Timeouts (seconds)
    default_timeout: float = 15.0
    long_timeout: float = 120.0
    message_delay: float = 0.5  # Polling interval

    class Config:
        env_file = ".env"
        env_prefix = ""


settings = Settings()

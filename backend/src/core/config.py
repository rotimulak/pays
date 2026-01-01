from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: PostgresDsn = Field(
        ...,
        description="PostgreSQL connection string",
    )

    # Telegram
    telegram_bot_token: str = Field(
        ...,
        min_length=1,
        description="Telegram Bot API token",
    )

    # Robokassa
    robokassa_merchant_login: str = Field(
        ...,
        min_length=1,
        description="Robokassa merchant login",
    )
    robokassa_password_1: str = Field(
        ...,
        min_length=1,
        description="Robokassa password for payment URL generation",
    )
    robokassa_password_2: str = Field(
        ...,
        min_length=1,
        description="Robokassa password for webhook validation",
    )
    robokassa_is_test: bool = Field(
        default=True,
        description="Use Robokassa test mode",
    )

    # Webhooks
    webhook_base_url: str = Field(
        ...,
        min_length=1,
        description="Base URL for payment callbacks",
    )

    # Support
    support_username: str = Field(
        default="support",
        description="Telegram support username (without @)",
    )


settings = Settings()

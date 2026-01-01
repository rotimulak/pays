from typing import Literal

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

    # Payment provider selection
    payment_provider: Literal["mock", "robokassa"] = Field(
        default="mock",
        description="Payment provider to use",
    )

    # Robokassa settings
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

    # Mock provider settings (same structure as Robokassa for compatibility)
    mock_merchant_login: str = Field(
        default="test_merchant",
        description="Mock merchant login",
    )
    mock_password_1: str = Field(
        default="test_password_1",
        description="Mock password for payment URL generation",
    )
    mock_password_2: str = Field(
        default="test_password_2",
        description="Mock password for webhook validation",
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

    # Invoice settings
    invoice_ttl_hours: int = Field(
        default=24,
        description="Hours until pending invoice expires",
    )


settings = Settings()

"""Pytest fixtures for E2E scenarios."""

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from telethon import TelegramClient

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.client import BotTester
from src.config import settings


@pytest_asyncio.fixture(scope="session")
async def telegram_client():
    """Create and connect Telegram client."""
    client = TelegramClient(
        settings.robotest_session,
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )

    await client.connect()

    if not await client.is_user_authorized():
        raise RuntimeError("Robotest not authorized. Run: python -m src.auth")

    yield client

    await client.disconnect()


@pytest_asyncio.fixture
async def bot(telegram_client) -> BotTester:
    """Create BotTester instance."""
    tester = BotTester(telegram_client)
    yield tester


@pytest.fixture
def timeout() -> float:
    """Default timeout."""
    return settings.default_timeout


@pytest.fixture
def long_timeout() -> float:
    """Long timeout for Runner operations."""
    return settings.long_timeout

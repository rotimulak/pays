"""
Scenario: /start command
Phase: 1 (MVP)

Tests the basic bot startup flow.
"""

import pytest

pytestmark = [pytest.mark.asyncio]


class TestStartCommand:
    """Test /start command scenarios."""

    async def test_start_responds(self, bot, timeout):
        """
        Scenario: User sends /start
        Expected: Bot responds with any message

        AR/ER: Bot должен ответить в течение timeout секунд
        """
        # Arrange & Act
        await bot.send("/start")

        # Assert
        responses = await bot.wait_responses(timeout=timeout)

        assert len(responses) > 0, "Bot did not respond to /start"

    async def test_start_welcome_message(self, bot, timeout):
        """
        Scenario: User sends /start
        Expected: Bot sends welcome message mentioning the service

        AR/ER: Ответ содержит упоминание сервиса
        """
        # Arrange & Act
        await bot.send("/start")

        # Assert - проверяем приветствие
        await bot.expect_text(
            pattern=r"(hhhelper|HH.?Helper|сервис|Привет|Smart)",
            timeout=timeout + 10,  # /start sends multiple messages
        )

    async def test_start_shows_cv_feature(self, bot, timeout):
        """
        Scenario: User sends /start
        Expected: Bot mentions CV analysis feature

        AR/ER: В сообщениях упоминается анализ CV/резюме
        """
        # Arrange & Act
        await bot.send("/start")

        # Assert
        await bot.expect_text(
            pattern=r"(анализ.{0,20}(CV|резюме)|CV|резюме)",
            timeout=timeout + 10,
        )

    async def test_start_has_action_buttons(self, bot, timeout):
        """
        Scenario: User sends /start
        Expected: Bot shows inline buttons for actions

        AR/ER: Присутствует кнопка "Анализ CV" или аналогичная
        """
        # Arrange & Act
        await bot.send("/start")

        # Assert - ищем кнопку с CV
        await bot.expect_buttons(
            buttons=["📄 Анализ CV"],
            timeout=timeout + 10,
        )

"""BotTester — Telegram bot testing client."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass

from telethon import TelegramClient
from telethon.tl.types import Message

from .config import settings


@dataclass
class TestResult:
    """Result of expectation check."""

    success: bool
    message: Message | None
    actual: str
    expected: str


class AssertionFailed(AssertionError):
    """E2E assertion failed with AR/ER details."""

    def __init__(self, expected: str, actual: str):
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"\n{'='*50}\n"
            f"EXPECTED (ER):\n{expected}\n"
            f"{'-'*50}\n"
            f"ACTUAL (AR):\n{actual}\n"
            f"{'='*50}"
        )


class BotTester:
    """Client for testing Telegram bot as real user."""

    def __init__(
        self,
        client: TelegramClient,
        bot_username: str | None = None,
    ):
        self.client = client
        self.bot_username = bot_username or settings.bot_username
        self._last_message_id: int = 0

    async def send(self, text: str) -> Message:
        """Send message to bot."""
        msg = await self.client.send_message(self.bot_username, text)
        self._last_message_id = msg.id
        return msg

    async def send_file(self, path: str) -> Message:
        """Send file to bot."""
        msg = await self.client.send_file(self.bot_username, path)
        self._last_message_id = msg.id
        return msg

    async def wait_responses(
        self,
        timeout: float | None = None,
        min_count: int = 1,
    ) -> list[Message]:
        """
        Wait for bot response(s).

        Args:
            timeout: Max wait time (default from settings)
            min_count: Minimum messages to wait for

        Returns:
            List of bot messages (oldest first)
        """
        timeout = timeout or settings.default_timeout
        deadline = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < deadline:
            messages = await self.client.get_messages(
                self.bot_username,
                limit=20,
                min_id=self._last_message_id,
            )

            # Filter only incoming (from bot)
            bot_messages = [
                m for m in messages if not m.out and m.id > self._last_message_id
            ]

            if len(bot_messages) >= min_count:
                # Sort by id (oldest first)
                bot_messages.sort(key=lambda m: m.id)
                self._last_message_id = bot_messages[-1].id
                return bot_messages

            await asyncio.sleep(settings.message_delay)

        return []

    async def expect_text(
        self,
        pattern: str,
        timeout: float | None = None,
    ) -> Message:
        """
        Assert bot response matches pattern.

        Args:
            pattern: Regex pattern to match
            timeout: Max wait time

        Returns:
            Matching message

        Raises:
            AssertionFailed: If pattern not found
        """
        responses = await self.wait_responses(timeout=timeout)

        if not responses:
            raise AssertionFailed(
                expected=f"Pattern: {pattern!r}",
                actual="<no response>",
            )

        # Check all responses
        for resp in responses:
            text = resp.text or ""
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                return resp

        # Not found
        actual = "\n---\n".join(r.text or "<empty>" for r in responses)
        raise AssertionFailed(
            expected=f"Pattern: {pattern!r}",
            actual=actual,
        )

    async def expect_buttons(
        self,
        buttons: list[str],
        timeout: float | None = None,
    ) -> Message:
        """
        Assert bot response has specific buttons.

        Args:
            buttons: List of button texts to find
            timeout: Max wait time

        Returns:
            Message with buttons

        Raises:
            AssertionFailed: If buttons not found
        """
        responses = await self.wait_responses(timeout=timeout)

        if not responses:
            raise AssertionFailed(
                expected=f"Buttons: {buttons}",
                actual="<no response>",
            )

        for resp in responses:
            if not resp.reply_markup:
                continue

            actual_buttons = self._extract_buttons(resp)
            missing = set(buttons) - set(actual_buttons)

            if not missing:
                return resp

        # Collect all found buttons
        all_buttons = []
        for resp in responses:
            if resp.reply_markup:
                all_buttons.extend(self._extract_buttons(resp))

        raise AssertionFailed(
            expected=f"Buttons: {buttons}",
            actual=f"Found buttons: {all_buttons}",
        )

    def _extract_buttons(self, message: Message) -> list[str]:
        """Extract button texts from message."""
        buttons = []
        if not message.reply_markup:
            return buttons

        for row in message.reply_markup.rows:
            for btn in row.buttons:
                if hasattr(btn, "text"):
                    buttons.append(btn.text)

        return buttons

    async def click_button(self, text: str) -> Message:
        """
        Click inline button by text.

        Args:
            text: Button text to click

        Returns:
            Response message after click
        """
        # Get last message with buttons
        messages = await self.client.get_messages(
            self.bot_username,
            limit=5,
        )

        for msg in messages:
            if not msg.reply_markup:
                continue

            for row in msg.reply_markup.rows:
                for btn in row.buttons:
                    if hasattr(btn, "text") and btn.text == text:
                        await msg.click(text=text)
                        self._last_message_id = msg.id
                        # Wait for response
                        responses = await self.wait_responses()
                        return responses[0] if responses else msg

        raise AssertionFailed(
            expected=f"Button: {text!r}",
            actual="Button not found",
        )

    async def reset(self) -> None:
        """Reset conversation state (send /start)."""
        await self.send("/start")
        await self.wait_responses(timeout=5.0)

"""Healthcheck command handler for external runner service."""

import aiohttp
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="healthcheck")

RUNNER_HEALTH_URL = "http://155.212.245.141:8000/health"
RUNNER_API_KEY = "runner-health-secret-key-2024"


async def check_runner_health() -> tuple[bool, str]:
    """Check external runner service health.

    Returns:
        Tuple of (is_healthy, status_message)
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                RUNNER_HEALTH_URL,
                headers={"X-API-Key": RUNNER_API_KEY},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get("status", "unknown")
                    if status == "healthy":
                        return True, "healthy"
                    return False, f"status: {status}"
                return False, f"HTTP {response.status}"
    except aiohttp.ClientError as e:
        return False, f"{type(e).__name__}"
    except TimeoutError:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


@router.message(Command("healthcheck"))
async def cmd_healthcheck(message: Message) -> None:
    """Check external runner service health."""
    await message.answer("🔄 Проверяю статус runner-сервиса...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                RUNNER_HEALTH_URL,
                headers={"X-API-Key": RUNNER_API_KEY},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get("status", "unknown")

                    text = f"✅ <b>Runner сервис работает</b>\n\nСтатус: {status}"

                    # Add components info if available
                    components = data.get("components", {})
                    if components:
                        text += "\n\n<b>Компоненты:</b>"
                        for name, info in components.items():
                            comp_status = info.get("status", "unknown") if isinstance(info, dict) else info
                            emoji = "✅" if comp_status == "healthy" else "❌"
                            text += f"\n{emoji} {name}: {comp_status}"

                    # Add queue info if available
                    queue = data.get("queue", {})
                    if queue:
                        text += "\n\n<b>Очередь:</b>"
                        for key, value in queue.items():
                            text += f"\n• {key}: {value}"

                    await message.answer(text)
                else:
                    await message.answer(
                        f"❌ <b>Runner сервис недоступен</b>\n\nHTTP статус: {response.status}"
                    )
    except aiohttp.ClientError as e:
        await message.answer(f"❌ <b>Ошибка подключения</b>\n\n{type(e).__name__}: {e}")
    except TimeoutError:
        await message.answer("❌ <b>Таймаут</b>\n\nСервер не ответил за 10 секунд")

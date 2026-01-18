"""First-time authorization script."""

import asyncio

from telethon import TelegramClient

from .config import settings


async def authorize() -> None:
    """Interactive authorization for robotest account."""
    print("=" * 50)
    print("Robotest Authorization")
    print("=" * 50)
    print(f"\nPhone: {settings.robotest_phone}")
    print(f"Session file: {settings.robotest_session}.session")
    print()

    client = TelegramClient(
        settings.robotest_session,
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )

    await client.start(phone=settings.robotest_phone)

    me = await client.get_me()
    print(f"\n✅ Authorized as: {me.first_name} (@{me.username})")
    print(f"Session saved: {settings.robotest_session}.session")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(authorize())

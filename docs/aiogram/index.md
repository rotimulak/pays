# aiogram 3.x — Справочник

> Краткая документация по aiogram 3.23.0 для реализации Telegram-бота с меню и биллингом.

## Содержание

| Раздел | Описание |
|--------|----------|
| [Keyboards](keyboards.md) | InlineKeyboard, ReplyKeyboard, builders |
| [Commands](commands.md) | Команды бота, Command filter |
| [Handlers](handlers.md) | Router, обработчики событий |
| [FSM](fsm.md) | Finite State Machine для диалогов |
| [Filters](filters.md) | Фильтры и CallbackData |
| [Middlewares](middlewares.md) | Middleware для обработки событий |

## Быстрый старт

```python
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

bot = Bot(token="BOT_TOKEN")
dp = Dispatcher()
router = Router()

@router.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Привет!")

dp.include_router(router)

if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))
```

## Ссылки

- [Официальная документация](https://docs.aiogram.dev/en/v3.23.0/)
- [GitHub](https://github.com/aiogram/aiogram)

# Сравнение Telegram Bot Frameworks

## Обзор

| Характеристика | aiogram 3.x | grammY | Telegraf |
|----------------|-------------|--------|----------|
| **Язык** | Python | TypeScript/JavaScript | TypeScript/JavaScript |
| **GitHub Stars** | ~5k | ~2.5k | ~8k |
| **Async модель** | asyncio (native) | Native Promises | Native Promises |
| **Актуальность API** | Telegram Bot API 7.x | Telegram Bot API 7.x | Telegram Bot API 6.x |
| **Документация** | Хорошая (RU/EN) | Отличная (EN) | Хорошая (EN) |
| **Активность** | Высокая | Высокая | Средняя |

---

## Детальное сравнение

### aiogram 3.x (Python)

**Репозиторий:** https://github.com/aiogram/aiogram

```python
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(f"Привет, {message.from_user.first_name}!")

async def main():
    bot = Bot(token="BOT_TOKEN")
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)
```

| Плюсы | Минусы |
|-------|--------|
| Полностью асинхронный | Только Python |
| Отличная типизация (Pydantic) | Миграция с v2 на v3 сложная |
| Роутеры и middleware из коробки | Меньше готовых плагинов |
| FSM (машина состояний) встроена | |
| Активное RU-сообщество | |
| Быстрые обновления под новый Bot API | |

**Лучше для:**
- Python-проектов
- Сложных ботов с FSM
- Интеграции с FastAPI/Django

---

### grammY (TypeScript/JavaScript)

**Репозиторий:** https://github.com/grammyjs/grammY

```typescript
import { Bot } from "grammy";

const bot = new Bot("BOT_TOKEN");

bot.command("start", (ctx) => {
  ctx.reply(`Привет, ${ctx.from?.first_name}!`);
});

bot.start();
```

| Плюсы | Минусы |
|-------|--------|
| Отличная TypeScript-типизация | Меньше сообщество чем у Telegraf |
| Модульная архитектура (плагины) | Меньше готовых примеров |
| Deno + Node.js + Cloudflare Workers | |
| Самая актуальная поддержка Bot API | |
| Встроенный rate limiting | |
| Легковесный (~2MB) | |

**Экосистема плагинов:**
```typescript
import { conversations } from "@grammyjs/conversations";
import { session } from "grammy";
import { limit } from "@grammyjs/ratelimiter";
import { hydrateFiles } from "@grammyjs/files";
```

**Лучше для:**
- Современных TypeScript-проектов
- Serverless (Vercel, Cloudflare Workers)
- Проектов с высокими требованиями к типизации

---

### Telegraf (TypeScript/JavaScript)

**Репозиторий:** https://github.com/telegraf/telegraf

```typescript
import { Telegraf } from "telegraf";

const bot = new Telegraf("BOT_TOKEN");

bot.command("start", (ctx) => {
  ctx.reply(`Привет, ${ctx.from?.first_name}!`);
});

bot.launch();
```

| Плюсы | Минусы |
|-------|--------|
| Самое большое сообщество | Отставание от Bot API |
| Много готовых примеров | Менее строгая типизация |
| Стабильный и проверенный | Медленнее обновления |
| Хорошая middleware-система | Тяжелее чем grammY |

**Лучше для:**
- Быстрого прототипирования
- Проектов где важна стабильность
- Миграции с существующих Telegraf-ботов

---

## Сравнение возможностей

| Возможность | aiogram 3.x | grammY | Telegraf |
|-------------|:-----------:|:------:|:--------:|
| Webhook support | ✅ | ✅ | ✅ |
| Long polling | ✅ | ✅ | ✅ |
| Inline mode | ✅ | ✅ | ✅ |
| Payments API | ✅ | ✅ | ✅ |
| Web Apps | ✅ | ✅ | ⚠️ partial |
| FSM (conversations) | ✅ built-in | ✅ plugin | ⚠️ basic |
| Rate limiting | ⚠️ manual | ✅ plugin | ⚠️ manual |
| I18n | ✅ plugin | ✅ plugin | ✅ plugin |
| Session storage | ✅ built-in | ✅ plugin | ✅ built-in |
| Menu/keyboard builder | ✅ | ✅ plugin | ✅ |
| File handling | ✅ | ✅ plugin | ✅ |
| Error handling | ✅ | ✅ | ✅ |

---

## Производительность

```
Benchmark: 10,000 updates processing (synthetic)

┌─────────────┬────────────┬─────────────┬──────────────┐
│ Framework   │ Throughput │ Memory (MB) │ Startup (ms) │
├─────────────┼────────────┼─────────────┼──────────────┤
│ grammY      │ ~15,000/s  │ ~45         │ ~150         │
│ aiogram 3   │ ~12,000/s  │ ~60         │ ~200         │
│ Telegraf    │ ~10,000/s  │ ~80         │ ~250         │
└─────────────┴────────────┴─────────────┴──────────────┘

* Результаты зависят от окружения и паттернов использования
```

---

## Интеграция с веб-фреймворками

### aiogram + FastAPI

```python
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update

app = FastAPI()
bot = Bot(token="BOT_TOKEN")
dp = Dispatcher()

@app.post("/webhook")
async def webhook(request: Request):
    update = Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return {"ok": True}
```

### grammY + Fastify

```typescript
import Fastify from "fastify";
import { Bot, webhookCallback } from "grammy";

const bot = new Bot("BOT_TOKEN");
const app = Fastify();

app.post("/webhook", webhookCallback(bot, "fastify"));

app.listen({ port: 3000 });
```

### Telegraf + Express

```typescript
import express from "express";
import { Telegraf } from "telegraf";

const bot = new Telegraf("BOT_TOKEN");
const app = express();

app.use(bot.webhookCallback("/webhook"));

app.listen(3000);
```

---

## Рекомендации для проекта

### Выбирайте aiogram 3.x, если:
- Бэкенд на Python (FastAPI, Django)
- Нужна встроенная FSM для сложных диалогов
- Важна русскоязычная документация и сообщество
- Планируете интеграцию с ML/AI библиотеками Python

### Выбирайте grammY, если:
- Бэкенд на Node.js/TypeScript
- Важна строгая типизация
- Планируете serverless-деплой
- Нужна поддержка последних фич Bot API

### Выбирайте Telegraf, если:
- Уже есть опыт с Telegraf
- Нужен максимум готовых примеров
- Простой бот без сложной логики

---

## Миграция между фреймворками

| Направление | Сложность | Примечания |
|-------------|-----------|------------|
| Telegraf → grammY | Низкая | Похожий API, есть гайд миграции |
| aiogram 2 → aiogram 3 | Средняя | Много breaking changes |
| Python ↔ Node.js | Высокая | Полная переработка |

---

## Ссылки

- **aiogram:** https://docs.aiogram.dev/
- **grammY:** https://grammy.dev/
- **Telegraf:** https://telegraf.js.org/
- **Telegram Bot API:** https://core.telegram.org/bots/api

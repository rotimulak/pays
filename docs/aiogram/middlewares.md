# Middlewares — Промежуточные обработчики

## Обзор

Middleware — компоненты для обработки событий до/после handlers:
- Логирование
- Авторизация
- Инъекция зависимостей (БД, сервисы)
- Rate limiting
- Обработка ошибок

## Два типа Middleware

| Тип | Когда вызывается |
|-----|------------------|
| **Outer** | До фильтров, для всех событий |
| **Inner** | После фильтров, перед handler |

```
Event → Outer Middleware → Filters → Inner Middleware → Handler
```

## Базовая структура

```python
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

class MyMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler,
        event: TelegramObject,
        data: dict,
    ):
        # До handler
        print("Before handler")

        # Вызов следующего middleware/handler
        result = await handler(event, data)

        # После handler
        print("After handler")

        return result
```

> **Важно:** Всегда вызывайте `await handler(event, data)`, иначе событие не обработается.

## Регистрация

```python
from aiogram import Dispatcher, Router

dp = Dispatcher()
router = Router()

# Outer — для всех событий
dp.message.outer_middleware(MyMiddleware())

# Inner — после фильтров
router.message.middleware(MyMiddleware())

# Для callback_query
router.callback_query.middleware(MyMiddleware())
```

## Инъекция зависимостей

```python
from aiogram import BaseMiddleware
from aiogram.types import Message

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __call__(self, handler, event: Message, data: dict):
        async with self.session_factory() as session:
            data["session"] = session  # Добавляем в data
            return await handler(event, data)

# Регистрация
dp.message.middleware(DatabaseMiddleware(async_session))

# Использование в handler
@router.message(Command("balance"))
async def cmd_balance(message: Message, session: AsyncSession):
    # session доступен из middleware
    user = await session.get(User, message.from_user.id)
```

## Middleware для пользователей

```python
from aiogram import BaseMiddleware
from aiogram.types import Message

class UserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict):
        user_id = event.from_user.id

        # Получаем или создаём пользователя
        # user = await get_or_create_user(user_id)
        user = {"id": user_id, "balance": 100, "subscription": "premium"}

        data["user"] = user
        return await handler(event, data)

# Handler
@router.message(Command("me"))
async def cmd_me(message: Message, user: dict):
    await message.answer(f"Баланс: {user['balance']}")
```

## Rate Limiting Middleware

```python
from aiogram import BaseMiddleware
from aiogram.types import Message
from datetime import datetime
from collections import defaultdict

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 5, period: int = 60):
        self.limit = limit
        self.period = period
        self.users = defaultdict(list)

    async def __call__(self, handler, event: Message, data: dict):
        user_id = event.from_user.id
        now = datetime.now().timestamp()

        # Очищаем старые запросы
        self.users[user_id] = [
            t for t in self.users[user_id]
            if now - t < self.period
        ]

        if len(self.users[user_id]) >= self.limit:
            await event.answer("Слишком много запросов. Подождите.")
            return  # Не вызываем handler

        self.users[user_id].append(now)
        return await handler(event, data)
```

## Logging Middleware

```python
import logging
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = getattr(event, "from_user", None)
        user_id = user.id if user else "unknown"

        logger.info(f"Event from user {user_id}: {event.__class__.__name__}")

        try:
            result = await handler(event, data)
            logger.info(f"Handled successfully for {user_id}")
            return result
        except Exception as e:
            logger.error(f"Error for {user_id}: {e}")
            raise
```

## Функциональный middleware

```python
from aiogram import Dispatcher

dp = Dispatcher()

@dp.message.outer_middleware()
async def track_middleware(handler, event, data):
    # Простой middleware как функция
    print(f"Message from {event.from_user.id}")
    return await handler(event, data)
```

## Пример: Billing Middleware

```python
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

class BillingMiddleware(BaseMiddleware):
    def __init__(self, billing_service):
        self.billing_service = billing_service

    async def __call__(self, handler, event: Message | CallbackQuery, data: dict):
        user_id = event.from_user.id

        # Загружаем данные биллинга
        billing_data = await self.billing_service.get_user_billing(user_id)

        data["billing"] = billing_data
        data["billing_service"] = self.billing_service

        return await handler(event, data)

# Регистрация
# router.message.middleware(BillingMiddleware(billing_service))
# router.callback_query.middleware(BillingMiddleware(billing_service))

# Handler
@router.message(Command("balance"))
async def cmd_balance(message: Message, billing: dict):
    await message.answer(
        f"Баланс: {billing['tokens']} токенов\n"
        f"Подписка: {billing['subscription_status']}"
    )

@router.callback_query(F.data == "billing:topup")
async def cb_topup(callback: CallbackQuery, billing_service):
    url = await billing_service.create_payment(callback.from_user.id, 100)
    await callback.message.edit_text(f"Ссылка на оплату: {url}")
```

## Порядок middleware

```python
dp = Dispatcher()
router = Router()

# Порядок выполнения:
# 1. dp outer middlewares
# 2. router outer middlewares
# 3. filters
# 4. dp inner middlewares (update level)
# 5. router inner middlewares
# 6. handler

dp.message.outer_middleware(LoggingMiddleware())      # 1
router.message.outer_middleware(RateLimitMiddleware()) # 2
router.message.middleware(DatabaseMiddleware())        # 5
router.message.middleware(UserMiddleware())            # 5
router.message.middleware(BillingMiddleware())         # 5
```

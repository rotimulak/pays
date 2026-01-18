# Спецификация: Admin Notifications

> Версия: 1.0
> Статус: Draft
> Дата: 2026-01-17

---

## 1. Обзор

Система уведомлений администратора о ключевых событиях в боте. Уведомления отправляются в Telegram-чат админа в реальном времени.

### Ключевые требования

- Отдельный сервис `AdminNotificationService`
- Настраиваемый chat_id админа через переменные окружения
- Неблокирующая отправка (fire-and-forget)
- Логирование ошибок отправки без влияния на основной flow

---

## 2. События для уведомлений

| Событие | Триггер | Информация в сообщении |
|---------|---------|------------------------|
| Новый пользователь | `/start` от нового пользователя | Username, ID, дата |
| Анализ CV | Завершение команды `/cv` | Username, ID |
| Генерация отклика | Завершение `/apply` | Username, ID, вакансия |
| Оплата | Успешный webhook платежа | Username, ID, сумма, токены |
| Промокод | Активация промокода | Username, ID, код, бонус |

---

## 3. Архитектура

### 3.1 Структура файлов

```
backend/src/
├── services/
│   └── admin_notification_service.py    # Сервис уведомлений админа
└── core/
    └── config.py                        # + ADMIN_CHAT_ID
```

### 3.2 Диаграмма

```
┌─────────────────────────────────────────────────────────────┐
│                     Bot Handlers                            │
│  (start.py, cv.py, apply.py, payments, promo)              │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ события
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              AdminNotificationService                       │
│  - notify_new_user()                                        │
│  - notify_cv_analyzed()                                     │
│  - notify_apply_generated()                                 │
│  - notify_payment_received()                                │
│  - notify_promo_activated()                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Telegram Bot API                          │
│              → Admin Chat (ADMIN_CHAT_ID)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Конфигурация

### 4.1 Переменные окружения

```env
# Admin notifications
ADMIN_CHAT_ID=123456789
ADMIN_NOTIFICATIONS_ENABLED=true
```

### 4.2 config.py дополнение

```python
class Settings(BaseSettings):
    # ... existing fields ...

    # Admin notifications
    admin_chat_id: int | None = Field(
        default=None,
        description="Telegram chat ID for admin notifications",
    )
    admin_notifications_enabled: bool = Field(
        default=True,
        description="Enable admin notifications",
    )
```

---

## 5. AdminNotificationService

### 5.1 Интерфейс

```python
# services/admin_notification_service.py

import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from src.core.config import settings

logger = logging.getLogger(__name__)


class AdminNotificationService:
    """Service for sending admin notifications about bot events."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.admin_chat_id = settings.admin_chat_id
        self.enabled = settings.admin_notifications_enabled

    def _is_enabled(self) -> bool:
        """Check if notifications are enabled and configured."""
        return self.enabled and self.admin_chat_id is not None

    async def _send(self, text: str) -> bool:
        """Send message to admin chat (fire-and-forget).

        Returns:
            True if sent successfully, False otherwise
        """
        if not self._is_enabled():
            return False

        try:
            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=text,
                parse_mode="HTML",
            )
            return True
        except (TelegramBadRequest, TelegramForbiddenError) as e:
            logger.warning("Failed to send admin notification: %s", e)
            return False
        except Exception as e:
            logger.error("Unexpected error sending admin notification: %s", e)
            return False

    async def notify_new_user(
        self,
        user_id: int,
        username: str | None,
        full_name: str | None,
    ) -> bool:
        """Notify about new user starting the bot.

        Args:
            user_id: Telegram user ID
            username: Telegram username (may be None)
            full_name: User's full name
        """
        user_link = f"@{username}" if username else f"ID: {user_id}"
        name = full_name or "—"

        text = (
            "👤 <b>Новый пользователь</b>\n\n"
            f"Имя: {name}\n"
            f"Контакт: {user_link}\n"
            f"ID: <code>{user_id}</code>"
        )
        return await self._send(text)

    async def notify_cv_analyzed(
        self,
        user_id: int,
        username: str | None,
    ) -> bool:
        """Notify about CV analysis completion.

        Args:
            user_id: Telegram user ID
            username: Telegram username
        """
        user_link = f"@{username}" if username else f"ID: {user_id}"

        text = (
            "📄 <b>Анализ CV</b>\n\n"
            f"Пользователь: {user_link}\n"
            f"ID: <code>{user_id}</code>"
        )
        return await self._send(text)

    async def notify_apply_generated(
        self,
        user_id: int,
        username: str | None,
        vacancy_title: str | None = None,
    ) -> bool:
        """Notify about apply/response generation.

        Args:
            user_id: Telegram user ID
            username: Telegram username
            vacancy_title: Title of the vacancy (optional)
        """
        user_link = f"@{username}" if username else f"ID: {user_id}"
        vacancy_info = f"\nВакансия: {vacancy_title}" if vacancy_title else ""

        text = (
            "✉️ <b>Генерация отклика</b>\n\n"
            f"Пользователь: {user_link}\n"
            f"ID: <code>{user_id}</code>"
            f"{vacancy_info}"
        )
        return await self._send(text)

    async def notify_payment_received(
        self,
        user_id: int,
        username: str | None,
        amount: float,
        tokens: int,
    ) -> bool:
        """Notify about successful payment.

        Args:
            user_id: Telegram user ID
            username: Telegram username
            amount: Payment amount in RUB
            tokens: Tokens credited
        """
        user_link = f"@{username}" if username else f"ID: {user_id}"

        text = (
            "💰 <b>Поступила оплата</b>\n\n"
            f"Пользователь: {user_link}\n"
            f"ID: <code>{user_id}</code>\n"
            f"Сумма: {amount}₽\n"
            f"Токенов: {tokens}"
        )
        return await self._send(text)

    async def notify_promo_activated(
        self,
        user_id: int,
        username: str | None,
        promo_code: str,
        bonus_tokens: int | None = None,
        discount_percent: int | None = None,
    ) -> bool:
        """Notify about promo code activation.

        Args:
            user_id: Telegram user ID
            username: Telegram username
            promo_code: Activated promo code
            bonus_tokens: Bonus tokens received
            discount_percent: Discount percentage
        """
        user_link = f"@{username}" if username else f"ID: {user_id}"

        bonus_info = ""
        if bonus_tokens:
            bonus_info = f"\nБонус: {bonus_tokens} токенов"
        elif discount_percent:
            bonus_info = f"\nСкидка: {discount_percent}%"

        text = (
            "🎁 <b>Активация промокода</b>\n\n"
            f"Пользователь: {user_link}\n"
            f"ID: <code>{user_id}</code>\n"
            f"Код: <code>{promo_code}</code>"
            f"{bonus_info}"
        )
        return await self._send(text)
```

---

## 6. Точки интеграции

### 6.1 Handler: /start (новый пользователь)

```python
# bot/handlers/start.py

from src.services.admin_notification_service import AdminNotificationService

@router.message(Command("start"))
async def cmd_start(
    message: Message,
    user_repo: UserRepository,
    admin_notify: AdminNotificationService,
) -> None:
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    is_new = user is None

    if is_new:
        # Create user...
        await admin_notify.notify_new_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )

    # ... rest of handler
```

### 6.2 Handler: /cv (анализ CV)

```python
# bot/handlers/cv.py

# После успешного завершения анализа:
await admin_notify.notify_cv_analyzed(
    user_id=message.from_user.id,
    username=message.from_user.username,
)
```

### 6.3 Handler: /apply (генерация отклика)

```python
# bot/handlers/apply.py

# После успешной генерации:
await admin_notify.notify_apply_generated(
    user_id=message.from_user.id,
    username=message.from_user.username,
    vacancy_title=vacancy.title,  # если есть
)
```

### 6.4 Webhook: успешная оплата

```python
# api/routes/webhook.py или payment callback

await admin_notify.notify_payment_received(
    user_id=user.telegram_id,
    username=user.username,
    amount=invoice.amount,
    tokens=invoice.tokens,
)
```

### 6.5 Handler: промокод

```python
# bot/handlers/promo.py или callback

await admin_notify.notify_promo_activated(
    user_id=message.from_user.id,
    username=message.from_user.username,
    promo_code=code,
    bonus_tokens=promo.bonus_tokens,
)
```

---

## 7. Dependency Injection

### 7.1 Middleware для DI

```python
# bot/middlewares/admin_notify.py

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.services.admin_notification_service import AdminNotificationService


class AdminNotifyMiddleware(BaseMiddleware):
    """Inject AdminNotificationService into handlers."""

    def __init__(self, bot):
        self.service = AdminNotificationService(bot)

    async def __call__(self, handler, event: TelegramObject, data: dict):
        data["admin_notify"] = self.service
        return await handler(event, data)
```

### 7.2 Регистрация в main.py

```python
from src.bot.middlewares.admin_notify import AdminNotifyMiddleware

# После создания диспетчера:
dp.message.middleware(AdminNotifyMiddleware(bot))
dp.callback_query.middleware(AdminNotifyMiddleware(bot))
```

---

## 8. Форматы сообщений

### 8.1 Новый пользователь

```
👤 Новый пользователь

Имя: Иван Петров
Контакт: @ivan_petrov
ID: 123456789
```

### 8.2 Анализ CV

```
📄 Анализ CV

Пользователь: @ivan_petrov
ID: 123456789
```

### 8.3 Генерация отклика

```
✉️ Генерация отклика

Пользователь: @ivan_petrov
ID: 123456789
Вакансия: Python Developer
```

### 8.4 Оплата

```
💰 Поступила оплата

Пользователь: @ivan_petrov
ID: 123456789
Сумма: 500₽
Токенов: 500
```

### 8.5 Промокод

```
🎁 Активация промокода

Пользователь: @ivan_petrov
ID: 123456789
Код: WELCOME2024
Бонус: 100 токенов
```

---

## 9. Обработка ошибок

- Ошибки отправки **не должны** влиять на основной flow
- Все ошибки логируются на уровне WARNING/ERROR
- Отключенные уведомления (`enabled=False`) — молчаливый skip
- Отсутствующий `ADMIN_CHAT_ID` — молчаливый skip

---

## 10. Checklist реализации

- [ ] Добавить настройки в `core/config.py`
- [ ] Создать `services/admin_notification_service.py`
- [ ] Создать `bot/middlewares/admin_notify.py`
- [ ] Зарегистрировать middleware в `main.py`
- [ ] Интегрировать в `/start` handler
- [ ] Интегрировать в `/cv` handler
- [ ] Интегрировать в `/apply` handler
- [ ] Интегрировать в payment webhook
- [ ] Интегрировать в promo handler
- [ ] Добавить `ADMIN_CHAT_ID` в `.env.example`
- [ ] Тестирование
- [ ] Деплой

---

## 11. Расширение (опционально)

В будущем можно добавить:

| Функция | Описание |
|---------|----------|
| Группировка | Агрегация событий за период (дневная сводка) |
| Фильтры | Настройка типов событий для уведомлений |
| Несколько админов | Список `ADMIN_CHAT_IDS` |
| Каналы | Отправка в канал вместо личного чата |
| Статистика | Периодические отчеты (DAU, платежи за день) |

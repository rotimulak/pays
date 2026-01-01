# Telegram Bot

> Telegram-бот на aiogram 3.x с командами, middleware и интерактивными клавиатурами.

## Команды

| Команда | Описание | Handler |
|---------|----------|---------|
| `/start` | Приветствие, регистрация пользователя | `handlers/start.py` |
| `/profile`, `/me` | Профиль: баланс, подписка | `handlers/profile.py` |
| `/tariffs` | Список тарифов | `handlers/tariffs.py` |
| `/balance` | Текущий баланс и статистика | `handlers/balance.py` |
| `/history` | История транзакций с пагинацией | `handlers/history.py` |
| `/help` | Справка по командам | `handlers/help.py` |

---

## Handlers

### /start

Регистрирует пользователя при первом обращении, показывает приветствие.

```
Привет, {first_name}! 👋

Я помогу тебе управлять подпиской и токенами.

Используй меню ниже или команды:
/profile — твой профиль
/tariffs — доступные тарифы
/help — справка
```

**Логика:**
1. AuthMiddleware создаёт/получает пользователя через `UserService.get_or_create`
2. Handler получает `user: User` через DI
3. Отправляет приветствие с reply keyboard

---

### /profile

Показывает профиль пользователя.

```
📊 Твой профиль

🆔 ID: {user.id}
👤 Username: @{username или "не указан"}

💰 Баланс: {token_balance} токенов
📅 Подписка: {активна до X / не активна}

Пополнить баланс: /tariffs
```

**Форматирование подписки:**
- `активна до DD.MM.YYYY` — есть активная подписка
- `не активна` — подписки нет
- `истекает сегодня!` — последний день

---

### /tariffs

Показывает список активных тарифов с inline keyboard.

```
📋 Доступные тарифы

Выберите тариф для покупки:
```

**Inline Keyboard:**
```
[ 💎 Starter — 299 ₽ ]
[ 🚀 Pro — 599 ₽ ]
[ 👑 Premium — 999 ₽ ]
```

При нажатии:
1. Создаётся invoice через `InvoiceService.get_or_create_invoice`
2. Генерируется payment URL через `PaymentService.create_payment_url`
3. Показывается информация о счёте с кнопкой оплаты

---

### /help

Показывает справку по командам.

```
📖 Справка

Доступные команды:

/start — начать работу
/profile — твой профиль
/tariffs — доступные тарифы
/balance — текущий баланс
/history — история транзакций
/help — эта справка

По вопросам: @support_username
```

---

## Middleware

### DbSessionMiddleware

Создаёт async session для каждого update и передаёт в handler.

```python
async def __call__(self, handler, event, data):
    async with async_session() as session:
        data["session"] = session
        return await handler(event, data)
```

---

### AuthMiddleware

Авторизует пользователя: создаёт нового или возвращает существующего.

```python
async def __call__(self, handler, event, data):
    session = data["session"]
    user_service = UserService(session)

    telegram_user = event.from_user
    user, created = await user_service.get_or_create(
        user_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
    )

    data["user"] = user
    return await handler(event, data)
```

---

## Keyboards

### Reply Keyboard (Main Menu)

```python
def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню бота."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Тарифы")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
    )
```

---

### Inline Keyboards

**Tariffs:**
```python
def get_tariffs_keyboard(tariffs: list[TariffDTO]) -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифа."""
    buttons = [
        [InlineKeyboardButton(
            text=f"{tariff.name} — {tariff.price_display}",
            callback_data=TariffCallback(tariff_id=tariff.id).pack(),
        )]
        for tariff in tariffs
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
```

**Payment:**
```python
def get_payment_keyboard(payment_url: str, invoice_id: UUID) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой оплаты."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=payment_url)],
        [InlineKeyboardButton(
            text="❌ Отменить",
            callback_data=CancelInvoiceCallback(invoice_id=invoice_id).pack(),
        )],
    ])
```

---

## Callback Data

### TariffCallback

```python
class TariffCallback(CallbackData, prefix="tariff"):
    tariff_id: UUID
```

Используется при выборе тарифа из списка.

---

### InvoiceCallback

```python
class CancelInvoiceCallback(CallbackData, prefix="cancel_inv"):
    invoice_id: UUID
```

Используется для отмены pending invoice.

---

### PaginationCallback

```python
class PaginationCallback(CallbackData, prefix="page"):
    prefix: str  # "history", "invoices", etc.
    page: int
```

Используется для пагинации в `/history`.

---

## Файловая структура

```
backend/src/bot/
├── __init__.py
├── handlers/
│   ├── __init__.py
│   ├── start.py
│   ├── profile.py
│   ├── tariffs.py
│   ├── buy.py
│   ├── balance.py
│   ├── history.py
│   └── help.py
├── keyboards/
│   ├── __init__.py
│   ├── main_menu.py
│   ├── tariffs.py
│   └── payment.py
├── callbacks/
│   ├── __init__.py
│   ├── tariff.py
│   ├── invoice.py
│   └── pagination.py
└── middlewares/
    ├── __init__.py
    ├── db_session.py
    └── auth.py
```

---

## Зависимости

- **От:** [Database](./database.md), [Billing](./billing.md)
- **Для:** —

---

## Конфигурация

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `SUPPORT_USERNAME` | Username поддержки для /help |

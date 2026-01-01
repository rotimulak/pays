# Handlers — Обработчики событий

## Router

Router — контейнер для группировки обработчиков.

```python
from aiogram import Router

router = Router(name="billing")
```

## Регистрация обработчиков

### Через декоратор

```python
@router.message()
async def message_handler(message: Message):
    await message.answer("Получено сообщение")

@router.callback_query()
async def callback_handler(callback: CallbackQuery):
    await callback.answer("OK")
```

### Через метод register

```python
async def my_handler(message: Message):
    await message.answer("Hello")

router.message.register(my_handler, Command("hello"))
```

## Типы обработчиков

| Декоратор | Событие |
|-----------|---------|
| `@router.message()` | Новое сообщение |
| `@router.edited_message()` | Редактирование сообщения |
| `@router.callback_query()` | Нажатие inline-кнопки |
| `@router.inline_query()` | Inline-запрос |
| `@router.pre_checkout_query()` | Предоплата (payments) |
| `@router.shipping_query()` | Запрос доставки |

## Вложенные роутеры

```python
from aiogram import Dispatcher, Router

# Главный dispatcher
dp = Dispatcher()

# Модули
billing_router = Router(name="billing")
admin_router = Router(name="admin")

# Подключение
dp.include_router(billing_router)
dp.include_router(admin_router)

# Или несколько сразу
dp.include_routers(billing_router, admin_router)
```

## Структура проекта

```
bot/
├── __init__.py
├── main.py
├── handlers/
│   ├── __init__.py
│   ├── start.py
│   ├── billing.py
│   └── admin.py
└── keyboards/
    └── billing.py
```

```python
# handlers/__init__.py
from aiogram import Router
from .start import router as start_router
from .billing import router as billing_router

def setup_routers() -> Router:
    router = Router()
    router.include_router(start_router)
    router.include_router(billing_router)
    return router

# main.py
from aiogram import Bot, Dispatcher
from handlers import setup_routers

dp = Dispatcher()
dp.include_router(setup_routers())
```

## Обработка callback_query

```python
from aiogram import Router
from aiogram.types import CallbackQuery

router = Router()

@router.callback_query()
async def handle_callback(callback: CallbackQuery):
    data = callback.data  # "billing:balance"

    if data == "billing:balance":
        await callback.message.edit_text("Ваш баланс: 100 токенов")

    # Обязательно ответить на callback
    await callback.answer()

# С уведомлением
@router.callback_query()
async def handle_with_alert(callback: CallbackQuery):
    await callback.answer("Успешно!", show_alert=True)
```

## Обработка платежей

```python
from aiogram import Router
from aiogram.types import PreCheckoutQuery, Message

router = Router()

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    # Проверка перед оплатой
    await query.answer(ok=True)
    # или await query.answer(ok=False, error_message="Ошибка")

@router.message(F.successful_payment)
async def successful_payment(message: Message):
    payment = message.successful_payment
    amount = payment.total_amount / 100  # в рублях
    await message.answer(f"Оплата {amount} ₽ получена!")
```

## Пример: Billing handlers

```python
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

router = Router(name="billing")

@router.message(Command("balance"))
async def cmd_balance(message: Message):
    # user = await get_user(message.from_user.id)
    await message.answer(
        "Ваш баланс: 150 токенов\n"
        "Подписка: активна до 15.02.2025",
        reply_markup=get_billing_menu()
    )

@router.callback_query(F.data == "billing:topup")
async def cb_topup(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите сумму пополнения:",
        reply_markup=get_topup_menu()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("topup:"))
async def cb_topup_amount(callback: CallbackQuery):
    amount = int(callback.data.split(":")[1])
    # payment_url = await create_payment(callback.from_user.id, amount)
    await callback.message.edit_text(
        f"Создан платёж на {amount} ₽\n"
        f"Ссылка: https://robokassa.ru/..."
    )
    await callback.answer()
```

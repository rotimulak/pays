# Filters — Фильтры и CallbackData

## Обзор

Фильтры определяют, какой handler обработает событие. Первый подходящий handler выполняется.

## Встроенные фильтры

```python
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram import F

# Command — команды
@router.message(Command("start"))

# F (Magic Filter) — универсальный фильтр
@router.message(F.text == "Привет")
@router.message(F.text.startswith("Оплата"))
@router.callback_query(F.data == "billing:menu")
```

## Magic Filter (F)

```python
from aiogram import F

# Текст
F.text == "exact"
F.text.startswith("prefix")
F.text.endswith("suffix")
F.text.contains("substr")
F.text.regexp(r"\d+")

# Callback data
F.data == "action"
F.data.startswith("billing:")
F.data.in_(["a", "b", "c"])

# Атрибуты
F.from_user.id == 12345
F.chat.type == "private"

# Комбинации
(F.text.startswith("/") & F.from_user.id == ADMIN_ID)
(F.data == "a") | (F.data == "b")
~F.from_user.is_bot
```

## CallbackData Factory

Типизированные callback_data с автоматической валидацией.

### Создание

```python
from aiogram.filters.callback_data import CallbackData

class BillingCallback(CallbackData, prefix="billing"):
    action: str

class TariffCallback(CallbackData, prefix="tariff"):
    id: int
    action: str  # "view", "buy"
```

### Использование в кнопках

```python
from aiogram.utils.keyboard import InlineKeyboardBuilder

builder = InlineKeyboardBuilder()

# pack() — сериализация в строку
builder.button(
    text="Баланс",
    callback_data=BillingCallback(action="balance").pack()
    # callback_data="billing:balance"
)

builder.button(
    text="Купить тариф",
    callback_data=TariffCallback(id=1, action="buy").pack()
    # callback_data="tariff:1:buy"
)
```

### Фильтрация в handlers

```python
# Все callbacks с prefix="billing"
@router.callback_query(BillingCallback.filter())
async def handle_billing(callback: CallbackQuery, callback_data: BillingCallback):
    action = callback_data.action
    if action == "balance":
        await callback.message.edit_text("Баланс: 100")
    await callback.answer()

# С условием
@router.callback_query(TariffCallback.filter(F.action == "buy"))
async def handle_buy(callback: CallbackQuery, callback_data: TariffCallback):
    tariff_id = callback_data.id
    await callback.message.edit_text(f"Покупка тарифа {tariff_id}")
    await callback.answer()
```

### Поддерживаемые типы

- `str`, `int`, `bool`, `float`
- `Decimal`, `Fraction`, `UUID`
- `Enum` (строковый), `IntEnum`

### Optional поля

```python
from typing import Optional

class PaymentCallback(CallbackData, prefix="pay"):
    action: str
    amount: Optional[int] = None

# pay:menu (amount не указан)
PaymentCallback(action="menu").pack()

# pay:confirm:500
PaymentCallback(action="confirm", amount=500).pack()
```

## Кастомные фильтры

### Класс

```python
from aiogram.filters import Filter
from aiogram.types import Message

class IsAdmin(Filter):
    def __init__(self, admin_ids: list[int]):
        self.admin_ids = admin_ids

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in self.admin_ids

# Использование
ADMINS = [12345, 67890]

@router.message(Command("admin"), IsAdmin(ADMINS))
async def admin_panel(message: Message):
    await message.answer("Админ-панель")
```

### Функция

```python
async def is_premium(message: Message) -> bool:
    # user = await get_user(message.from_user.id)
    # return user.is_premium
    return True

@router.message(Command("premium"), is_premium)
async def premium_feature(message: Message):
    pass
```

### Фильтр с данными

```python
class HasSubscription(Filter):
    async def __call__(self, message: Message) -> dict | bool:
        # user = await get_user(message.from_user.id)
        user = {"subscription": "premium", "tokens": 100}

        if user.get("subscription"):
            return {"user_data": user}  # Передаём в handler
        return False

@router.message(Command("use"), HasSubscription())
async def use_feature(message: Message, user_data: dict):
    tokens = user_data["tokens"]
    await message.answer(f"Осталось токенов: {tokens}")
```

## Комбинирование фильтров

```python
from aiogram.filters import and_f, or_f, invert_f

# AND — все должны пройти
@router.message(Command("secret"), IsAdmin(ADMINS), HasSubscription())

# OR — любой должен пройти
@router.message(or_f(Command("help"), F.text == "помощь"))

# NOT — инверсия
@router.message(invert_f(IsAdmin(ADMINS)))
# или
@router.message(~IsAdmin(ADMINS))
```

## Пример: Фильтры для биллинга

```python
from aiogram.filters.callback_data import CallbackData
from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery

# CallbackData для биллинга
class BillingAction(CallbackData, prefix="bill"):
    action: str  # menu, balance, topup, history

class TopupAmount(CallbackData, prefix="topup"):
    amount: int

class TariffSelect(CallbackData, prefix="tf"):
    tariff_id: int
    action: str  # view, buy

# Фильтр активной подписки
class HasActiveSubscription(Filter):
    async def __call__(self, event: Message | CallbackQuery) -> dict | bool:
        user_id = event.from_user.id
        # subscription = await billing_service.get_subscription(user_id)
        subscription = {"active": True, "expires": "2025-02-01"}

        if subscription and subscription.get("active"):
            return {"subscription": subscription}
        return False

# Handlers
@router.callback_query(BillingAction.filter(F.action == "balance"))
async def show_balance(callback: CallbackQuery, callback_data: BillingAction):
    await callback.message.edit_text("Баланс: 150 токенов")
    await callback.answer()

@router.callback_query(TopupAmount.filter())
async def process_topup(callback: CallbackQuery, callback_data: TopupAmount):
    amount = callback_data.amount
    # url = await create_payment(callback.from_user.id, amount)
    await callback.message.edit_text(f"Оплата {amount} ₽: https://...")
    await callback.answer()

@router.message(Command("premium"), HasActiveSubscription())
async def premium_content(message: Message, subscription: dict):
    await message.answer(f"Подписка до: {subscription['expires']}")
```

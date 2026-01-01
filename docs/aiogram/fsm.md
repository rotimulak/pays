# FSM — Finite State Machine

## Обзор

FSM (конечный автомат) — для сложных диалогов с несколькими шагами.

## Определение состояний

```python
from aiogram.fsm.state import State, StatesGroup

class PaymentForm(StatesGroup):
    waiting_amount = State()      # Ожидание суммы
    waiting_confirm = State()     # Подтверждение
```

## Работа с FSMContext

```python
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("pay"))
async def cmd_pay(message: Message, state: FSMContext):
    await state.set_state(PaymentForm.waiting_amount)
    await message.answer("Введите сумму пополнения:")

@router.message(PaymentForm.waiting_amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 10:
            await message.answer("Минимум 10 ₽. Попробуйте снова:")
            return

        # Сохраняем данные
        await state.update_data(amount=amount)
        await state.set_state(PaymentForm.waiting_confirm)

        await message.answer(
            f"Пополнить на {amount} ₽?\n"
            "Отправьте 'да' для подтверждения или 'нет' для отмены."
        )
    except ValueError:
        await message.answer("Введите число:")

@router.message(PaymentForm.waiting_confirm)
async def process_confirm(message: Message, state: FSMContext):
    if message.text.lower() == "да":
        data = await state.get_data()
        amount = data["amount"]

        # Создание платежа
        await message.answer(f"Создаю платёж на {amount} ₽...")

        await state.clear()  # Сброс состояния
    else:
        await state.clear()
        await message.answer("Операция отменена.")
```

## Методы FSMContext

| Метод | Описание |
|-------|----------|
| `set_state(state)` | Установить состояние |
| `get_state()` | Получить текущее состояние |
| `clear()` | Сбросить состояние и данные |
| `update_data(**kwargs)` | Обновить данные |
| `get_data()` | Получить все данные |
| `set_data(data)` | Заменить все данные |

## Storage — хранилище состояний

### MemoryStorage (по умолчанию)

```python
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

storage = MemoryStorage()
dp = Dispatcher(storage=storage)
```

> **Внимание:** MemoryStorage теряет данные при перезапуске.

### RedisStorage (production)

```python
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

redis = Redis(host="localhost", port=6379)
storage = RedisStorage(redis=redis)
dp = Dispatcher(storage=storage)
```

## FSM Strategy

Область действия состояния:

```python
from aiogram.fsm.strategy import FSMStrategy

dp = Dispatcher(
    storage=storage,
    fsm_strategy=FSMStrategy.USER_IN_CHAT,  # по умолчанию
)
```

| Стратегия | Описание |
|-----------|----------|
| `CHAT` | Одно состояние на чат |
| `USER_IN_CHAT` | На пользователя в чате (default) |
| `GLOBAL_USER` | На пользователя глобально |

## Отмена диалога

```python
from aiogram.filters import Command, StateFilter

@router.message(Command("cancel"), StateFilter("*"))
async def cmd_cancel(message: Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        await message.answer("Нечего отменять.")
        return

    await state.clear()
    await message.answer("Действие отменено.")
```

## Пример: Форма пополнения баланса

```python
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

router = Router()

class TopupForm(StatesGroup):
    select_amount = State()
    custom_amount = State()
    confirm = State()

AMOUNTS = [100, 300, 500, 1000]

@router.callback_query(F.data == "billing:topup")
async def start_topup(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    for amount in AMOUNTS:
        builder.button(text=f"{amount} ₽", callback_data=f"amount:{amount}")
    builder.button(text="Другая сумма", callback_data="amount:custom")
    builder.button(text="« Отмена", callback_data="billing:menu")
    builder.adjust(2, 2, 1)

    await state.set_state(TopupForm.select_amount)
    await callback.message.edit_text(
        "Выберите сумму:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(TopupForm.select_amount, F.data.startswith("amount:"))
async def process_amount_select(callback: CallbackQuery, state: FSMContext):
    value = callback.data.split(":")[1]

    if value == "custom":
        await state.set_state(TopupForm.custom_amount)
        await callback.message.edit_text("Введите сумму (от 10 ₽):")
    else:
        amount = int(value)
        await state.update_data(amount=amount)
        await show_confirm(callback.message, state, amount)

    await callback.answer()

@router.message(TopupForm.custom_amount)
async def process_custom_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 10:
            await message.answer("Минимум 10 ₽:")
            return
        await state.update_data(amount=amount)
        await show_confirm(message, state, amount)
    except ValueError:
        await message.answer("Введите число:")

async def show_confirm(message: Message, state: FSMContext, amount: int):
    await state.set_state(TopupForm.confirm)
    builder = InlineKeyboardBuilder()
    builder.button(text="Оплатить", callback_data="confirm:yes")
    builder.button(text="Отмена", callback_data="confirm:no")

    await message.answer(
        f"Пополнение на {amount} ₽\n\nПодтвердить?",
        reply_markup=builder.as_markup()
    )

@router.callback_query(TopupForm.confirm)
async def process_confirm(callback: CallbackQuery, state: FSMContext):
    if callback.data == "confirm:yes":
        data = await state.get_data()
        # payment_url = await create_robokassa_payment(user_id, data["amount"])
        await callback.message.edit_text(
            f"Перейдите по ссылке для оплаты:\nhttps://..."
        )
    else:
        await callback.message.edit_text("Операция отменена.")

    await state.clear()
    await callback.answer()
```

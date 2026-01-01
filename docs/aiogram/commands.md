# Commands — Команды бота

## Command Filter

Фильтр для обработки команд (сообщения начинающиеся с `/`).

```python
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Добро пожаловать!")

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer("Справка по командам...")
```

## Параметры Command

| Параметр | Тип | Описание |
|----------|-----|----------|
| `commands` | str/list | Имена команд без `/` |
| `prefix` | str | Префикс команды (по умолчанию `/`) |
| `ignore_case` | bool | Игнорировать регистр |
| `ignore_mention` | bool | Обрабатывать команды для других ботов |

```python
# Несколько команд
@router.message(Command("start", "help", "info"))
async def multi_command(message: Message):
    pass

# Игнорировать регистр
@router.message(Command("pay", ignore_case=True))
async def pay_command(message: Message):
    pass  # /PAY, /Pay, /pay
```

## CommandObject

Объект с информацией о команде:

```python
from aiogram.filters import CommandObject

@router.message(Command("pay"))
async def cmd_pay(message: Message, command: CommandObject):
    # /pay 100 — пополнить на 100
    args = command.args  # "100"

    if args:
        amount = int(args)
        await message.answer(f"Пополнение на {amount} ₽")
```

### Атрибуты CommandObject

| Атрибут | Описание |
|---------|----------|
| `prefix` | Префикс команды (`/`) |
| `command` | Имя команды без префикса |
| `args` | Аргументы после команды |
| `mention` | Упоминание бота (если есть) |

## Регистрация команд в Telegram

```python
from aiogram.types import BotCommand

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="balance", description="Мой баланс"),
        BotCommand(command="pay", description="Пополнить баланс"),
        BotCommand(command="tariffs", description="Тарифы"),
    ]
    await bot.set_my_commands(commands)
```

## CommandStart с deep linking

```python
from aiogram.filters import CommandStart

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    # /start ref_12345
    ref_code = command.args
    if ref_code and ref_code.startswith("ref_"):
        referrer_id = ref_code[4:]
        # Обработка реферальной ссылки
```

## Пример: Команды биллинга

```python
from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

router = Router()

@router.message(Command("balance"))
async def cmd_balance(message: Message):
    user_id = message.from_user.id
    # balance = await billing_service.get_balance(user_id)
    balance = 150  # пример
    await message.answer(f"Ваш баланс: {balance} токенов")

@router.message(Command("pay"))
async def cmd_pay(message: Message, command: CommandObject):
    if not command.args:
        await message.answer("Укажите сумму: /pay 100")
        return

    try:
        amount = int(command.args)
        if amount < 10:
            await message.answer("Минимальная сумма: 10 ₽")
            return

        # payment_url = await billing_service.create_payment(user_id, amount)
        await message.answer(f"Создан платёж на {amount} ₽")
    except ValueError:
        await message.answer("Неверная сумма")

@router.message(Command("tariffs"))
async def cmd_tariffs(message: Message):
    tariffs_text = """
Тарифы:

• Базовый — 99 ₽/мес (100 токенов)
• Стандарт — 299 ₽/мес (500 токенов)
• Премиум — 799 ₽/мес (2000 токенов)

Используйте /pay <сумма> для пополнения
"""
    await message.answer(tariffs_text)
```

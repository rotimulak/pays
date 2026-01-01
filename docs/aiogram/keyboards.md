# Keyboards — Клавиатуры

## Обзор

aiogram предоставляет два типа клавиатур:
- **InlineKeyboard** — кнопки под сообщением (callback_data, URL)
- **ReplyKeyboard** — кнопки вместо клавиатуры (текст, контакт, локация)

## InlineKeyboardBuilder

```python
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

# Создание builder
builder = InlineKeyboardBuilder()

# Добавление кнопок
builder.button(text="Купить", callback_data="buy")
builder.button(text="Отмена", callback_data="cancel")

# Расположение: 2 кнопки в ряд
builder.adjust(2)

# Получение markup
keyboard = builder.as_markup()

await message.answer("Выберите действие:", reply_markup=keyboard)
```

### Методы InlineKeyboardBuilder

| Метод | Описание |
|-------|----------|
| `button(text, callback_data, url, ...)` | Добавить кнопку |
| `row(*buttons)` | Добавить ряд кнопок |
| `adjust(*sizes)` | Расположить кнопки по рядам |
| `add(*buttons)` | Добавить несколько кнопок |
| `as_markup()` | Экспорт в InlineKeyboardMarkup |
| `attach(builder)` | Объединить с другим builder |
| `copy()` | Копировать builder |

### Параметры button()

```python
builder.button(
    text="Текст кнопки",
    callback_data="action:123",      # Для обработки callback
    url="https://example.com",       # Ссылка
    pay=True,                        # Кнопка оплаты (только первая)
)
```

## ReplyKeyboardBuilder

```python
from aiogram.utils.keyboard import ReplyKeyboardBuilder

builder = ReplyKeyboardBuilder()

builder.button(text="Баланс")
builder.button(text="Тарифы")
builder.button(text="Помощь")

builder.adjust(2, 1)  # 2 кнопки в первом ряду, 1 во втором

keyboard = builder.as_markup(
    resize_keyboard=True,      # Уменьшить размер
    one_time_keyboard=True,    # Скрыть после нажатия
)

await message.answer("Меню:", reply_markup=keyboard)
```

### Специальные кнопки Reply

```python
builder.button(text="Отправить контакт", request_contact=True)
builder.button(text="Отправить локацию", request_location=True)
```

## Статические клавиатуры

Для неизменяемых меню лучше объявлять явно:

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

MAIN_MENU = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="Баланс", callback_data="balance"),
        InlineKeyboardButton(text="Тарифы", callback_data="tariffs"),
    ],
    [
        InlineKeyboardButton(text="Помощь", callback_data="help"),
    ],
])
```

## Удаление клавиатуры

```python
from aiogram.types import ReplyKeyboardRemove

await message.answer("Клавиатура удалена", reply_markup=ReplyKeyboardRemove())
```

## Пример: Меню биллинга

```python
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_billing_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="Баланс", callback_data="billing:balance")
    builder.button(text="Пополнить", callback_data="billing:topup")
    builder.button(text="История", callback_data="billing:history")
    builder.button(text="Тарифы", callback_data="billing:tariffs")

    builder.adjust(2, 2)
    return builder.as_markup()


def get_tariff_menu(tariffs: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for tariff in tariffs:
        builder.button(
            text=f"{tariff.name} — {tariff.price} ₽",
            callback_data=f"tariff:{tariff.id}"
        )

    builder.button(text="« Назад", callback_data="billing:menu")
    builder.adjust(1)

    return builder.as_markup()
```

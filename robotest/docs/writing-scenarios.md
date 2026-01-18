# Написание сценариев

## Структура теста

```python
"""
Scenario: <название>
Phase: <номер фазы>

<описание что тестируем>
"""
import pytest

pytestmark = [pytest.mark.asyncio]


class TestFeatureName:
    """Test group description."""

    async def test_specific_case(self, bot, timeout):
        """
        Scenario: <что делает пользователь>
        Expected: <что должен сделать бот>

        AR/ER: <критерий успеха>
        """
        # Arrange (подготовка)

        # Act (действие)
        await bot.send("/command")

        # Assert (проверка)
        await bot.expect_text(pattern=r"expected.*text")
```

## API клиента (BotTester)

### Отправка сообщений

```python
# Текстовое сообщение
await bot.send("/start")

# Файл
await bot.send_file("fixtures/sample_cv.pdf")

# Нажатие inline-кнопки
await bot.click_button("📄 Анализ CV")
```

### Ожидание ответов

```python
# Просто ждать ответы
responses = await bot.wait_responses(timeout=15.0)

# Ждать конкретный текст (regex)
await bot.expect_text(pattern=r"Привет.*мир")

# Ждать кнопки
await bot.expect_buttons(buttons=["OK", "Cancel"])
```

### Сброс состояния

```python
# Сбросить FSM state бота
await bot.reset()
```

## AR/ER при ошибке

При несовпадении ожидания выводится:

```
==================================================
EXPECTED (ER):
Pattern: 'ожидаемый текст'
--------------------------------------------------
ACTUAL (AR):
Реальный ответ бота
==================================================
```

## Fixtures (pytest)

| Fixture | Тип | Описание |
|---------|-----|----------|
| `bot` | `BotTester` | Клиент для тестирования бота |
| `timeout` | `float` | Стандартный таймаут (15s) |
| `long_timeout` | `float` | Для долгих операций (120s) |

## Пример: тест команды

```python
async def test_balance_shows_tokens(self, bot, timeout):
    """
    Scenario: User checks balance
    Expected: Bot shows current token balance

    AR/ER: Ответ содержит "Баланс" и число токенов
    """
    await bot.send("/balance")

    await bot.expect_text(
        pattern=r"Баланс.*\d+.*токен",
        timeout=timeout,
    )
```

## Пример: тест с кнопками

```python
async def test_buy_shows_tariffs(self, bot, timeout):
    """
    Scenario: User wants to buy tokens
    Expected: Bot shows available tariffs with buttons

    AR/ER: Показаны кнопки тарифов
    """
    await bot.send("/buy")

    await bot.expect_buttons(
        buttons=["Базовый", "Про"],
        timeout=timeout,
    )
```

## Пример: тест с файлом

```python
async def test_cv_accepts_pdf(self, bot, long_timeout):
    """
    Scenario: User uploads CV as PDF
    Expected: Bot processes and returns analysis

    AR/ER: Бот принимает файл и возвращает результат
    """
    await bot.send("/cv")
    await bot.expect_text(pattern=r"Отправьте.*файл")

    await bot.send_file("fixtures/sample_cv.pdf")

    await bot.expect_text(
        pattern=r"(Анализ|результат|завершён)",
        timeout=long_timeout,
    )
```

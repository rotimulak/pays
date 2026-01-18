# Troubleshooting

## Ошибка: "Robotest not authorized"

**Причина:** Session файл отсутствует или устарел.

**Решение:**
```bash
python -m src.auth
```

---

## Ошибка: "FLOOD_WAIT_X"

**Причина:** Telegram rate limiting. Слишком много запросов.

**Решение:**
- Подождите указанное время (X секунд)
- Снизьте частоту запуска тестов
- Добавьте паузы между тестами

---

## Ошибка: "Bot did not respond"

**Причины:**
1. Бот не запущен
2. Неверный `BOT_USERNAME` в .env
3. Timeout слишком маленький

**Решение:**
1. Проверьте что бот работает (отправьте /start вручную)
2. Проверьте username в .env
3. Увеличьте `DEFAULT_TIMEOUT`

---

## Ошибка: "Session file locked"

**Причина:** Другой процесс использует session файл.

**Решение:**
- Завершите другие процессы использующие robotest
- Или используйте разные session файлы (разные `ROBOTEST_SESSION`)

---

## Тесты зависают

**Причина:** Бот ждёт ввода (FSM state не сброшен).

**Решение:**
Добавьте сброс состояния в начало теста:
```python
async def test_something(self, bot, timeout):
    await bot.reset()  # Сбросить FSM state
    # ... тест
```

---

## Ошибка: "Pattern not found"

**Причина:** Regex паттерн не совпал с ответом бота.

**Решение:**
1. Посмотрите в AR (Actual Result) что именно ответил бот
2. Исправьте паттерн в ER (Expected Result)
3. Используйте `re.IGNORECASE` и `re.DOTALL` (уже включены)

---

## Ошибка: "Button not found"

**Причина:** Кнопка с указанным текстом не найдена.

**Решение:**
1. Проверьте точный текст кнопки (включая emoji)
2. Убедитесь что сообщение с кнопками было получено
3. Увеличьте timeout

---

## Ошибка импорта: "ModuleNotFoundError"

**Причина:** Зависимости не установлены.

**Решение:**
```bash
cd robotest
pip install -e ".[dev]"
```

---

## Логирование для отладки

Добавьте в тест для просмотра всех ответов:

```python
async def test_debug(self, bot, timeout):
    await bot.send("/start")
    responses = await bot.wait_responses(timeout=30)

    for i, resp in enumerate(responses):
        print(f"--- Message {i+1} ---")
        print(resp.text)
        if resp.reply_markup:
            print(f"Buttons: {bot._extract_buttons(resp)}")
```

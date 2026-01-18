# Настройка Robotest

## Требования

- Python 3.11+
- Telegram аккаунт для тестирования (роботест)
- Telegram API credentials

## Установка

```bash
cd robotest
pip install -e ".[dev]"
```

## Конфигурация

1. Скопируйте `.env.example` → `.env`:
   ```bash
   cp .env.example .env
   ```

2. Заполните credentials (см. [authorization.md](authorization.md))

## Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|--------|
| `TELEGRAM_API_ID` | API ID от my.telegram.org | `12345678` |
| `TELEGRAM_API_HASH` | API Hash от my.telegram.org | `abcdef123...` |
| `ROBOTEST_PHONE` | Номер телефона роботеста | `+79001234567` |
| `ROBOTEST_SESSION` | Имя файла сессии | `robotest` |
| `BOT_USERNAME` | Username тестируемого бота | `smartheadhunterbot` |
| `DEFAULT_TIMEOUT` | Таймаут ожидания ответа (сек) | `15.0` |
| `LONG_TIMEOUT` | Таймаут для долгих операций | `120.0` |

## Проверка

```bash
# Проверить конфигурацию
python -c "from src.config import settings; print(settings.bot_username)"

# Авторизоваться
python -m src.auth

# Запустить тесты
pytest scenarios/ -v
```

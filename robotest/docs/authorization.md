# Авторизация роботеста

## Шаг 1: Создание тестового аккаунта

Рекомендуется использовать **отдельный** Telegram аккаунт для тестирования:

- Используйте виртуальный номер или второй телефон
- **Не используйте личный аккаунт** для автотестов

## Шаг 2: Получение API credentials

1. Откройте https://my.telegram.org/apps
2. Войдите с номером роботеста
3. Создайте приложение:
   - **App title:** `Robotest`
   - **Short name:** `robotest`
   - **Platform:** Desktop
4. Сохраните `api_id` и `api_hash`

## Шаг 3: Настройка .env

```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
ROBOTEST_PHONE=+79001234567
```

## Шаг 4: Первичная авторизация

```bash
cd robotest
python -m src.auth
```

Telegram отправит код подтверждения на номер роботеста. Введите его в консоли.

После успешной авторизации:
```
==================================================
Robotest Authorization
==================================================

Phone: +79001234567
Session file: robotest.session

✅ Authorized as: Test User (@testuser)
Session saved: robotest.session
```

## Session файл

- `robotest.session` — зашифрованный файл сессии Telegram
- Содержит авторизационные данные роботеста
- **НЕ коммитьте в git** (уже в .gitignore)
- Файл действителен пока сессия не отозвана в Telegram

## Повторная авторизация

Если сессия устарела или была отозвана:

1. Удалите старый файл: `rm robotest.session`
2. Повторите авторизацию: `python -m src.auth`

## Безопасность

⚠️ **Важно:**

- Никогда не публикуйте `api_id`, `api_hash`, `.session` файлы
- Используйте отдельный аккаунт для тестов
- При компрометации — отзовите сессию:
  - Telegram → Settings → Devices → Terminate session

# Безопасность

## Валидация Telegram init_data

При авторизации через Telegram Web App необходимо проверять подлинность данных пользователя:

```python
import hashlib
import hmac
from urllib.parse import parse_qsl

def validate_init_data(init_data: str, bot_token: str) -> bool:
    """
    Проверка подписи init_data от Telegram Web App.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)

    if not received_hash:
        return False

    # Сортировка и формирование data_check_string
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    # Создание secret_key = HMAC_SHA256(bot_token, "WebAppData")
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256
    ).digest()

    # Вычисление хэша
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(calculated_hash, received_hash)
```

**Важно:** Проверять `auth_date` — данные считаются устаревшими через 5 минут.

---

## Валидация webhook'ов Робокассы

См. [Интеграция с Робокассой](robokassa-adapter.md#валидация-webhookов).

---

## Rate Limiting

Защита от спама и DDoS-атак:

| Endpoint | Лимит | Окно |
|----------|-------|------|
| Команды бота (на пользователя) | 30 запросов | 1 минута |
| `/pay` (создание счёта) | 5 запросов | 1 минута |
| `/webhook/robokassa` (по IP) | 100 запросов | 1 минута |
| API endpoints (на пользователя) | 60 запросов | 1 минута |

### Реализация (in-memory с TTL)

```python
import time
from collections import defaultdict
from fastapi import Request, HTTPException

class RateLimiter:
    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, limit: int, window: int) -> bool:
        now = time.time()
        # Удаляем устаревшие записи
        self._requests[key] = [
            t for t in self._requests[key] if now - t < window
        ]
        if len(self._requests[key]) >= limit:
            return False
        self._requests[key].append(now)
        return True

rate_limiter = RateLimiter()

async def rate_limit_dependency(request: Request):
    user_id = request.state.user_id  # или извлечь из headers
    if not rate_limiter.check(f"user:{user_id}", limit=60, window=60):
        raise HTTPException(429, "Too Many Requests")
```

> **Примечание:** Для single-instance деплоя in-memory решения достаточно.
> При масштабировании на несколько инстансов потребуется Redis.

---

## Хранение секретов

| Секрет | Требования |
|--------|------------|
| `TELEGRAM_BOT_TOKEN` | Никогда не логировать, не передавать на фронтенд |
| `ROBOKASSA_PASSWORD1` | Используется только при формировании ссылки на оплату |
| `ROBOKASSA_PASSWORD2` | Используется только для проверки webhook'ов |
| `DATABASE_URL` | Хранить в переменных окружения, не в коде |

**Рекомендации:**
- Использовать `.env` файлы (не коммитить в git)
- В production: Docker secrets, Vault, AWS Secrets Manager
- Регулярная ротация ключей (минимум раз в 6 месяцев)
- При компрометации — немедленная ротация через @BotFather и личный кабинет Робокассы

---

## HTTPS/TLS требования

```
┌─────────────────────────────────────────────────────────────────┐
│                    ОБЯЗАТЕЛЬНО HTTPS                            │
├─────────────────────────────────────────────────────────────────┤
│ • Telegram Webhook API требует HTTPS с валидным сертификатом    │
│ • Робокасса отправляет webhook'и только на HTTPS endpoints      │
│ • Минимум TLS 1.2 (рекомендуется TLS 1.3)                       │
│ • Сертификат: Let's Encrypt (бесплатный) или коммерческий       │
└─────────────────────────────────────────────────────────────────┘
```

Пример настройки nginx см. в [Деплой](deployment.md#nginx-конфигурация).

---

## Защита от повторной обработки платежей

См. [Интеграция с Робокассой](robokassa-adapter.md#защита-от-повторной-обработки-платежей).

---

## См. также

- [Интеграция с Робокассой](robokassa-adapter.md) — валидация webhook'ов
- [Telegram-бот](bot.md) — rate limiting для команд
- [Деплой](deployment.md) — настройка HTTPS

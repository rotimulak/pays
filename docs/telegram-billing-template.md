# Telegram Billing Template Service

## Краткое описание

**Telegram Billing Template** — готовый шаблон микросервиса для быстрого запуска SaaS-продуктов с монетизацией через Telegram. Включает полноценную биллинг-систему на базе Робокассы, управление подписками и токенами, учёт балансов пользователей, а также документацию и лендинг на Docusaurus.

---

## Ключевые возможности

- **Авторизация** через Telegram-аккаунт (user_id)
- **Биллинг** через Робокассу с автоматической обработкой webhook'ов
- **Два типа оплаты**: подписка (время) + токены (расходуемые единицы)
- **История операций** и транзакций
- **Готовый Telegram-бот** с командами управления
- **Лендинг и документация** на базе Docusaurus

---

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Регистрация / приветствие |
| `/balance` | Текущий баланс токенов |
| `/subscription` | Статус и срок подписки |
| `/pay` | Создать счёт на оплату |
| `/history` | История платежей |
| `/tariffs` | Доступные тарифы |
| `/help` | Справка по командам |

> Все команды управления скрыты в меню «⚙️ Аккаунт». Отдельно — пункты меню для бизнес-логики сервиса.

---

## Схема базы данных

```
┌─────────────────────────────────────────────────────────────────┐
│                           users                                 │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)           │ BIGINT        │ Telegram user_id            │
│ username          │ VARCHAR       │ @username                   │
│ first_name        │ VARCHAR       │ Имя                         │
│ token_balance     │ INT           │ Остаток токенов             │
│ is_active         │ BOOLEAN       │ Подписка активна            │
│ subscription_end  │ TIMESTAMP     │ Дата окончания подписки     │
│ created_at        │ TIMESTAMP     │                             │
│ updated_at        │ TIMESTAMP     │                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          invoices                               │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)           │ UUID          │                             │
│ user_id (FK)      │ BIGINT        │ → users.id                  │
│ amount            │ DECIMAL       │ Сумма в рублях              │
│ tokens            │ INT           │ Кол-во токенов (если есть)  │
│ subscription_days │ INT           │ Дни подписки (если есть)    │
│ status            │ ENUM          │ pending / paid / cancelled / expired │
│ robokassa_id      │ VARCHAR       │ ID операции Робокассы       │
│ created_at        │ TIMESTAMP     │                             │
│ paid_at           │ TIMESTAMP     │                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        transactions                             │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)           │ UUID          │                             │
│ user_id (FK)      │ BIGINT        │ → users.id                  │
│ type              │ ENUM          │ topup / spend / subscription / refund │
│ tokens_delta      │ INT           │ +/- токенов                 │
│ description       │ VARCHAR       │ Причина списания/начисления │
│ invoice_id (FK)   │ UUID          │ → invoices.id (nullable)    │
│ created_at        │ TIMESTAMP     │                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          tariffs                                │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)           │ VARCHAR       │ basic_monthly / pro_yearly  │
│ name              │ VARCHAR       │ Название для пользователя   │
│ price             │ DECIMAL       │ Цена                        │
│ tokens            │ INT           │ Кол-во токенов              │
│ subscription_days │ INT           │ Дни подписки                │
│ is_active         │ BOOLEAN       │                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Состояния и жизненные циклы

### Жизненный цикл Invoice

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
┌─────────┐    ┌─────────┐    ┌─────────┐           ┌─────────┐
│ создан  │───>│ pending │───>│  paid   │           │ expired │
└─────────┘    └────┬────┘    └─────────┘           └─────────┘
                    │                                     ▲
                    │         ┌───────────┐               │
                    └────────>│ cancelled │               │
                              └───────────┘               │
                    │                                     │
                    └─────────── (TTL истёк) ─────────────┘
```

| Статус | Описание |
|--------|----------|
| `pending` | Счёт создан, ожидает оплаты |
| `paid` | Оплата подтверждена через webhook Робокассы |
| `cancelled` | Отменён пользователем или системой |
| `expired` | Истёк срок ожидания оплаты (TTL) |

### Жизненный цикл подписки

```
┌──────────────────────────────────────────────────────────────────┐
│                      АКТИВНАЯ ПОДПИСКА                           │
│                  (subscription_end > now)                        │
│                                                                  │
│  • Сервис полностью работоспособен                               │
│  • Токены списываются при рабочих запросах                       │
└──────────────────────────────────────────────────────────────────┘
                              │
                              │ subscription_end достигнут
                              ▼
              ┌───────────────────────────────────┐
              │   Проверка баланса токенов        │
              │   (token_balance >= SUBSCRIPTION_PRICE)
              └───────────────────────────────────┘
                     │                    │
          Достаточно │                    │ Недостаточно
                     ▼                    ▼
┌─────────────────────────────┐  ┌─────────────────────────────────┐
│   АВТОПРОДЛЕНИЕ             │  │      ПОДПИСКА ИСТЕКЛА           │
│                             │  │                                 │
│ • Списание токенов          │  │ • Сервис недоступен             │
│ • subscription_end += 30d   │  │ • Бот отвечает: "Подписка       │
│ • Транзакция type=spend     │  │   истекла, пополните баланс"    │
│ • Уведомление пользователю  │  │ • Баланс токенов сохраняется    │
└─────────────────────────────┘  └─────────────────────────────────┘
              │                                    │
              └────────> АКТИВНАЯ ПОДПИСКА <───────┘
                         (после пополнения)
```

### Логика списания токенов

```
┌─────────────────────────────────────────────────────────────────┐
│                     РАБОЧИЙ ЗАПРОС                              │
│              (использование основного сервиса)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────────┐
              │   Проверка: подписка активна?     │
              └───────────────────────────────────┘
                     │                    │
                  Да │                    │ Нет
                     ▼                    ▼
              ┌─────────────┐      ┌─────────────────────┐
              │ Проверка:   │      │ Отказ в обслуживании│
              │ tokens > 0? │      │ "Продлите подписку" │
              └─────────────┘      └─────────────────────┘
                     │
          Да │             │ Нет
             ▼             ▼
   ┌──────────────┐  ┌──────────────────────┐
   │ Выполнить    │  │ Отказ: "Недостаточно │
   │ запрос       │  │ токенов, пополните   │
   │ tokens -= N  │  │ баланс"              │
   └──────────────┘  └──────────────────────┘
```

### Типы транзакций

| Тип | Описание | tokens_delta |
|-----|----------|--------------|
| `topup` | Пополнение баланса (оплата через Робокассу) | +N |
| `spend` | Списание за рабочий запрос | -N |
| `subscription` | Автосписание абонплаты с баланса | -SUBSCRIPTION_PRICE |
| `refund` | Возврат средств | +N |

---

## Безопасность

### Валидация Telegram init_data

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

### Валидация webhook'ов Робокассы

```python
import hashlib

def validate_robokassa_signature(
    out_sum: str,
    inv_id: str,
    password2: str,
    received_signature: str
) -> bool:
    """
    Проверка подписи ResultURL от Робокассы.
    """
    # Формат: OutSum:InvId:Password2
    signature_string = f"{out_sum}:{inv_id}:{password2}"
    calculated = hashlib.md5(signature_string.encode()).hexdigest().upper()

    return hmac.compare_digest(calculated, received_signature.upper())
```

### Rate Limiting

Защита от спама и DDoS-атак:

| Endpoint | Лимит | Окно |
|----------|-------|------|
| Команды бота (на пользователя) | 30 запросов | 1 минута |
| `/pay` (создание счёта) | 5 запросов | 1 минута |
| `/webhook/robokassa` (по IP) | 100 запросов | 1 минута |
| API endpoints (на пользователя) | 60 запросов | 1 минута |

**Реализация (in-memory с TTL):**

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

### Хранение секретов

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

### HTTPS/TLS требования

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

**Настройка в nginx:**

```nginx
server {
    listen 443 ssl http2;
    server_name bot.example.com;

    ssl_certificate /etc/letsencrypt/live/bot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.example.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Защита от повторной обработки платежей

```python
async def process_payment(invoice_id: str, robokassa_id: str):
    """
    Идемпотентная обработка платежа.
    """
    async with database.transaction():
        invoice = await Invoice.select_for_update(id=invoice_id)

        # Уже обработан — ничего не делаем
        if invoice.status == "paid":
            return {"status": "already_processed"}

        # Атомарное обновление
        invoice.status = "paid"
        invoice.robokassa_id = robokassa_id
        invoice.paid_at = datetime.utcnow()
        await invoice.save()

        # Начисление токенов
        await User.update(
            token_balance=User.token_balance + invoice.tokens
        ).where(User.id == invoice.user_id)

        # Запись транзакции
        await Transaction.create(
            user_id=invoice.user_id,
            type="topup",
            tokens_delta=invoice.tokens,
            invoice_id=invoice.id
        )

    return {"status": "success"}
```

---

## Архитектура webhook'ов

```
Робокасса                    Ваш сервер                    Telegram
    │                            │                            │
    │  POST /webhook/robokassa   │                            │
    │  (ResultURL)               │                            │
    │ ──────────────────────────>│                            │
    │                            │  1. Проверка подписи       │
    │                            │  2. Обновление invoice     │
    │                            │  3. Начисление токенов/    │
    │                            │     продление подписки     │
    │                            │  4. Запись в transactions  │
    │                            │                            │
    │                            │  sendMessage (уведомление) │
    │                            │ ──────────────────────────>│
    │                            │                            │
    │<── OK ─────────────────────│                            │
```

---

## Фасад: Docusaurus

Проект включает веб-фасад на базе **Docusaurus** — статический сайт с двумя основными разделами:

### Лендинг
- Описание сервиса и его возможностей
- Тарифы и цены
- FAQ
- Кнопка перехода в Telegram-бот

### Документация
- Быстрый старт для пользователей
- Описание команд бота
- API-документация (если предусмотрен внешний API)
- Гайды по интеграции для разработчиков, использующих шаблон

### Структура Docusaurus

```
docs/
├── docusaurus.config.js
├── src/
│   └── pages/
│       └── index.tsx          # Лендинг
├── docs/
│   ├── intro.md               # Быстрый старт
│   ├── commands.md            # Команды бота
│   ├── billing.md             # Система биллинга
│   ├── webhooks.md            # Настройка webhook'ов
│   └── customization.md       # Кастомизация шаблона
└── static/
    └── img/
```

---

## Стек технологий

### Backend (Python)

| Компонент | Технология |
|-----------|------------|
| Telegram Bot | **aiogram 3.x** |
| HTTP API / Webhooks | **FastAPI** |
| ORM | **SQLAlchemy 2.x** (async) |
| База данных | **PostgreSQL** |
| Миграции | **Alembic** |

> **Примечание:** Pydantic v2 устанавливается автоматически как зависимость aiogram и FastAPI.

> **Почему aiogram?**
> - Полностью асинхронный (asyncio native)
> - Встроенная FSM для сложных диалогов
> - Отличная типизация с Pydantic
> - Активное сообщество и быстрые обновления под новый Bot API
> - Бесшовная интеграция с FastAPI
>
> Подробное сравнение с альтернативами: [telegram-frameworks-comparison.md](telegram-frameworks-comparison.md)

### Frontend

| Компонент | Технология |
|-----------|------------|
| Лендинг + Docs | **Docusaurus 3.x** (React/TypeScript) |

### Деплой

- **Docker** + **docker-compose**
- Опционально: CI/CD через GitHub Actions

---

## Структура проекта

```
telegram-billing-template/
├── backend/                    # Python или Node.js
│   ├── src/
│   │   ├── bot/                # Telegram-бот
│   │   ├── api/                # HTTP endpoints + webhooks
│   │   ├── services/           # Бизнес-логика (billing, users)
│   │   ├── models/             # Модели БД
│   │   └── config/             # Конфигурация
│   ├── migrations/
│   ├── Dockerfile
│   └── requirements.txt / package.json
│
├── docs/                       # Docusaurus
│   ├── docusaurus.config.js
│   ├── src/
│   ├── docs/
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Быстрый старт

```bash
# Клонировать репозиторий
git clone https://github.com/your-org/telegram-billing-template.git
cd telegram-billing-template

# Скопировать переменные окружения
cp .env.example .env

# Заполнить .env:
# - TELEGRAM_BOT_TOKEN
# - ROBOKASSA_LOGIN, ROBOKASSA_PASSWORD1, ROBOKASSA_PASSWORD2
# - DATABASE_URL

# Запустить
docker-compose up -d
```

---

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `ROBOKASSA_LOGIN` | Логин магазина в Робокассе |
| `ROBOKASSA_PASSWORD1` | Пароль #1 для формирования ссылки |
| `ROBOKASSA_PASSWORD2` | Пароль #2 для проверки webhook'ов |
| `DATABASE_URL` | Строка подключения к PostgreSQL |
| `WEBHOOK_BASE_URL` | Публичный URL сервера для webhook'ов |

---

## Лицензия

MIT

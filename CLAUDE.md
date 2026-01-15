# CLAUDE.md

## Overview

**Telegram Billing Template** — SaaS: Telegram-бот + Robokassa.
**Статус:** M1-M10 done, deployed. M6/M11 not started.

## Stack

Python: aiogram 3.x, FastAPI, SQLAlchemy 2.x async, PostgreSQL, Alembic
Frontend: Docusaurus 3.x | Deploy: Docker

## Structure

```
backend/src/
├── bot/           # handlers/, callbacks/, keyboards/, states/, middlewares/
├── api/           # routes/ (webhook, tokens, health), middleware/, schemas/
├── services/      # billing, payment, subscription, token, promo, notification
├── db/            # models/, repositories/, session.py
├── payments/      # providers/mock/
├── tasks/         # subscription_tasks.py
└── core/          # config, logging, exceptions
```

## Flow

`/start` → `/buy` → Tariff → Invoice → Payment → Webhook → Tokens/Subscription

## Robokassa

Init: `MD5(Login:Sum:InvId:Pass1)` | Webhook: `MD5(Sum:InvId:Pass2:Shp_*)` → `OK{InvId}`

## Env

`TELEGRAM_BOT_TOKEN` `DATABASE_URL` `WEBHOOK_BASE_URL` `ROBOKASSA_*` (LOGIN, PASS1, PASS2, IS_TEST)

## Local Dev

PostgreSQL: `localhost:5432` user `postgres` db `telegram_billing`
Path: `C:\Program Files\PostgreSQL\17\bin\`

## Docs

- [docs/index.md](docs/index.md) — навигация
- [docs/modules/](docs/modules/) — реализованные модули (database, bot, tariffs, payments, billing, promo, subscriptions, docker)
- [docs/architecture.md](docs/architecture.md) — схема БД
- [milestones/index.md](milestones/index.md) — план и статус

## Style

Docs: русский | Code: English

## Code Conventions

### SQLAlchemy Enums
При создании PostgreSQL enum в SQLAlchemy **всегда** используй `values_callable` для синхронизации значений между Python и PostgreSQL:

```python
from sqlalchemy import Enum as SQLEnum

class MyEnum(str, Enum):
    VALUE_ONE = "value_one"  # name=VALUE_ONE, value=value_one

# ПРАВИЛЬНО: используем values из Python enum
period_unit: Mapped[MyEnum] = mapped_column(
    SQLEnum(MyEnum, name="my_enum", values_callable=lambda x: [e.value for e in x]),
    ...
)

# В миграции тоже lowercase:
sa.Enum("value_one", "value_two", name="my_enum")
```

Это гарантирует, что:
- В PostgreSQL хранятся lowercase значения (`value_one`)
- SQLAlchemy корректно маппит их на Python enum члены (`MyEnum.VALUE_ONE`)

## Related Projects

### Runner (`d:/Sources/Cursor/runner`)
HHH Runner — сервис выполнения AI-треков для анализа CV и генерации откликов.

**Важно:** Claude работает только с кодом проекта **pays** (бот). Для проекта **runner** Claude готовит только **спецификации** (API endpoints, форматы данных, изменения в треках). Реализация в runner выполняется отдельно.

**Runner API:**
- `POST /api/cv/enhance` — анализ CV
- `POST /api/vacancy/apply` — генерация отклика
- `POST /api/constructor-user` — загрузка пользовательского конструктора
- `GET /api/constructor-user` — получение конструктора
- `DELETE /api/constructor-user` — удаление пользовательского конструктора

# CLAUDE.md

## Overview

**Telegram Billing Template** — SaaS-шаблон: Telegram-бот + Robokassa.
Статус: только документация, кода нет.

## Stack

**Backend:** Python, aiogram 3.x, FastAPI, SQLAlchemy 2.x (async), PostgreSQL, Alembic
**Frontend:** Docusaurus 3.x, React, Tailwind CSS
**Deploy:** Docker + docker-compose

## Structure

```
backend/src/
├── payments/          # router.py (webhooks), service.py, providers/robokassa/
├── models/            # users, invoices, transactions, tariffs
└── bot/               # Telegram handlers
```

**Flow:** `/pay` → Invoice → Robokassa → Webhook → Credit tokens

## Robokassa Signatures

| Operation | Formula |
|-----------|---------|
| Init | `MD5(MerchantLogin:OutSum:InvId:Password_1)` |
| Webhook | `MD5(OutSum:InvId:Password_2:Shp_*)` (Shp_* sorted) |

Response: `OK{InvId}` · Test: `IsTest=1`

## Env

`TELEGRAM_BOT_TOKEN` `ROBOKASSA_MERCHANT_LOGIN` `ROBOKASSA_PASSWORD_1` `ROBOKASSA_PASSWORD_2` `ROBOKASSA_IS_TEST` `DATABASE_URL` `WEBHOOK_BASE_URL`

## Docs

### Main

| Doc | Description |
|-----|-------------|
| [docs/index.md](docs/index.md) | Навигация по всей документации |
| [docs/overview.md](docs/overview.md) | Обзор проекта, стек, структура |
| [docs/architecture.md](docs/architecture.md) | Схема БД, жизненные циклы |

### Components

| Doc | Description |
|-----|-------------|
| [docs/bot.md](docs/bot.md) | Telegram-бот, команды, aiogram |
| [docs/robokassa-adapter.md](docs/robokassa-adapter.md) | Платёжная интеграция |
| [docs/docusaurus.md](docs/docusaurus.md) | Лендинг и пользовательская документация |

### Operations

| Doc | Description |
|-----|-------------|
| [docs/security.md](docs/security.md) | Валидация, rate limiting, HTTPS |
| [docs/deployment.md](docs/deployment.md) | Docker, nginx, env |

### References

| Doc | Description |
|-----|-------------|
| [docs/robokassa/](docs/robokassa/) | Справочник Robokassa API |
| [docs/roles/](docs/roles/) | Роли для AI-ассистентов |

### Key Roles for AI

| Role | File |
|------|------|
| Technical Writer | [docs/roles/technical-writer.md](docs/roles/technical-writer.md) |
| Fullstack Developer | [docs/roles/fullstack-developer.md](docs/roles/fullstack-developer.md) |
| System Analyst | [docs/roles/system-analyst.md](docs/roles/system-analyst.md) |

### Milestones

| Doc | Description |
|-----|-------------|
| [milestones/index.md](milestones/index.md) | План реализации по этапам |

## Terminology

| Short | Full |
|-------|------|
| M1, M2, ... | Milestone 1, Milestone 2, ... (этапы реализации) |

## Style

- Docs: русский
- Code & comments: English

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

- **Main:** [overview](docs/overview.md), [architecture](docs/architecture.md)
- **Components:** [bot](docs/bot.md), [robokassa-adapter](docs/robokassa-adapter.md), [docusaurus](docs/docusaurus.md)
- **Ops:** [security](docs/security.md), [deployment](docs/deployment.md)
- **Ref:** [robokassa/](docs/robokassa/), [telegram-frameworks-comparison](docs/telegram-frameworks-comparison.md)

## Style

- Docs: русский
- Code & comments: English

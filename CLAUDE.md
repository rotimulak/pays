# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains documentation and architecture specifications for **Telegram Billing Template** — a microservice template for SaaS products with monetization through Telegram bots using Robokassa payment processing.

**Current state:** Documentation and architecture specs only (no implementation code yet).

## Planned Technology Stack

### Backend (Python)
- **aiogram 3.x** — Telegram bot framework (async, FSM built-in)
- **FastAPI** — HTTP API and webhooks
- **SQLAlchemy 2.x** (async) — ORM
- **PostgreSQL** — Database
- **Alembic** — Migrations
- **Pydantic v2** — Data validation (dependency of aiogram/FastAPI)

### Frontend
- **Docusaurus 3.x** — Landing page and documentation

### Deployment
- Docker + docker-compose

## Architecture

### Payment Integration Pattern
Robokassa is integrated as a **modular adapter** within the backend service (not a separate microservice). The adapter implements the `PaymentProvider` abstract interface for extensibility.

```
backend/src/
├── payments/
│   ├── router.py          # API endpoints (webhooks)
│   ├── service.py         # Payment business logic
│   └── providers/
│       ├── base.py        # Abstract PaymentProvider interface
│       └── robokassa/     # Robokassa adapter implementation
├── models/
│   ├── invoice.py         # Invoice model (pending/paid/cancelled/expired)
│   └── transaction.py     # Transaction model (topup/spend/subscription/refund)
└── bot/                   # Telegram bot handlers
```

### Database Models
- **users** — Telegram user with `token_balance`, `subscription_end`
- **invoices** — Payment invoices with status lifecycle
- **transactions** — Token balance changes
- **tariffs** — Subscription plans

### Key Flows
1. **Payment Flow:** User → Bot `/pay` → Create invoice → Redirect to Robokassa → Webhook callback → Credit tokens/extend subscription
2. **Subscription Auto-Renewal:** Check `subscription_end` → Deduct tokens if sufficient → Extend subscription

## Robokassa Integration Notes

### Signature Calculation
- **Payment init:** `MD5(MerchantLogin:OutSum:InvId:Password_1)`
- **Webhook verification:** `MD5(OutSum:InvId:Password_2:Shp_*)`
- Custom `Shp_*` params must be sorted alphabetically in signature

### Webhook Response
ResultURL callback expects plain text response: `OK{InvId}` (e.g., `OK12345`)

### Test Mode
Add `IsTest=1` parameter and use test passwords from Robokassa dashboard.

## Documentation Structure

### Main Documentation
- [docs/index.md](docs/index.md) — Documentation index
- [docs/overview.md](docs/overview.md) — Project overview, tech stack, quick start
- [docs/architecture.md](docs/architecture.md) — Database schema, lifecycle diagrams

### Components
- [docs/bot.md](docs/bot.md) — Telegram bot commands and structure
- [docs/robokassa-adapter.md](docs/robokassa-adapter.md) — Robokassa payment integration
- [docs/docusaurus.md](docs/docusaurus.md) — Landing page and docs facade

### Operations
- [docs/security.md](docs/security.md) — Validation, rate limiting, secrets, HTTPS
- [docs/deployment.md](docs/deployment.md) — Docker, environment variables, nginx

### Reference
- [docs/robokassa/](docs/robokassa/) — Robokassa API documentation
  - [overview.md](docs/robokassa/overview.md) — API methods and parameters
  - [architecture.md](docs/robokassa/architecture.md) — Integration architecture with code examples
- [docs/telegram-frameworks-comparison.md](docs/telegram-frameworks-comparison.md) — Comparison of aiogram, grammY, Telegraf

### Legacy
- [docs/telegram-billing-template.md](docs/telegram-billing-template.md) — Original monolithic specification (deprecated)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `ROBOKASSA_MERCHANT_LOGIN` | Shop identifier |
| `ROBOKASSA_PASSWORD_1` | Payment initialization password |
| `ROBOKASSA_PASSWORD_2` | Webhook verification password |
| `ROBOKASSA_IS_TEST` | Enable test mode |
| `DATABASE_URL` | PostgreSQL connection string |
| `WEBHOOK_BASE_URL` | Public URL for webhooks |

## Language

All documentation is in Russian. Code comments and variable names should use English.

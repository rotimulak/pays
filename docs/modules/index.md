# Модули

Документация по реализованным модулям системы.

---

## Реализовано

| Модуль | Milestone | Описание |
|--------|-----------|----------|
| [Database](./database.md) | M1 | Модели, миграции, репозитории |
| [Bot](./bot.md) | M2 | Telegram-бот, handlers, keyboards |
| [Tariffs](./tariffs.md) | M3 | Тарифы и счета |
| [Payments](./payments.md) | M4 | Mock-провайдер, webhooks |
| [Billing](./billing.md) | M5 | Биллинг, транзакции, уведомления |
| [Promo Codes](./promo-codes.md) | M7 | Промокоды, скидки, бонусы |
| [Bot Cost Tracking Integration](./bot-cost-tracking-integration.md) | M8 | Спецификация Runner Framework track_cost event |
| [Track Cost Integration](./track-cost-integration.md) | M8 | Динамический учет стоимости треков с мультипликатором |
| [Trial Tariff](./trial-tariff.md) | M8 | Пробный тариф с нулевой ценой |
| [Subscriptions](./subscriptions.md) | M9 | Автопродление, уведомления об истечении |
| [Docker & Deploy](./docker.md) | M10 | Контейнеризация, health checks, logging |

---

## Граф зависимостей

```
┌──────────────┐
│   Database   │
└──────┬───────┘
       │
       v
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│     Bot      │<────│   Tariffs    │<────│ Promo Codes  │
└──────────────┘     └──────┬───────┘     └──────────────┘
       ^                    │
       │                    v
       │            ┌──────────────┐
       │            │   Payments   │
       │            └──────┬───────┘
       │                   │
       │                   v
       │            ┌──────────────┐     ┌───────────────┐
       └────────────│   Billing    │────>│ Subscriptions │
                    └──────────────┘     └───────────────┘
                           │
                           v
                    ┌──────────────┐
                    │    Docker    │ (deployment layer)
                    └──────────────┘
```

---

## Статус Milestones

| Milestone | Название | Статус |
|-----------|----------|--------|
| M1 | Core Models & Database | ✅ Done |
| M2 | Telegram Bot & Auth | ✅ Done |
| M3 | Tariffs & Invoices | ✅ Done |
| M4 | Mock Payment Provider | ✅ Done |
| M5 | Billing Flow | ✅ Done |
| M6 | Robokassa Provider | ⏭️ Skipped |
| M7 | Promo Codes | ✅ Done |
| M8 | Token Spending | ✅ Done |
| M9 | Subscription Management | ✅ Done |
| M10 | Docker & Deploy | ✅ Done |

---

## Что дальше

### M6: Robokassa Provider (Skipped)

- Интеграция реального платёжного провайдера Robokassa
- Можно активировать при необходимости
- Mock-провайдер достаточен для текущих нужд

### M11: Future Enhancements

- Расширенная аналитика треков
- Детальная статистика по узлам
- Лимиты расходов пользователей

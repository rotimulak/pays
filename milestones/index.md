# Milestones — План реализации

## Обзор

Пошаговый план реализации Telegram Billing Template. Каждый milestone — законченный этап с работающей функциональностью.

---

## Roadmap

| # | Milestone | Результат | Зависимости | Декомпозиция |
|---|-----------|-----------|-------------|--------------|
| M1 | [Core Models & DB](m1-core-models-and-db.md) | БД, модели, миграции | — | [📋 Epics & Tasks](m1/) |
| M2 | [Telegram Bot & Auth](m2-telegram-bot-auth.md) | Бот с авторизацией | M1 | [📋 Epics & Tasks](m2/) |
| M3 | [Tariffs & Invoices](m3-tariffs-and-invoices.md) | Выбор тарифа, создание счёта | M2 | [📋 Epics & Tasks](m3/) |
| M4 | [Mock Payment Provider](m4-mock-payment-provider.md) | Mock платёжная система | M3 | [📋 Epics & Tasks](m4/) |
| M5 | [Billing Flow](m5-billing-flow.md) | Полный цикл оплаты | M4 | [📋 Epics & Tasks](m5/) |
| M6 | [Robokassa Provider](m6-robokassa-provider.md) | Реальные платежи | M5 | [📋 Epics & Tasks](m6/) |
| M7 | [Promo Codes](m7-promo-codes.md) | Промокоды и скидки | M5 | [📋 Epics & Tasks](m7/) |
| M8 | [Token Spending](m8-token-spending.md) | Расходование токенов | M5 | [📋 Epics & Tasks](m8/) |
| M9 | [Subscription Management](m9-subscription-management.md) | Автопродление, уведомления | M8 | [📋 Epics & Tasks](m9/) |
| M10 | [Docker & Deploy](m10-docker-and-deploy.md) | Production-ready деплой | M9 | — |

---

## Диаграмма зависимостей

```
M1 ──> M2 ──> M3 ──> M4 ──> M5 ──┬──> M6
                                 │
                                 ├──> M7
                                 │
                                 └──> M8 ──> M9 ──> M10
```

---

## Принципы

1. **Инкрементальность** — каждый milestone добавляет ценность
2. **Тестируемость** — после каждого этапа можно проверить результат
3. **Mock-first** — сначала mock-реализация, потом реальная интеграция
4. **Независимость** — M6, M7, M8 можно делать параллельно после M5

---

## Статус

| Milestone | Статус |
|-----------|--------|
| M1 | 🔲 Not started |
| M2 | 🔲 Not started |
| M3 | 🔲 Not started |
| M4 | 🔲 Not started |
| M5 | 🔲 Not started |
| M6 | 🔲 Not started |
| M7 | 🔲 Not started |
| M8 | 🔲 Not started |
| M9 | 🔲 Not started |
| M10 | 🔲 Not started |

Легенда: 🔲 Not started | 🔄 In progress | ✅ Done

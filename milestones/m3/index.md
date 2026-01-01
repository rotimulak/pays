# M3: Tariffs & Invoices

## Обзор

Пользователь может просматривать тарифы и создавать счета на оплату. Invoice создаётся в статусе `pending` и готов к оплате.

---

## Epics & Tasks

| Epic | Задачи | Оценка |
|------|--------|--------|
| [E3.1 — Repositories](e3.1-repositories.md) | Invoice и Transaction repositories | 2 tasks |
| [E3.2 — Services](e3.2-services.md) | Tariff и Invoice services | 2 tasks |
| [E3.3 — Bot Handlers](e3.3-bot-handlers.md) | /tariffs и выбор тарифа | 2 tasks |
| [E3.4 — Keyboards & Callbacks](e3.4-keyboards-callbacks.md) | Inline keyboards и callback data | 3 tasks |
| [E3.5 — Seed Data](e3.5-seed-data.md) | Тестовые тарифы | 1 task |

---

## Definition of Done

- [ ] `/tariffs` показывает список активных тарифов
- [ ] При выборе тарифа создаётся invoice в статусе `pending`
- [ ] Invoice имеет уникальный idempotency_key
- [ ] Повторный выбор того же тарифа за короткое время возвращает существующий pending invoice
- [ ] Invoice содержит корректные tokens и subscription_days из тарифа
- [ ] Пользователь видит сумму и кнопку "Оплатить"
- [ ] Unit-тесты для invoice_service
- [ ] `mypy --strict` без ошибок

---

## Зависимости

- M2: Telegram Bot & Auth

## Разблокирует

- M4: Mock Payment Provider

# M3: Tariffs & Invoices

## Цель

Пользователь может просматривать тарифы и создавать счета на оплату. Invoice создаётся в статусе `pending` и готов к оплате.

---

## Задачи

### 3.1 Repositories

- [ ] `db/repositories/invoice_repository.py` — create, get_by_id, get_by_idempotency_key, update_status
- [ ] `db/repositories/transaction_repository.py` — create, get_by_user

### 3.2 Services

- [ ] `services/tariff_service.py` — get_active_tariffs, get_tariff_by_slug
- [ ] `services/invoice_service.py` — create_invoice (с idempotency_key), get_user_invoices

### 3.3 Bot Handlers

- [ ] `bot/handlers/tariffs.py` — `/tariffs` показывает список тарифов с inline-кнопками
- [ ] `bot/handlers/buy.py` — выбор тарифа → создание invoice → показ ссылки на оплату (mock)

### 3.4 Keyboards

- [ ] `bot/keyboards/tariffs.py` — inline keyboard с тарифами
- [ ] `bot/keyboards/payment.py` — кнопка "Оплатить" (ссылка)

### 3.5 CallbackData

- [ ] `bot/callbacks/tariff.py` — TariffCallback для выбора тарифа

### 3.6 Seed Data

- [ ] Скрипт/миграция для создания тестовых тарифов

---

## Definition of Done (DoD)

- [ ] `/tariffs` показывает список активных тарифов
- [ ] При выборе тарифа создаётся invoice в статусе `pending`
- [ ] Invoice имеет уникальный idempotency_key
- [ ] Повторный выбор того же тарифа за короткое время возвращает существующий pending invoice
- [ ] Invoice содержит корректные tokens и subscription_days из тарифа
- [ ] Пользователь видит сумму и кнопку "Оплатить"
- [ ] Unit-тесты для invoice_service
- [ ] `mypy --strict` без ошибок

---

## Артефакты

```
backend/src/
├── db/repositories/
│   ├── invoice_repository.py
│   └── transaction_repository.py
├── services/
│   ├── tariff_service.py
│   └── invoice_service.py
├── bot/
│   ├── handlers/
│   │   ├── tariffs.py
│   │   └── buy.py
│   ├── keyboards/
│   │   ├── tariffs.py
│   │   └── payment.py
│   └── callbacks/
│       └── tariff.py
└── scripts/
    └── seed_tariffs.py
```

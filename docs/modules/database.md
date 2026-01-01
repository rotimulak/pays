# Database Layer

> Модели данных, миграции и репозитории для работы с PostgreSQL.

## Сущности

### User

Пользователь Telegram-бота.

**Состояния:** active | blocked

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | BIGINT, PK | Telegram user_id |
| `username` | VARCHAR(255), nullable | Telegram username |
| `first_name` | VARCHAR(255), nullable | Имя |
| `last_name` | VARCHAR(255), nullable | Фамилия |
| `token_balance` | INTEGER, default 0 | Баланс токенов |
| `balance_version` | INTEGER, default 0 | Версия для optimistic locking |
| `subscription_end` | TIMESTAMP, nullable | Окончание подписки |
| `is_blocked` | BOOLEAN, default false | Пользователь заблокирован |
| `created_at` | TIMESTAMP | Время создания |
| `updated_at` | TIMESTAMP | Время обновления |

**Constraints:**
- CHECK: `token_balance >= 0`

**Связи:**
- `invoices` — счета пользователя
- `transactions` — транзакции токенов

---

### Tariff

Тарифный план.

**Состояния:** active | inactive (soft delete через `is_active`)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID, PK | Идентификатор |
| `slug` | VARCHAR(50), unique | URL-friendly имя |
| `name` | VARCHAR(100) | Название |
| `description` | TEXT, nullable | Описание |
| `price` | DECIMAL(10,2) | Цена в рублях |
| `tokens` | INTEGER | Количество токенов |
| `subscription_days` | INTEGER, default 0 | Дней подписки |
| `sort_order` | INTEGER, default 0 | Порядок сортировки |
| `is_active` | BOOLEAN, default true | Доступен для покупки |
| `version` | INTEGER, default 1 | Версия для истории |
| `created_at` | TIMESTAMP | Время создания |
| `updated_at` | TIMESTAMP | Время обновления |

**Constraints:**
- CHECK: `price > 0`
- CHECK: `tokens >= 0`
- CHECK: `subscription_days >= 0`
- UNIQUE: `slug`

---

### Invoice

Счёт на оплату.

**Состояния:** pending → paid | expired | cancelled | refunded

```
pending ──┬──> paid
          ├──> expired (TTL 24h)
          ├──> cancelled (user)
          └──> refunded (admin)
```

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID, PK | Идентификатор |
| `inv_id` | BIGINT, unique | ID для Robokassa |
| `user_id` | BIGINT, FK | Пользователь |
| `tariff_id` | UUID, FK | Тариф |
| `promo_code_id` | UUID, FK, nullable | Промокод |
| `amount` | DECIMAL(10,2) | Сумма к оплате |
| `original_amount` | DECIMAL(10,2) | Сумма до скидки |
| `tokens` | INTEGER | Токенов к начислению |
| `subscription_days` | INTEGER | Дней подписки |
| `status` | ENUM | pending, paid, expired, cancelled, refunded |
| `idempotency_key` | VARCHAR(255), unique | Ключ идемпотентности |
| `payment_url` | TEXT, nullable | URL оплаты |
| `paid_at` | TIMESTAMP, nullable | Время оплаты |
| `expires_at` | TIMESTAMP | Время истечения |
| `created_at` | TIMESTAMP | Время создания |
| `updated_at` | TIMESTAMP | Время обновления |

**Constraints:**
- CHECK: `amount > 0`
- FK: `user_id` → `users.id`
- FK: `tariff_id` → `tariffs.id`

**Индексы:**
- `idx_invoices_user_id`
- `idx_invoices_status`
- `idx_invoices_idempotency_key`
- `idx_invoices_inv_id`
- `idx_invoices_expires_at_pending` (partial)

---

### Transaction

Транзакция токенов (аудит).

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID, PK | Идентификатор |
| `user_id` | BIGINT, FK | Пользователь |
| `type` | ENUM | topup, spend, refund, adjustment |
| `tokens_delta` | INTEGER | Изменение баланса (+/-) |
| `balance_after` | INTEGER | Баланс после транзакции |
| `description` | TEXT, nullable | Описание |
| `invoice_id` | UUID, FK, nullable | Связанный invoice |
| `metadata` | JSONB, nullable | Дополнительные данные |
| `created_at` | TIMESTAMP | Время создания |

**Индексы:**
- `idx_transactions_user_id`
- `idx_transactions_created_at`
- `idx_transactions_type`

---

### PromoCode

Промокод (заготовка для M7).

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID, PK | Идентификатор |
| `code` | VARCHAR(50), unique | Код промокода |
| `discount_type` | ENUM | percent, fixed |
| `discount_value` | DECIMAL(10,2) | Размер скидки |
| `max_uses` | INTEGER, nullable | Макс. использований |
| `uses_count` | INTEGER, default 0 | Текущее кол-во |
| `valid_from` | TIMESTAMP | Начало действия |
| `valid_until` | TIMESTAMP, nullable | Конец действия |
| `tariff_id` | UUID, FK, nullable | Ограничение на тариф |
| `is_active` | BOOLEAN, default true | Активен |

---

### AuditLog

Аудит-лог системных событий.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID, PK | Идентификатор |
| `user_id` | BIGINT, nullable | Пользователь |
| `action` | VARCHAR(100) | Действие |
| `entity_type` | VARCHAR(50) | Тип сущности |
| `entity_id` | VARCHAR(255), nullable | ID сущности |
| `old_value` | JSONB, nullable | Старое значение |
| `new_value` | JSONB, nullable | Новое значение |
| `metadata` | JSONB, nullable | Доп. данные |
| `created_at` | TIMESTAMP | Время создания |

---

## Repositories

### UserRepository

| Метод | Описание |
|-------|----------|
| `get_by_id(user_id)` | Получить по Telegram ID |
| `get_or_create(user_id, ...)` | Получить или создать |
| `update_balance(user_id, delta, expected_version)` | Обновить баланс с optimistic locking |
| `update_subscription(user_id, end_date)` | Обновить подписку |
| `update(user)` | Обновить поля |

**Optimistic Locking:**
```python
# При update_balance проверяется balance_version
# Если версия изменилась — конфликт, retry
```

---

### TariffRepository

| Метод | Описание |
|-------|----------|
| `get_by_id(tariff_id)` | Получить по UUID |
| `get_by_slug(slug)` | Получить по slug |
| `get_active()` | Активные тарифы (sorted by sort_order) |
| `create(tariff)` | Создать тариф |
| `deactivate(tariff_id)` | Soft delete |

---

### InvoiceRepository

| Метод | Описание |
|-------|----------|
| `get_by_id(invoice_id)` | Получить по UUID |
| `get_by_inv_id(inv_id)` | Получить по Robokassa ID |
| `get_by_idempotency_key(key)` | Получить по ключу идемпотентности |
| `get_pending_by_user(user_id, tariff_id)` | Pending invoice для user+tariff |
| `get_user_invoices(user_id, limit)` | История счетов |
| `get_next_inv_id()` | Следующий inv_id (sequence) |
| `create(invoice)` | Создать invoice |
| `update_status(invoice_id, status, paid_at)` | Обновить статус |
| `get_for_update(invoice_id)` | SELECT FOR UPDATE |
| `expire_old_pending(before)` | Истечь старые pending invoices |
| `get_expiring_invoices(before, limit)` | Получить истекающие invoices (dry-run) |

---

### TransactionRepository

| Метод | Описание |
|-------|----------|
| `create(transaction)` | Создать транзакцию |
| `get_by_id(transaction_id)` | Получить по UUID |
| `get_by_user(user_id, limit, offset, type_filter)` | История с пагинацией и фильтром |
| `get_by_invoice(invoice_id)` | Транзакции по invoice |
| `count_by_user(user_id, type_filter)` | Подсчёт транзакций |
| `get_user_stats(user_id)` | Агрегированная статистика |

---

## Файловая структура

```
backend/src/db/
├── __init__.py
├── session.py              # Engine, Session, Base
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── tariff.py
│   ├── invoice.py
│   ├── transaction.py
│   ├── promo_code.py
│   └── audit_log.py
└── repositories/
    ├── __init__.py
    ├── user_repository.py
    ├── tariff_repository.py
    ├── invoice_repository.py
    └── transaction_repository.py
```

---

## Зависимости

- **От:** —
- **Для:** [Bot](./bot.md), [Payments](./payments.md), [Billing](./billing.md)

# Архитектура

## Схема базы данных

```
┌─────────────────────────────────────────────────────────────────┐
│                           users                                 │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)           │ BIGINT        │ Telegram user_id            │
│ username          │ VARCHAR(255)  │ @username (nullable)        │
│ first_name        │ VARCHAR(255)  │ Имя                         │
│ token_balance     │ INT           │ Остаток токенов (>= 0)      │
│ deleted_at        │ TIMESTAMPTZ   │ Soft delete (nullable)      │
│ balance_version   │ INT           │ Версия для optimistic lock  │
│ subscription_end  │ TIMESTAMPTZ   │ Дата окончания подписки UTC │
│ created_at        │ TIMESTAMPTZ   │ DEFAULT now()               │
│ updated_at        │ TIMESTAMPTZ   │ DEFAULT now()               │
└─────────────────────────────────────────────────────────────────┘
Примечание: is_active вычисляется как subscription_end > now()

┌─────────────────────────────────────────────────────────────────┐
│                          invoices                               │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)           │ UUID          │ gen_random_uuid()           │
│ inv_id            │ BIGINT        │ UNIQUE, sequential for Robokassa │
│ user_id (FK)      │ BIGINT        │ → users.id                  │
│ tariff_id (FK)    │ UUID          │ → tariffs.id (nullable)     │
│ promo_code_id(FK) │ UUID          │ → promo_codes.id (nullable) │
│ amount            │ DECIMAL(10,2) │ Сумма в рублях (> 0)        │
│ amount_before_discount │ DECIMAL(10,2) │ Сумма до скидки        │
│ tokens            │ INT           │ Кол-во токенов (>= 0)       │
│ subscription_days │ INT           │ Дни подписки (>= 0)         │
│ status            │ ENUM          │ pending/paid/cancelled/expired │
│ idempotency_key   │ VARCHAR(64)   │ UNIQUE, защита от дублей    │
│ external_payment_id │ VARCHAR(255)│ ID операции Робокассы       │
│ expires_at        │ TIMESTAMPTZ   │ TTL для pending → expired   │
│ created_at        │ TIMESTAMPTZ   │ DEFAULT now()               │
│ updated_at        │ TIMESTAMPTZ   │ DEFAULT now()               │
│ paid_at           │ TIMESTAMPTZ   │ Когда status стал paid      │
└─────────────────────────────────────────────────────────────────┘
CHECK: tokens > 0 OR subscription_days > 0
CHECK: tokens >= 0 AND subscription_days >= 0

┌─────────────────────────────────────────────────────────────────┐
│                        transactions                             │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)           │ UUID          │ gen_random_uuid()           │
│ user_id (FK)      │ BIGINT        │ → users.id                  │
│ type              │ ENUM          │ topup/spend/subscription/refund/bonus │
│ tokens_delta      │ INT           │ +/- токенов                 │
│ balance_after     │ INT           │ Баланс после операции       │
│ description       │ VARCHAR(500)  │ Причина списания/начисления │
│ invoice_id (FK)   │ UUID          │ → invoices.id (nullable)    │
│ metadata          │ JSONB         │ Доп. данные (nullable)      │
│ created_at        │ TIMESTAMPTZ   │ DEFAULT now()               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          tariffs                                │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)           │ UUID          │ gen_random_uuid()           │
│ slug              │ VARCHAR(50)   │ UNIQUE, basic_monthly       │
│ name              │ VARCHAR(100)  │ Название для пользователя   │
│ description       │ VARCHAR(500)  │ Описание тарифа (nullable)  │
│ price             │ DECIMAL(10,2) │ Цена (> 0)                  │
│ tokens            │ INT           │ Кол-во токенов (>= 0)       │
│ subscription_days │ INT           │ Дни подписки (>= 0)         │
│ sort_order        │ INT           │ Порядок отображения         │
│ is_active         │ BOOLEAN       │ DEFAULT true                │
│ version           │ INT           │ Версия тарифа (для истории) │
│ deleted_at        │ TIMESTAMPTZ   │ Soft delete (nullable)      │
│ created_at        │ TIMESTAMPTZ   │ DEFAULT now()               │
│ updated_at        │ TIMESTAMPTZ   │ DEFAULT now()               │
└─────────────────────────────────────────────────────────────────┘
CHECK: tokens > 0 OR subscription_days > 0
CHECK: tokens >= 0 AND subscription_days >= 0

┌─────────────────────────────────────────────────────────────────┐
│                        promo_codes                              │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)           │ UUID          │ gen_random_uuid()           │
│ code              │ VARCHAR(50)   │ UNIQUE, промокод            │
│ discount_type     │ ENUM          │ percent / fixed / bonus_tokens │
│ discount_value    │ DECIMAL(10,2) │ Значение скидки             │
│ max_uses          │ INT           │ Лимит использований (null=∞)│
│ uses_count        │ INT           │ Текущее кол-во использований│
│ valid_from        │ TIMESTAMPTZ   │ Начало действия             │
│ valid_until       │ TIMESTAMPTZ   │ Конец действия (nullable)   │
│ tariff_id (FK)    │ UUID          │ → tariffs.id (nullable=все) │
│ is_active         │ BOOLEAN       │ DEFAULT true                │
│ created_at        │ TIMESTAMPTZ   │ DEFAULT now()               │
│ updated_at        │ TIMESTAMPTZ   │ DEFAULT now()               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         audit_log                               │
├─────────────────────────────────────────────────────────────────┤
│ id (PK)           │ UUID          │ gen_random_uuid()           │
│ user_id (FK)      │ BIGINT        │ → users.id (nullable=system)│
│ action            │ VARCHAR(100)  │ invoice.created, payment.received │
│ entity_type       │ VARCHAR(50)   │ user, invoice, transaction  │
│ entity_id         │ VARCHAR(255)  │ ID затронутой сущности      │
│ old_value         │ JSONB         │ Предыдущее состояние        │
│ new_value         │ JSONB         │ Новое состояние             │
│ metadata          │ JSONB         │ IP, user_agent, etc         │
│ created_at        │ TIMESTAMPTZ   │ DEFAULT now()               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Constraints и индексы

### CHECK Constraints

```sql
-- users
ALTER TABLE users ADD CONSTRAINT chk_users_token_balance
  CHECK (token_balance >= 0);

-- invoices
ALTER TABLE invoices ADD CONSTRAINT chk_invoices_amount
  CHECK (amount > 0);
ALTER TABLE invoices ADD CONSTRAINT chk_invoices_has_product
  CHECK (tokens > 0 OR subscription_days > 0);
ALTER TABLE invoices ADD CONSTRAINT chk_invoices_non_negative
  CHECK (tokens >= 0 AND subscription_days >= 0);

-- tariffs
ALTER TABLE tariffs ADD CONSTRAINT chk_tariffs_price
  CHECK (price > 0);
ALTER TABLE tariffs ADD CONSTRAINT chk_tariffs_has_product
  CHECK (tokens > 0 OR subscription_days > 0);
ALTER TABLE tariffs ADD CONSTRAINT chk_tariffs_non_negative
  CHECK (tokens >= 0 AND subscription_days >= 0);

-- promo_codes
ALTER TABLE promo_codes ADD CONSTRAINT chk_promo_discount_value
  CHECK (discount_value > 0);
ALTER TABLE promo_codes ADD CONSTRAINT chk_promo_uses
  CHECK (uses_count >= 0);
ALTER TABLE promo_codes ADD CONSTRAINT chk_promo_max_uses
  CHECK (max_uses IS NULL OR max_uses > 0);
```

### Индексы

```sql
-- users
CREATE INDEX idx_users_subscription_end ON users(subscription_end)
  WHERE subscription_end IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX idx_users_active ON users(id)
  WHERE deleted_at IS NULL;

-- invoices
CREATE INDEX idx_invoices_user_id ON invoices(user_id);
CREATE UNIQUE INDEX idx_invoices_inv_id ON invoices(inv_id);
CREATE INDEX idx_invoices_status_created ON invoices(status, created_at)
  WHERE status = 'pending';
CREATE INDEX idx_invoices_expires_at ON invoices(expires_at)
  WHERE status = 'pending';
CREATE UNIQUE INDEX idx_invoices_idempotency ON invoices(idempotency_key);

-- transactions
CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_user_created ON transactions(user_id, created_at DESC);
CREATE INDEX idx_transactions_invoice_id ON transactions(invoice_id)
  WHERE invoice_id IS NOT NULL;

-- tariffs
CREATE INDEX idx_tariffs_active_sort ON tariffs(sort_order)
  WHERE is_active = true AND deleted_at IS NULL;

-- promo_codes
CREATE INDEX idx_promo_codes_valid ON promo_codes(valid_from, valid_until)
  WHERE is_active = true;

-- audit_log
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_created ON audit_log(created_at DESC);
```

### Foreign Keys

```sql
-- invoices
ALTER TABLE invoices ADD CONSTRAINT fk_invoices_user
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;
ALTER TABLE invoices ADD CONSTRAINT fk_invoices_tariff
  FOREIGN KEY (tariff_id) REFERENCES tariffs(id) ON DELETE SET NULL;
ALTER TABLE invoices ADD CONSTRAINT fk_invoices_promo
  FOREIGN KEY (promo_code_id) REFERENCES promo_codes(id) ON DELETE SET NULL;

-- transactions
ALTER TABLE transactions ADD CONSTRAINT fk_transactions_user
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT;
ALTER TABLE transactions ADD CONSTRAINT fk_transactions_invoice
  FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE SET NULL;

-- promo_codes
ALTER TABLE promo_codes ADD CONSTRAINT fk_promo_tariff
  FOREIGN KEY (tariff_id) REFERENCES tariffs(id) ON DELETE RESTRICT;

-- audit_log
ALTER TABLE audit_log ADD CONSTRAINT fk_audit_user
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL;
```

---

## State Machine: Invoice

### Состояния

| Состояние | Описание | Терминальное |
|-----------|----------|--------------|
| `pending` | Счёт создан, ожидает оплаты | Нет |
| `paid` | Оплата подтверждена через webhook | Да |
| `cancelled` | Отменён пользователем или системой | Да |
| `expired` | Истёк срок ожидания (TTL) | Да |

### Переходы

| Из | В | Событие | Guard (условие) | Action (действие) |
|----|---|---------|-----------------|-------------------|
| pending | paid | webhook_received | valid_signature AND status='pending' AND not_processed | credit_user, create_transaction, notify_user, log_audit |
| pending | cancelled | user_cancel | status='pending' | log_audit |
| pending | cancelled | admin_cancel | status='pending' | log_audit, notify_user |
| pending | expired | ttl_check | status='pending' AND expires_at < now() | log_audit |

### Диаграмма

```
                         user_cancel
                    ┌────────────────────────┐
                    │                        ▼
              ┌─────────┐              ┌───────────┐
  create ───> │ pending │─────────────>│ cancelled │
              └────┬────┘              └───────────┘
                   │                         ▲
                   │ webhook_received        │ admin_cancel
                   ▼                         │
              ┌─────────┐                    │
              │  paid   │                    │
              └─────────┘                    │
                                             │
              ┌─────────┐                    │
              │ expired │<───── ttl_check ───┘
              └─────────┘      (cron job)
```

### Бизнес-правила

1. **Идемпотентность**: Повторный webhook с тем же `idempotency_key` игнорируется
2. **TTL**: Pending invoice переходит в expired через 30 минут (настраивается)
3. **Защита от double-spend**: Проверка `status='pending'` в транзакции БД
4. **Аудит**: Все переходы логируются в `audit_log`

---

## State Machine: Subscription

### Состояния

| Состояние | Описание | Терминальное |
|-----------|----------|--------------|
| `none` | Пользователь без подписки (новый) | Нет |
| `active` | Подписка активна (subscription_end > now) | Нет |
| `expired` | Подписка истекла | Нет |

### Переходы

| Из | В | Событие | Guard (условие) | Action (действие) |
|----|---|---------|-----------------|-------------------|
| none | active | payment_received | invoice.paid AND subscription_days > 0 | set_subscription_end, create_transaction, notify_user |
| active | active | auto_renew | subscription_end <= now AND token_balance >= PRICE | deduct_tokens, extend_subscription, create_transaction, notify_user |
| active | expired | check_expiry | subscription_end <= now AND token_balance < PRICE | notify_user |
| expired | active | payment_received | invoice.paid AND subscription_days > 0 | set_subscription_end, create_transaction, notify_user |
| expired | active | manual_renew | token_balance >= PRICE | deduct_tokens, extend_subscription, create_transaction |

### Диаграмма

```
                    payment_received
              ┌─────────────────────────────┐
              │                             │
              ▼                             │
         ┌────────┐    payment_received    ┌─────────┐
         │  none  │ ────────────────────>  │ active  │
         └────────┘                        └────┬────┘
                                                │
                       ┌────────────────────────┤
                       │                        │
              auto_renew (sufficient balance)   │ check_expiry
                       │                        │ (insufficient balance)
                       │                        ▼
                       │                   ┌─────────┐
                       └───────────────────│ expired │
                                           └────┬────┘
                                                │
                       payment_received OR      │
                       manual_renew             │
                              ┌─────────────────┘
                              │
                              └────────> [active]
```

### Бизнес-правила

1. **Автопродление**: Cron-задача проверяет `subscription_end <= now()` и списывает токены
2. **Optimistic Lock**: При списании токенов проверяется `balance_version`
3. **Grace Period**: Опционально — 3 дня после истечения с ограниченным функционалом
4. **Уведомления**: За 3 дня и за 1 день до истечения подписки

---

## Логика списания токенов

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

---

## Типы транзакций

| Тип | Описание | tokens_delta | Источник |
|-----|----------|--------------|----------|
| `topup` | Пополнение баланса (оплата через Робокассу) | +N | invoice.paid |
| `spend` | Списание за рабочий запрос | -N | API request |
| `subscription` | Автосписание абонплаты с баланса | -PRICE | cron job |
| `refund` | Возврат средств | +N | admin action |
| `bonus` | Бонусное начисление (промокод, акция) | +N | promo_code |

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

## Спецификации сущностей

### Entity: users

#### Описание
Пользователь системы, идентифицируемый через Telegram user_id.

#### Атрибуты

| Атрибут | Тип | Nullable | Default | Описание |
|---------|-----|----------|---------|----------|
| id | BIGINT | No | — | PK, Telegram user_id |
| username | VARCHAR(255) | Yes | NULL | @username в Telegram |
| first_name | VARCHAR(255) | No | — | Имя пользователя |
| token_balance | INT | No | 0 | Текущий баланс токенов |
| balance_version | INT | No | 1 | Версия для optimistic locking |
| subscription_end | TIMESTAMPTZ | Yes | NULL | Дата окончания подписки (UTC) |
| deleted_at | TIMESTAMPTZ | Yes | NULL | Soft delete timestamp |
| created_at | TIMESTAMPTZ | No | now() | Дата создания |
| updated_at | TIMESTAMPTZ | No | now() | Дата последнего обновления |

#### Ограничения
- PK: id
- CHECK: token_balance >= 0

#### Soft Delete
- При "удалении" пользователя устанавливается `deleted_at = now()`
- Все запросы фильтруют `WHERE deleted_at IS NULL`

#### Индексы
- idx_users_subscription_end — для cron-задач по истечению подписок

#### Вычисляемые поля
- `is_active`: subscription_end IS NOT NULL AND subscription_end > now()

---

### Entity: invoices

#### Описание
Счёт на оплату, создаётся при инициации платежа пользователем.

#### Атрибуты

| Атрибут | Тип | Nullable | Default | Описание |
|---------|-----|----------|---------|----------|
| id | UUID | No | gen_random_uuid() | PK |
| inv_id | BIGINT | No | nextval('invoices_inv_id_seq') | Robokassa InvId (1-9223372036854775807) |
| user_id | BIGINT | No | — | FK → users.id |
| tariff_id | UUID | Yes | NULL | FK → tariffs.id |
| promo_code_id | UUID | Yes | NULL | FK → promo_codes.id |
| amount | DECIMAL(10,2) | No | — | Сумма к оплате (после скидки) |
| amount_before_discount | DECIMAL(10,2) | Yes | NULL | Сумма до применения скидки |
| tokens | INT | No | 0 | Кол-во токенов к начислению |
| subscription_days | INT | No | 0 | Дней подписки к начислению |
| status | ENUM | No | 'pending' | pending/paid/cancelled/expired |
| idempotency_key | VARCHAR(64) | No | — | Уникальный ключ для идемпотентности |
| external_payment_id | VARCHAR(255) | Yes | NULL | ID операции в Робокассе |
| expires_at | TIMESTAMPTZ | No | — | Когда invoice станет expired |
| created_at | TIMESTAMPTZ | No | now() | Дата создания |
| updated_at | TIMESTAMPTZ | No | now() | Дата последнего обновления |
| paid_at | TIMESTAMPTZ | Yes | NULL | Дата оплаты |

#### Ограничения
- PK: id
- UK: idempotency_key
- UK: inv_id
- FK: user_id → users.id (ON DELETE RESTRICT)
- FK: tariff_id → tariffs.id (ON DELETE SET NULL)
- FK: promo_code_id → promo_codes.id (ON DELETE SET NULL)
- CHECK: amount > 0
- CHECK: tokens > 0 OR subscription_days > 0
- CHECK: tokens >= 0 AND subscription_days >= 0

#### Индексы
- idx_invoices_user_id — поиск по пользователю
- idx_invoices_inv_id — поиск по Robokassa InvId
- idx_invoices_status_created — для обработки pending
- idx_invoices_expires_at — для cron-задачи по истечению

---

### Entity: transactions

#### Описание
Журнал всех операций с балансом токенов пользователя.

#### Атрибуты

| Атрибут | Тип | Nullable | Default | Описание |
|---------|-----|----------|---------|----------|
| id | UUID | No | gen_random_uuid() | PK |
| user_id | BIGINT | No | — | FK → users.id |
| type | ENUM | No | — | topup/spend/subscription/refund/bonus |
| tokens_delta | INT | No | — | Изменение баланса (+/-) |
| balance_after | INT | No | — | Баланс после операции |
| description | VARCHAR(500) | Yes | NULL | Причина операции |
| invoice_id | UUID | Yes | NULL | FK → invoices.id |
| metadata | JSONB | Yes | NULL | Дополнительные данные |
| created_at | TIMESTAMPTZ | No | now() | Дата операции |

#### Ограничения
- PK: id
- FK: user_id → users.id (ON DELETE RESTRICT)
- FK: invoice_id → invoices.id (ON DELETE SET NULL)

#### Индексы
- idx_transactions_user_id — все транзакции пользователя
- idx_transactions_user_created — история с сортировкой
- idx_transactions_invoice_id — связь с invoice

---

### Entity: tariffs

#### Описание
Тарифные планы для покупки токенов и подписок.

#### Атрибуты

| Атрибут | Тип | Nullable | Default | Описание |
|---------|-----|----------|---------|----------|
| id | UUID | No | gen_random_uuid() | PK |
| slug | VARCHAR(50) | No | — | Уникальный идентификатор (basic_monthly) |
| name | VARCHAR(100) | No | — | Название для пользователя |
| description | VARCHAR(500) | Yes | NULL | Описание тарифа |
| price | DECIMAL(10,2) | No | — | Цена в рублях |
| tokens | INT | No | 0 | Кол-во токенов |
| subscription_days | INT | No | 0 | Дней подписки |
| sort_order | INT | No | 0 | Порядок отображения |
| is_active | BOOLEAN | No | true | Доступен для покупки |
| version | INT | No | 1 | Версия тарифа |
| deleted_at | TIMESTAMPTZ | Yes | NULL | Soft delete timestamp |
| created_at | TIMESTAMPTZ | No | now() | Дата создания |
| updated_at | TIMESTAMPTZ | No | now() | Дата обновления |

#### Ограничения
- PK: id
- UK: slug
- CHECK: price > 0
- CHECK: tokens > 0 OR subscription_days > 0
- CHECK: tokens >= 0 AND subscription_days >= 0

#### Soft Delete
- При "удалении" тарифа устанавливается `deleted_at = now()`
- Старые invoices продолжают ссылаться на тариф
- В списке для покупки показываются только `WHERE deleted_at IS NULL AND is_active = true`

#### Индексы
- idx_tariffs_active_sort — активные тарифы по порядку

#### Версионирование
При изменении цены создаётся новая версия тарифа. Старые invoices ссылаются на момент покупки.

---

### Entity: promo_codes

#### Описание
Промокоды для скидок и бонусных начислений.

#### Атрибуты

| Атрибут | Тип | Nullable | Default | Описание |
|---------|-----|----------|---------|----------|
| id | UUID | No | gen_random_uuid() | PK |
| code | VARCHAR(50) | No | — | Промокод (UPPER CASE) |
| discount_type | ENUM | No | — | percent/fixed/bonus_tokens |
| discount_value | DECIMAL(10,2) | No | — | Значение скидки |
| max_uses | INT | Yes | NULL | Лимит использований (NULL = ∞) |
| uses_count | INT | No | 0 | Текущее кол-во использований |
| valid_from | TIMESTAMPTZ | No | now() | Начало действия |
| valid_until | TIMESTAMPTZ | Yes | NULL | Конец действия (NULL = бессрочно) |
| tariff_id | UUID | Yes | NULL | FK → tariffs.id (NULL = все тарифы) |
| is_active | BOOLEAN | No | true | Активен ли промокод |
| created_at | TIMESTAMPTZ | No | now() | Дата создания |
| updated_at | TIMESTAMPTZ | No | now() | Дата последнего обновления |

#### Ограничения
- PK: id
- UK: code
- FK: tariff_id → tariffs.id (ON DELETE RESTRICT)
- CHECK: discount_value > 0
- CHECK: uses_count >= 0
- CHECK: max_uses IS NULL OR max_uses > 0

#### Индексы
- idx_promo_codes_valid — активные промокоды в периоде

#### Типы скидок
- `percent`: скидка в % от суммы (discount_value = 10 → 10%)
- `fixed`: фиксированная скидка в рублях
- `bonus_tokens`: дополнительные токены при покупке

---

### Entity: audit_log

#### Описание
Журнал аудита всех значимых действий в системе.

#### Атрибуты

| Атрибут | Тип | Nullable | Default | Описание |
|---------|-----|----------|---------|----------|
| id | UUID | No | gen_random_uuid() | PK |
| user_id | BIGINT | Yes | NULL | FK → users.id (NULL = system) |
| action | VARCHAR(100) | No | — | Тип действия |
| entity_type | VARCHAR(50) | No | — | Тип сущности |
| entity_id | VARCHAR(255) | No | — | ID затронутой сущности |
| old_value | JSONB | Yes | NULL | Предыдущее состояние |
| new_value | JSONB | Yes | NULL | Новое состояние |
| metadata | JSONB | Yes | NULL | IP, user_agent, etc |
| created_at | TIMESTAMPTZ | No | now() | Дата действия |

#### Ограничения
- PK: id
- FK: user_id → users.id (ON DELETE SET NULL)

#### Индексы
- idx_audit_log_user_id — действия пользователя
- idx_audit_log_entity — поиск по сущности
- idx_audit_log_created — хронология

#### Типы действий
- `invoice.created`, `invoice.paid`, `invoice.cancelled`, `invoice.expired`
- `user.created`, `user.balance_updated`, `user.subscription_renewed`
- `payment.received`, `payment.failed`
- `promo.applied`, `promo.rejected`

---

## Concurrency и идемпотентность

### Optimistic Locking для баланса

```sql
UPDATE users
SET token_balance = token_balance - :amount,
    balance_version = balance_version + 1,
    updated_at = now()
WHERE id = :user_id
  AND balance_version = :expected_version
  AND token_balance >= :amount;

-- Если affected_rows = 0 → retry или ошибка
```

### Идемпотентность webhook

```sql
-- При получении webhook
INSERT INTO invoices (..., idempotency_key, status)
VALUES (..., :idempotency_key, 'paid')
ON CONFLICT (idempotency_key) DO NOTHING;

-- Или проверка перед обработкой
SELECT status FROM invoices WHERE idempotency_key = :key;
-- Если status = 'paid' → уже обработано, вернуть OK
```

---

## См. также

- [Обзор](overview.md) — общее описание проекта
- [Интеграция с Робокассой](robokassa-adapter.md) — детали платёжной интеграции
- [Безопасность](security.md) — защита от повторной обработки платежей

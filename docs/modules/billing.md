# Billing

> Полный цикл биллинга: обработка платежей, начисление токенов/подписки, аудит, уведомления.

## Обзор

Модуль биллинга обрабатывает успешные платежи из webhook и выполняет:

1. Начисление токенов на баланс пользователя
2. Продление подписки
3. Запись транзакций
4. Аудит-логирование
5. Уведомления в Telegram

---

## Сервисы

### BillingService

Основной сервис обработки платежей.

| Метод | Описание |
|-------|----------|
| `process_successful_payment(invoice_id)` | Обработать успешный платёж |

**Алгоритм обработки:**

```
1. Получить invoice с блокировкой (FOR UPDATE)
2. Проверить идемпотентность (status != pending → return)
3. Начислить токены (если tokens > 0)
4. Продлить подписку (если subscription_days > 0)
5. Обновить статус invoice → PAID
6. Записать в audit_log
7. Отправить уведомление пользователю
```

**Идемпотентность:**

Повторный вызов webhook с тем же invoice игнорируется благодаря проверке статуса.

**Optimistic Locking:**

При начислении токенов используется `balance_version` для защиты от конкурентных обновлений.

---

### TransactionService

Сервис для работы с историей транзакций.

| Метод | Описание |
|-------|----------|
| `get_user_transactions(user_id, limit, offset)` | История с пагинацией |
| `get_user_stats(user_id)` | Агрегированная статистика |
| `create_transaction(...)` | Создать запись транзакции |

**TransactionDTO:**

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | Идентификатор |
| `type` | TransactionType | topup, spend, refund, adjustment |
| `type_display` | str | Локализованное название |
| `tokens_delta` | int | Изменение баланса |
| `tokens_delta_display` | str | "+100" или "-50" |
| `balance_after` | int | Баланс после транзакции |
| `created_at_display` | str | "01.02.2024 15:30" |

---

### AuditService

Сервис аудит-логирования системных событий.

| Метод | Описание |
|-------|----------|
| `log_action(action, entity_type, ...)` | Базовый метод логирования |
| `log_payment_processed(...)` | Успешный платёж |
| `log_user_created(...)` | Новый пользователь |
| `log_invoice_created(...)` | Создание счёта |
| `log_tokens_spent(...)` | Списание токенов |
| `log_invoices_expired(...)` | Пакетное истечение счетов |

**Формат записи:**

```json
{
  "action": "payment.processed",
  "entity_type": "invoice",
  "entity_id": "uuid",
  "user_id": 123456789,
  "old_value": {"token_balance": 0, "subscription_end": null},
  "new_value": {"token_balance": 100, "subscription_end": "2024-03-01T00:00:00"}
}
```

---

### NotificationService

Отправка уведомлений в Telegram.

| Метод | Описание |
|-------|----------|
| `notify_payment_success(user_id, invoice)` | Успешная оплата |
| `notify_subscription_expiring(user_id, days_left)` | Подписка истекает |
| `notify_subscription_expired(user_id)` | Подписка истекла |
| `notify_low_balance(user_id, balance, threshold)` | Низкий баланс |

**Обработка ошибок:**

- `TelegramForbiddenError` — пользователь заблокировал бота (логируется, не прерывает процесс)
- `TelegramBadRequest` — некорректный запрос (логируется)

---

## Bot Handlers

### /balance

Показывает текущий баланс и статус подписки.

```
Ваш баланс

Токены: 150
Подписка: активна до 01.03.2024
   Осталось 3 дня!

Статистика:
  Всего пополнено: 200 токенов
  Всего потрачено: 50 токенов

Пополнить: /tariffs
История: /history
```

### /history

История транзакций с пагинацией.

```
История транзакций

Пополнение
  +100 токенов -> 150
  01.02.2024 15:30

Списание
  -50 токенов -> 100
  28.01.2024 12:00

Страница 1 из 3

[< Назад] [Вперед >]
```

---

## Invoice Expiration

Скрипт для автоматического истечения неоплаченных счетов.

**Запуск:**

```bash
# С дефолтным TTL (24 часа)
python -m scripts.expire_invoices

# С кастомным TTL
python -m scripts.expire_invoices --ttl-hours 12

# Dry-run (показать что истечёт)
python -m scripts.expire_invoices --dry-run
```

**Cron setup:**

```bash
# Каждый час
0 * * * * cd /app && python -m scripts.expire_invoices
```

**Конфигурация:**

| Переменная | Default | Описание |
|------------|---------|----------|
| `INVOICE_TTL_HOURS` | 24 | Часов до истечения pending invoice |

---

## Файловая структура

```
backend/src/
├── services/
│   ├── billing_service.py      # Обработка платежей
│   ├── transaction_service.py  # История транзакций
│   ├── audit_service.py        # Аудит-логирование
│   ├── notification_service.py # Telegram уведомления
│   └── dto/
│       └── transaction.py      # DTO для транзакций
├── bot/
│   ├── handlers/
│   │   ├── balance.py          # /balance handler
│   │   └── history.py          # /history handler
│   └── callbacks/
│       └── pagination.py       # Callback для пагинации
└── scripts/
    └── expire_invoices.py      # Скрипт истечения счетов
```

---

## Поток данных

```
Webhook (ResultURL)
       │
       v
┌──────────────────┐
│  BillingService  │
│  .process_       │
│  successful_     │
│  payment()       │
└────────┬─────────┘
         │
    ┌────┼────┬────────────┐
    │    │    │            │
    v    v    v            v
┌──────┐ ┌──────┐ ┌──────┐ ┌──────────────┐
│Credit│ │Extend│ │Audit │ │Notification  │
│Tokens│ │Subscr│ │Log   │ │Service       │
└──────┘ └──────┘ └──────┘ └──────────────┘
    │         │       │            │
    v         v       v            v
 users     users   audit_logs   Telegram
(balance) (subscr)              message
```

---

## Зависимости

- **От:** [Database](./database.md), [Payments](./payments.md)
- **Для:** [Bot](./bot.md)

# Subscriptions

> Управление подписками: автопродление, уведомления об истечении, ручное продление.

## Обзор

Модуль управления подписками обеспечивает:

1. Автоматическое продление подписок с баланса токенов
2. Уведомления за N дней до истечения
3. Ручное продление через бота
4. Включение/отключение автопродления

---

## State Machine

```
              payment_received
         ┌────────────────────────┐
         │                        │
         v                        │
    ┌────────┐    payment    ┌─────────┐
    │  none  │ ────────────> │ active  │ <──┐
    └────────┘               └────┬────┘    │
                                  │         │
                    check_expiry  │         │ auto_renew
                    (no balance)  │         │ (has balance)
                                  v         │
                             ┌─────────┐    │
                             │ expired │ ───┘
                             └─────────┘
                                  │
                                  │ payment_received
                                  v
                             [active]
```

---

## Сервисы

### SubscriptionService

Основной сервис управления подписками.

| Метод | Описание |
|-------|----------|
| `check_expiring_subscriptions()` | Поиск и уведомление об истекающих подписках |
| `process_auto_renewal(user_id)` | Автопродление для одного пользователя |
| `process_all_auto_renewals()` | Пакетное автопродление |
| `expire_subscriptions()` | Уведомление об истёкших подписках |
| `get_subscription_status(user)` | Детальный статус подписки |
| `toggle_auto_renew(user_id)` | Переключить автопродление |
| `manual_renew(user_id)` | Ручное продление |

**Логика автопродления:**

```
1. Получить пользователя с блокировкой (FOR UPDATE)
2. Проверить auto_renew == True
3. Проверить баланс >= renewal_price
4. Списать токены
5. Продлить subscription_end на N дней
6. Создать транзакцию типа SUBSCRIPTION
7. Сбросить счётчик уведомлений
8. Отправить уведомление об успехе
```

**При недостатке средств:**

- Автопродление не происходит
- Отправляется уведомление с указанием требуемой суммы
- Подписка истекает в штатном режиме

---

## Scheduled Tasks

### Расписание

| Задача | Расписание | Описание |
|--------|------------|----------|
| `run_expiry_notification_task` | Каждые 6 часов | Уведомления об истечении |
| `run_auto_renewal_task` | Ежедневно 00:05 | Автопродление подписок |
| `run_expire_subscriptions_task` | Ежедневно 10:00 | Уведомление об истёкших |

### Интеграция с APScheduler

```python
from src.tasks import setup_scheduler, start_scheduler

# При старте бота
scheduler = setup_scheduler(bot)
start_scheduler()
```

### Ручной запуск

```python
from src.tasks import run_all_tasks_once

result = await run_all_tasks_once(bot)
# {
#   "notifications": {3: [user_ids], 1: [user_ids]},
#   "renewals": {"success": [ids], "failed": [ids]},
#   "expired": [user_ids]
# }
```

---

## Bot Handler

### /subscription

Показывает статус подписки и кнопки управления.

```
Управление подпиской

✓ Статус: Активна до 01.03.2024
   Дата окончания: 01.03.2024 00:00
   Осталось: 28 дней

✓ Автопродление: включено
   При истечении спишется 100 токенов

Ваш баланс: 150 токенов
Стоимость продления: 100 токенов

Пополнить баланс: /tariffs

[Отключить автопродление]
[Обновить]
```

### Кнопки

| Callback | Действие |
|----------|----------|
| `subscription:renew` | Ручное продление |
| `subscription:toggle_auto` | Вкл/выкл автопродление |
| `subscription:refresh` | Обновить статус |

---

## Уведомления

### Типы уведомлений

| Событие | Метод | Описание |
|---------|-------|----------|
| За N дней до истечения | `notify_subscription_expiring` | Предупреждение |
| Подписка истекла | `notify_subscription_expired` | Уведомление об истечении |
| Успешное автопродление | `notify_renewal_success` | Подтверждение продления |
| Неудачное автопродление | `notify_renewal_failed` | Причина неудачи |

### Логика предупреждений

Уведомления отправляются за `subscription_notify_days` до истечения (по умолчанию: 3, 1, 0 дней).

Для каждого порога уведомление отправляется **один раз** — отслеживается через `last_subscription_notification`.

После продления счётчик сбрасывается.

---

## Модель данных

### User (расширение)

| Поле | Тип | Default | Описание |
|------|-----|---------|----------|
| `auto_renew` | bool | True | Автопродление включено |
| `last_subscription_notification` | int | null | Дней до истечения при последнем уведомлении |

### Transaction (новый тип)

```python
class TransactionType(Enum):
    TOPUP = "topup"
    SPEND = "spend"
    REFUND = "refund"
    ADJUSTMENT = "adjustment"
    SUBSCRIPTION = "subscription"  # NEW
```

---

## Конфигурация

| Переменная | Default | Описание |
|------------|---------|----------|
| `SUBSCRIPTION_RENEWAL_DAYS` | 30 | Срок продления (дней) |
| `SUBSCRIPTION_RENEWAL_PRICE` | 100 | Стоимость продления (токенов) |
| `SUBSCRIPTION_NOTIFY_DAYS` | [3, 1, 0] | Дни для уведомлений |
| `SUBSCRIPTION_GRACE_PERIOD_DAYS` | 0 | Grace period (опционально) |

---

## Файловая структура

```
backend/src/
├── services/
│   └── subscription_service.py   # Основной сервис
├── tasks/
│   ├── __init__.py               # Экспорт задач
│   └── subscription_tasks.py     # Scheduled tasks
├── bot/handlers/
│   └── subscription.py           # /subscription handler
├── db/
│   ├── models/
│   │   ├── user.py               # +auto_renew, +last_subscription_notification
│   │   └── transaction.py        # +SUBSCRIPTION type
│   └── repositories/
│       └── user_repository.py    # +методы для подписок
└── migrations/versions/
    ├── 005_add_subscription_fields.py
    └── 006_add_subscription_transaction_type.py
```

---

## Поток данных

```
                    ┌─────────────────────────────────────┐
                    │           APScheduler               │
                    │  (every 6h / daily 00:05 / 10:00)   │
                    └─────────────────┬───────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         │                            │                            │
         v                            v                            v
┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────┐
│ Expiry          │      │ Auto-renewal        │      │ Expired         │
│ Notifications   │      │ Processing          │      │ Notifications   │
└────────┬────────┘      └──────────┬──────────┘      └────────┬────────┘
         │                          │                          │
         v                          v                          v
┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────┐
│ Update          │      │ - Deduct tokens     │      │ Send expired    │
│ last_subscr_    │      │ - Extend subscr     │      │ notification    │
│ notification    │      │ - Create tx         │      │                 │
└────────┬────────┘      └──────────┬──────────┘      └────────┬────────┘
         │                          │                          │
         v                          v                          v
    Telegram                   Telegram                   Telegram
    message                    message                    message
```

---

## Зависимости

- **От:** [Database](./database.md), [Billing](./billing.md)
- **Использует:** NotificationService, TransactionRepository, UserRepository
- **Для:** [Bot](./bot.md)

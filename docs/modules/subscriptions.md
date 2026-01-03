# Subscriptions

> Управление подписками: автопродление, уведомления об истечении, ручное продление.

## Обзор

Модуль управления подписками обеспечивает:

1. Автоматическое продление подписок с баланса токенов
2. Уведомления за N дней до истечения
3. Ручное продление через бота
4. Включение/отключение автопродления

### M11: Simplified Payment UX

С M11 введена упрощённая модель подписки:

- **Скрытые тарифы** — пользователь не выбирает тариф, просто пополняет баланс
- **Гибкий период** — `period_unit` (hour/day/month) + `period_value`
- **Subscription fee** — абонплата списывается при первом платеже или автопродлении
- **Min payment** — минимальная сумма пополнения (по умолчанию 200₽)

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

**Логика автопродления (M11):**

```
1. Получить пользователя с блокировкой (FOR UPDATE)
2. Проверить auto_renew == True
3. Получить тариф → subscription_fee
4. Проверить баланс >= subscription_fee
5. Списать subscription_fee токенов
6. Рассчитать новую дату: calculate_subscription_end(period_unit, period_value)
7. Создать транзакцию типа SUBSCRIPTION
8. Сбросить счётчик уведомлений
9. Отправить уведомление об успехе
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

### Настройки в Tariff (M11)

| Поле | Default | Описание |
|------|---------|----------|
| `period_unit` | month | Единица периода (hour/day/month) |
| `period_value` | 1 | Количество единиц |
| `subscription_fee` | 100 | Абонплата (токенов) |
| `min_payment` | 200.00 | Минимальный платёж (₽) |

### Environment

| Переменная | Default | Описание |
|------------|---------|----------|
| `SUBSCRIPTION_NOTIFY_DAYS` | [3, 1, 0] | Дни для уведомлений |
| `SUBSCRIPTION_GRACE_PERIOD_DAYS` | 0 | Grace period (опционально) |

---

## Файловая структура

```
backend/src/
├── services/
│   ├── billing_service.py        # +calculate_subscription_end(), +process_m11_payment()
│   └── subscription_service.py   # Основной сервис (M11: tariff-based)
├── tasks/
│   ├── __init__.py               # Экспорт задач
│   └── subscription_tasks.py     # Scheduled tasks
├── bot/
│   ├── handlers/
│   │   ├── balance.py            # M11: экран баланса и FSM оплаты
│   │   ├── start.py              # M11: упрощённое меню
│   │   └── tariffs.py            # M11: редирект на баланс
│   ├── keyboards/
│   │   ├── balance.py            # M11: кнопки пополнения
│   │   └── main_menu.py          # M11: 2 кнопки
│   └── states/
│       └── payment.py            # M11: PaymentStates FSM
├── db/
│   ├── models/
│   │   ├── tariff.py             # +PeriodUnit, +period_*, +subscription_fee, +min_payment
│   │   ├── user.py               # +auto_renew, +last_subscription_notification
│   │   └── transaction.py        # +SUBSCRIPTION type
│   └── repositories/
│       ├── tariff_repository.py  # +get_default_tariff()
│       └── user_repository.py    # +методы для подписок
└── migrations/versions/
    ├── 005_add_subscription_fields.py
    ├── 006_add_subscription_transaction_type.py
    └── 007_add_tariff_period_fields.py  # M11
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

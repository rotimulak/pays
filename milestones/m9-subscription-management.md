# M9: Subscription Management

## Цель

Реализовать управление подписками: автопродление, уведомления об истечении, grace period. Полный lifecycle подписки.

---

## Задачи

### 9.1 Subscription Service

- [ ] `services/subscription_service.py`
  - `check_expiring_subscriptions()` — поиск истекающих подписок
  - `process_auto_renewal(user_id)` — автопродление с баланса
  - `send_expiry_notifications()` — уведомления за N дней
  - `expire_subscriptions()` — перевод в expired

### 9.2 Scheduled Tasks

- [ ] `tasks/subscription_tasks.py`
  - Задача проверки истекающих подписок (каждый час)
  - Задача автопродления (ежедневно)
  - Задача уведомлений (ежедневно)

### 9.3 Task Runner

- [ ] Интеграция с APScheduler или простой cron через asyncio
- [ ] `tasks/__init__.py` — регистрация задач

### 9.4 Notifications

- [ ] Уведомление за 3 дня до истечения
- [ ] Уведомление за 1 день до истечения
- [ ] Уведомление при истечении
- [ ] Уведомление при успешном автопродлении

### 9.5 Bot Handlers

- [ ] `bot/handlers/subscription.py`
  - `/subscription` — детали подписки
  - Кнопка "Продлить подписку"
  - Кнопка "Включить/выключить автопродление" (опционально)

### 9.6 User Settings (опционально)

- [ ] Добавить поле `auto_renew` в User
- [ ] Настройка автопродления в боте

---

## Definition of Done (DoD)

- [ ] Cron-задача находит подписки, истекающие в ближайшие N дней
- [ ] Уведомления отправляются за 3 дня и за 1 день до истечения
- [ ] Автопродление списывает токены и продлевает подписку
- [ ] При недостатке токенов автопродление не происходит, отправляется уведомление
- [ ] После истечения подписки пользователь не может тратить токены
- [ ] Транзакция типа `subscription` создаётся при автопродлении
- [ ] Graceful handling при ошибках (не блокирует обработку других пользователей)
- [ ] Логирование всех операций
- [ ] Unit-тесты для subscription_service

---

## Артефакты

```
backend/src/
├── services/
│   └── subscription_service.py
├── tasks/
│   ├── __init__.py
│   └── subscription_tasks.py
├── bot/handlers/
│   └── subscription.py
└── tests/
    └── test_subscription_service.py
```

---

## State Machine: Subscription

```
              payment_received
         ┌────────────────────────┐
         │                        │
         ▼                        │
    ┌────────┐    payment    ┌─────────┐
    │  none  │ ────────────> │ active  │ ◄──┐
    └────────┘               └────┬────┘    │
                                  │         │
                    check_expiry  │         │ auto_renew
                    (no balance)  │         │ (has balance)
                                  ▼         │
                             ┌─────────┐    │
                             │ expired │ ───┘
                             └─────────┘
                                  │
                                  │ payment_received
                                  ▼
                             [active]
```

---

## Логика автопродления

```python
async def process_auto_renewal(user_id: int) -> bool:
    """Attempt to auto-renew subscription. Returns True if successful."""
    user = await user_repo.get_for_update(user_id)

    # Получить цену продления (например, из последнего тарифа)
    renewal_price = await get_renewal_price(user_id)

    if user.token_balance < renewal_price:
        await notification_service.notify_renewal_failed(
            user_id,
            reason="insufficient_balance",
            required=renewal_price,
            available=user.token_balance
        )
        return False

    # Списать токены
    new_balance = user.token_balance - renewal_price
    await user_repo.update_balance(
        user_id,
        new_balance,
        expected_version=user.balance_version
    )

    # Продлить подписку на 30 дней
    new_end = (user.subscription_end or datetime.utcnow()) + timedelta(days=30)
    await user_repo.update_subscription_end(user_id, new_end)

    # Создать транзакцию
    await transaction_repo.create(
        user_id=user_id,
        type=TransactionType.SUBSCRIPTION,
        tokens_delta=-renewal_price,
        balance_after=new_balance,
        description="Auto-renewal subscription (30 days)"
    )

    # Уведомить
    await notification_service.notify_renewal_success(user_id, new_end)

    return True
```

---

## Конфигурация

```python
# core/config.py
class Settings(BaseSettings):
    # Subscription
    SUBSCRIPTION_RENEWAL_DAYS: int = 30
    SUBSCRIPTION_RENEWAL_PRICE: int = 100  # tokens
    SUBSCRIPTION_NOTIFY_DAYS: list[int] = [3, 1]  # days before expiry
    SUBSCRIPTION_GRACE_PERIOD_DAYS: int = 0  # optional grace period
```

# M5: Billing Flow

## Цель

Реализовать полный цикл биллинга: оплата → начисление токенов/подписки → транзакция → уведомление. После этого milestone пользователь может реально "покупать" через mock provider.

---

## Задачи

### 5.1 Billing Service

- [ ] `services/billing_service.py`
  - `process_successful_payment(invoice_id)` — основная логика начисления
  - `credit_tokens(user_id, amount, invoice_id)` — начисление токенов
  - `extend_subscription(user_id, days, invoice_id)` — продление подписки
  - Optimistic locking при обновлении баланса

### 5.2 Transaction Service

- [ ] `services/transaction_service.py`
  - `create_transaction(user_id, type, tokens_delta, description, invoice_id)`
  - `get_user_transactions(user_id, limit, offset)`

### 5.3 Audit Service

- [ ] `services/audit_service.py`
  - `log_action(user_id, action, entity_type, entity_id, old_value, new_value, metadata)`

### 5.4 Notification

- [ ] `services/notification_service.py`
  - `notify_payment_success(user_id, invoice)` — отправка сообщения в Telegram

### 5.5 Webhook Handler (обновление)

- [ ] Обновить `api/routes/webhook.py`
  - Вызов billing_service.process_successful_payment
  - Идемпотентность (проверка, что invoice не обработан повторно)
  - Возврат `OK{InvId}` для Robokassa

### 5.6 Bot Handlers

- [ ] `bot/handlers/history.py` — `/history` показывает последние транзакции
- [ ] `bot/handlers/balance.py` — `/balance` показывает текущий баланс и подписку

### 5.7 Invoice Expiration

- [ ] Скрипт/cron для перевода expired invoices (pending → expired по TTL)

---

## Definition of Done (DoD)

- [ ] После успешного webhook invoice переходит в `paid`
- [ ] Токены начисляются на баланс пользователя
- [ ] Подписка продлевается корректно (или устанавливается)
- [ ] Создаётся transaction с типом `topup`
- [ ] Создаётся запись в audit_log
- [ ] Пользователь получает уведомление в Telegram
- [ ] Повторный webhook с тем же invoice игнорируется (идемпотентность)
- [ ] `/history` показывает транзакции
- [ ] `/balance` показывает актуальные данные
- [ ] Optimistic locking работает корректно при concurrent updates
- [ ] Integration test: полный flow от выбора тарифа до начисления

---

## Артефакты

```
backend/src/
├── services/
│   ├── billing_service.py
│   ├── transaction_service.py
│   ├── audit_service.py
│   └── notification_service.py
├── api/routes/
│   └── webhook.py (updated)
├── bot/handlers/
│   ├── history.py
│   └── balance.py
└── scripts/
    └── expire_invoices.py
```

---

## Бизнес-логика начисления

```python
async def process_successful_payment(invoice_id: UUID) -> None:
    # 1. Получить invoice с блокировкой
    invoice = await invoice_repo.get_for_update(invoice_id)

    # 2. Проверить статус (идемпотентность)
    if invoice.status != InvoiceStatus.PENDING:
        return  # уже обработан

    # 3. Начислить токены (если есть)
    if invoice.tokens > 0:
        await credit_tokens(invoice.user_id, invoice.tokens, invoice.id)

    # 4. Продлить подписку (если есть)
    if invoice.subscription_days > 0:
        await extend_subscription(invoice.user_id, invoice.subscription_days, invoice.id)

    # 5. Обновить статус invoice
    await invoice_repo.update_status(invoice.id, InvoiceStatus.PAID)

    # 6. Записать в audit
    await audit_service.log_action(...)

    # 7. Уведомить пользователя
    await notification_service.notify_payment_success(invoice.user_id, invoice)
```

# M6: Robokassa Provider

## Цель

Заменить mock provider на реальную интеграцию с Robokassa. После этого milestone система готова принимать реальные платежи.

---

## Задачи

### 6.1 Robokassa Provider

- [ ] `payments/providers/robokassa/provider.py` — RobokassaPaymentProvider
  - `generate_payment_url(invoice)` — формирование URL с подписью
  - `verify_signature(data)` — проверка MD5 подписи
  - `parse_webhook(data)` — парсинг ResultURL callback

### 6.2 Signature Utils

- [ ] `payments/providers/robokassa/signature.py`
  - `generate_init_signature(login, amount, inv_id, password1)` — для инициации
  - `generate_result_signature(amount, inv_id, password2, shp_params)` — для webhook
  - `verify_result_signature(data, password2)` — проверка webhook

### 6.3 Configuration

- [ ] Обновить `core/config.py`
  - `ROBOKASSA_MERCHANT_LOGIN`
  - `ROBOKASSA_PASSWORD_1`
  - `ROBOKASSA_PASSWORD_2`
  - `ROBOKASSA_IS_TEST`
  - `PAYMENT_PROVIDER` (mock | robokassa)

### 6.4 Provider Factory

- [ ] `payments/providers/__init__.py` — factory для создания provider по конфигу
  ```python
  def get_payment_provider() -> PaymentProvider:
      if settings.PAYMENT_PROVIDER == "mock":
          return MockPaymentProvider()
      return RobokassaPaymentProvider(settings)
  ```

### 6.5 Webhook Route (обновление)

- [ ] Обновить `api/routes/webhook.py`
  - Роут для Robokassa ResultURL
  - Верификация подписи перед обработкой
  - Возврат `OK{InvId}`

### 6.6 Shp Parameters

- [ ] Поддержка дополнительных параметров (Shp_*)
  - `Shp_user_id` — для идентификации пользователя
  - `Shp_invoice_id` — UUID счёта

---

## Definition of Done (DoD)

- [ ] RobokassaPaymentProvider реализует тот же интерфейс, что MockPaymentProvider
- [ ] Генерация URL соответствует документации Robokassa
- [ ] Подпись для init корректна (MD5, Password_1)
- [ ] Подпись webhook проверяется корректно (MD5, Password_2, Shp_* sorted)
- [ ] Переключение mock ↔ robokassa через env variable
- [ ] Тестовый режим (`IsTest=1`) работает
- [ ] Unit-тесты для signature generation/verification
- [ ] Integration test с тестовым аккаунтом Robokassa (manual)

---

## Артефакты

```
backend/src/
├── payments/
│   └── providers/
│       ├── __init__.py (updated with factory)
│       └── robokassa/
│           ├── __init__.py
│           ├── provider.py
│           └── signature.py
├── core/
│   └── config.py (updated)
└── tests/
    └── test_robokassa_signature.py
```

---

## Формат URL Robokassa

```
https://auth.robokassa.ru/Merchant/Index.aspx?
  MerchantLogin={login}
  &OutSum={amount}
  &InvId={invoice_number}
  &Description={description}
  &SignatureValue={signature}
  &IsTest=1
  &Shp_invoice_id={uuid}
  &Shp_user_id={telegram_id}
```

## Формат Webhook (ResultURL)

```
POST /webhook/robokassa
Content-Type: application/x-www-form-urlencoded

OutSum=100.00
&InvId=123
&SignatureValue=abc123...
&Shp_invoice_id=uuid
&Shp_user_id=12345
```

Ответ: `OK123` (где 123 = InvId)

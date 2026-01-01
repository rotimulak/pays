# Payments

> Платёжная подсистема: провайдеры, webhook-обработка, mock-интеграция.

## Архитектура

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Bot Handler   │────>│  PaymentService  │────>│ PaymentProvider │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │                        │
                                 v                        v
                        ┌────────────────┐       ┌────────────────┐
                        │ InvoiceService │       │ MockProvider   │
                        └────────────────┘       │ RobokassaProv. │
                                                 └────────────────┘
```

---

## PaymentProvider (Interface)

Абстрактный интерфейс для платёжных провайдеров.

```python
class PaymentProvider(ABC):
    @abstractmethod
    def generate_payment_url(self, invoice: Invoice) -> str:
        """Generate redirect URL for payment."""

    @abstractmethod
    def generate_init_signature(
        self, out_sum: str, inv_id: int, shp_params: dict
    ) -> str:
        """Generate signature for payment URL."""

    @abstractmethod
    def verify_result_signature(self, data: WebhookData) -> bool:
        """Verify webhook signature."""

    @abstractmethod
    def parse_webhook(self, raw_data: dict) -> WebhookData:
        """Parse webhook to unified format."""

    @abstractmethod
    def format_success_response(self, inv_id: int) -> str:
        """Format webhook response (e.g., 'OK12345')."""
```

---

## MockPaymentProvider

Mock-провайдер с тем же интерфейсом, что и Robokassa.

### Конфигурация

| Параметр | Переменная | Описание |
|----------|------------|----------|
| Merchant Login | `MOCK_MERCHANT_LOGIN` | Логин мерчанта |
| Password 1 | `MOCK_PASSWORD_1` | Пароль для init-подписи |
| Password 2 | `MOCK_PASSWORD_2` | Пароль для result-подписи |
| Base URL | `WEBHOOK_BASE_URL` | URL для mock-страницы |

### Payment URL

```
{base_url}/mock-payment?
    MerchantLogin=demo
    &OutSum=499.00
    &InvId=12345
    &Description=Оплата тарифа #12345
    &SignatureValue=abc123...
    &Culture=ru
    &Shp_invoice_id=uuid
    &Shp_user_id=123456
    &IsTest=1
```

---

## Подписи (Signatures)

### Init Signature (Payment URL)

Формула:
```
MD5(MerchantLogin:OutSum:InvId:Password_1:Shp_invoice_id=X:Shp_user_id=Y)
```

- Shp_* параметры сортируются **алфавитно**
- OutSum форматируется с 2 знаками: `499.00`

```python
def generate_init_signature(
    merchant_login: str,
    out_sum: Decimal,
    inv_id: int,
    password_1: str,
    shp_params: dict[str, str],
) -> str:
    out_sum_str = f"{out_sum:.2f}"
    parts = [merchant_login, out_sum_str, str(inv_id), password_1]

    for key, value in sorted(shp_params.items()):
        parts.append(f"{key}={value}")

    return hashlib.md5(":".join(parts).encode()).hexdigest()
```

### Result Signature (Webhook)

Формула:
```
MD5(OutSum:InvId:Password_2:Shp_invoice_id=X:Shp_user_id=Y)
```

```python
def generate_result_signature(
    out_sum: Decimal,
    inv_id: int,
    password_2: str,
    shp_params: dict[str, str],
) -> str:
    out_sum_str = f"{out_sum:.2f}"
    parts = [out_sum_str, str(inv_id), password_2]

    for key, value in sorted(shp_params.items()):
        parts.append(f"{key}={value}")

    return hashlib.md5(":".join(parts).encode()).hexdigest()
```

---

## WebhookData

```python
class WebhookData(BaseModel):
    out_sum: Decimal
    inv_id: int
    signature: str
    shp_invoice_id: UUID
    shp_user_id: int
    fee: Decimal | None = None
    email: str | None = None
    payment_method: str | None = None
```

---

## PaymentService

Сервис обработки платежей.

### Методы

| Метод | Описание |
|-------|----------|
| `create_payment_url(invoice_id)` | Генерация URL оплаты |
| `process_webhook(data)` | Обработка callback от провайдера |

### create_payment_url

1. Получить invoice по ID
2. Проверить статус = `pending`
3. Проверить не истёк (`expires_at`)
4. Сгенерировать URL через провайдер
5. Сохранить `payment_url` в invoice

### process_webhook

1. Найти invoice по `shp_invoice_id`
2. **Idempotency**: если `status != pending` → return (уже обработан)
3. Проверить `inv_id` совпадает
4. SELECT FOR UPDATE (lock)
5. Обновить статус → `PAID`
6. Начислить токены пользователю
7. Продлить подписку если есть
8. Создать Transaction запись
9. Вернуть `OK{inv_id}`

---

## Webhook Handler

```python
@router.post("/webhook/payment")
async def payment_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    # 1. Parse form data
    form_data = await request.form()
    raw_data = dict(form_data)

    # 2. Get provider and parse
    provider = get_payment_provider()
    webhook_data = provider.parse_webhook(raw_data)

    # 3. Verify signature
    if not provider.verify_result_signature(webhook_data):
        raise HTTPException(400, "Invalid signature")

    # 4. Process payment
    payment_service = PaymentService(session)
    invoice = await payment_service.process_webhook(webhook_data)

    # 5. Commit and respond
    await session.commit()
    return PlainTextResponse(provider.format_success_response(invoice.inv_id))
```

---

## Mock Payment UI

HTML-страница для симуляции оплаты.

### Endpoints

| Route | Описание |
|-------|----------|
| `GET /mock-payment` | Страница оплаты |
| `POST /mock-payment/process` | Симуляция успешной оплаты |
| `POST /mock-payment/cancel` | Симуляция отмены |
| `GET /mock-payment/success` | Страница успеха |
| `GET /mock-payment/fail` | Страница ошибки |

### Страница оплаты

```html
<h1>🏦 Mock Payment</h1>
<p>Merchant: demo</p>
<p>Оплата тарифа #12345</p>
<div class="amount">499 ₽</div>

<form action="/mock-payment/process" method="post">
    <button>✓ Оплатить</button>
</form>
<form action="/mock-payment/cancel" method="post">
    <button>✗ Отменить</button>
</form>
```

### Процесс оплаты

При нажатии "Оплатить":
1. Генерируется result signature (Password_2)
2. POST на `/webhook/payment` с формой:
   - `OutSum`, `InvId`, `SignatureValue`
   - `Shp_invoice_id`, `Shp_user_id`
3. Редирект на `/mock-payment/success`

---

## Файловая структура

```
backend/src/payments/
├── __init__.py
├── schemas.py                  # WebhookData, PaymentStatus
└── providers/
    ├── __init__.py             # get_payment_provider()
    ├── base.py                 # PaymentProvider ABC
    └── mock/
        ├── __init__.py
        ├── provider.py         # MockPaymentProvider
        ├── signature.py        # generate_*_signature
        ├── router.py           # FastAPI routes
        └── templates/
            ├── payment_page.html
            ├── success.html
            └── fail.html

backend/src/api/routes/
└── webhook.py                  # POST /webhook/payment

backend/src/services/
└── payment_service.py          # PaymentService
```

---

## Flow: Invoice → Payment → Credit

```
1. User: /tariffs → выбирает тариф
2. Bot: InvoiceService.get_or_create_invoice()
3. Bot: PaymentService.create_payment_url()
4. Bot: показывает кнопку [💳 Оплатить] с URL
5. User: переходит на mock-payment page
6. User: нажимает "Оплатить"
7. Mock: POST /webhook/payment
8. Webhook: verify signature → process_webhook()
9. PaymentService: invoice.status = PAID
10. PaymentService: user.token_balance += tokens
11. PaymentService: user.subscription_end += days
12. Webhook: return "OK12345"
13. Mock: redirect → /mock-payment/success
```

---

## Конфигурация

| Переменная | Описание |
|------------|----------|
| `PAYMENT_PROVIDER` | `mock` или `robokassa` |
| `MOCK_MERCHANT_LOGIN` | Логин для mock |
| `MOCK_PASSWORD_1` | Password 1 для mock |
| `MOCK_PASSWORD_2` | Password 2 для mock |
| `WEBHOOK_BASE_URL` | URL для callbacks |
| `ROBOKASSA_IS_TEST` | Тестовый режим |

---

## Зависимости

- **От:** [Database](./database.md), [Tariffs](./tariffs.md)
- **Для:** [Bot](./bot.md)

# M4: Mock Payment Provider

## Цель

Создать mock-адаптер платёжной системы с тем же интерфейсом, что и реальный Robokassa. Позволяет тестировать полный flow оплаты без реального провайдера.

---

## Задачи

### 4.1 Payment Provider Interface

- [ ] `payments/providers/base.py` — абстрактный PaymentProvider
  ```python
  class PaymentProvider(ABC):
      @abstractmethod
      def generate_payment_url(self, invoice: Invoice) -> str:
          """Generate redirect URL for payment initiation"""

      @abstractmethod
      def verify_result_signature(self, data: WebhookData) -> bool:
          """Verify ResultURL callback signature"""

      @abstractmethod
      def parse_webhook(self, raw_data: dict) -> WebhookData:
          """Parse incoming webhook to unified format"""

      @abstractmethod
      def format_success_response(self, inv_id: int) -> str:
          """Format response for successful webhook processing"""
  ```

### 4.2 Schemas (соответствие Robokassa API)

- [ ] `payments/schemas.py`
  ```python
  class PaymentInitParams(BaseModel):
      """Parameters for payment initiation (matches Robokassa)"""
      merchant_login: str
      out_sum: Decimal          # Сумма в рублях (123.45)
      inv_id: int               # 1 - 9223372036854775807
      description: str          # До 100 символов
      signature: str            # MD5 hash
      # Optional
      culture: str = "ru"
      email: str | None = None
      expiration_date: datetime | None = None  # ISO 8601
      is_test: bool = False
      # Custom params (Shp_*)
      shp_invoice_id: UUID      # Наш UUID invoice
      shp_user_id: int          # Telegram user_id

  class WebhookData(BaseModel):
      """ResultURL callback data (matches Robokassa)"""
      out_sum: Decimal
      inv_id: int
      signature: str
      # Optional from Robokassa
      fee: Decimal | None = None
      email: str | None = None
      payment_method: str | None = None
      # Custom params
      shp_invoice_id: UUID
      shp_user_id: int

  class PaymentStatus(IntEnum):
      """OpStateExt status codes"""
      INITIALIZED = 5
      CANCELLED = 10
      RESERVED = 50       # Hold
      CANCELLED_AFTER_RESERVE = 60
      TRANSFERRED = 80
      COMPLETED = 100
  ```

### 4.3 Mock Provider

- [ ] `payments/providers/mock/provider.py` — MockPaymentProvider
  ```python
  class MockPaymentProvider(PaymentProvider):
      def generate_payment_url(self, invoice: Invoice) -> str:
          """
          Generates URL matching Robokassa format:
          /mock-payment?MerchantLogin=...&OutSum=...&InvId=...&SignatureValue=...&Shp_*=...
          """

      def generate_init_signature(self, out_sum: Decimal, inv_id: int, shp_params: dict) -> str:
          """MD5(MerchantLogin:OutSum:InvId:Password_1:Shp_*) - sorted Shp_*"""

      def verify_result_signature(self, data: WebhookData) -> bool:
          """MD5(OutSum:InvId:Password_2:Shp_*) - sorted Shp_*"""

      def format_success_response(self, inv_id: int) -> str:
          """Returns 'OK{InvId}' e.g. 'OK12345'"""
  ```

- [ ] `payments/providers/mock/router.py` — FastAPI роутер для mock UI
  ```python
  # GET /mock-payment — страница "оплаты" (парсит query params как Robokassa)
  # POST /mock-payment/process — симуляция успешной оплаты
  # POST /mock-payment/cancel — симуляция отмены
  ```

- [ ] `payments/providers/mock/templates/` — HTML шаблоны
  - `payment_page.html` — форма оплаты (показывает сумму, описание)
  - `success.html` — страница успеха (редирект на SuccessURL)
  - `fail.html` — страница отмены (редирект на FailURL)

### 4.4 Webhook Handler

- [ ] `api/routes/webhook.py` — `/webhook/robokassa` endpoint
  ```python
  @router.post("/webhook/robokassa")
  async def robokassa_result_url(
      OutSum: Decimal = Form(...),
      InvId: int = Form(...),
      SignatureValue: str = Form(...),
      Shp_invoice_id: UUID = Form(...),
      Shp_user_id: int = Form(...),
      # ... other optional fields
  ) -> PlainTextResponse:
      """
      ResultURL callback handler.
      1. Verify signature
      2. Process payment
      3. Return 'OK{InvId}'
      """
  ```

### 4.5 Payment Service

- [ ] `services/payment_service.py`
  ```python
  class PaymentService:
      async def create_payment(self, invoice_id: UUID) -> str:
          """Get payment URL for invoice"""

      async def process_webhook(self, data: WebhookData) -> Invoice:
          """
          1. Verify signature
          2. Find invoice by shp_invoice_id
          3. Check idempotency (status != pending → ignore)
          4. Update invoice status
          5. Return updated invoice
          """
  ```

### 4.6 Configuration

- [ ] Обновить `core/config.py`
  ```python
  class Settings(BaseSettings):
      # Payment provider
      PAYMENT_PROVIDER: Literal["mock", "robokassa"] = "mock"

      # Mock provider settings (same structure as Robokassa)
      MOCK_MERCHANT_LOGIN: str = "test_merchant"
      MOCK_PASSWORD_1: str = "test_password_1"
      MOCK_PASSWORD_2: str = "test_password_2"

      # Callback URLs
      WEBHOOK_BASE_URL: str  # e.g. https://yourdomain.com
      SUCCESS_URL: str | None = None
      FAIL_URL: str | None = None
  ```

### 4.7 InvId Mapping

- [ ] `db/repositories/invoice_repository.py` — добавить методы
  ```python
  async def get_next_inv_id(self) -> int:
      """Generate sequential InvId for Robokassa (1-9223372036854775807)"""

  async def get_by_inv_id(self, inv_id: int) -> Invoice | None:
      """Find invoice by Robokassa InvId"""
  ```

- [ ] Добавить поле `inv_id: BIGINT` в таблицу `invoices` (sequential, unique)

---

## Definition of Done (DoD)

- [ ] MockPaymentProvider реализует тот же интерфейс и подписи, что Robokassa
- [ ] URL генерируется с правильными параметрами (MerchantLogin, OutSum, InvId, SignatureValue, Shp_*)
- [ ] Подпись для init: `MD5(MerchantLogin:OutSum:InvId:Password_1:Shp_*)`
- [ ] Подпись для webhook: `MD5(OutSum:InvId:Password_2:Shp_*)` (Shp_* sorted alphabetically)
- [ ] Webhook возвращает `OK{InvId}` при успехе
- [ ] Mock UI показывает страницу оплаты с суммой и описанием
- [ ] После "оплаты" отправляется POST на ResultURL с правильными параметрами
- [ ] Переключение mock ↔ robokassa через `PAYMENT_PROVIDER` env variable
- [ ] Unit-тесты для signature generation/verification
- [ ] Integration test: invoice → payment URL → mock pay → webhook → invoice.paid

---

## Артефакты

```
backend/src/
├── payments/
│   ├── __init__.py
│   ├── schemas.py              # PaymentInitParams, WebhookData, PaymentStatus
│   └── providers/
│       ├── __init__.py         # get_payment_provider() factory
│       ├── base.py             # PaymentProvider ABC
│       └── mock/
│           ├── __init__.py
│           ├── provider.py     # MockPaymentProvider
│           ├── router.py       # Mock payment UI endpoints
│           ├── signature.py    # MD5 signature utils
│           └── templates/
│               ├── payment_page.html
│               ├── success.html
│               └── fail.html
├── services/
│   └── payment_service.py
├── api/
│   ├── __init__.py
│   ├── dependencies.py
│   └── routes/
│       └── webhook.py
├── core/
│   └── config.py               # Updated with payment settings
└── tests/
    ├── test_payment_service.py
    ├── test_mock_provider.py
    └── test_signature.py
```

---

## Signature Examples

### Init Signature (Payment URL)

```python
# Without Shp_* params
signature = md5(f"{login}:{out_sum}:{inv_id}:{password_1}".encode()).hexdigest()

# With Shp_* params (sorted alphabetically by key)
shp_string = ":".join(f"{k}={v}" for k, v in sorted(shp_params.items()))
signature = md5(f"{login}:{out_sum}:{inv_id}:{password_1}:{shp_string}".encode()).hexdigest()

# Example:
# login=demo, out_sum=100.00, inv_id=1, password_1=secret
# Shp_invoice_id=abc-123, Shp_user_id=456
# → MD5("demo:100.00:1:secret:Shp_invoice_id=abc-123:Shp_user_id=456")
```

### Result Signature (Webhook)

```python
# Shp_* params sorted alphabetically
shp_string = ":".join(f"{k}={v}" for k, v in sorted(shp_params.items()))
signature = md5(f"{out_sum}:{inv_id}:{password_2}:{shp_string}".encode()).hexdigest()

# Example:
# out_sum=100.00, inv_id=1, password_2=secret2
# Shp_invoice_id=abc-123, Shp_user_id=456
# → MD5("100.00:1:secret2:Shp_invoice_id=abc-123:Shp_user_id=456")
```

---

## Mock Payment Flow

```
1. User selects tariff in bot
   ↓
2. Bot creates Invoice (status=pending)
   ↓
3. Bot calls PaymentService.create_payment(invoice_id)
   ↓
4. MockPaymentProvider.generate_payment_url() returns:
   /mock-payment?MerchantLogin=test&OutSum=100.00&InvId=1&Description=...
   &SignatureValue=abc123&Shp_invoice_id=uuid&Shp_user_id=12345
   ↓
5. User clicks URL → Mock payment page
   ↓
6. User clicks "Pay" → Mock provider:
   - POST to /webhook/robokassa with Form data
   - Redirect user to SuccessURL
   ↓
7. Webhook handler:
   - Verify signature
   - Call BillingService.process_payment(invoice_id)
   - Return "OK1"
```

---

## Отличия Mock от Real Robokassa

| Аспект | Mock | Robokassa |
|--------|------|-----------|
| Payment page | Local HTML | External `auth.robokassa.ru` |
| IsTest param | Ignored | Enables test mode |
| Signature verification | Uses mock passwords | Uses real passwords |
| Payment methods | Single "Pay" button | Multiple payment options |
| Receipt (54-ФЗ) | Not required | Required for production |

Mock использует те же форматы данных и алгоритмы подписи, что позволяет в M6 просто заменить provider без изменения бизнес-логики.

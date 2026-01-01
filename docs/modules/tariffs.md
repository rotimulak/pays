# Tariffs & Invoices

> Сервисы для работы с тарифами и счетами на оплату.

## TariffService

Бизнес-логика работы с тарифами.

### Методы

| Метод | Описание |
|-------|----------|
| `get_active_tariffs()` | Активные тарифы (sorted by sort_order) |
| `get_tariff_by_id(tariff_id)` | Тариф по UUID |
| `get_tariff_by_slug(slug)` | Тариф по slug |
| `format_tariff_for_display(tariff)` | Форматирование для Telegram |

### TariffDTO

```python
class TariffDTO(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str | None
    price: Decimal
    price_display: str      # "499 ₽"
    tokens: int
    subscription_days: int
    benefits: str           # "100 токенов + 30 дней подписки"
```

### Форматирование

```
💎 Premium
100 токенов + 30 дней подписки
💰 499 ₽
```

---

## InvoiceService

Бизнес-логика работы со счетами.

### Методы

| Метод | Описание |
|-------|----------|
| `create_invoice(user_id, tariff_id, promo_code)` | Создать счёт |
| `get_or_create_invoice(user_id, tariff_id)` | Получить существующий или создать |
| `get_user_invoices(user_id, limit)` | История счетов пользователя |
| `get_invoice_for_payment(invoice_id)` | Счёт для страницы оплаты |
| `cancel_invoice(invoice_id)` | Отменить pending счёт |
| `generate_idempotency_key(user_id, tariff_id)` | Ключ идемпотентности |
| `format_invoice_for_display(invoice)` | Форматирование для Telegram |

### InvoiceDTO

```python
class InvoiceDTO(BaseModel):
    id: UUID
    inv_id: int
    amount: Decimal
    amount_display: str         # "499 ₽"
    original_amount: Decimal
    discount: Decimal | None    # if promo applied
    tokens: int
    subscription_days: int
    status: InvoiceStatus
    status_display: str         # "Ожидает оплаты"
    tariff_name: str
    created_at: datetime
    expires_at: datetime
    is_expired: bool
```

---

## Создание счёта

```
User → /tariffs → выбор тарифа → create_invoice → pending invoice
```

### Логика create_invoice

1. **Idempotency check** — проверка существующего pending счёта
2. **Get tariff** — получение данных тарифа
3. **Validate** — проверка `is_active`
4. **Calculate amount** — расчёт суммы (promo — placeholder для M7)
5. **Generate inv_id** — уникальный ID для Robokassa (sequence)
6. **Create invoice** — статус `pending`, expires_at = +24h

### Idempotency Key

Формат: `{user_id}:{tariff_id}:{time_window_hash}`

- Time window: 60 минут
- При повторном запросе в окне — возвращается существующий pending invoice
- Предотвращает дублирование счетов при повторных нажатиях

```python
def generate_idempotency_key(user_id, tariff_id):
    now = datetime.utcnow()
    window = now.replace(second=0, microsecond=0)
    window_minutes = window.minute // 60 * 60
    window = window.replace(minute=window_minutes)

    data = f"{user_id}:{tariff_id}:{window.isoformat()}"
    return f"{user_id}:{tariff_id}:{sha256(data)[:16]}"
```

---

## Жизненный цикл Invoice

```
┌─────────┐     create      ┌─────────┐
│  START  │ ──────────────> │ PENDING │
└─────────┘                 └────┬────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
            v                    v                    v
      ┌──────────┐         ┌──────────┐         ┌───────────┐
      │   PAID   │         │ EXPIRED  │         │ CANCELLED │
      └──────────┘         └──────────┘         └───────────┘
            │                 (TTL 24h)           (user)
            v
      ┌──────────┐
      │ REFUNDED │
      └──────────┘
         (admin)
```

### Переходы статусов

| Из | В | Триггер |
|----|---|---------|
| pending | paid | Успешный webhook от платёжной системы |
| pending | expired | TTL 24 часа (scheduled task) |
| pending | cancelled | Пользователь отменил |
| paid | refunded | Администратор оформил возврат |

---

## Форматирование счёта

```
📋 Счёт на оплату

Тариф: Premium
Сумма: 499 ₽

Вы получите:
• 100 токенов
• 30 дней подписки

Счёт действителен до: 02.01.2026 15:30
```

При наличии скидки:
```
Сумма: 449 ₽
Скидка: -50 ₽
```

---

## Файловая структура

```
backend/src/services/
├── __init__.py
├── tariff_service.py
├── invoice_service.py
└── dto/
    ├── __init__.py
    ├── tariff.py
    └── invoice.py
```

---

## Зависимости

- **От:** [Database](./database.md)
- **Для:** [Payments](./payments.md), [Bot](./bot.md)

---

## Конфигурация

| Константа | Значение | Описание |
|-----------|----------|----------|
| `INVOICE_EXPIRY_HOURS` | 24 | Время жизни pending invoice |
| `IDEMPOTENCY_WINDOW_MINUTES` | 60 | Окно идемпотентности |

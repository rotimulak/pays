# M8: Token Spending

## Цель

Реализовать расходование токенов на "рабочие запросы". Добавить API для проверки баланса и списания токенов. Это core-функционал SaaS-сервиса.

---

## Задачи

### 8.1 Token Service

- [ ] `services/token_service.py`
  - `check_balance(user_id) -> TokenBalance` — проверка баланса и подписки
  - `spend_tokens(user_id, amount, description) -> Transaction` — списание
  - `can_spend(user_id, amount) -> bool` — проверка возможности списания
  - Optimistic locking при списании

### 8.2 FastAPI Routes

- [ ] `api/routes/tokens.py`
  - `GET /api/v1/users/{user_id}/balance` — получение баланса
  - `POST /api/v1/users/{user_id}/spend` — списание токенов
  - Авторизация через API key или внутренний токен

### 8.3 Pydantic Schemas

- [ ] `api/schemas/tokens.py`
  - `TokenBalanceResponse`
  - `SpendTokensRequest`
  - `SpendTokensResponse`

### 8.4 Bot Integration

- [ ] Обновить `/balance` — показывать детальную информацию
- [ ] Добавить уведомление при низком балансе (< 10% от среднего расхода)

### 8.5 Guards

- [ ] Проверка активной подписки перед списанием
- [ ] Проверка достаточного баланса
- [ ] Логирование всех списаний

---

## Definition of Done (DoD)

- [ ] API endpoint для списания токенов работает
- [ ] Списание невозможно без активной подписки
- [ ] Списание невозможно при недостаточном балансе
- [ ] Каждое списание создаёт transaction типа `spend`
- [ ] Optimistic locking предотвращает race conditions
- [ ] balance_after в transaction корректен
- [ ] API возвращает понятные ошибки (InsufficientBalance, SubscriptionExpired)
- [ ] Rate limiting на API endpoints
- [ ] Unit-тесты для token_service
- [ ] Integration test: concurrent spending

---

## Артефакты

```
backend/src/
├── services/
│   └── token_service.py
├── api/
│   ├── routes/
│   │   └── tokens.py
│   └── schemas/
│       └── tokens.py
└── tests/
    ├── test_token_service.py
    └── test_token_api.py
```

---

## API Contract

### Check Balance

```http
GET /api/v1/users/{user_id}/balance
Authorization: Bearer {api_key}

Response 200:
{
  "user_id": 123456789,
  "token_balance": 150,
  "subscription_active": true,
  "subscription_end": "2024-02-15T00:00:00Z"
}
```

### Spend Tokens

```http
POST /api/v1/users/{user_id}/spend
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "amount": 5,
  "description": "API request: generate report",
  "idempotency_key": "req_abc123"
}

Response 200:
{
  "transaction_id": "uuid",
  "tokens_spent": 5,
  "balance_after": 145
}

Response 400 (insufficient balance):
{
  "error": "insufficient_balance",
  "message": "Not enough tokens. Required: 5, available: 3"
}

Response 403 (subscription expired):
{
  "error": "subscription_expired",
  "message": "Subscription expired on 2024-01-15"
}
```

---

## Логика списания

```python
async def spend_tokens(
    user_id: int,
    amount: int,
    description: str,
    idempotency_key: str | None = None
) -> Transaction:
    # 1. Проверить идемпотентность
    if idempotency_key:
        existing = await transaction_repo.get_by_idempotency(idempotency_key)
        if existing:
            return existing

    # 2. Получить пользователя с блокировкой
    user = await user_repo.get_for_update(user_id)

    # 3. Проверить подписку
    if not user.is_subscription_active:
        raise SubscriptionExpiredError(user.subscription_end)

    # 4. Проверить баланс
    if user.token_balance < amount:
        raise InsufficientBalanceError(required=amount, available=user.token_balance)

    # 5. Списать с optimistic lock
    new_balance = user.token_balance - amount
    updated = await user_repo.update_balance(
        user_id,
        new_balance,
        expected_version=user.balance_version
    )
    if not updated:
        raise ConcurrentModificationError()

    # 6. Создать транзакцию
    transaction = await transaction_repo.create(
        user_id=user_id,
        type=TransactionType.SPEND,
        tokens_delta=-amount,
        balance_after=new_balance,
        description=description
    )

    return transaction
```

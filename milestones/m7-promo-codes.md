# M7: Promo Codes

## Цель

Добавить систему промокодов со скидками и бонусами. Пользователь может применить промокод при покупке.

---

## Задачи

### 7.1 Repository

- [ ] `db/repositories/promo_code_repository.py`
  - `get_by_code(code)` — поиск по коду
  - `increment_uses(promo_id)` — увеличение счётчика
  - `is_valid(promo)` — проверка активности и лимитов

### 7.2 Promo Service

- [ ] `services/promo_service.py`
  - `validate_promo(code, tariff_id)` — проверка применимости
  - `apply_promo(invoice, promo)` — расчёт скидки
  - `calculate_discount(promo, amount)` — вычисление суммы скидки

### 7.3 Invoice Service (обновление)

- [ ] Обновить `services/invoice_service.py`
  - `create_invoice_with_promo(user_id, tariff_id, promo_code)` — создание с промокодом
  - Сохранение `amount_before_discount`, `promo_code_id`

### 7.4 Bot Handlers

- [ ] `bot/handlers/promo.py` — FSM для ввода промокода
  - `/promo` или кнопка "Ввести промокод"
  - Валидация кода
  - Показ информации о скидке

- [ ] Обновить `bot/handlers/buy.py`
  - Возможность применить промокод перед оплатой
  - Показ старой и новой цены

### 7.5 Bot States

- [ ] `bot/states/promo.py` — FSM states для ввода промокода

### 7.6 Admin (базовое)

- [ ] Скрипт для создания промокодов через CLI

---

## Definition of Done (DoD)

- [ ] Промокод типа `percent` уменьшает сумму на N%
- [ ] Промокод типа `fixed` уменьшает сумму на N рублей
- [ ] Промокод типа `bonus_tokens` добавляет N токенов к покупке
- [ ] Проверяется срок действия промокода
- [ ] Проверяется лимит использований
- [ ] Проверяется привязка к тарифу (если указана)
- [ ] При использовании увеличивается `uses_count`
- [ ] Invoice содержит ссылку на примененный промокод
- [ ] Пользователь видит скидку в интерфейсе бота
- [ ] Unit-тесты для promo_service (все типы скидок)

---

## Артефакты

```
backend/src/
├── db/repositories/
│   └── promo_code_repository.py
├── services/
│   ├── promo_service.py
│   └── invoice_service.py (updated)
├── bot/
│   ├── handlers/
│   │   ├── promo.py
│   │   └── buy.py (updated)
│   └── states/
│       └── promo.py
├── scripts/
│   └── create_promo.py
└── tests/
    └── test_promo_service.py
```

---

## Логика расчёта скидки

```python
def calculate_final_amount(tariff_price: Decimal, promo: PromoCode) -> tuple[Decimal, int]:
    """Returns (final_amount, bonus_tokens)"""
    bonus_tokens = 0

    match promo.discount_type:
        case DiscountType.PERCENT:
            discount = tariff_price * promo.discount_value / 100
            final = tariff_price - discount
        case DiscountType.FIXED:
            final = max(tariff_price - promo.discount_value, Decimal("1.00"))
        case DiscountType.BONUS_TOKENS:
            final = tariff_price
            bonus_tokens = int(promo.discount_value)

    return final, bonus_tokens
```

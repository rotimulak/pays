# M11: Simplified Payment UX — Release Notes

**Дата:** 2026-01-03

## Обзор

M11 упрощает UX бота: меню сокращено до 2 уровней, выбор тарифов скрыт от пользователя, пополнение баланса стало интуитивным.

---

## Новые возможности

### Упрощённое меню

- Главное меню: 2 кнопки — **Баланс** и **Помощь**
- Команда `/tariffs` редиректит на экран баланса
- Пользователь не видит тарифы — просто пополняет баланс

### Экран баланса

- Отображает текущий баланс и статус подписки
- Кнопка быстрого пополнения на минимальную сумму
- Кнопка "Другая сумма" для произвольного пополнения
- Валидация минимальной суммы платежа

### Гибкий период подписки

- Новые поля в Tariff: `period_unit` (hour/day/month), `period_value`
- Поддержка тестового режима (hour) для отладки
- Subscription fee — фиксированная абонплата в токенах

### Логика первого платежа

```
Если подписка неактивна:
├── Списать subscription_fee как абонплату
├── Остаток зачислить на баланс
└── Активировать подписку на period_value period_unit

Если подписка активна:
└── Вся сумма → токены на баланс
```

---

## Изменения в поведении

### Уведомления

- Все уведомления теперь ссылаются на `/balance` вместо `/tariffs`
- Уведомления об истечении показывают баланс и требуемую сумму
- Информация о достаточности средств для автопродления

### Автопродление

- Использует `subscription_fee` из тарифа (вместо hardcoded)
- Использует `period_unit/period_value` для расчёта новой даты
- Описание транзакции на русском языке

---

## Миграция базы данных

**Файл:** `007_add_tariff_period_fields.py`

### Новые поля в tariffs

| Поле | Тип | Default | Описание |
|------|-----|---------|----------|
| `period_unit` | ENUM | 'month' | Единица периода |
| `period_value` | INT | 1 | Количество единиц |
| `subscription_fee` | INT | 100 | Абонплата (токенов) |
| `min_payment` | DECIMAL(10,2) | 200.00 | Минимальный платёж |

### Constraints

- `period_value > 0`
- `subscription_fee >= 0`
- `min_payment > 0`

---

## Новые зависимости

```
python-dateutil>=2.8.0
```

---

## Файлы изменены

### Models
- `backend/src/db/models/tariff.py` — PeriodUnit enum, новые поля

### Services
- `backend/src/services/billing_service.py` — calculate_subscription_end(), process_m11_payment()
- `backend/src/services/subscription_service.py` — tariff-based renewal
- `backend/src/services/notification_service.py` — обновлённые тексты

### Bot
- `backend/src/bot/handlers/balance.py` — новый экран баланса
- `backend/src/bot/handlers/start.py` — упрощённое меню
- `backend/src/bot/handlers/tariffs.py` — редирект на баланс
- `backend/src/bot/handlers/help.py` — новый текст справки
- `backend/src/bot/keyboards/balance.py` — кнопки пополнения
- `backend/src/bot/keyboards/main_menu.py` — 2 кнопки
- `backend/src/bot/states/payment.py` — PaymentStates FSM

### Repositories
- `backend/src/db/repositories/tariff_repository.py` — get_default_tariff()

---

## Breaking Changes

- Команда `/tariffs` больше не показывает список тарифов
- Уведомления ссылаются на `/balance` вместо `/tariffs`
- Для автопродления теперь требуется активный тариф в базе

---

## Откат

```bash
# Откатить миграцию
alembic downgrade 006_subscription_tx_type

# Откатить код
git checkout HEAD~1 -- backend/src/
```

---

## Проверка после деплоя

1. `/start` показывает 2 кнопки (Баланс, Помощь)
2. Кнопка "Баланс" показывает экран с балансом и статусом
3. `/tariffs` редиректит на экран баланса
4. Пополнение на минимальную сумму создаёт invoice
5. "Другая сумма" принимает ввод >= min_payment

# Track Cost Integration

Version: 1.0
Status: Implemented
Created: 2026-01-13

> Интеграция динамического учета стоимости выполнения треков Runner Framework с системой биллинга. Заменяет фиксированное списание токенов на расчет на основе фактической стоимости выполнения с применением мультипликатора.

## Обзор

### Проблема
До реализации система списывала фиксированную стоимость (1 токен) за каждый запуск трека независимо от реальных затрат на API вызовы к LLM.

### Решение
Динамический расчет стоимости на основе события `track_cost` от Runner Framework:
```
final_cost = track_cost.total_cost × COST_MULTIPLIER
```

Где `total_cost` — фактическая стоимость в рублях, `COST_MULTIPLIER` — настраиваемая наценка (по умолчанию 3.14).

## Архитектура

### Поток данных

```
1. User запускает трек (/cv или /apply)
   ↓
2. Runner выполняет трек, собирает метрики
   ↓
3. Runner отправляет SSE событие track_cost
   {
     "type": "track_cost",
     "total_cost": 0.05,
     "currency": "RUB",
     "api_calls": 3,
     "total_tokens": 150,
     ...
   }
   ↓
4. RunnerClient парсит событие → StreamMessage
   ↓
5. CVService/ApplyService получает track_cost
   ↓
6. Применение мультипликатора: 0.05 × 3.14 = 0.16
   ↓
7. TokenService.spend_tokens(amount=0.16)
   ↓
8. Transaction создается с metadata
   ↓
9. User получает "Потрачено 0.16 токенов"
```

## Компоненты

### TrackCost (Data Model)

**Файл**: [`backend/src/services/runner/models.py:7`](../../backend/src/services/runner/models.py#L7)

```python
@dataclass
class TrackCost:
    """Track cost data from Runner Framework."""
    total_cost: float           # Стоимость в валюте
    currency: str               # Код валюты (RUB)
    api_calls: int             # Количество API запросов
    total_tokens: int          # Всего токенов
    prompt_tokens: int | None  # Токены промпта
    completion_tokens: int | None  # Токены ответа
    free_requests: int = 0     # Бесплатные запросы
    node_costs: dict | None    # Детализация по узлам
```

### StreamMessage.as_track_cost()

**Файл**: [`backend/src/services/runner/models.py:77`](../../backend/src/services/runner/models.py#L77)

Парсит SSE событие `track_cost` в структурированный `TrackCost` объект.

**Обработка ошибок**:
- Возвращает `None` если `type != "track_cost"`
- Возвращает `None` если `track_cost_data` отсутствует
- Возвращает `None` при `KeyError` или `TypeError`

### RunnerClient Event Parsing

**Файл**: [`backend/src/services/runner/client.py:217`](../../backend/src/services/runner/client.py#L217)

```python
if msg_type == "track_cost":
    yield StreamMessage(
        type="track_cost",
        content="",
        track_cost_data=msg,  # Весь payload сохраняется
    )
    continue
```

### Service Integration (CVService, ApplyService)

**Файлы**:
- [`backend/src/services/cv_service.py:154`](../../backend/src/services/cv_service.py#L154)
- [`backend/src/services/apply_service.py:164`](../../backend/src/services/apply_service.py#L164)

**Состояние сервиса**:
```python
self._track_cost: float | None = None
```

**Lifecycle**:
1. **Инициализация**: `_track_cost = None`
2. **Получение события**: `_track_cost = cost_data.total_cost`
3. **Списание**: вычисление `final_cost`, вызов `spend_tokens()`
4. **Сброс**: `_track_cost = None`

**Обработка в стриме**:
```python
if message.type == "track_cost":
    cost_data = message.as_track_cost()
    if cost_data:
        self._track_cost = cost_data.total_cost
        logger.info(f"Track cost received: {cost_data.total_cost}")
    return "continue"
```

**Списание после завершения**:
```python
if success:
    # Fallback если событие не пришло
    if self._track_cost is None:
        logger.warning("Track completed without cost data")
        self._track_cost = 0.0

    # Применение мультипликатора
    from src.core.config import settings
    final_cost = self._track_cost * settings.cost_multiplier
    final_cost = round(final_cost, 2)  # Округление до копеек

    # Списание
    await self.token_service.spend_tokens(
        user_id=user_id,
        amount=final_cost,
        description="Анализ CV",
        metadata={
            "task_id": task_id,
            "cost_raw": self._track_cost,
            "cost_multiplier": settings.cost_multiplier,
            "cost_final": final_cost,
        },
    )

    # Уведомление пользователя
    if final_cost > 0:
        await self.bot.send_message(chat_id, f"Потрачено {final_cost} токенов")

    # Сброс состояния
    self._track_cost = None
```

### TokenService Updates

**Файл**: [`backend/src/services/token_service.py`](../../backend/src/services/token_service.py)

**Изменения**:
- `amount: int` → `amount: float` (строки 99, 122)
- `tokens_spent: int` → `tokens_spent: float` (строка 42)
- `balance_before/after: int` → `float` (строки 43-44)

**Новое поведение при недостатке баланса**:
```python
# БЫЛО: raise InsufficientBalanceError
# СТАЛО: логирование + продолжение
if user.token_balance < amount:
    logger.warning(f"User {user_id} balance will go negative: ...")
    # Продолжаем списание, баланс уходит в минус
```

**Защита от повторных запусков**:
```python
# В check_balance()
elif user.token_balance < 0:  # Только при отрицательном
    can_spend = False
    reason = "Insufficient balance (negative)"
```

## База данных

### Migration: 542d7e567590

**Файл**: [`backend/migrations/versions/542d7e567590_support_fractional_tokens_and_negative_.py`](../../backend/migrations/versions/542d7e567590_support_fractional_tokens_and_negative_.py)

**Изменения**:

| Таблица | Колонка | Было | Стало |
|---------|---------|------|-------|
| `users` | `token_balance` | `Integer` | `Float` |
| `users` | constraint | `>= 0` | `>= -1000.0` |
| `transactions` | `tokens_delta` | `Integer` | `Float` |
| `transactions` | `balance_after` | `Integer` | `Float` |

**Применение**:
```bash
cd backend
alembic upgrade head
```

**Откат**:
```bash
alembic downgrade -1
```

### User Model

**Файл**: [`backend/src/db/models/user.py:39`](../../backend/src/db/models/user.py#L39)

```python
token_balance: Mapped[float] = mapped_column(
    Float,
    default=0.0,
    nullable=False,
)

__table_args__ = (
    CheckConstraint("token_balance >= -1000.0", name="token_balance_limit"),
)
```

### Transaction Model

**Файл**: [`backend/src/db/models/transaction.py:51`](../../backend/src/db/models/transaction.py#L51)

```python
tokens_delta: Mapped[float] = mapped_column(Float, nullable=False)
balance_after: Mapped[float] = mapped_column(Float, nullable=False)
```

**Metadata пример**:
```json
{
  "task_id": "abc123",
  "cost_raw": 0.05,
  "cost_multiplier": 3.14,
  "cost_final": 0.16
}
```

## Конфигурация

### Settings

**Файл**: [`backend/src/core/config.py:145`](../../backend/src/core/config.py#L145)

```python
cost_multiplier: float = Field(
    default=3.14,
    description="Multiplier for track execution costs",
)
```

### Environment

**Файл**: [`.env.example:51`](../../.env.example#L51)

```bash
# Token spending
COST_MULTIPLIER=3.14
```

**Изменение мультипликатора**:
1. Обновить значение в `.env`
2. Перезапустить сервис
3. Новые треки используют обновленное значение

## API Изменения

### API Schemas

**Файл**: [`backend/src/api/schemas/tokens.py`](../../backend/src/api/schemas/tokens.py)

**Обновленные типы**:
```python
class TokenBalanceResponse(BaseModel):
    token_balance: float  # было int

class SpendTokensRequest(BaseModel):
    amount: float  # было int

class SpendTokensResponse(BaseModel):
    tokens_spent: float  # было int
    balance_before: float  # было int
    balance_after: float  # было int
```

## Тестовый сценарий

### Успешное выполнение

```python
# Initial state
user.token_balance = 10.0

# /cv command
# Runner executes track
# Runner sends: {"type": "track_cost", "total_cost": 0.05}

# Service calculates
raw_cost = 0.05
final_cost = 0.05 * 3.14 = 0.157 → round → 0.16

# TokenService processes
user.token_balance = 10.0 - 0.16 = 9.84

# Transaction created
{
  "tokens_delta": -0.16,
  "balance_after": 9.84,
  "metadata": {
    "cost_raw": 0.05,
    "cost_multiplier": 3.14,
    "cost_final": 0.16
  }
}

# User notification
"Потрачено 0.16 токенов"
```

### Отрицательный баланс

```python
# Initial state
user.token_balance = 0.05

# Track cost = 0.10 RUB
final_cost = 0.10 * 3.14 = 0.31

# Списание происходит
user.token_balance = 0.05 - 0.31 = -0.26  # ✅ Разрешено

# Warning логируется
logger.warning("User 123 balance will go negative: current=0.05, spend=0.31, result=-0.26")

# Новый запуск блокируется
can_spend = False  # token_balance < 0
reason = "Insufficient balance (negative)"
```

### Track без cost data

```python
# Runner не отправил track_cost (старая версия, ошибка)
# self._track_cost остается None

# При списании
if self._track_cost is None:
    logger.warning("Track completed without cost data")
    self._track_cost = 0.0

final_cost = 0.0 * 3.14 = 0.0

# Списание 0 токенов
# Сообщение не отправляется (if final_cost > 0)
```

## Edge Cases

| Ситуация | Поведение |
|----------|-----------|
| `track_cost` не пришел | Списание 0.0 токенов, warning в логе |
| `total_cost = 0.0` | Списание 0.0, уведомление не отправляется |
| Баланс уходит в минус | ✅ Разрешено, warning в логе |
| Баланс < 0 при запуске | ❌ Запрещено через `can_spend` |
| Изменен мультипликатор | Применяется сразу, без перезапуска кода |
| `track_cost` парсинг ошибка | Возврат `None`, fallback на 0.0 |
| Concurrent track execution | Каждый трек хранит `_track_cost` в instance |

## Мониторинг

### Логи

**Успешное получение**:
```
INFO: Track cost received: 0.05 RUB
```

**Списание**:
```
INFO: Charging user: raw_cost=0.05, multiplier=3.14, final_cost=0.16
INFO: Tokens spent: user=123, amount=0.16, balance=10.0->9.84, tx=uuid
```

**Warning**:
```
WARNING: Track completed without cost data
WARNING: User 123 balance will go negative: current=0.05, spend=0.31, result=-0.26
```

### Метрики для мониторинга

- Среднее значение `cost_raw`
- Среднее значение `cost_final`
- Частота отрицательного баланса
- Частота отсутствия `track_cost`

## Зависимости

### От модулей

- **Runner Framework**: источник события `track_cost`
- **TokenService**: списание дробных токенов
- **PostgreSQL**: хранение Float значений

### Используется в

- `CVService` - анализ резюме
- `ApplyService` - создание откликов
- Любые будущие сервисы, использующие Runner треки

## Миграция с фиксированной стоимости

### Backward Compatibility

✅ **Старые транзакции совместимы**:
- Integer значения автоматически конвертируются в Float
- `1 → 1.0`, `100 → 100.0`

✅ **Старые треки без `track_cost`**:
- Fallback на `0.0`
- Система продолжает работать

### Breaking Changes

❌ **API контракты**:
- Клиенты должны ожидать `float` вместо `int`
- JSON: `{"token_balance": 9.84}` вместо `{"token_balance": 10}`

❌ **Баланс пользователя**:
- Может быть отрицательным
- Клиенты должны обрабатывать `-0.5`, а не только `0`

## Troubleshooting

### Problem: Списание всегда 0.0

**Причина**: Runner не отправляет `track_cost`

**Проверка**:
```bash
# В логах должно быть
grep "Track cost received" logs/app.log

# Если нет - проверить Runner
curl http://runner:8000/health
```

**Решение**: Обновить Runner Framework до версии с поддержкой `track_cost`

### Problem: Баланс не уходит в минус

**Причина**: Старая версия `TokenService`

**Проверка**:
```python
# Должно быть в token_service.py:167
if user.token_balance < amount:
    logger.warning(...)
    # НЕ raise InsufficientBalanceError
```

**Решение**: Применить миграцию кода и перезапустить

### Problem: Мультипликатор не применяется

**Причина**: Не установлен `COST_MULTIPLIER` в `.env`

**Проверка**:
```bash
echo $COST_MULTIPLIER  # Должно быть 3.14
```

**Решение**:
```bash
echo "COST_MULTIPLIER=3.14" >> .env
# Перезапустить сервис
```

## См. также

- [Bot Cost Tracking Integration](./bot-cost-tracking-integration.md) - Спецификация Runner Framework
- [Billing Module](./billing.md) - Общая система биллинга
- [Database Schema](../architecture.md) - Схема БД

## Changelog

| Версия | Дата | Изменения |
|--------|------|-----------|
| 1.0 | 2026-01-13 | Первая реализация: Float токены, track_cost, мультипликатор |

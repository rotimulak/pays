# Fullstack Developer (Python + Docusaurus)

## Стек

| Слой | Технология | Паттерны |
|------|------------|----------|
| Bot | aiogram 3.x | Router, FSM, Middleware, CallbackData |
| API | FastAPI | Depends, Pydantic v2, Background Tasks |
| ORM | SQLAlchemy 2.x async | Repository, Unit of Work, selectinload |
| DB | PostgreSQL | Индексы, JSONB, транзакции |
| Migrations | Alembic | Auto-generate, data migrations |
| Docs | Docusaurus 3.x | MDX, React components |

---

## Принципы

| Принцип | Правило |
|---------|---------|
| YAGNI | Только то, что нужно сейчас |
| KISS | Простое решение лучше умного |
| DRY | Не дублировать логику |
| Fail Fast | Ошибка должна проявиться рано |
| Explicit > Implicit | Никаких магических значений |
| Separation of Concerns | Handler ≠ бизнес-логика |
| Idempotency | Повторный запрос = тот же результат |

---

## Архитектура

```
src/
├── bot/
│   ├── handlers/      # Роутеры по доменам
│   ├── keyboards/     # Reply и Inline
│   ├── middlewares/   # Throttling, auth, DB session
│   ├── states/        # FSM
│   └── filters/
├── api/
│   ├── routes/
│   ├── dependencies/
│   └── schemas/       # Pydantic
├── services/          # Бизнес-логика
├── db/
│   ├── models/
│   ├── repositories/
│   └── session.py
├── core/
│   ├── config.py
│   └── exceptions.py
└── tests/
```

**Поток:** Handler/Route → Service → Repository → Database

---

## Слои

### Handler / Route
- Валидация (Pydantic)
- Вызов сервиса
- Формирование ответа
- **НЕ содержит:** бизнес-логику, прямые запросы к БД

### Service
- Бизнес-логика
- Координация репозиториев
- Транзакции
- **НЕ содержит:** HTTP/Telegram-специфику

### Repository
- CRUD
- Сложные запросы
- **НЕ содержит:** бизнес-логику

---

## Решения

### Sync vs Async
```
async: I/O (БД, HTTP), aiogram/FastAPI
sync: CPU-bound → thread pool
```

### Состояние
```
FSM          → Многошаговые диалоги
Database     → Персистентные данные
Redis        → Кэш, rate limiting, сессии
Environment  → Конфиг, секреты
```

### Ошибки
```
Handler  → Ловить, логировать, user-friendly ответ
Service  → Пробрасывать / domain exception
External → Retry + backoff + timeout
```

---

## Контрольные вопросы

### Код
- Какой контракт? Вход, выход, ошибки?
- Идемпотентная операция?
- Что если вызов придёт дважды?
- Где граница транзакции?

### БД
- Какие индексы нужны?
- Это N+1?
- Нужна миграция данных?

### Бот
- FSM или callback_data?
- Таймаут диалога?
- Есть throttling?

---

## Антипаттерны

| Антипаттерн | Решение |
|-------------|---------|
| `except Exception: pass` | Конкретные исключения, логировать |
| Запросы в цикле (N+1) | selectinload, batch queries |
| Секреты в коде | Environment, secrets manager |
| `time.sleep()` в async | `asyncio.sleep()` |
| Бизнес-логика в handler | Выносить в Service |
| Нет таймаутов | `asyncio.timeout()` |

---

## Чек-лист перед PR

### Код
- [ ] `mypy --strict`
- [ ] `ruff check && ruff format`
- [ ] Тесты для критичных путей

### Данные
- [ ] Миграция создана и протестирована
- [ ] Нет N+1
- [ ] Индексы для новых запросов

### Безопасность
- [ ] Нет хардкода секретов
- [ ] Входные данные валидируются
- [ ] Ошибки не раскрывают внутренности

### Production
- [ ] Логирование
- [ ] Edge cases обработаны
- [ ] Идемпотентность где требуется

---

## Code Reference

### Typed callback (aiogram)
```python
class PaymentCallback(CallbackData, prefix="pay"):
    action: str
    amount: int

@router.callback_query(PaymentCallback.filter(F.action == "confirm"))
async def on_confirm(callback: CallbackQuery, callback_data: PaymentCallback):
    ...
```

### Repository + DI (FastAPI)
```python
class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

async def get_user_repo(session: AsyncSession = Depends(get_session)) -> UserRepository:
    return UserRepository(session)
```

### Pydantic v2
```python
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    created_at: datetime
```

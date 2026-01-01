# Fullstack Developer (Python + Docusaurus)

## Миссия

Разрабатывать надёжные, типизированные и масштабируемые решения. Писать код, который легко поддерживать, тестировать и расширять.

---

## Принципы

### Фундаментальные

| Принцип | Применение |
|---------|------------|
| **YAGNI** | Не пиши код "на будущее". Реализуй только то, что нужно сейчас |
| **KISS** | Простое решение лучше умного. Сложность — враг надёжности |
| **DRY** | Дублирование логики — источник багов. Но не путай с похожим кодом |
| **Fail Fast** | Ошибка должна проявиться как можно раньше, а не замаскироваться |
| **Explicit > Implicit** | Явное лучше неявного. Никаких магических значений и скрытых зависимостей |

### Архитектурные

| Принцип | Применение |
|---------|------------|
| **Separation of Concerns** | Handler не содержит бизнес-логику, репозиторий не знает про HTTP |
| **Single Responsibility** | Один модуль — одна причина для изменения |
| **Dependency Inversion** | Зависимость от абстракций (интерфейсов), не от реализаций |
| **Composition over Inheritance** | Собирай поведение из компонентов, а не наследуй |

### Операционные

| Принцип | Применение |
|---------|------------|
| **Idempotency** | Повторный запрос даёт тот же результат. Критично для платежей и webhooks |
| **Graceful Degradation** | Сбой части системы не роняет всё. Fallback'и и circuit breakers |
| **Observability** | Если не можешь измерить — не можешь улучшить. Логи, метрики, трейсы |
| **Zero Downtime** | Деплой без прерывания сервиса. Миграции совместимы с предыдущей версией |

---

## Фреймворки принятия решений

### Выбор подхода к задаче

```
1. Это уже решено в проекте?
   → Да: используй существующий паттерн
   → Нет: продолжай

2. Есть стандартное решение в экосистеме?
   → Да: используй его (Pydantic, SQLAlchemy patterns)
   → Нет: продолжай

3. Решение нужно в нескольких местах?
   → Да: абстрагируй (но не раньше 3-го использования)
   → Нет: напиши простой inline-код
```

### Sync vs Async

```
Использовать async когда:
├── I/O операции (БД, HTTP, файлы)
├── Нужна конкурентность (много одновременных запросов)
└── Работа с aiogram/FastAPI (они async-first)

Использовать sync когда:
├── CPU-bound вычисления (вынести в thread pool)
├── Простые скрипты и утилиты
└── Библиотека не поддерживает async
```

### Где хранить состояние

```
FSM (aiogram)     → Многошаговые диалоги с пользователем
Session/Cookie    → Аутентификация веб-пользователей
Database          → Персистентные данные, история, аудит
Redis/Cache       → Временные данные, rate limiting, сессии бота
Environment       → Конфигурация, секреты
```

### Обработка ошибок

```
Уровень          │ Стратегия
─────────────────┼──────────────────────────────────
Handler/Route    │ Ловить, логировать, возвращать user-friendly ответ
Service          │ Пробрасывать или оборачивать в domain exception
Repository       │ Пробрасывать DB-ошибки как есть
External API     │ Retry с backoff, timeout, fallback
```

---

## Технологический стек

| Слой | Технология | Ключевые паттерны |
|------|------------|-------------------|
| **Bot** | aiogram 3.x | Router, FSM, Middleware, CallbackData |
| **API** | FastAPI | Depends, Pydantic v2, Background Tasks |
| **ORM** | SQLAlchemy 2.x async | Repository, Unit of Work, selectinload |
| **DB** | PostgreSQL | Индексы, JSONB, транзакции |
| **Migrations** | Alembic | Auto-generate, data migrations |
| **Docs** | Docusaurus 3.x | MDX, React components |

---

## Архитектура

```
src/
├── bot/
│   ├── handlers/      # Роутеры по доменам (payments, users, admin)
│   ├── keyboards/     # Reply и Inline клавиатуры
│   ├── middlewares/   # Throttling, auth, DB session injection
│   ├── states/        # FSM состояния
│   └── filters/       # Кастомные фильтры
├── api/
│   ├── routes/        # FastAPI роутеры
│   ├── dependencies/  # Depends (session, current_user, etc.)
│   └── schemas/       # Pydantic request/response модели
├── services/          # Бизнес-логика (PaymentService, UserService)
├── db/
│   ├── models/        # SQLAlchemy модели
│   ├── repositories/  # Абстракция доступа к данным
│   └── session.py     # async_sessionmaker
├── core/
│   ├── config.py      # pydantic-settings
│   └── exceptions.py  # Domain exceptions
└── tests/
```

### Поток данных

```
[Telegram/HTTP] → Handler/Route → Service → Repository → Database
                      ↓               ↓
                  Validation      Business Logic
                  (Pydantic)      (Domain rules)
```

---

## Паттерны по слоям

### Handler / Route
- Валидация входных данных (Pydantic)
- Вызов сервиса
- Формирование ответа
- **Не содержит:** бизнес-логику, прямые запросы к БД

### Service
- Бизнес-логика и правила домена
- Координация между репозиториями
- Транзакции (Unit of Work)
- **Не содержит:** HTTP-специфику, Telegram-специфику

### Repository
- CRUD операции
- Сложные запросы (joins, aggregations)
- **Не содержит:** бизнес-логику, валидацию

---

## Контрольные вопросы

### Перед написанием кода

| Вопрос | Почему важен |
|--------|--------------|
| Какой контракт? Вход, выход, ошибки? | Определяет интерфейс до реализации |
| Это идемпотентная операция? | Критично для webhooks, ретраев |
| Что если вызов придёт дважды? | Защита от дублей |
| Где граница транзакции? | Консистентность данных |

### При работе с БД

| Вопрос | Почему важен |
|--------|--------------|
| Какие индексы нужны? | Производительность на проде |
| Это N+1? | Самый частый performance-баг |
| Нужна ли миграция данных? | Zero-downtime deployment |

### При работе с ботом

| Вопрос | Почему важен |
|--------|--------------|
| FSM или callback_data? | FSM для многошаговых, callback для простых |
| Как обрабатываем таймаут диалога? | Пользователь может уйти посреди FSM |
| Есть throttling? | Telegram банит за спам |

---

## Code Reference

### Типизированный callback (aiogram)

```python
class PaymentCallback(CallbackData, prefix="pay"):
    action: str
    amount: int

@router.callback_query(PaymentCallback.filter(F.action == "confirm"))
async def on_confirm(callback: CallbackQuery, callback_data: PaymentCallback):
    ...
```

### Repository + Dependency Injection (FastAPI)

```python
class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

async def get_user_repo(
    session: AsyncSession = Depends(get_session)
) -> UserRepository:
    return UserRepository(session)
```

### Pydantic v2 схема

```python
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    created_at: datetime
```

---

## Антипаттерны

| Антипаттерн | Риск | Решение |
|-------------|------|---------|
| `except Exception: pass` | Скрытые баги | Ловить конкретные исключения, логировать |
| Запросы к БД в цикле | N+1, медленно | `selectinload`, `joinedload`, batch queries |
| Секреты в коде | Утечка credentials | Environment variables, secrets manager |
| `time.sleep()` в async | Блокировка event loop | `asyncio.sleep()` |
| Бизнес-логика в handler | Нетестируемо, дублирование | Выносить в Service |
| Отсутствие таймаутов | Зависание на внешних вызовах | `asyncio.timeout()`, httpx timeout |

---

## Чек-лист перед PR

### Код
- [ ] Типы проверены (`mypy --strict`)
- [ ] Линтеры пройдены (`ruff check && ruff format`)
- [ ] Тесты написаны для критичных путей

### Данные
- [ ] Миграция создана и протестирована
- [ ] Нет N+1 запросов
- [ ] Индексы для новых запросов

### Безопасность
- [ ] Нет хардкода секретов
- [ ] Входные данные валидируются
- [ ] Ошибки не раскрывают внутренности

### Production
- [ ] Логирование для диагностики
- [ ] Edge cases обработаны
- [ ] Идемпотентность где требуется

---

## Инструменты

| Задача | Инструмент |
|--------|------------|
| Типизация | mypy --strict |
| Линтинг | ruff (заменяет black, isort, flake8) |
| Тесты | pytest, pytest-asyncio, httpx |
| Debug | ipdb, rich.traceback |
| БД | pgcli, DBeaver |
| API | Swagger UI (встроен в FastAPI) |

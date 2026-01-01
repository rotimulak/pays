# M1: Core Models & Database

## Цель

Создать базовую инфраструктуру проекта: модели БД, миграции, конфигурацию. После этого milestone можно подключаться к БД и работать с основными сущностями.

---

## Задачи

### 1.1 Инициализация проекта

- [ ] Создать структуру `backend/src/` согласно архитектуре
- [ ] Настроить `pyproject.toml` / `requirements.txt` с зависимостями
- [ ] Создать `core/config.py` с Pydantic Settings (DATABASE_URL, etc.)
- [ ] Настроить `core/exceptions.py` с базовыми исключениями

### 1.2 Database Layer

- [ ] Создать `db/session.py` с async engine и session factory
- [ ] Настроить Alembic для миграций

### 1.3 Модели SQLAlchemy

- [ ] `models/user.py` — User (id, username, first_name, token_balance, balance_version, subscription_end, timestamps)
- [ ] `models/tariff.py` — Tariff (id, slug, name, description, price, tokens, subscription_days, sort_order, is_active, version, timestamps)
- [ ] `models/invoice.py` — Invoice (id, user_id, tariff_id, promo_code_id, amount, tokens, subscription_days, status, idempotency_key, etc.)
- [ ] `models/transaction.py` — Transaction (id, user_id, type, tokens_delta, balance_after, description, invoice_id, metadata, created_at)
- [ ] `models/promo_code.py` — PromoCode (id, code, discount_type, discount_value, max_uses, uses_count, valid_from, valid_until, tariff_id, is_active)
- [ ] `models/audit_log.py` — AuditLog (id, user_id, action, entity_type, entity_id, old_value, new_value, metadata, created_at)

### 1.4 Миграции

- [ ] Сгенерировать initial migration со всеми таблицами
- [ ] Добавить CHECK constraints (token_balance >= 0, amount > 0, etc.)
- [ ] Добавить индексы согласно architecture.md

### 1.5 Repositories (базовые)

- [ ] `db/repositories/user_repository.py` — CRUD для User
- [ ] `db/repositories/tariff_repository.py` — CRUD для Tariff

---

## Definition of Done (DoD)

- [ ] Проект запускается без ошибок
- [ ] `alembic upgrade head` успешно создаёт все таблицы
- [ ] Все CHECK constraints и FK constraints созданы
- [ ] Индексы созданы согласно спецификации
- [ ] Unit-тесты для моделей проходят
- [ ] `mypy --strict` на моделях без ошибок
- [ ] `ruff check && ruff format` без замечаний

---

## Артефакты

```
backend/
├── src/
│   ├── core/
│   │   ├── config.py
│   │   └── exceptions.py
│   ├── db/
│   │   ├── session.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── tariff.py
│   │   │   ├── invoice.py
│   │   │   ├── transaction.py
│   │   │   ├── promo_code.py
│   │   │   └── audit_log.py
│   │   └── repositories/
│   │       ├── user_repository.py
│   │       └── tariff_repository.py
│   └── tests/
│       └── test_models.py
├── migrations/
│   └── versions/
│       └── 001_initial.py
├── alembic.ini
├── pyproject.toml
└── requirements.txt
```

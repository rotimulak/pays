# M1: Core Models & Database

## Обзор

Создание базовой инфраструктуры проекта: модели БД, миграции, конфигурация. После этого milestone можно подключаться к БД и работать с основными сущностями.

---

## Epics & Tasks

| Epic | Задачи | Оценка |
|------|--------|--------|
| [E1.1 — Project Setup](e1.1-project-setup.md) | Структура, зависимости, config | 4 tasks |
| [E1.2 — Database Layer](e1.2-database-layer.md) | Session, engine, Alembic | 2 tasks |
| [E1.3 — SQLAlchemy Models](e1.3-models.md) | User, Tariff, Invoice, Transaction, PromoCode, AuditLog | 6 tasks |
| [E1.4 — Migrations](e1.4-migrations.md) | Initial migration, constraints, indexes | 3 tasks |
| [E1.5 — Repositories](e1.5-repositories.md) | User и Tariff repositories | 2 tasks |

---

## Definition of Done

- [ ] Проект запускается без ошибок
- [ ] `alembic upgrade head` успешно создаёт все таблицы
- [ ] Все CHECK constraints и FK constraints созданы
- [ ] Индексы созданы согласно спецификации
- [ ] Unit-тесты для моделей проходят
- [ ] `mypy --strict` на моделях без ошибок
- [ ] `ruff check && ruff format` без замечаний

---

## Зависимости

- Нет (первый milestone)

## Разблокирует

- M2: Telegram Bot & Auth

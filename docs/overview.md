# Telegram Billing Template Service

## Краткое описание

**Telegram Billing Template** — готовый шаблон микросервиса для быстрого запуска SaaS-продуктов с монетизацией через Telegram. Включает полноценную биллинг-систему на базе Робокассы, управление подписками и токенами, учёт балансов пользователей, а также документацию и лендинг на Docusaurus.

---

## Ключевые возможности

- **Авторизация** через Telegram-аккаунт (user_id)
- **Биллинг** через Робокассу с автоматической обработкой webhook'ов
- **Два типа оплаты**: подписка (время) + токены (расходуемые единицы)
- **История операций** и транзакций
- **Готовый Telegram-бот** с командами управления
- **Лендинг и документация** на базе Docusaurus

---

## Стек технологий

### Backend (Python)

| Компонент | Технология |
|-----------|------------|
| Telegram Bot | **aiogram 3.x** |
| HTTP API / Webhooks | **FastAPI** |
| ORM | **SQLAlchemy 2.x** (async) |
| База данных | **PostgreSQL** |
| Миграции | **Alembic** |

> **Примечание:** Pydantic v2 устанавливается автоматически как зависимость aiogram и FastAPI.

> **Почему aiogram?**
> - Полностью асинхронный (asyncio native)
> - Встроенная FSM для сложных диалогов
> - Отличная типизация с Pydantic
> - Активное сообщество и быстрые обновления под новый Bot API
> - Бесшовная интеграция с FastAPI

### Frontend

| Компонент | Технология |
|-----------|------------|
| Лендинг + Docs | **Docusaurus 3.x** (React/TypeScript) |

### Деплой

- **Docker** + **docker-compose**
- Опционально: CI/CD через GitHub Actions

---

## Структура проекта

```
telegram-billing-template/
├── backend/                    # Python
│   ├── src/
│   │   ├── bot/                # Telegram-бот
│   │   ├── api/                # HTTP endpoints + webhooks
│   │   ├── services/           # Бизнес-логика (billing, users)
│   │   ├── models/             # Модели БД
│   │   └── config/             # Конфигурация
│   ├── migrations/
│   ├── Dockerfile
│   └── requirements.txt
│
├── docs/                       # Docusaurus
│   ├── docusaurus.config.js
│   ├── src/
│   ├── docs/
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Быстрый старт

```bash
# Клонировать репозиторий
git clone https://github.com/your-org/telegram-billing-template.git
cd telegram-billing-template

# Скопировать переменные окружения
cp .env.example .env

# Заполнить .env:
# - TELEGRAM_BOT_TOKEN
# - ROBOKASSA_LOGIN, ROBOKASSA_PASSWORD1, ROBOKASSA_PASSWORD2
# - DATABASE_URL

# Запустить
docker-compose up -d
```

---

## Лицензия

MIT

---

## См. также

- [Архитектура](architecture.md) — схема БД и жизненные циклы
- [Telegram-бот](bot.md) — команды и меню
- [Интеграция с Робокассой](robokassa-adapter.md) — платежи и webhook'и
- [Безопасность](security.md) — валидация, rate limiting, секреты
- [Деплой](deployment.md) — Docker, переменные окружения
- [Docusaurus](docusaurus.md) — лендинг и документация

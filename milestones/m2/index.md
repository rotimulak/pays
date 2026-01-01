# M2: Telegram Bot & Auth

## Обзор

Запуск Telegram-бота с авторизацией пользователей. Пользователь может начать диалог с ботом, автоматически регистрируется в системе и видит свой профиль.

---

## Epics & Tasks

| Epic | Задачи | Оценка |
|------|--------|--------|
| [E2.1 — Bot Foundation](e2.1-bot-foundation.md) | Инициализация бота, dispatcher, middlewares | 3 tasks |
| [E2.2 — User Handlers](e2.2-user-handlers.md) | /start, /profile, /help handlers | 3 tasks |
| [E2.3 — User Service](e2.3-user-service.md) | Сервис работы с пользователями | 2 tasks |
| [E2.4 — Keyboards & Entry Point](e2.4-keyboards-entry.md) | Клавиатуры и запуск бота | 2 tasks |

---

## Definition of Done

- [ ] Бот запускается и отвечает на `/start`
- [ ] При первом `/start` пользователь создаётся в БД
- [ ] При повторном `/start` пользователь не дублируется
- [ ] `/profile` показывает telegram_id, баланс токенов, статус подписки
- [ ] Middleware корректно передаёт session в handlers
- [ ] Логирование входящих команд
- [ ] `mypy --strict` без ошибок
- [ ] `ruff check && ruff format` без замечаний

---

## Зависимости

- M1: Core Models & Database

## Разблокирует

- M3: Tariffs & Invoices

# M2: Telegram Bot & Auth

## Цель

Запустить Telegram-бота с авторизацией пользователей. Пользователь может начать диалог с ботом, автоматически регистрируется в системе и видит свой профиль.

---

## Задачи

### 2.1 Базовая структура бота

- [ ] Создать `bot/__init__.py` с инициализацией Bot и Dispatcher
- [ ] Создать `bot/middlewares/db_session.py` — middleware для DB session
- [ ] Создать `bot/middlewares/auth.py` — middleware для auto-register пользователя

### 2.2 Handlers

- [ ] `bot/handlers/start.py` — команда `/start`, приветствие, создание пользователя
- [ ] `bot/handlers/profile.py` — команда `/profile` или `/me`, показ баланса и подписки
- [ ] `bot/handlers/help.py` — команда `/help`

### 2.3 Services

- [ ] `services/user_service.py` — get_or_create_user, get_user_profile

### 2.4 Keyboards

- [ ] `bot/keyboards/main_menu.py` — главное меню (Reply keyboard)

### 2.5 Entry Point

- [ ] Создать `main.py` для запуска бота (polling mode для разработки)
- [ ] Настроить graceful shutdown

---

## Definition of Done (DoD)

- [ ] Бот запускается и отвечает на `/start`
- [ ] При первом `/start` пользователь создаётся в БД
- [ ] При повторном `/start` пользователь не дублируется
- [ ] `/profile` показывает telegram_id, баланс токенов, статус подписки
- [ ] Middleware корректно передаёт session в handlers
- [ ] Логирование входящих команд
- [ ] `mypy --strict` без ошибок
- [ ] `ruff check && ruff format` без замечаний

---

## Артефакты

```
backend/src/
├── bot/
│   ├── __init__.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py
│   │   ├── profile.py
│   │   └── help.py
│   ├── keyboards/
│   │   └── main_menu.py
│   └── middlewares/
│       ├── __init__.py
│       ├── db_session.py
│       └── auth.py
├── services/
│   └── user_service.py
└── main.py
```

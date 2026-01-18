# Robotest

E2E тестирование Telegram-бота через Telegram User API.

## Что это?

Robotest — автоматические тесты, которые взаимодействуют с ботом как реальный пользователь Telegram. Отправляют команды, проверяют ответы, нажимают кнопки.

**Роботест** — тестовый аккаунт Telegram, от лица которого выполняются тесты.

## Быстрый старт

### 1. Получите Telegram API credentials

1. Откройте https://my.telegram.org/apps
2. Войдите с номером телефона роботеста
3. Создайте приложение (App title: `Robotest`)
4. Скопируйте `api_id` и `api_hash`

### 2. Установите зависимости

```bash
cd robotest
pip install -e ".[dev]"
```

### 3. Настройте .env

```bash
cp .env.example .env
```

Заполните `.env`:
```env
TELEGRAM_API_ID=<ваш api_id>
TELEGRAM_API_HASH=<ваш api_hash>
ROBOTEST_PHONE=<номер телефона роботеста>
BOT_USERNAME=smartheadhunterbot
```

### 4. Авторизуйте роботест

⚠️ **ВАЖНО:** Авторизацию нужно запускать **ВРУЧНУЮ в терминале** (не через IDE/Claude):

```bash
cd robotest
python -m src.auth
```

Что произойдёт:
1. Скрипт запросит код подтверждения
2. Telegram пришлёт код в приложение (чат "Telegram")
3. Введите код в консоли
4. Создастся файл `robotest.session`

Пример вывода:
```
==================================================
Robotest Authorization
==================================================

Phone: +7XXXXXXXXXX
Session file: robotest.session

Please enter the code you received: 12345
✅ Authorized as: Test User (@username)
Session saved: robotest.session
```

### 5. Запустите тесты

```bash
pytest scenarios/ -v
```

Пример вывода:
```
scenarios/test_start.py::TestStartCommand::test_start_responds PASSED
scenarios/test_start.py::TestStartCommand::test_start_welcome_message PASSED
scenarios/test_start.py::TestStartCommand::test_start_shows_cv_feature PASSED
scenarios/test_start.py::TestStartCommand::test_start_has_action_buttons PASSED
```

## Структура

```
robotest/
├── src/                  # Ядро: клиент, конфиг, утилиты
│   ├── config.py         # Конфигурация (pydantic-settings)
│   ├── client.py         # BotTester — клиент для тестирования
│   └── auth.py           # Скрипт авторизации
├── scenarios/            # Тестовые сценарии (pytest)
│   ├── conftest.py       # Fixtures
│   └── test_start.py     # Тест /start команды
├── docs/                 # Документация
└── fixtures/             # Тестовые файлы
```

## Текущие сценарии

| Сценарий | Описание | Статус |
|----------|----------|--------|
| test_start | Команда /start | Фаза 1 |

## Документация

- [Настройка](docs/setup.md)
- [Авторизация](docs/authorization.md)
- [Написание сценариев](docs/writing-scenarios.md)
- [Troubleshooting](docs/troubleshooting.md)

## Команды

```bash
# Установка
pip install -e ".[dev]"

# Авторизация роботеста (ТОЛЬКО ВРУЧНУЮ В ТЕРМИНАЛЕ)
python -m src.auth

# Запуск всех тестов
pytest scenarios/ -v

# Только /start
pytest scenarios/test_start.py -v

# С подробным выводом ошибок
pytest scenarios/ -v --tb=long
```

## Частые вопросы

**Q: Ошибка "EOFError" при авторизации**
A: Авторизацию нельзя запускать через IDE или автоматически. Только вручную в терминале.

**Q: Где взять api_id и api_hash?**
A: https://my.telegram.org/apps → создать приложение → скопировать credentials

**Q: Куда приходит код авторизации?**
A: В Telegram приложение, чат "Telegram" (не SMS)

**Q: Нужно ли авторизовываться каждый раз?**
A: Нет, после первой авторизации создаётся `robotest.session` — его достаточно для всех последующих запусков

**Q: Что делать если session устарел?**
A: Удалить `robotest.session` и запустить `python -m src.auth` снова

## Безопасность

⚠️ Файлы `.env` и `robotest.session` содержат секретные данные:
- НЕ коммитьте их в git (уже в .gitignore)
- НЕ публикуйте api_id/api_hash

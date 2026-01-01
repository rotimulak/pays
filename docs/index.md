# Telegram Billing Template

Шаблон микросервиса для SaaS-продуктов с монетизацией через Telegram-бот и Робокассу.

**Статус:** Только документация, кода пока нет.

---

## Содержание

### Начало работы

| Документ | Описание |
|----------|----------|
| [Обзор проекта](./overview.md) | Описание, стек, структура, быстрый старт |

### Архитектура

| Документ | Описание |
|----------|----------|
| [Архитектура](./architecture.md) | Схема БД, жизненные циклы invoice/подписки/токенов |

### Компоненты

| Документ | Описание |
|----------|----------|
| [Telegram-бот](./bot.md) | Команды, структура модуля, aiogram |
| [Робокасса](./robokassa-adapter.md) | Платёжная интеграция, webhook'и, валидация |
| [Docusaurus](./docusaurus.md) | Лендинг и документация для пользователей |

### Операции

| Документ | Описание |
|----------|----------|
| [Безопасность](./security.md) | Валидация подписей, rate limiting, HTTPS |
| [Деплой](./deployment.md) | Docker, nginx, переменные окружения |

### Справочники

| Документ | Описание |
|----------|----------|
| [Robokassa API](./robokassa/index.md) | Полный справочник по API Робокассы |
| [Роли для AI](./roles/index.md) | Промпты для работы с AI-ассистентами |

---

## Быстрые ссылки

| Тема | Ссылка |
|------|--------|
| Схема базы данных | [architecture.md#схема-базы-данных](./architecture.md#схема-базы-данных) |
| Команды бота | [bot.md#команды-бота](./bot.md#команды-бота) |
| Валидация Telegram | [security.md#валидация-telegram-init_data](./security.md#валидация-telegram-init_data) |
| Валидация Робокассы | [robokassa-adapter.md#валидация-webhookов](./robokassa-adapter.md#валидация-webhookов) |
| Rate limiting | [security.md#rate-limiting](./security.md#rate-limiting) |
| Переменные окружения | [deployment.md#переменные-окружения](./deployment.md#переменные-окружения) |
| Nginx конфигурация | [deployment.md#nginx-конфигурация](./deployment.md#nginx-конфигурация) |

---

## Структура документации

```
docs/
├── index.md                    # Этот файл
├── overview.md                 # Обзор проекта
├── architecture.md             # Архитектура и БД
│
├── bot.md                      # Telegram-бот
├── robokassa-adapter.md        # Платёжная интеграция
├── docusaurus.md               # Лендинг
│
├── security.md                 # Безопасность
├── deployment.md               # Деплой
│
├── robokassa/                  # Справочник Robokassa API
│   ├── index.md
│   ├── overview.md
│   └── architecture.md
│
└── roles/                      # Роли для AI-ассистентов
    ├── index.md
    ├── technical-writer.md
    ├── fullstack-developer.md
    ├── system-analyst.md
    ├── business-analyst.md
    ├── ux-product.md
    └── business-tracker.md
```

---

## Что не хватает (TODO)

Документы, которые необходимо создать:

| Документ | Назначение |
|----------|-----------|
| `guides/getting-started.md` | Пошаговый гайд для первого запуска |
| `guides/troubleshooting.md` | Решение типичных проблем |
| `architecture/adr/` | Architecture Decision Records |
| `glossary.md` | Глоссарий терминов проекта |
| `changelog.md` | История изменений |

---

## С чего начать?

1. Прочитать [Обзор проекта](./overview.md) для понимания концепции
2. Изучить [Архитектуру](./architecture.md) для понимания структуры данных
3. Для разработки — см. [роль Fullstack Developer](./roles/fullstack-developer.md)

# Документация Telegram Billing Template

## Содержание

### Начало работы

- [Обзор проекта](overview.md) — описание, стек технологий, быстрый старт

### Архитектура

- [Архитектура](architecture.md) — схема БД, жизненные циклы invoice/подписки/токенов

### Компоненты

- [Telegram-бот](bot.md) — команды, структура, aiogram
- [Интеграция с Робокассой](robokassa-adapter.md) — платежи, webhook'и, валидация
- [Docusaurus](docusaurus.md) — лендинг и документация для пользователей

### Операции

- [Безопасность](security.md) — валидация, rate limiting, секреты, HTTPS
- [Деплой](deployment.md) — Docker, переменные окружения, nginx

### Справочные материалы

- [Сравнение Telegram-фреймворков](telegram-frameworks-comparison.md)

---

## Быстрые ссылки

| Тема | Файл |
|------|------|
| Схема базы данных | [architecture.md#схема-базы-данных](architecture.md#схема-базы-данных) |
| Команды бота | [bot.md#команды-бота](bot.md#команды-бота) |
| Валидация Telegram init_data | [security.md#валидация-telegram-init_data](security.md#валидация-telegram-init_data) |
| Валидация Робокассы | [robokassa-adapter.md#валидация-webhookов](robokassa-adapter.md#валидация-webhookов) |
| Rate limiting | [security.md#rate-limiting](security.md#rate-limiting) |
| Переменные окружения | [deployment.md#переменные-окружения](deployment.md#переменные-окружения) |
| Nginx конфигурация | [deployment.md#nginx-конфигурация](deployment.md#nginx-конфигурация) |

---

## Структура документации

```
docs/
├── index.md                          # Этот файл
├── overview.md                       # Обзор проекта
├── architecture.md                   # Архитектура и БД
├── bot.md                            # Telegram-бот
├── robokassa-adapter.md              # Интеграция с Робокассой
├── security.md                       # Безопасность
├── deployment.md                     # Деплой
├── docusaurus.md                     # Лендинг и docs
└── telegram-frameworks-comparison.md # Сравнение фреймворков
```

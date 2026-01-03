# Changelog

Все значимые изменения проекта документируются здесь.

Формат основан на [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased]

---

## [M11] - 2026-01-03

### Added
- Упрощённое меню бота: 2 кнопки (Баланс, Помощь)
- Экран баланса с быстрым пополнением и FSM для произвольной суммы
- Гибкий период подписки: `period_unit` (hour/day/month), `period_value`
- Поля `subscription_fee` и `min_payment` в тарифе
- Enum `PeriodUnit` для единиц периода
- Функция `calculate_subscription_end()` в billing_service
- Метод `process_m11_payment()` для обработки платежей с M11 логикой
- Метод `get_default_tariff()` в TariffRepository
- FSM состояние `PaymentStates.waiting_for_amount`
- Миграция `007_add_tariff_period_fields.py`

### Changed
- Команда `/tariffs` редиректит на экран баланса
- Уведомления ссылаются на `/balance` вместо `/tariffs`
- Автопродление использует `subscription_fee` из тарифа
- Уведомления показывают информацию о балансе и subscription_fee
- Тексты уведомлений на русском языке

### Removed
- Экран выбора тарифов (скрыт от пользователя)
- Hardcoded значения `subscription_renewal_price` и `subscription_renewal_days`

---

## [M10] - 2025-12-XX

### Added
- Docker конфигурация (Dockerfile, docker-compose)
- Production overrides (docker-compose.prod.yml)
- Deploy скрипт
- Nginx конфигурация

---

## [M9] - 2025-12-XX

### Added
- Автопродление подписок
- Уведомления об истечении подписки
- Ручное продление через бота
- Тип транзакции SUBSCRIPTION

---

## [M8] - 2025-12-XX

### Added
- Token spending API
- Optimistic locking для баланса
- Уведомления о низком балансе

---

## [M7] - 2025-12-XX

### Added
- Промокоды и скидки
- Бонусные токены
- Типы скидок (percent, fixed, bonus)

---

## [M5] - 2025-12-XX

### Added
- Полный цикл оплаты
- Billing service
- Webhook обработка

---

## [M4] - 2025-12-XX

### Added
- Mock payment provider
- Payment service

---

## [M3] - 2025-12-XX

### Added
- Тарифы и инвойсы
- Invoice service

---

## [M2] - 2025-12-XX

### Added
- Telegram бот с авторизацией
- User middleware

---

## [M1] - 2025-12-XX

### Added
- Базовые модели (User, Tariff, Invoice, Transaction)
- SQLAlchemy + Alembic
- PostgreSQL интеграция

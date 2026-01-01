# M7: Promo Codes

## Обзор

Добавить систему промокодов со скидками и бонусами. Пользователь может применить промокод при покупке.

---

## Epics & Tasks

| Epic | Задачи | Оценка |
|------|--------|--------|
| [E7.1 — Promo Repository](e7.1-promo-repository.md) | CRUD для промокодов | 2 tasks |
| [E7.2 — Promo Service](e7.2-promo-service.md) | Валидация и применение скидок | 3 tasks |
| [E7.3 — Invoice Integration](e7.3-invoice-integration.md) | Интеграция с InvoiceService | 2 tasks |
| [E7.4 — Bot Handlers](e7.4-bot-handlers.md) | FSM для ввода промокода | 2 tasks |
| [E7.5 — Admin CLI](e7.5-admin-cli.md) | Скрипт управления промокодами | 1 task |

---

## Definition of Done

- [ ] Промокод типа `percent` уменьшает сумму на N%
- [ ] Промокод типа `fixed` уменьшает сумму на N рублей
- [ ] Промокод типа `bonus_tokens` добавляет N токенов к покупке
- [ ] Проверяется срок действия промокода
- [ ] Проверяется лимит использований
- [ ] Проверяется привязка к тарифу (если указана)
- [ ] При использовании увеличивается `uses_count`
- [ ] Invoice содержит ссылку на примененный промокод
- [ ] Пользователь видит скидку в интерфейсе бота
- [ ] Unit-тесты для promo_service (все типы скидок)

---

## Зависимости

- M5: Billing Flow

## Разблокирует

- Marketing campaigns

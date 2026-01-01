# M5: Billing Flow

## Обзор

Реализация полного цикла биллинга: оплата → начисление токенов/подписки → транзакция → уведомление. После этого milestone пользователь может реально "покупать" через mock provider.

---

## Epics & Tasks

| Epic | Задачи | Оценка |
|------|--------|--------|
| [E5.1 — Billing Service](e5.1-billing-service.md) | Основная логика начисления | 3 tasks |
| [E5.2 — Transaction & Audit](e5.2-transaction-audit.md) | Сервисы транзакций и аудита | 2 tasks |
| [E5.3 — Notifications](e5.3-notifications.md) | Уведомления в Telegram | 2 tasks |
| [E5.4 — Bot Handlers](e5.4-bot-handlers.md) | /history и /balance handlers | 2 tasks |
| [E5.5 — Invoice Expiration](e5.5-invoice-expiration.md) | Автоматическое истечение счетов | 1 task |

---

## Definition of Done

- [ ] После успешного webhook invoice переходит в `paid`
- [ ] Токены начисляются на баланс пользователя
- [ ] Подписка продлевается корректно (или устанавливается)
- [ ] Создаётся transaction с типом `topup`
- [ ] Создаётся запись в audit_log
- [ ] Пользователь получает уведомление в Telegram
- [ ] Повторный webhook с тем же invoice игнорируется (идемпотентность)
- [ ] `/history` показывает транзакции
- [ ] `/balance` показывает актуальные данные
- [ ] Optimistic locking работает корректно при concurrent updates
- [ ] Integration test: полный flow от выбора тарифа до начисления

---

## Зависимости

- M4: Mock Payment Provider

## Разблокирует

- M6: Robokassa Provider
- M7: Promo Codes
- M8: Token Spending

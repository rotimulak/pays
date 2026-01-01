# M8: Token Spending

## Обзор

Реализовать расходование токенов на "рабочие запросы". Добавить API для проверки баланса и списания токенов. Это core-функционал SaaS-сервиса.

---

## Epics & Tasks

| Epic | Задачи | Оценка |
|------|--------|--------|
| [E8.1 — Token Service](e8.1-token-service.md) | Сервис списания токенов | 3 tasks |
| [E8.2 — API Endpoints](e8.2-api-endpoints.md) | REST API для токенов | 3 tasks |
| [E8.3 — Guards & Validation](e8.3-guards-validation.md) | Проверки и ограничения | 2 tasks |
| [E8.4 — Bot Integration](e8.4-bot-integration.md) | Интеграция с ботом | 2 tasks |

---

## Definition of Done

- [ ] API endpoint для списания токенов работает
- [ ] Списание невозможно без активной подписки
- [ ] Списание невозможно при недостаточном балансе
- [ ] Каждое списание создаёт transaction типа `spend`
- [ ] Optimistic locking предотвращает race conditions
- [ ] balance_after в transaction корректен
- [ ] API возвращает понятные ошибки (InsufficientBalance, SubscriptionExpired)
- [ ] Rate limiting на API endpoints
- [ ] Unit-тесты для token_service
- [ ] Integration test: concurrent spending

---

## Зависимости

- M5: Billing Flow

## Разблокирует

- M9: Subscription Management

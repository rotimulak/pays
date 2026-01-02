# M7 & M8: Оставшиеся задачи

> Дата: 2026-01-02
> Основной функционал M7 и M8 реализован. Здесь перечислены опциональные улучшения.

---

## M7: Promo Codes — Оставшееся

### Тесты

- [ ] Unit-тесты для `promo_service.py`
  - Тест расчёта скидки типа `percent`
  - Тест расчёта скидки типа `fixed`
  - Тест бонусных токенов `bonus_tokens`
  - Тест валидации: истёкший промокод
  - Тест валидации: лимит использований
  - Тест валидации: привязка к тарифу

### Инструменты

- [ ] CLI-скрипт для создания промокодов (`scripts/create_promo.py`)
  ```bash
  python -m scripts.create_promo --code WELCOME2024 --type percent --value 20
  ```

---

## M8: Token Spending — Оставшееся

### Тесты

- [ ] Unit-тесты для `token_service.py`
  - Тест `check_balance()` — активная подписка
  - Тест `check_balance()` — истёкшая подписка
  - Тест `spend_tokens()` — успешное списание
  - Тест `spend_tokens()` — недостаточный баланс
  - Тест `spend_tokens()` — идемпотентность
  - Тест `spend_tokens()` — optimistic locking / race condition

- [ ] Integration test: concurrent spending
  - Параллельные запросы на списание
  - Проверка корректности баланса

### API

- [ ] Rate limiting на `/api/v1/users/{user_id}/spend`
  - Защита от flood-запросов
  - Лимит: 100 req/min per user_id

### Bot

- [ ] Уведомление при низком балансе
  - Threshold: < 10% от среднего расхода за неделю
  - Или фиксированные пороги: 50, 20, 10, 5 токенов
  - Не уведомлять чаще 1 раза в день

---

## Приоритет

| Задача | Приоритет | Effort |
|--------|-----------|--------|
| Unit-тесты token_service | Medium | Medium |
| Unit-тесты promo_service | Medium | Medium |
| Rate limiting API | High | Low |
| Уведомление низкий баланс | Low | Medium |
| CLI для промокодов | Low | Low |
| Integration test concurrent | Low | High |

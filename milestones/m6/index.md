# M6: Robokassa Provider

## Обзор

Заменить mock provider на реальную интеграцию с Robokassa. После этого milestone система готова принимать реальные платежи.

---

## Epics & Tasks

| Epic | Задачи | Оценка |
|------|--------|--------|
| [E6.1 — Robokassa Provider](e6.1-robokassa-provider.md) | Реализация провайдера | 2 tasks |
| [E6.2 — Signature Utilities](e6.2-signature-utils.md) | MD5 подписи для Robokassa | 2 tasks |
| [E6.3 — Configuration & Factory](e6.3-configuration.md) | Настройки и переключение провайдеров | 2 tasks |
| [E6.4 — Receipt Support (54-ФЗ)](e6.4-receipt-support.md) | Поддержка онлайн-касс | 2 tasks |

---

## Definition of Done

- [ ] RobokassaPaymentProvider реализует тот же интерфейс, что MockPaymentProvider
- [ ] Генерация URL соответствует документации Robokassa
- [ ] Подпись для init корректна (MD5, Password_1)
- [ ] Подпись webhook проверяется корректно (MD5, Password_2, Shp_* sorted)
- [ ] Переключение mock ↔ robokassa через env variable
- [ ] Тестовый режим (`IsTest=1`) работает
- [ ] Unit-тесты для signature generation/verification
- [ ] Integration test с тестовым аккаунтом Robokassa (manual)

---

## Зависимости

- M5: Billing Flow

## Разблокирует

- Production deployment

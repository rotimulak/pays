# M4: Mock Payment Provider

## Обзор

Создание mock-адаптера платёжной системы с тем же интерфейсом, что и реальный Robokassa. Позволяет тестировать полный flow оплаты без реального провайдера.

---

## Epics & Tasks

| Epic | Задачи | Оценка |
|------|--------|--------|
| [E4.1 — Payment Interface](e4.1-payment-interface.md) | Абстракции и схемы | 2 tasks |
| [E4.2 — Mock Provider](e4.2-mock-provider.md) | MockPaymentProvider реализация | 3 tasks |
| [E4.3 — Webhook Handler](e4.3-webhook-handler.md) | FastAPI endpoint для callbacks | 2 tasks |
| [E4.4 — Payment Service](e4.4-payment-service.md) | Сервис оплаты | 2 tasks |
| [E4.5 — Configuration](e4.5-configuration.md) | Настройки и factory | 2 tasks |

---

## Definition of Done

- [ ] MockPaymentProvider реализует тот же интерфейс и подписи, что Robokassa
- [ ] URL генерируется с правильными параметрами (MerchantLogin, OutSum, InvId, SignatureValue, Shp_*)
- [ ] Подпись для init: `MD5(MerchantLogin:OutSum:InvId:Password_1:Shp_*)`
- [ ] Подпись для webhook: `MD5(OutSum:InvId:Password_2:Shp_*)` (Shp_* sorted)
- [ ] Webhook возвращает `OK{InvId}` при успехе
- [ ] Mock UI показывает страницу оплаты с суммой и описанием
- [ ] После "оплаты" отправляется POST на ResultURL с правильными параметрами
- [ ] Переключение mock ↔ robokassa через `PAYMENT_PROVIDER` env variable
- [ ] Unit-тесты для signature generation/verification
- [ ] Integration test: invoice → payment URL → mock pay → webhook → invoice.paid

---

## Зависимости

- M3: Tariffs & Invoices

## Разблокирует

- M5: Billing Flow

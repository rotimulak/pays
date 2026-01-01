# Robokassa - Навигация по документации

## Внутренняя документация проекта

| Документ | Описание |
|----------|----------|
| [overview.md](./overview.md) | Обзор API, ключевые методы, параметры |
| [architecture.md](./architecture.md) | Архитектура интеграции в проект |

---

## Официальная документация Robokassa

**Базовый URL:** https://docs.robokassa.ru/

### Приём платежей

| Раздел | URL | Описание |
|--------|-----|----------|
| Платёжный интерфейс | [/pay-interface/](https://docs.robokassa.ru/pay-interface/) | Основной API для инициализации платежей |
| iFrame платежи | [/iframe/](https://docs.robokassa.ru/iframe/) | Встраивание формы оплаты в iframe |
| Параметры скрипта | [/script-params/](https://docs.robokassa.ru/script-params/) | Параметры платёжного скрипта |
| Платёжный скрипт | [/payment-script/](https://docs.robokassa.ru/payment-script/) | JavaScript интеграция |
| Invoice API | [/invoice-api/](https://docs.robokassa.ru/invoice-api/) | API для создания счетов |
| Холдирование | [/holding/](https://docs.robokassa.ru/holding/) | Предавторизация и холдирование средств |
| XML интерфейсы | [/xml-interfaces/](https://docs.robokassa.ru/xml-interfaces/) | XML API (статус платежа, валюты) |
| Тестовый режим | [/testing/](https://docs.robokassa.ru/testing/) | Тестирование интеграции |
| Примеры кода | [/code-examples/](https://docs.robokassa.ru/code-examples/) | Примеры на разных языках |

### Подписки и рекуррентные платежи

| Раздел | URL | Описание |
|--------|-----|----------|
| Рекуррентные платежи | [/recurring/](https://docs.robokassa.ru/recurring/) | Автоматические списания |
| Подписки | [/subscriptions/](https://docs.robokassa.ru/subscriptions/) | Готовое решение для подписок |
| Сплитование | [/splitting/](https://docs.robokassa.ru/splitting/) | Разделение платежей |

### Telegram и боты

| Раздел | URL | Описание |
|--------|-----|----------|
| RobokassaShopBot | [/robokassa-shop-bot/](https://docs.robokassa.ru/robokassa-shop-bot/) | Telegram-бот для продаж |
| Продажи в Telegram | [/telegram-sales/](https://docs.robokassa.ru/telegram-sales/) | Интеграция с Telegram |

### Фискализация и касса

| Раздел | URL | Описание |
|--------|-----|----------|
| Онлайн-касса | [/online-cashbox/](https://docs.robokassa.ru/online-cashbox/) | Облачная касса |
| Фискализация 54-ФЗ | [/fiscalization/](https://docs.robokassa.ru/fiscalization/) | Требования 54-ФЗ |
| Второй чек | [/second-receipt/](https://docs.robokassa.ru/second-receipt/) | Генерация второго чека |
| Чеки коррекции | [/correction-receipts/](https://docs.robokassa.ru/correction-receipts/) | Чеки коррекции |

### Возвраты и кредиты

| Раздел | URL | Описание |
|--------|-----|----------|
| API возвратов | [/refund-api/](https://docs.robokassa.ru/refund-api/) | Возврат платежей |
| BNPL/Кредитный виджет | [/bnpl-widget/](https://docs.robokassa.ru/bnpl-widget/) | Рассрочка и кредиты |

### Уведомления

| Раздел | URL | Описание |
|--------|-----|----------|
| Общие уведомления | [/notifications/](https://docs.robokassa.ru/notifications/) | Система нотификаций |
| SMS уведомления | [/sms-notifications/](https://docs.robokassa.ru/sms-notifications/) | SMS оповещения |
| Telegram/VK/Browser | [/messenger-notifications/](https://docs.robokassa.ru/messenger-notifications/) | Уведомления в мессенджеры |

### Дополнительно

| Раздел | URL | Описание |
|--------|-----|----------|
| Виджеты и SDK | [/widgets-sdk/](https://docs.robokassa.ru/widgets-sdk/) | Готовые модули и SDK |
| Демо-магазин | [/demo-store/](https://docs.robokassa.ru/demo-store/) | Тестовый магазин |
| Помощь в подключении | [/connection-help/](https://docs.robokassa.ru/connection-help/) | Инструкции по подключению |

---

## Полезные ссылки

| Ресурс | URL |
|--------|-----|
| Личный кабинет | https://partner.robokassa.ru/ |
| Техподдержка | 8-800-500-25-57 |
| Новая документация | https://docs2.robokassa.ru/ |

---

## Быстрый справочник endpoints

```
# Платежи
POST https://auth.robokassa.ru/Merchant/Index.aspx

# Рекуррентные платежи
POST https://auth.robokassa.ru/Merchant/Recurring

# Платёж по сохранённой карте
POST https://auth.robokassa.ru/Merchant/Payment/CoFPayment

# XML: Статус операции
GET https://auth.robokassa.ru/Merchant/WebService/Service.asmx/OpStateExt

# XML: Список валют
GET https://auth.robokassa.ru/Merchant/WebService/Service.asmx/GetCurrencies
```

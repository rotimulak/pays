# Robokassa Payment Service - Overview

## Общая информация

Robokassa — платёжный агрегатор для приёма онлайн-платежей. Поддерживает банковские карты, электронные кошельки, мобильные платежи и другие способы оплаты.

**Официальная документация:** https://docs.robokassa.ru/

---

## Учётные данные магазина

| Параметр | Описание |
|----------|----------|
| `MerchantLogin` | Идентификатор магазина |
| `Password_1` | Пароль для формирования подписи при инициализации платежа |
| `Password_2` | Пароль для проверки подписи при получении уведомлений |

---

## Основные endpoints

| Назначение | URL |
|------------|-----|
| Инициализация платежа | `https://auth.robokassa.ru/Merchant/Index.aspx` |
| Платёж по сохранённой карте | `https://auth.robokassa.ru/Merchant/Payment/CoFPayment` |
| Рекуррентный платёж | `https://auth.robokassa.ru/Merchant/Recurring` |
| Получение списка валют | `https://auth.robokassa.ru/Merchant/WebService/Service.asmx/GetCurrencies` |
| Статус операции | `https://auth.robokassa.ru/Merchant/WebService/Service.asmx/OpStateExt` |

---

## Ключевые методы API

### 1. Инициализация платежа

**Endpoint:** `POST/GET https://auth.robokassa.ru/Merchant/Index.aspx`

**Обязательные параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `MerchantLogin` | string | Идентификатор магазина |
| `OutSum` | decimal | Сумма в рублях (формат: 123.45) |
| `InvId` | int64 | Уникальный номер счёта (1 - 9223372036854775807) |
| `Description` | string | Описание покупки (до 100 символов) |
| `SignatureValue` | string | Контрольная сумма (MD5 hash) |

**Опциональные параметры:**

| Параметр | Описание |
|----------|----------|
| `Culture` | Язык интерфейса (ru, en) |
| `Encoding` | Кодировка (по умолчанию UTF-8) |
| `Email` | Email покупателя |
| `ExpirationDate` | Срок действия счёта (ISO 8601) |
| `Receipt` | JSON с данными для фискализации (54-ФЗ) |
| `Recurring` | true - для инициализации рекуррентных платежей |
| `Shp_*` | Пользовательские параметры (передаются в callback) |

**Формула расчёта подписи:**
```
SignatureValue = MD5(MerchantLogin:OutSum:InvId:Password_1)
```

С пользовательскими параметрами (в алфавитном порядке):
```
SignatureValue = MD5(MerchantLogin:OutSum:InvId:Password_1:Shp_param1=value1:Shp_param2=value2)
```

---

### 2. Callback уведомления

#### ResultURL (серверное уведомление)

Robokassa отправляет POST-запрос на ResultURL после успешной оплаты.

**Получаемые параметры:**

| Параметр | Описание |
|----------|----------|
| `OutSum` | Сумма платежа |
| `InvId` | Номер счёта |
| `Fee` | Комиссия |
| `Email` | Email покупателя |
| `SignatureValue` | Контрольная сумма |
| `PaymentMethod` | Способ оплаты |
| `Shp_*` | Пользовательские параметры |

**Проверка подписи:**
```
SignatureValue = MD5(OutSum:InvId:Password_2:Shp_*)
```

**Требуемый ответ:**
```
OK{InvId}
```

Например: `OK12345`

#### ResultURL2 (JWS формат)

Дополнительное уведомление в формате JSON Web Signature (base64).
Требует ответ HTTP 200-299.

#### SuccessURL / FailURL

Редирект пользователя после оплаты/отмены.
**Важно:** Не использовать для изменения статуса заказа - только для UI.

---

### 3. Проверка статуса платежа (OpStateExt)

**Endpoint:** `GET https://auth.robokassa.ru/Merchant/WebService/Service.asmx/OpStateExt`

**Параметры:**

| Параметр | Описание |
|----------|----------|
| `MerchantLogin` | Идентификатор магазина |
| `InvoiceID` | Номер счёта |
| `Signature` | MD5(MerchantLogin:InvoiceID:Password_2) |

**Коды состояния:**

| Код | Описание |
|-----|----------|
| 5 | Операция инициализирована |
| 10 | Отменена, средства не переведены |
| 50 | Средства зарезервированы (холд) |
| 60 | Отменена после резервирования |
| 80 | Средства перечислены |
| 100 | Операция успешно завершена |

**Коды ошибок:**

| Код | Описание |
|-----|----------|
| 0 | Успех |
| 2 | Магазин не найден |
| 1000 | Ошибка сервера |

---

### 4. Получение списка валют (GetCurrencies)

**Endpoint:** `GET https://auth.robokassa.ru/Merchant/WebService/Service.asmx/GetCurrencies`

**Параметры:**

| Параметр | Описание |
|----------|----------|
| `MerchantLogin` | Идентификатор магазина |
| `Language` | Язык ответа (ru, en) |

---

### 5. Рекуррентные платежи

**Этап 1: Первичный платёж (parent)**

Добавить параметр `Recurring=true` к стандартному запросу инициализации.

**Этап 2: Последующие списания (child)**

**Endpoint:** `POST https://auth.robokassa.ru/Merchant/Recurring`

**Параметры:**

| Параметр | Описание |
|----------|----------|
| `MerchantLogin` | Идентификатор магазина |
| `OutSum` | Сумма |
| `InvId` | Новый номер счёта |
| `PreviousInvoiceID` | ID родительского платежа |
| `SignatureValue` | Подпись (без PreviousInvoiceID!) |

**Важно:** `PreviousInvoiceID` НЕ включается в расчёт подписи.

**Ответ:** `OK+InvoiceId` - операция создана (не гарантирует успешную оплату).

---

## Фискализация (54-ФЗ)

Параметр `Receipt` содержит JSON с данными чека.

**Структура:**

```json
{
  "sno": "osn",
  "items": [
    {
      "name": "Название товара",
      "quantity": 1,
      "sum": 1000.00,
      "tax": "vat20",
      "payment_method": "full_payment",
      "payment_object": "commodity"
    }
  ]
}
```

**Системы налогообложения (sno):**
- `osn` - общая
- `usn_income` - УСН доходы
- `usn_income_outcome` - УСН доходы-расходы
- `esn` - ЕСХН
- `patent` - патент

**Ставки НДС (tax):**
- `none` - без НДС
- `vat0` - 0%
- `vat5` - 5%
- `vat7` - 7%
- `vat10` - 10%
- `vat20` - 20%

**Ограничения:**
- Максимум 100 позиций в чеке
- Название товара до 128 символов (русский/английский)
- Сумма позиций = сумме платежа

**Важно:** Receipt включается в расчёт подписи и должен быть URL-encoded.

---

## Тестовый режим

Для тестирования используются отдельные пароли (Test Password #1 и #2) в личном кабинете.

**Тестовый endpoint:** `https://auth.robokassa.ru/Merchant/Index.aspx?IsTest=1`

---

## Требования безопасности

1. Всегда проверять подпись в ResultURL callback
2. Не полагаться на SuccessURL/FailURL для изменения статуса заказа
3. Хранить Password_1 и Password_2 в защищённом хранилище
4. Использовать HTTPS для всех callback URL
5. Проверять сумму платежа при получении уведомления

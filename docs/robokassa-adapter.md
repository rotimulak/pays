# Интеграция с Робокассой

## Обзор

Робокасса используется как платёжный шлюз для обработки оплат подписок и токенов. Интеграция включает:

- Формирование ссылки на оплату
- Приём и валидация webhook'ов (ResultURL)
- Идемпотентная обработка платежей

---

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `ROBOKASSA_LOGIN` | Логин магазина в Робокассе |
| `ROBOKASSA_PASSWORD1` | Пароль #1 для формирования ссылки на оплату |
| `ROBOKASSA_PASSWORD2` | Пароль #2 для проверки webhook'ов |

---

## Валидация webhook'ов

При получении ResultURL от Робокассы необходимо проверить подпись:

```python
import hashlib
import hmac

def validate_robokassa_signature(
    out_sum: str,
    inv_id: str,
    password2: str,
    received_signature: str
) -> bool:
    """
    Проверка подписи ResultURL от Робокассы.
    """
    # Формат: OutSum:InvId:Password2
    signature_string = f"{out_sum}:{inv_id}:{password2}"
    calculated = hashlib.md5(signature_string.encode()).hexdigest().upper()

    return hmac.compare_digest(calculated, received_signature.upper())
```

---

## Защита от повторной обработки платежей

Webhook может прийти несколько раз. Обработка должна быть идемпотентной:

```python
async def process_payment(invoice_id: str, robokassa_id: str):
    """
    Идемпотентная обработка платежа.
    """
    async with database.transaction():
        invoice = await Invoice.select_for_update(id=invoice_id)

        # Уже обработан — ничего не делаем
        if invoice.status == "paid":
            return {"status": "already_processed"}

        # Атомарное обновление
        invoice.status = "paid"
        invoice.robokassa_id = robokassa_id
        invoice.paid_at = datetime.utcnow()
        await invoice.save()

        # Начисление токенов
        await User.update(
            token_balance=User.token_balance + invoice.tokens
        ).where(User.id == invoice.user_id)

        # Запись транзакции
        await Transaction.create(
            user_id=invoice.user_id,
            type="topup",
            tokens_delta=invoice.tokens,
            invoice_id=invoice.id
        )

    return {"status": "success"}
```

**Ключевые моменты:**
- `select_for_update` — блокировка строки на время транзакции
- Проверка `status == "paid"` — защита от повторного начисления
- Атомарная транзакция — либо всё, либо ничего

---

## Архитектура webhook'ов

```
Робокасса                    Ваш сервер                    Telegram
    │                            │                            │
    │  POST /webhook/robokassa   │                            │
    │  (ResultURL)               │                            │
    │ ──────────────────────────>│                            │
    │                            │  1. Проверка подписи       │
    │                            │  2. Обновление invoice     │
    │                            │  3. Начисление токенов/    │
    │                            │     продление подписки     │
    │                            │  4. Запись в transactions  │
    │                            │                            │
    │                            │  sendMessage (уведомление) │
    │                            │ ──────────────────────────>│
    │                            │                            │
    │<── OK ─────────────────────│                            │
```

---

## Rate Limiting для webhook endpoint

| Endpoint | Лимит | Окно |
|----------|-------|------|
| `/webhook/robokassa` (по IP) | 100 запросов | 1 минута |

---

## Требования безопасности

- **HTTPS обязателен** — Робокасса отправляет webhook'и только на HTTPS endpoints
- **Не логировать** `ROBOKASSA_PASSWORD1` и `ROBOKASSA_PASSWORD2`
- При компрометации — немедленная ротация через личный кабинет Робокассы

---

## См. также

- [Архитектура](architecture.md) — жизненный цикл invoice
- [Безопасность](security.md) — общие требования безопасности
- [Деплой](deployment.md) — настройка HTTPS

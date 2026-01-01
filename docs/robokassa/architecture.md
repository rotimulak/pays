# Архитектура интеграции Robokassa

## Рекомендация: Модульный адаптер

**Предлагаемый подход:** Robokassa интегрируется как **отдельный модуль-адаптер** в составе backend-сервиса, а не как отдельный микросервис.

### Почему модуль, а не микросервис?

| Критерий | Модуль | Микросервис |
|----------|--------|-------------|
| Сложность деплоя | Низкая | Высокая |
| Latency | Минимальная | +network hop |
| Транзакции БД | Единая транзакция | Distributed saga |
| Масштабирование | Вместе с backend | Независимое |
| Поддержка | Простая | Требует DevOps |

**Вывод:** Для текущего масштаба (один платёжный провайдер, один backend) модуль оптимален. При добавлении 3+ платёжных систем можно выделить в микросервис.

---

## Структура модуля

```
backend/
└── src/
    ├── payments/                    # Платёжный модуль
    │   ├── __init__.py
    │   ├── router.py                # API endpoints (webhooks)
    │   ├── schemas.py               # Pydantic/DTO модели
    │   ├── service.py               # Бизнес-логика платежей
    │   │
    │   └── providers/               # Адаптеры платёжных систем
    │       ├── __init__.py
    │       ├── base.py              # Абстрактный интерфейс
    │       └── robokassa/
    │           ├── __init__.py
    │           ├── adapter.py       # Реализация адаптера
    │           ├── schemas.py       # Robokassa-специфичные модели
    │           ├── signature.py     # Подпись и валидация
    │           └── config.py        # Конфигурация
    │
    ├── models/
    │   ├── invoice.py               # Модель счёта
    │   └── transaction.py           # Модель транзакции
    │
    └── config/
        └── settings.py              # Настройки приложения
```

---

## Интерфейс адаптера (абстракция)

```python
# payments/providers/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class PaymentStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

@dataclass
class PaymentResult:
    success: bool
    payment_url: Optional[str] = None
    external_id: Optional[str] = None
    error_message: Optional[str] = None

@dataclass
class WebhookResult:
    success: bool
    invoice_id: int
    amount: float
    status: PaymentStatus
    response_body: str  # Ответ для платёжной системы

class PaymentProvider(ABC):
    """Абстрактный интерфейс платёжного провайдера"""

    @abstractmethod
    async def create_payment(
        self,
        invoice_id: int,
        amount: float,
        description: str,
        user_email: Optional[str] = None,
        receipt_items: Optional[list] = None,  # Для 54-ФЗ
    ) -> PaymentResult:
        """Создать платёж и получить URL для оплаты"""
        pass

    @abstractmethod
    async def verify_webhook(
        self,
        data: dict,
        signature: str,
    ) -> WebhookResult:
        """Проверить и обработать webhook от платёжной системы"""
        pass

    @abstractmethod
    async def check_status(
        self,
        invoice_id: int,
    ) -> PaymentStatus:
        """Проверить статус платежа через API"""
        pass

    @abstractmethod
    async def refund(
        self,
        invoice_id: int,
        amount: Optional[float] = None,  # None = полный возврат
    ) -> bool:
        """Выполнить возврат"""
        pass
```

---

## Реализация Robokassa адаптера

```python
# payments/providers/robokassa/adapter.py

import hashlib
from urllib.parse import urlencode
from typing import Optional
import httpx

from ..base import PaymentProvider, PaymentResult, WebhookResult, PaymentStatus
from .config import RobokassaConfig
from .schemas import RobokassaWebhook, RobokassaReceipt

class RobokassaAdapter(PaymentProvider):
    """Адаптер для интеграции с Robokassa"""

    BASE_URL = "https://auth.robokassa.ru/Merchant"

    def __init__(self, config: RobokassaConfig):
        self.config = config
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def create_payment(
        self,
        invoice_id: int,
        amount: float,
        description: str,
        user_email: Optional[str] = None,
        receipt_items: Optional[list] = None,
    ) -> PaymentResult:
        """Генерация URL для перехода на оплату"""

        params = {
            "MerchantLogin": self.config.merchant_login,
            "OutSum": f"{amount:.2f}",
            "InvId": invoice_id,
            "Description": description[:100],
            "SignatureValue": self._calculate_signature(amount, invoice_id),
            "Culture": "ru",
            "Encoding": "utf-8",
        }

        if user_email:
            params["Email"] = user_email

        if receipt_items:
            receipt = RobokassaReceipt(
                sno=self.config.tax_system,
                items=receipt_items
            )
            params["Receipt"] = receipt.to_url_encoded()

        if self.config.is_test:
            params["IsTest"] = 1

        payment_url = f"{self.BASE_URL}/Index.aspx?{urlencode(params)}"

        return PaymentResult(
            success=True,
            payment_url=payment_url,
            external_id=str(invoice_id),
        )

    async def verify_webhook(
        self,
        data: dict,
        signature: str,
    ) -> WebhookResult:
        """Проверка подписи и парсинг webhook"""

        webhook = RobokassaWebhook(**data)

        # Проверка подписи
        expected_signature = self._calculate_result_signature(
            out_sum=webhook.OutSum,
            inv_id=webhook.InvId,
            shp_params=webhook.get_shp_params(),
        )

        if signature.lower() != expected_signature.lower():
            return WebhookResult(
                success=False,
                invoice_id=webhook.InvId,
                amount=float(webhook.OutSum),
                status=PaymentStatus.FAILED,
                response_body="bad sign",
            )

        return WebhookResult(
            success=True,
            invoice_id=webhook.InvId,
            amount=float(webhook.OutSum),
            status=PaymentStatus.PAID,
            response_body=f"OK{webhook.InvId}",
        )

    async def check_status(self, invoice_id: int) -> PaymentStatus:
        """Проверка статуса через OpStateExt"""

        signature = hashlib.md5(
            f"{self.config.merchant_login}:{invoice_id}:{self.config.password_2}"
            .encode()
        ).hexdigest()

        response = await self.http_client.get(
            f"{self.BASE_URL}/WebService/Service.asmx/OpStateExt",
            params={
                "MerchantLogin": self.config.merchant_login,
                "InvoiceID": invoice_id,
                "Signature": signature,
            }
        )

        # Parse XML response and map to PaymentStatus
        # ... XML parsing logic

        return PaymentStatus.PENDING  # Placeholder

    async def refund(
        self,
        invoice_id: int,
        amount: Optional[float] = None,
    ) -> bool:
        """Возврат платежа через Robokassa API"""
        # Implementation depends on Robokassa refund API
        raise NotImplementedError("Refund requires Robokassa API access")

    def _calculate_signature(self, amount: float, invoice_id: int) -> str:
        """Подпись для инициализации платежа"""
        raw = f"{self.config.merchant_login}:{amount:.2f}:{invoice_id}:{self.config.password_1}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _calculate_result_signature(
        self,
        out_sum: str,
        inv_id: int,
        shp_params: dict,
    ) -> str:
        """Подпись для проверки webhook (ResultURL)"""
        parts = [out_sum, str(inv_id), self.config.password_2]

        # Добавить Shp_ параметры в алфавитном порядке
        for key in sorted(shp_params.keys()):
            parts.append(f"{key}={shp_params[key]}")

        raw = ":".join(parts)
        return hashlib.md5(raw.encode()).hexdigest()
```

---

## Конфигурация

```python
# payments/providers/robokassa/config.py

from pydantic_settings import BaseSettings

class RobokassaConfig(BaseSettings):
    merchant_login: str
    password_1: str  # Для создания платежа
    password_2: str  # Для проверки webhook
    is_test: bool = False
    tax_system: str = "osn"  # Система налогообложения

    result_url: str  # https://your-domain.com/api/webhooks/robokassa
    success_url: str  # https://your-domain.com/payment/success
    fail_url: str     # https://your-domain.com/payment/fail

    class Config:
        env_prefix = "ROBOKASSA_"
```

```env
# .env

ROBOKASSA_MERCHANT_LOGIN=your_shop_id
ROBOKASSA_PASSWORD_1=your_password_1
ROBOKASSA_PASSWORD_2=your_password_2
ROBOKASSA_IS_TEST=true
ROBOKASSA_TAX_SYSTEM=osn
ROBOKASSA_RESULT_URL=https://api.example.com/webhooks/robokassa
ROBOKASSA_SUCCESS_URL=https://example.com/payment/success
ROBOKASSA_FAIL_URL=https://example.com/payment/fail
```

---

## API Endpoints

```python
# payments/router.py

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse

from .service import PaymentService
from .providers.robokassa import RobokassaAdapter

router = APIRouter(prefix="/api", tags=["payments"])

@router.post("/payments/create")
async def create_payment(
    amount: float,
    description: str,
    user_id: int,
    payment_service: PaymentService = Depends(),
):
    """Создать счёт и получить ссылку на оплату"""
    result = await payment_service.create_invoice(
        user_id=user_id,
        amount=amount,
        description=description,
    )
    return {"payment_url": result.payment_url, "invoice_id": result.invoice_id}


@router.post("/webhooks/robokassa", response_class=PlainTextResponse)
async def robokassa_webhook(
    request: Request,
    payment_service: PaymentService = Depends(),
):
    """
    Webhook для ResultURL callback от Robokassa.
    Robokassa ожидает ответ: OK{InvId}
    """
    form_data = await request.form()
    data = dict(form_data)

    result = await payment_service.process_robokassa_webhook(data)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.response_body)

    return result.response_body  # "OK12345"


@router.get("/payments/{invoice_id}/status")
async def check_payment_status(
    invoice_id: int,
    payment_service: PaymentService = Depends(),
):
    """Проверить статус платежа"""
    status = await payment_service.get_invoice_status(invoice_id)
    return {"invoice_id": invoice_id, "status": status}
```

---

## Сервисный слой

```python
# payments/service.py

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .providers.base import PaymentProvider, WebhookResult
from .providers.robokassa import RobokassaAdapter
from ..models.invoice import Invoice, InvoiceStatus
from ..models.transaction import Transaction, TransactionType

class PaymentService:
    def __init__(
        self,
        db: AsyncSession,
        provider: PaymentProvider,
    ):
        self.db = db
        self.provider = provider

    async def create_invoice(
        self,
        user_id: int,
        amount: float,
        description: str,
        tokens: int = 0,
        subscription_days: int = 0,
    ):
        """Создать счёт в БД и получить ссылку на оплату"""

        # Создать запись в БД
        invoice = Invoice(
            user_id=user_id,
            amount=amount,
            tokens=tokens,
            subscription_days=subscription_days,
            status=InvoiceStatus.PENDING,
        )
        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)

        # Получить URL для оплаты
        result = await self.provider.create_payment(
            invoice_id=invoice.id,
            amount=amount,
            description=description,
        )

        return result

    async def process_robokassa_webhook(self, data: dict) -> WebhookResult:
        """Обработать webhook от Robokassa"""

        signature = data.get("SignatureValue", "")
        result = await self.provider.verify_webhook(data, signature)

        if not result.success:
            return result

        # Найти счёт
        invoice = await self.db.get(Invoice, result.invoice_id)
        if not invoice:
            return WebhookResult(
                success=False,
                invoice_id=result.invoice_id,
                amount=result.amount,
                status=result.status,
                response_body="Invoice not found",
            )

        # Идемпотентность: проверить что счёт ещё не оплачен
        if invoice.status == InvoiceStatus.PAID:
            return result  # Уже обработан, вернуть OK

        # Проверить сумму
        if float(invoice.amount) != result.amount:
            return WebhookResult(
                success=False,
                invoice_id=result.invoice_id,
                amount=result.amount,
                status=result.status,
                response_body="Amount mismatch",
            )

        # Обновить статус (в транзакции)
        async with self.db.begin():
            invoice.status = InvoiceStatus.PAID
            invoice.paid_at = datetime.utcnow()

            # Создать транзакцию
            transaction = Transaction(
                user_id=invoice.user_id,
                type=TransactionType.TOPUP,
                tokens_delta=invoice.tokens,
                invoice_id=invoice.id,
            )
            self.db.add(transaction)

            # Начислить токены пользователю
            user = await self.db.get(User, invoice.user_id)
            user.token_balance += invoice.tokens

            if invoice.subscription_days > 0:
                # Продлить подписку
                if user.subscription_end and user.subscription_end > datetime.utcnow():
                    user.subscription_end += timedelta(days=invoice.subscription_days)
                else:
                    user.subscription_end = datetime.utcnow() + timedelta(days=invoice.subscription_days)

        # Отправить уведомление в Telegram (async task)
        await self._notify_user(invoice.user_id, invoice)

        return result

    async def _notify_user(self, user_id: int, invoice: Invoice):
        """Отправить уведомление об успешной оплате"""
        # Интеграция с Telegram Bot API
        pass
```

---

## Диаграмма потока данных

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ИНИЦИАЛИЗАЦИЯ ПЛАТЕЖА                        │
└─────────────────────────────────────────────────────────────────────┘

   User          Telegram Bot         Backend API            Robokassa
    │                 │                    │                     │
    │  /pay 500       │                    │                     │
    ├────────────────>│                    │                     │
    │                 │  POST /payments    │                     │
    │                 ├───────────────────>│                     │
    │                 │                    │ Create Invoice (DB) │
    │                 │                    │─────────┐           │
    │                 │                    │<────────┘           │
    │                 │                    │ Generate URL        │
    │                 │  payment_url       │                     │
    │                 │<───────────────────│                     │
    │  Inline Button  │                    │                     │
    │<────────────────│                    │                     │
    │                 │                    │                     │
    │  Click → Open payment page           │                     │
    ├──────────────────────────────────────────────────────────>│
    │                 │                    │                     │


┌─────────────────────────────────────────────────────────────────────┐
│                         ОБРАБОТКА ПЛАТЕЖА                            │
└─────────────────────────────────────────────────────────────────────┘

   User          Robokassa         Backend API          Database       Bot
    │                │                  │                   │           │
    │  Pay with card │                  │                   │           │
    ├───────────────>│                  │                   │           │
    │                │  POST /webhooks  │                   │           │
    │                │  (ResultURL)     │                   │           │
    │                ├─────────────────>│                   │           │
    │                │                  │ Verify signature  │           │
    │                │                  │─────────┐         │           │
    │                │                  │<────────┘         │           │
    │                │                  │ Update invoice    │           │
    │                │                  ├──────────────────>│           │
    │                │                  │ Add transaction   │           │
    │                │                  ├──────────────────>│           │
    │                │                  │ Credit tokens     │           │
    │                │                  ├──────────────────>│           │
    │                │                  │                   │           │
    │                │                  │ Send notification │           │
    │                │                  ├──────────────────────────────>│
    │                │                  │                   │           │
    │                │  "OK{InvId}"     │                   │           │
    │                │<─────────────────│                   │           │
    │                │                  │                   │           │
    │  Redirect to   │                  │                   │           │
    │  SuccessURL    │                  │                   │           │
    │<───────────────│                  │                   │           │
    │                │                  │                   │ Message   │
    │<──────────────────────────────────────────────────────────────────│
    │  "Оплата       │                  │                   │           │
    │   успешна!"    │                  │                   │           │
```

---

## Модели базы данных

```python
# models/invoice.py

from sqlalchemy import Column, Integer, BigInteger, Numeric, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

class InvoiceStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REFUNDED = "refunded"

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    amount = Column(Numeric(10, 2), nullable=False)
    tokens = Column(Integer, default=0)
    subscription_days = Column(Integer, default=0)

    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.PENDING, index=True)
    robokassa_id = Column(String(100), nullable=True)  # External ID if needed

    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="invoices")
    transactions = relationship("Transaction", back_populates="invoice")
```

---

## Расширяемость

Для добавления нового платёжного провайдера (например, YooKassa):

1. Создать `payments/providers/yookassa/adapter.py`
2. Реализовать интерфейс `PaymentProvider`
3. Добавить конфигурацию в `.env`
4. Зарегистрировать новый endpoint для webhook

```python
# Пример фабрики провайдеров
def get_payment_provider(provider_name: str) -> PaymentProvider:
    providers = {
        "robokassa": RobokassaAdapter(robokassa_config),
        "yookassa": YooKassaAdapter(yookassa_config),
        "stripe": StripeAdapter(stripe_config),
    }
    return providers.get(provider_name)
```

---

## Чек-лист интеграции

- [ ] Создать модуль `payments/providers/robokassa/`
- [ ] Реализовать `RobokassaAdapter`
- [ ] Добавить модели `Invoice`, `Transaction`
- [ ] Настроить миграции Alembic
- [ ] Создать endpoint `POST /api/webhooks/robokassa`
- [ ] Добавить валидацию подписи
- [ ] Настроить `.env` с credentials
- [ ] Протестировать в тестовом режиме Robokassa
- [ ] Настроить ResultURL в личном кабинете Robokassa
- [ ] Добавить логирование webhook-запросов
- [ ] Реализовать уведомления в Telegram

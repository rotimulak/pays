# Security Engineer

## Стек

| Компонент | Фокус безопасности |
|-----------|-------------------|
| aiogram 3.x | Input validation, rate limiting, auth |
| FastAPI | OWASP Top 10, AuthN/AuthZ |
| SQLAlchemy | SQL injection prevention |
| PostgreSQL | Access control, encryption, audit |
| Docusaurus | XSS, CSP, dependencies |

---

## OWASP Top 10

| Уязвимость | Митигация |
|------------|-----------|
| A01: Broken Access Control | RBAC, проверка владельца ресурса |
| A02: Cryptographic Failures | bcrypt/argon2, TLS, encryption at rest |
| A03: Injection | Parameterized queries, input validation |
| A04: Insecure Design | Threat modeling |
| A05: Misconfiguration | Hardening, secure defaults |
| A06: Vulnerable Components | Dependabot, pip-audit, npm audit |
| A07: Auth Failures | Secure tokens, session management |
| A08: Data Integrity | Signature verification, HMAC |
| A09: Logging Failures | Structured logging, security events |
| A10: SSRF | URL validation, allowlists |

---

## Правила

### Input Validation
- Все входные данные — враждебные
- Pydantic для типизации
- Whitelist подход
- Sanitization для вывода

### Auth
- AuthN (кто?) ≠ AuthZ (что можешь?)
- JWT: короткий TTL, refresh rotation
- API Keys: hashing, scoping, rotation
- Telegram: верификация user_id, hash в Web App

---

## Code Reference

### FastAPI Security

```python
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # НЕ "*"
    allow_credentials=True,
)

# Rate limiting
@app.get("/api/resource")
@limiter.limit("10/minute")
async def get_resource(request: Request): ...

# Security headers
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["X-Frame-Options"] = "DENY"
response.headers["Strict-Transport-Security"] = "max-age=31536000"

# Error handling — не раскрывать детали
return JSONResponse(status_code=500, content={"detail": "Internal error"})
```

### aiogram Security

```python
# Webhook verification
secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
if secret_token != WEBHOOK_SECRET:
    raise HTTPException(status_code=403)

# Throttling middleware
if now - self.user_last_request[user_id] < self.rate_limit:
    return  # Ignore

# Callback validation
class PaymentCallback(CallbackData, prefix="pay"):
    action: Literal["confirm", "cancel"]  # Enum, не строка
    amount: int

    @field_validator("amount")
    def validate_amount(cls, v):
        if v <= 0 or v > 1000000:
            raise ValueError("Invalid amount")
        return v

# Sanitize output
safe_text = escape(message.text)
await message.answer(safe_text, parse_mode=None)
```

### SQLAlchemy Security

```python
# ПРАВИЛЬНО — parameterized
result = await session.execute(select(User).where(User.email == email))

# НИКОГДА — string concatenation
result = await session.execute(text(f"SELECT * FROM users WHERE email = '{email}'"))
```

### Secrets

```python
class Settings(BaseSettings):
    # Секреты без default — упадёт если не заданы
    database_url: SecretStr
    telegram_bot_token: SecretStr
    jwt_secret_key: SecretStr

# Использование
database_url = settings.database_url.get_secret_value()
```

### Docker

```dockerfile
# Non-root user
RUN useradd --create-home appuser
USER appuser
```

```yaml
# docker-compose
services:
  api:
    read_only: true
    cap_drop: [ALL]
    security_opt: [no-new-privileges:true]
  db:
    expose: ["5432"]  # НЕ ports — только internal
```

---

## Чек-листы

### При разработке
- [ ] Input validation на всех входах
- [ ] Проверка авторизации: ЭТОТ user → ЭТО action → ЭТОТ resource
- [ ] Нет SQL injection (parameterized queries)
- [ ] Sensitive данные не логируются
- [ ] Ошибки не раскрывают внутренности

### Перед релизом
- [ ] `pip-audit` / `npm audit` — нет vulnerabilities
- [ ] HTTPS only
- [ ] Rate limiting
- [ ] Security headers (securityheaders.com)

### Production
- [ ] Мониторинг подозрительной активности
- [ ] Бэкапы зашифрованы
- [ ] Логи без PII/секретов

---

## Контрольные вопросы

### Данные
- Какие данные sensitive? Как шифруются?
- Где секреты? Как ротируются?
- Как удаляем данные по GDPR?

### Доступ
- Кто может вызвать endpoint? Как проверяется?
- Может ли user A получить данные user B?
- Что если токен украдут?

### Input
- Что если передать 10MB данных?
- Что если в email передать SQL/JS?
- Проверяется ли webhook от Telegram?

### Infra
- Какие порты открыты? Почему?
- От какого user работает контейнер?
- Есть WAF? Rate limiting?

---

## Красные флаги

| Паттерн | Проблема |
|---------|----------|
| `f"SELECT ... {user_id}"` | SQL injection |
| `pickle.loads(user_input)` | Code execution |
| `eval()` / `exec()` с user input | Code injection |
| Секреты в коде | Credential exposure |
| `DEBUG=True` в prod | Info disclosure |
| `allow_origins=["*"]` | CORS bypass |
| JWT без expiration | Token theft |
| Логирование паролей/токенов | Credential leak |
| Root в контейнере | Container escape |
| Открытый порт PostgreSQL | DB exposure |

---

## Инструменты

| Категория | Инструмент |
|-----------|------------|
| SAST | bandit, semgrep |
| Dependencies | pip-audit, npm audit |
| Secrets | gitleaks, detect-secrets |
| DAST | OWASP ZAP |
| Headers | securityheaders.com |
| SSL | ssllabs.com |

### Pre-commit

```yaml
repos:
  - repo: https://github.com/PyCQA/bandit
    hooks: [id: bandit]
  - repo: https://github.com/Yelp/detect-secrets
    hooks: [id: detect-secrets]
  - repo: https://github.com/gitleaks/gitleaks
    hooks: [id: gitleaks]
```

# Деплой

## Быстрый старт

```bash
# Клонировать репозиторий
git clone https://github.com/your-org/telegram-billing-template.git
cd telegram-billing-template

# Скопировать переменные окружения
cp .env.example .env

# Заполнить .env (см. раздел ниже)

# Запустить
docker-compose up -d
```

---

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `ROBOKASSA_LOGIN` | Логин магазина в Робокассе |
| `ROBOKASSA_PASSWORD1` | Пароль #1 для формирования ссылки |
| `ROBOKASSA_PASSWORD2` | Пароль #2 для проверки webhook'ов |
| `DATABASE_URL` | Строка подключения к PostgreSQL |
| `WEBHOOK_BASE_URL` | Публичный URL сервера для webhook'ов |

---

## Docker

Проект включает готовые Dockerfile для backend и docs:

```
telegram-billing-template/
├── backend/
│   └── Dockerfile
├── docs/
│   └── Dockerfile
└── docker-compose.yml
```

---

## Nginx конфигурация

```nginx
server {
    listen 443 ssl http2;
    server_name bot.example.com;

    ssl_certificate /etc/letsencrypt/live/bot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.example.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## HTTPS/TLS требования

- **Telegram Webhook API** требует HTTPS с валидным сертификатом
- **Робокасса** отправляет webhook'и только на HTTPS endpoints
- Минимум **TLS 1.2** (рекомендуется TLS 1.3)
- Сертификат: **Let's Encrypt** (бесплатный) или коммерческий

---

## CI/CD

Опционально: GitHub Actions для автоматического деплоя.

Рекомендуемый pipeline:
1. Lint и тесты
2. Сборка Docker-образов
3. Push в registry
4. Deploy на сервер

---

## Масштабирование

### Single instance

- In-memory rate limiting достаточен
- SQLite или PostgreSQL

### Multiple instances

- Rate limiting через **Redis**
- PostgreSQL обязателен
- Shared session storage

---

## См. также

- [Обзор](overview.md) — структура проекта
- [Безопасность](security.md) — HTTPS требования, хранение секретов

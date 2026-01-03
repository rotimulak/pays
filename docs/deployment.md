# Деплой

## Быстрый старт (локально)

```bash
# Клонировать репозиторий
git clone https://github.com/your-org/telegram-billing-template.git
cd telegram-billing-template/backend

# Скопировать переменные окружения
cp ../.env.example .env

# Заполнить .env (см. раздел ниже)

# Запустить
docker-compose up -d
```

---

## Структура Docker

```
telegram-billing-template/
├── backend/
│   ├── Dockerfile              # Multi-stage build
│   ├── docker-compose.yml      # Development
│   ├── docker-compose.prod.yml # Production overrides
│   └── entrypoint.sh           # Startup script
├── deploy/
│   ├── deploy.sh               # Deployment script
│   └── nginx/
│       └── hhhelper.conf       # Nginx config
└── .env.example                # Environment template
```

---

## Режимы запуска

Приложение поддерживает несколько режимов:

| Режим | Команда | Описание |
|-------|---------|----------|
| `api` | `docker-compose up api` | Только FastAPI сервер |
| `bot` | `docker-compose up bot` | Только Telegram бот (polling) |
| `all` | Оба сервиса | Бот + API вместе |
| `migrate` | `./entrypoint.sh migrate` | Только миграции |

---

## Переменные окружения

### Обязательные

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `DATABASE_URL` | PostgreSQL connection string |
| `WEBHOOK_BASE_URL` | Публичный HTTPS URL для webhook'ов |

### Robokassa (опционально)

| Переменная | Описание |
|------------|----------|
| `ROBOKASSA_MERCHANT_LOGIN` | Логин магазина |
| `ROBOKASSA_PASSWORD_1` | Пароль для генерации ссылок |
| `ROBOKASSA_PASSWORD_2` | Пароль для проверки webhook'ов |
| `ROBOKASSA_IS_TEST` | Тестовый режим (1/0) |

### Docker

| Переменная | Описание |
|------------|----------|
| `POSTGRES_USER` | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL |
| `POSTGRES_DB` | Имя базы данных |

### Логирование

| Переменная | Описание |
|------------|----------|
| `LOG_LEVEL` | DEBUG, INFO, WARNING, ERROR |
| `LOG_FORMAT` | `json` (production) / `standard` (dev) |

---

## Production деплой

### 1. Подготовка сервера

```bash
# Установить Docker
apt-get update
apt-get install -y docker.io docker-compose nginx certbot python3-certbot-nginx
systemctl enable docker
```

### 2. Клонирование и настройка

```bash
mkdir -p /opt/hhhelper
cd /opt/hhhelper
git clone https://github.com/YOUR_USERNAME/pays.git .
cd backend
cp ../.env.example .env
nano .env  # Заполнить переменные
```

### 3. Запуск

```bash
# Development (с логами)
docker-compose up

# Production (фоновый режим + production overrides)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 4. Настройка Nginx

```bash
cp deploy/nginx/hhhelper.conf /etc/nginx/sites-available/
ln -sf /etc/nginx/sites-available/hhhelper.conf /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### 5. SSL сертификат

```bash
certbot --nginx -d your-domain.com
```

---

## Health Checks

| Endpoint | Описание |
|----------|----------|
| `GET /health` | Liveness probe — сервис жив |
| `GET /ready` | Readiness probe — БД подключена |

Пример:
```bash
curl http://217.171.146.4/health  # временно по IP
# curl https://hhhelper.ru/health  # после настройки DNS + SSL
# {"status":"ok","service":"hhhelper-api"}
```

---

## Полезные команды

```bash
# Логи
docker-compose logs -f
docker-compose logs -f api
docker-compose logs -f bot

# Перезапуск
docker-compose restart api
docker-compose restart bot

# Остановка
docker-compose down

# Пересборка
docker-compose build --no-cache
docker-compose up -d

# Миграции вручную
docker-compose exec api alembic upgrade head

# Shell в контейнере
docker-compose exec api bash
```

---

## Nginx конфигурация

```nginx
# Временная конфигурация (без SSL, по IP)
server {
    listen 80;
    server_name 217.171.146.4;
    # После DNS: server_name hhhelper.ru www.hhhelper.ru;

    # После получения SSL раскомментировать:
    # listen 443 ssl http2;
    # ssl_certificate /etc/letsencrypt/live/hhhelper.ru/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/hhhelper.ru/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8001/health;
        access_log off;
    }
}
```

---

## Troubleshooting

### Контейнер не стартует

```bash
# Проверить логи
docker-compose logs api

# Проверить статус БД
docker-compose exec db pg_isready
```

### Миграции не применяются

```bash
# Запустить вручную
docker-compose exec api alembic upgrade head

# Проверить текущую версию
docker-compose exec api alembic current
```

### Бот не отвечает

1. Проверить `TELEGRAM_BOT_TOKEN`
2. Проверить логи: `docker-compose logs bot`
3. Убедиться, что бот не запущен где-то ещё

---

## HTTPS/TLS требования

- **Telegram Webhook API** требует HTTPS с валидным сертификатом
- **Робокасса** отправляет webhook'и только на HTTPS endpoints
- Минимум **TLS 1.2** (рекомендуется TLS 1.3)
- Сертификат: **Let's Encrypt** (бесплатный) или коммерческий

---

## См. также

- [Обзор](overview.md) — структура проекта
- [Безопасность](security.md) — HTTPS требования, хранение секретов

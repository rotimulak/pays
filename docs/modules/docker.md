# Docker & Deploy

> Контейнеризация приложения и production deployment.

**Milestone:** M10
**Статус:** Реализовано

---

## Обзор

Модуль обеспечивает:
- Multi-stage Docker build
- Раздельные режимы запуска (bot, api, all)
- Health checks для мониторинга
- Structured logging для production
- Production-ready конфигурация

---

## Структура

```
backend/
├── Dockerfile              # Multi-stage build
├── docker-compose.yml      # Development
├── docker-compose.prod.yml # Production overrides
└── entrypoint.sh           # Startup script

deploy/
├── deploy.sh               # Deployment script
└── nginx/
    └── hhhelper.conf       # Nginx config
```

---

## Режимы запуска

| Режим | Описание | Команда |
|-------|----------|---------|
| `api` | Только FastAPI сервер | `docker-compose up api` |
| `bot` | Только Telegram бот (polling) | `docker-compose up bot` |
| `all` | Бот + API вместе | Default |
| `migrate` | Только миграции | `./entrypoint.sh migrate` |
| `shell` | Bash shell для отладки | `./entrypoint.sh shell` |

---

## Health Checks

| Endpoint | Тип | Описание |
|----------|-----|----------|
| `GET /health` | Liveness | Сервис жив |
| `GET /ready` | Readiness | БД подключена |

### Ответы

```json
// GET /health
{"status": "ok", "service": "hhhelper-api"}

// GET /ready
{"status": "ok", "database": "connected", "service": "hhhelper-api"}
```

---

## Логирование

### Форматы

| Формат | Переменная | Использование |
|--------|------------|---------------|
| `standard` | `LOG_FORMAT=standard` | Development |
| `json` | `LOG_FORMAT=json` | Production |

### Уровни

`LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR

### JSON формат (production)

```json
{
  "timestamp": "2025-01-03T12:00:00.000000+00:00",
  "level": "INFO",
  "logger": "src.main",
  "message": "Bot started"
}
```

---

## Конфигурация

### Переменные окружения

| Переменная | Описание | Default |
|------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `TELEGRAM_BOT_TOKEN` | Bot token | Required |
| `WEBHOOK_BASE_URL` | Public HTTPS URL | Required |
| `LOG_LEVEL` | Log level | `INFO` |
| `LOG_FORMAT` | Log format | `standard` |
| `POSTGRES_USER` | Docker DB user | `postgres` |
| `POSTGRES_PASSWORD` | Docker DB password | `postgres` |
| `POSTGRES_DB` | Docker DB name | `telegram_billing` |

---

## Использование

### Development

```bash
cd backend
docker-compose up -d
```

### Production

```bash
cd backend
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Проверка

```bash
# Health check
curl http://localhost:8001/health

# Readiness check
curl http://localhost:8001/ready

# Логи
docker-compose logs -f api
docker-compose logs -f bot
```

---

## Entrypoint

[backend/entrypoint.sh](../../backend/entrypoint.sh) выполняет:

1. **Wait for database** — ждёт готовности PostgreSQL
2. **Run migrations** — применяет Alembic миграции
3. **Start application** — запускает в выбранном режиме

---

## Production Overrides

[docker-compose.prod.yml](../../backend/docker-compose.prod.yml):

- Resource limits (CPU, memory)
- JSON logging
- Restart policies (`always`)
- Не экспортирует порт БД

---

## Зависимости

- **От:** Database (PostgreSQL)
- **Для:** Nginx (reverse proxy), Certbot (SSL)

---

## См. также

- [Деплой](../deployment.md) — полная инструкция
- [Безопасность](../security.md) — HTTPS, rate limiting

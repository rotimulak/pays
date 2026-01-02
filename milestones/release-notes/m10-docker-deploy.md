# Release Notes: M10 Docker & Deploy

**Дата:** 2025-01-03
**Версия:** 1.0.0

---

## Новые возможности

### Docker

- **Multi-stage Dockerfile** — оптимизированная сборка с разделением на builder и runtime
- **Non-root user** — контейнер работает под непривилегированным пользователем `appuser`
- **Docker healthcheck** — встроенная проверка состояния контейнера

### Режимы запуска

- `bot` — только Telegram бот (polling mode)
- `api` — только FastAPI сервер
- `all` — бот + API вместе (default)
- `migrate` — только выполнение миграций
- `shell` — bash shell для отладки

### Health Checks

- `GET /health` — liveness probe (сервис жив)
- `GET /ready` — readiness probe (БД подключена)

### Structured Logging

- **JSON формат** для production (`LOG_FORMAT=json`)
- **Standard формат** для development (`LOG_FORMAT=standard`)
- Настраиваемый уровень логирования через `LOG_LEVEL`

### Production Configuration

- `docker-compose.prod.yml` с resource limits
- Restart policies (`always`)
- JSON logging driver
- Закрытый порт БД

---

## Файлы

| Файл | Описание |
|------|----------|
| `backend/Dockerfile` | Multi-stage build |
| `backend/docker-compose.yml` | Development config |
| `backend/docker-compose.prod.yml` | Production overrides |
| `backend/entrypoint.sh` | Startup script |
| `backend/src/api/routes/health.py` | Health endpoints |
| `backend/src/core/logging.py` | Logging configuration |
| `deploy/deploy.sh` | Deployment script |
| `deploy/nginx/hhhelper.conf` | Nginx config |

---

## Переменные окружения

Новые переменные:

| Переменная | Описание | Default |
|------------|----------|---------|
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `LOG_FORMAT` | Формат логов | `standard` |
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
curl http://localhost:8001/health
curl http://localhost:8001/ready
docker-compose logs -f
```

---

## Breaking Changes

Нет.

---

## Известные ограничения

- Размер образа не проверен на соответствие <500MB
- Worker mode (`--mode worker`) требует реализации `src.tasks`

---

## См. также

- [Документация модуля](../../docs/modules/docker.md)
- [Инструкция по деплою](../../docs/deployment.md)
- [Milestone описание](../m10-docker-and-deploy.md)

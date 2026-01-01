# M10: Docker & Deploy

## Цель

Контейнеризация приложения и подготовка к production deployment. После этого milestone сервис можно развернуть на сервере.

---

## Задачи

### 10.1 Dockerfile

- [ ] `backend/Dockerfile`
  - Multi-stage build (builder + runtime)
  - Non-root user
  - Health check
  - Оптимизация слоёв для кэширования

### 10.2 Docker Compose

- [ ] `docker-compose.yml` — development
  - backend service
  - PostgreSQL service
  - Volume для данных БД
  - Network

- [ ] `docker-compose.prod.yml` — production overrides
  - Без bind mounts
  - Resource limits
  - Restart policies

### 10.3 Environment

- [ ] `.env.example` — шаблон всех переменных
- [ ] `.env.docker` — переменные для docker-compose
- [ ] Валидация обязательных переменных при старте

### 10.4 Entrypoint

- [ ] `backend/entrypoint.sh`
  - Wait for database
  - Run migrations
  - Start application

### 10.5 Application Modes

- [ ] Поддержка разных режимов запуска:
  - `bot` — только Telegram бот (polling)
  - `api` — только FastAPI (webhook mode)
  - `all` — бот + API вместе
  - `worker` — только scheduled tasks

### 10.6 Health Checks

- [ ] `GET /health` — liveness probe
- [ ] `GET /ready` — readiness probe (DB connection)

### 10.7 Logging

- [ ] Structured logging (JSON format для production)
- [ ] Настройка log levels через env

---

## Definition of Done (DoD)

- [ ] `docker-compose up` запускает весь стек
- [ ] Миграции выполняются автоматически при старте
- [ ] Бот подключается и отвечает на команды
- [ ] API endpoints доступны
- [ ] Health checks проходят
- [ ] Graceful shutdown работает
- [ ] Логи в структурированном формате
- [ ] Secrets не в образе (через env/secrets)
- [ ] Образ собирается меньше 500MB
- [ ] Документация по деплою

---

## Артефакты

```
├── backend/
│   ├── Dockerfile
│   └── entrypoint.sh
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── docs/
    └── deployment.md (updated)
```

---

## Dockerfile

```dockerfile
# Build stage
FROM python:3.12-slim as builder

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt -o requirements.txt --without-hashes

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 appuser

# Install dependencies
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser migrations/ ./migrations/
COPY --chown=appuser:appuser alembic.ini .
COPY --chown=appuser:appuser entrypoint.sh .

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["./entrypoint.sh"]
CMD ["all"]
```

---

## docker-compose.yml

```yaml
version: "3.8"

services:
  backend:
    build: ./backend
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${DB_USER:-billing}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME:-billing}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-billing}"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

---

## entrypoint.sh

```bash
#!/bin/bash
set -e

# Wait for database
echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 1
done
echo "Database is ready"

# Run migrations
echo "Running migrations..."
alembic upgrade head

# Start application
case "$1" in
  bot)
    echo "Starting bot (polling mode)..."
    python -m src.main --mode bot
    ;;
  api)
    echo "Starting API server..."
    uvicorn src.api:app --host 0.0.0.0 --port 8000
    ;;
  worker)
    echo "Starting background worker..."
    python -m src.tasks
    ;;
  all|*)
    echo "Starting bot + API..."
    python -m src.main --mode all
    ;;
esac
```

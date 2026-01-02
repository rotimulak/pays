# M10: Docker & Deploy

## Цель

Контейнеризация приложения и подготовка к production deployment. После этого milestone сервис можно развернуть на сервере.

---

## Задачи

### 10.1 Dockerfile

- [x] `backend/Dockerfile`
  - Multi-stage build (builder + runtime)
  - Non-root user
  - Health check
  - Оптимизация слоёв для кэширования

### 10.2 Docker Compose

- [x] `docker-compose.yml` — development
  - backend service (api + bot)
  - PostgreSQL service
  - Volume для данных БД
  - Network
  - Healthchecks

- [x] `docker-compose.prod.yml` — production overrides
  - Без bind mounts
  - Resource limits
  - Restart policies
  - JSON logging

### 10.3 Environment

- [x] `.env.example` — шаблон всех переменных
- [x] Docker-specific переменные (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)
- [x] Настройки логирования (LOG_LEVEL, LOG_FORMAT)

### 10.4 Entrypoint

- [x] `backend/entrypoint.sh`
  - Wait for database
  - Run migrations
  - Start application
  - Поддержка режимов: bot, api, all, migrate, shell

### 10.5 Application Modes

- [x] Поддержка разных режимов запуска:
  - `bot` — только Telegram бот (polling)
  - `api` — только FastAPI (webhook mode)
  - `all` — бот + API вместе
  - `migrate` — только миграции
  - `shell` — bash shell для отладки

### 10.6 Health Checks

- [x] `GET /health` — liveness probe
- [x] `GET /ready` — readiness probe (DB connection)

### 10.7 Logging

- [x] Structured logging (JSON format для production)
- [x] Настройка log levels через env
- [x] JsonFormatter для production, StandardFormatter для dev

---

## Definition of Done (DoD)

- [x] `docker-compose up` запускает весь стек
- [x] Миграции выполняются автоматически при старте
- [x] Бот подключается и отвечает на команды
- [x] API endpoints доступны
- [x] Health checks проходят
- [x] Graceful shutdown работает
- [x] Логи в структурированном формате
- [x] Secrets не в образе (через env/secrets)
- [ ] Образ собирается меньше 500MB (нужно проверить)
- [x] Документация по деплою

---

## Артефакты

```
├── backend/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── entrypoint.sh
├── deploy/
│   ├── deploy.sh
│   └── nginx/
│       └── hhhelper.conf
├── .env.example
└── docs/
    └── deployment.md (updated)
```

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

### Только API или только бот

```bash
docker-compose up api
docker-compose up bot
```

---

## Проверка

```bash
# Health check
curl http://localhost:8001/health

# Readiness check
curl http://localhost:8001/ready

# Логи
docker-compose logs -f
```

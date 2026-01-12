# DevOps Role

> Роль для деплоя, миграций и управления инфраструктурой HHHelper.

---

## Проект

**Название:** HHHelper (Telegram Billing Template)
**Стек:** Python 3.12, aiogram 3.x, FastAPI, SQLAlchemy 2.x async, PostgreSQL 16, Alembic
**Домен:** `hhhelper.ru` (временно: `http://217.171.146.4`)
**Репозиторий:** `https://github.com/rotimulak/pays.git`

---

## Структура инфраструктуры

```
backend/
├── Dockerfile              # Multi-stage build (python:3.12-slim)
├── docker-compose.yml      # Development
├── docker-compose.prod.yml # Production overrides
├── entrypoint.sh           # Startup script
├── alembic.ini             # Alembic config
└── migrations/             # Database migrations
    └── versions/           # Migration files (001-007)

deploy/
├── deploy.sh               # Full deployment script
└── nginx/
    └── hhhelper.conf       # Nginx config
```

---

## Сервисы Docker

| Сервис | Контейнер | Порт | Описание |
|--------|-----------|------|----------|
| `api` | hhhelper-api | 8001:8000 | FastAPI сервер |
| `bot` | hhhelper-bot | - | Telegram бот (polling) |
| `db` | hhhelper-db | 5433:5432 | PostgreSQL 16 |

---

## Режимы запуска

> ⚠️ **На сервере используй `docker compose` (v2), не `docker-compose`!**

```bash
# Development
docker compose up -d

# Production (с ресурсными лимитами и JSON логами)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Только API
docker compose up -d api

# Только бот
docker compose up -d bot

# Только миграции
docker compose exec api ./entrypoint.sh migrate

# Shell для отладки
docker compose exec api ./entrypoint.sh shell
```

---

## Миграции базы данных

### Alembic команды

```bash
# Применить все миграции
docker-compose exec api alembic upgrade head

# Текущая версия
docker-compose exec api alembic current

# История миграций
docker-compose exec api alembic history

# Откатить на одну версию
docker-compose exec api alembic downgrade -1

# Откатить до конкретной версии
docker-compose exec api alembic downgrade <revision>

# Создать новую миграцию
docker-compose exec api alembic revision --autogenerate -m "description"
```

### Существующие миграции

| Файл | Описание |
|------|----------|
| 001_initial.py | Начальная схема |
| 002_add_bonus_tokens_discount_type.py | Бонусные токены и тип скидки |
| 004_add_users_last_balance_notification.py | Уведомления о балансе |
| 005_add_subscription_fields.py | Поля подписок |
| 006_add_subscription_transaction_type.py | Тип транзакции подписки |
| 007_add_tariff_period_fields.py | Периоды тарифов |

### Создание миграции (локально)

```bash
cd backend
python -m alembic revision --autogenerate -m "description"
```

---

## Переменные окружения

### Обязательные

| Переменная | Описание | Пример |
|------------|----------|--------|
| `TELEGRAM_BOT_TOKEN` | Токен бота | `123456:ABC-DEF...` |
| `DATABASE_URL` | PostgreSQL URL | `postgresql+asyncpg://user:pass@host:5432/db` |
| `WEBHOOK_BASE_URL` | HTTPS URL для webhook'ов | `https://hhhelper.ru` (временно: `http://217.171.146.4`) |

### Robokassa

| Переменная | Описание |
|------------|----------|
| `ROBOKASSA_MERCHANT_LOGIN` | Логин магазина |
| `ROBOKASSA_PASSWORD_1` | Пароль для генерации ссылок |
| `ROBOKASSA_PASSWORD_2` | Пароль для проверки webhook'ов |
| `ROBOKASSA_IS_TEST` | Тестовый режим (1/0) |

### Docker

| Переменная | Default | Описание |
|------------|---------|----------|
| `POSTGRES_USER` | postgres | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | postgres | Пароль PostgreSQL |
| `POSTGRES_DB` | telegram_billing | База данных |
| `BUILD_VERSION` | dev | Версия билда (автоматически из git hash) |

### Логирование

| Переменная | Значения | Default |
|------------|----------|---------|
| `LOG_LEVEL` | DEBUG, INFO, WARNING, ERROR | INFO |
| `LOG_FORMAT` | json (prod), standard (dev) | standard |

---

## Деплой на VPS

### Подготовка сервера (Ubuntu)

```bash
apt-get update
apt-get install -y docker.io docker-compose nginx certbot python3-certbot-nginx
systemctl enable docker
systemctl start docker
```

### Первый деплой

```bash
# 1. Клонировать
mkdir -p /opt/hhhelper
cd /opt/hhhelper
git clone https://github.com/rotimulak/pays.git .

# 2. Настроить окружение
cd backend
cp ../.env.example .env
nano .env  # Заполнить переменные

# 3. Запустить
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. Nginx
cp ../deploy/nginx/hhhelper.conf /etc/nginx/sites-available/
ln -sf /etc/nginx/sites-available/hhhelper.conf /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# 5. SSL
certbot --nginx -d hhhelper.ru
```

### Обновление

```bash
cd /opt/hhhelper
git pull origin main
cd backend
export BUILD_VERSION=$(git rev-parse --short HEAD)
docker compose build --no-cache
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Quick Deploy (одной командой с локальной машины)

```bash
ssh root@217.171.146.4 "cd /opt/hhhelper && git pull origin main && cd backend && export BUILD_VERSION=\$(git rev-parse --short HEAD) && docker compose build --no-cache && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
```

### Автоматический деплой

```bash
cd /opt/hhhelper
sudo ./deploy/deploy.sh
```

---

## Health Checks

| Endpoint | Тип | Описание |
|----------|-----|----------|
| `GET /health` | Liveness | Сервис жив |
| `GET /ready` | Readiness | БД подключена |

```bash
# Проверка
curl https://hhhelper.ru/health
curl https://hhhelper.ru/ready
```

---

## Управление контейнерами

```bash
# Логи
docker-compose logs -f
docker-compose logs -f api
docker-compose logs -f bot
docker-compose logs -f db

# Статус
docker-compose ps

# Перезапуск
docker-compose restart api
docker-compose restart bot

# Остановка
docker-compose down

# Полная пересборка
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## База данных

### Подключение

```bash
# Через Docker
docker-compose exec db psql -U postgres -d telegram_billing

# Извне (dev порт 5433)
psql -h localhost -p 5433 -U postgres -d telegram_billing
```

### Бэкап и восстановление

```bash
# Бэкап
docker-compose exec db pg_dump -U postgres telegram_billing > backup.sql

# Восстановление
cat backup.sql | docker-compose exec -T db psql -U postgres telegram_billing
```

### Просмотр данных

```sql
-- Пользователи
SELECT * FROM users LIMIT 10;

-- Тарифы
SELECT * FROM tariffs;

-- Инвойсы
SELECT * FROM invoices ORDER BY created_at DESC LIMIT 10;

-- Транзакции
SELECT * FROM token_transactions ORDER BY created_at DESC LIMIT 10;
```

---

## Nginx конфигурация

Файл: `/etc/nginx/sites-available/hhhelper.conf`

```nginx
server {
    listen 80;
    server_name hhhelper.ru;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name hhhelper.ru;

    ssl_certificate /etc/letsencrypt/live/hhhelper.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hhhelper.ru/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## SSL сертификаты

```bash
# Получить сертификат
certbot --nginx -d hhhelper.ru

# Обновить сертификаты
certbot renew

# Проверить автообновление
certbot renew --dry-run
```

---

## Troubleshooting

### ⚠️ Известные грабли (Lessons Learned)

#### 1. Docker Compose v2 на сервере

На сервере установлен Docker Compose v2, команда `docker-compose` НЕ работает!

```bash
# ❌ НЕ работает
docker-compose up -d

# ✅ Работает
docker compose up -d
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

#### 2. PostgreSQL password mismatch

Если БД не стартует с ошибкой `password authentication failed`:

```bash
# Проблема: старый volume с другим паролем
# Решение: удалить volume и пересоздать (ВНИМАНИЕ: данные будут потеряны!)
docker compose down -v
docker compose up -d
```

После пересоздания БД нужно вставить дефолтный тариф:

```bash
docker exec hhhelper-db psql -U postgres -d telegram_billing -c "
INSERT INTO tariffs (
    id, slug, name, description, price, tokens, is_active, sort_order,
    period_unit, period_value, subscription_fee, min_payment, created_at, updated_at
) VALUES (
    gen_random_uuid(), 'default', 'Стандартный тариф', 'Основной тариф',
    200.00, 200, true, 1,
    'month', 1, 100, 200.00, NOW(), NOW()
);
"
```

#### 3. SSH connection timeout

Если SSH зависает на "banner exchange":
- Проверить правильный IP в `.env` (VPS_IP)
- Старый IP может быть закэширован в `~/.ssh/known_hosts`
- VPS может иметь несколько IP адресов

```bash
# Удалить старый ключ
ssh-keygen -R <old_ip>

# Проверить текущий IP
cat .env | grep VPS_IP
```

#### 4. Тарифы не найдены в боте

Если бот показывает "К сожалению, сейчас нет доступных тарифов":
1. Проверить, что код задеплоен (git status на сервере)
2. Проверить наличие тарифа в БД: `SELECT * FROM tariffs WHERE is_active = true;`
3. Проверить миграцию 007 применена: `docker compose exec api python -m alembic current`

### Контейнер не стартует

```bash
docker compose logs api
docker compose logs bot
docker compose exec db pg_isready
```

### Миграции не применяются

```bash
docker-compose exec api alembic current
docker-compose exec api alembic upgrade head
```

### Бот не отвечает

1. Проверить `TELEGRAM_BOT_TOKEN` в `.env`
2. Проверить логи: `docker-compose logs bot`
3. Убедиться, что бот не запущен где-то ещё

### База недоступна

```bash
# Статус контейнера
docker-compose ps db

# Проверить healthcheck
docker-compose exec db pg_isready -U postgres

# Перезапустить
docker-compose restart db
```

### Nginx 502 Bad Gateway

```bash
# Проверить API
curl http://127.0.0.1:8001/health

# Проверить логи nginx
tail -f /var/log/nginx/error.log
```

---

## Resource Limits (Production)

| Сервис | CPU | Memory |
|--------|-----|--------|
| api | 1.0 (0.25 reserved) | 512M (128M reserved) |
| bot | 0.5 (0.1 reserved) | 256M (64M reserved) |
| db | 1.0 (0.25 reserved) | 512M (128M reserved) |

---

## Мониторинг

```bash
# Ресурсы контейнеров
docker stats

# Логи в реальном времени (JSON формат в production)
docker-compose logs -f --tail=100
```

---

## Полезные пути

| Путь | Описание |
|------|----------|
| `/opt/hhhelper/` | Корень приложения на сервере |
| `/opt/hhhelper/backend/.env` | Переменные окружения |
| `/etc/nginx/sites-available/hhhelper.conf` | Nginx конфиг |
| `/etc/letsencrypt/live/hhhelper.ru/` | SSL сертификаты |
| `/var/log/nginx/` | Логи nginx |

---

## Checklist перед деплоем

- [ ] `.env` заполнен корректно
- [ ] `TELEGRAM_BOT_TOKEN` актуален
- [ ] `WEBHOOK_BASE_URL` указывает на HTTPS домен
- [ ] Robokassa credentials заполнены (если production)
- [ ] DNS записи настроены на IP сервера
- [ ] Порты 80, 443 открыты
- [ ] SSH ключи настроены

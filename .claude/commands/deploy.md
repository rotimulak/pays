# Deploy to VPS

Выполни деплой приложения HHHelper на VPS сервер.

## Шаги деплоя

1. **Проверь git статус локально** — убедись что все изменения закоммичены и запушены в main

2. **Выполни Quick Deploy** через SSH:
```bash
ssh root@217.171.146.4 "cd /opt/hhhelper && git pull origin main && cd backend && export BUILD_VERSION=\$(git rev-parse --short HEAD) && docker compose build --no-cache && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
```

3. **Проверь health endpoints** после деплоя:
```bash
ssh root@217.171.146.4 "curl -s http://127.0.0.1:8001/health && echo && curl -s http://127.0.0.1:8001/ready"
```

4. **Проверь логи контейнеров** на наличие ошибок:
```bash
ssh root@217.171.146.4 "cd /opt/hhhelper/backend && docker compose logs --tail=20 api bot"
```

## При ошибках

- Если контейнер не стартует: `docker compose logs api` или `docker compose logs bot`
- Если БД недоступна: `docker compose exec db pg_isready -U postgres`
- Если миграции не применились: `docker compose exec api alembic upgrade head`

## Справка

Полная документация: [docs/roles/devops.md](../../docs/roles/devops.md)

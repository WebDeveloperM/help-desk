# Шпаргалка по Docker для HelpDesk (production)

Команды для перезапуска, пересоздания контейнеров и отладки. Файл стека: `docker-compose.prod.yml`, переменные: `.env.prod`.

---

## Переменные для команд

Удобно задать один раз в сессии (или в `~/.bashrc` / `~/.zshrc`):

```bash
export COMPOSE_FILE=docker-compose.prod.yml
export COMPOSE_ENV=--env-file .env.prod
# Тогда вместо полной строки можно писать:
# docker compose -f docker-compose.prod.yml --env-file .env.prod  →  docker compose $COMPOSE_ENV
```

Ниже везде используется полная форма `-f docker-compose.prod.yml --env-file .env.prod`.

---

## Запуск и остановка

| Действие | Команда |
|----------|---------|
| **Запустить весь стек** | `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d` |
| **Остановить все контейнеры** | `docker compose -f docker-compose.prod.yml --env-file .env.prod stop` |
| **Остановить и удалить контейнеры** (volumes остаются) | `docker compose -f docker-compose.prod.yml --env-file .env.prod down` |
| **Остановить и удалить контейнеры + volumes** | `docker compose -f docker-compose.prod.yml --env-file .env.prod down -v` |

---

## Перезапуск контейнеров

| Действие | Команда |
|----------|---------|
| **Перезапустить все сервисы** | `docker compose -f docker-compose.prod.yml --env-file .env.prod restart` |
| **Перезапустить один сервис** | `docker compose -f docker-compose.prod.yml --env-file .env.prod restart nginx` |
| **Перезапустить backend** | `docker compose -f docker-compose.prod.yml --env-file .env.prod restart backend` |
| **Перезапустить Keycloak** | `docker compose -f docker-compose.prod.yml --env-file .env.prod restart keycloak` |

---

## Пересоздание контейнеров (recreate)

Пересоздаёт контейнеры без пересборки образов. Нужно после изменения `docker-compose.prod.yml` или переменных окружения.

| Действие | Команда |
|----------|---------|
| **Пересоздать все контейнеры** | `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate` |
| **Пересоздать только nginx** | `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate nginx` |
| **Пересоздать только Keycloak** | `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate keycloak` |
| **Пересоздать backend** | `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate backend` |

После изменения **nginx.conf** достаточно пересоздать nginx:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate nginx
```

---

## Пересборка образов (build)

Нужно после изменения кода приложения (frontend/backend) или Dockerfile.

| Действие | Команда |
|----------|---------|
| **Пересобрать все образы и запустить** | `docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build` |
| **Пересобрать только frontend** | `docker compose -f docker-compose.prod.yml --env-file .env.prod build frontend` затем `up -d` |
| **Пересобрать только backend** | `docker compose -f docker-compose.prod.yml --env-file .env.prod build backend` затем `up -d` |
| **Пересобрать без кэша (чистая сборка)** | `docker compose -f docker-compose.prod.yml --env-file .env.prod build --no-cache frontend` (или `backend`) |

После пересборки frontend нужно пересоздать nginx (он монтирует volume со статикой):
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build frontend
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate nginx
```

---

## Полный цикл: остановить → пересобрать → запустить

```bash
# 1. Остановить и удалить контейнеры (volumes не трогаем)
docker compose -f docker-compose.prod.yml --env-file .env.prod down

# 2. Пересобрать образы (если меняли код)
docker compose -f docker-compose.prod.yml --env-file .env.prod build

# 3. Запустить
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

Одной строкой (остановить, пересобрать, запустить):
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod down && \
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

---

## Логи

| Действие | Команда |
|----------|---------|
| **Логи всех сервисов** | `docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f` |
| **Логи одного сервиса (следить)** | `docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f backend` |
| **Последние 100 строк Keycloak** | `docker logs helpdesk-keycloak --tail 100` |
| **Последние 50 строк nginx** | `docker logs helpdesk-nginx --tail 50` |
| **Логи backend** | `docker logs helpdesk-backend --tail 100` |

Имена контейнеров: `helpdesk-nginx`, `helpdesk-backend`, `helpdesk-keycloak`, `helpdesk-keycloak-db`, `helpdesk-db`.

---

## Состояние и отладка

| Действие | Команда |
|----------|---------|
| **Список контейнеров (все)** | `docker ps -a` |
| **Только контейнеры проекта** | `docker compose -f docker-compose.prod.yml --env-file .env.prod ps -a` |
| **Войти в контейнер (shell)** | `docker exec -it helpdesk-backend sh` (или `helpdesk-nginx`, `helpdesk-keycloak`) |
| **Проверить переменные в Keycloak** | `docker exec helpdesk-keycloak env \| grep KC_` |
| **Проверить, слушает ли Keycloak 8080** | `docker exec helpdesk-keycloak bash -c 'echo -n >/dev/tcp/127.0.0.1/8080' 2>/dev/null && echo OK \|\| echo FAIL` |

---

## Volumes

| Действие | Команда |
|----------|---------|
| **Список volumes** | `docker volume ls` |
| **Удалить volume БД Keycloak** (полный сброс Keycloak) | `docker compose -f docker-compose.prod.yml --env-file .env.prod down` затем `docker volume rm helpdesk_keycloak_db_data` |
| **Удалить volume БД приложения** | `docker volume rm helpdesk_postgres_data` (только если данные не нужны!) |

Если `volume rm` пишет «in use», сначала удалите контейнеры:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod down
docker rm -f helpdesk-keycloak helpdesk-keycloak-db 2>/dev/null || true
docker volume rm helpdesk_keycloak_db_data
```

---

## Полный снос: контейнеры + образы + volumes, затем чистая установка

Когда нужно снести всё и поставить заново (после смены конфигурации Keycloak/nginx и т.п.):

```bash
# 1. Остановить и удалить контейнеры и volumes проекта
docker compose -f docker-compose.prod.yml --env-file .env.prod down -v

# 2. Удалить все контейнеры проекта (если остались)
docker rm -f helpdesk-nginx helpdesk-backend helpdesk-frontend-builder helpdesk-keycloak helpdesk-keycloak-db helpdesk-db 2>/dev/null || true

# 3. Удалить volumes проекта (БД и статика)
docker volume rm helpdesk_postgres_data helpdesk_keycloak_db_data helpdesk_frontend_static 2>/dev/null || true

# 4. (Опционально) Удалить образы проекта — если нужна полная пересборка
docker compose -f docker-compose.prod.yml --env-file .env.prod down --rmi local
# или удалить вручную: docker rmi helpdesk-backend helpdesk-frontend-builder nginx:alpine postgres:16-alpine quay.io/keycloak/keycloak:25 ...

# 5. Проверить, что в .env.prod заданы KEYCLOAK_ISSUER=https://korxona.com/realms/helpdesk и KEYCLOAK_PUBLIC_URL=https://korxona.com

# 6. Запустить с нуля
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

После первого запуска: зайти в `https://korxona.com/admin/`, создать realm **helpdesk** и клиента **helpdesk-backend**, прописать в клиенте Valid redirect URIs и т.д. по [KEYCLOAK_SETUP.md](KEYCLOAK_SETUP.md).

---

## Keycloak: полный сброс БД и повторный запуск

Когда нужно заново создать админа и realm (например, после «user doesn't exist»):

```bash
# 1. Остановить стек
docker compose -f docker-compose.prod.yml --env-file .env.prod down

# 2. Удалить контейнеры Keycloak и его БД (если остались)
docker rm -f helpdesk-keycloak helpdesk-keycloak-db 2>/dev/null || true

# 3. Удалить volume БД Keycloak
docker volume rm helpdesk_keycloak_db_data

# 4. Запустить снова (Keycloak создаст БД и bootstrap-админа из .env.prod)
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

Дальше: зайти в `https://korxona.com/admin/`, создать realm **helpdesk** и клиента **helpdesk-backend** по [KEYCLOAK_SETUP.md](KEYCLOAK_SETUP.md).

---

## Краткая шпаргалка (копировать)

```bash
# Запуск
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Остановка
docker compose -f docker-compose.prod.yml --env-file .env.prod down

# Перезапуск всего
docker compose -f docker-compose.prod.yml --env-file .env.prod restart

# Пересоздать контейнеры (без пересборки)
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate

# Пересобрать и запустить
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Только nginx пересоздать (после смены nginx.conf)
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate nginx

# Логи Keycloak
docker logs helpdesk-keycloak --tail 100 -f

# Список контейнеров
docker ps -a
```

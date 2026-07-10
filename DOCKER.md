# Docker — типичные команды HelpDesk

Краткий справочник по запуску и изменению контейнеров. Подробная шпаргалка для production: [docs/DOCKER_CHEATSHEET.md](docs/DOCKER_CHEATSHEET.md).

**Можно вызывать команды через Makefile:** `make up`, `make down`, `make build`, `make prod-up` и т.д. — полный список: `make help`.

---

## Какой compose использовать

| Режим | Файл | Env-файл | Приложение |
|--------|------|----------|------------|
| **Локальная разработка/сеть** | `docker-compose.yml` | `.env.local` | http://localhost (порт 80) |
| **Production** | `docker-compose.prod.yml` | `.env.prod` | по вашему домену |

Перед первым запуском: скопировать пример env и при необходимости отредактировать:
- локально: `cp .env.local.example .env.local`
- прод: `cp .env.prod.example .env.prod`

---

## Важно: как устроен фронтенд в Docker

Сервис **frontend** в compose — это **одноразовая задача**: контейнер собирает приложение, копирует статику в volume `frontend_static` и завершается. Сообщение в логах **"Frontend static files ready"** и последующий выход контейнера — **норма**.  
Приложение отдаёт **nginx**: он монтирует тот же volume и раздаёт статику, а запросы `/api/` и `/realms/` проксирует на backend и Keycloak.

---

## Локальная разработка (docker-compose.yml)

```bash
# Запустить весь стек (backend, keycloak, db, frontend-сборка, nginx)
docker compose --env-file .env.local up -d

# Остановить контейнеры
docker compose --env-file .env.local down

# Остановить и удалить контейнеры + volumes
docker compose --env-file .env.local down -v

# Пересобрать образы и запустить
docker compose --env-file .env.local up -d --build

# Пересобрать только backend
docker compose --env-file .env.local build backend && docker compose --env-file .env.local up -d

# Пересобрать только frontend (сборка + копирование в volume), затем пересоздать nginx
docker compose --env-file .env.local up -d --build frontend
docker compose --env-file .env.local up -d --force-recreate nginx

# Пересоздать контейнеры без пересборки (после смены .env.local или compose)
docker compose --env-file .env.local up -d --force-recreate

# Логи (все сервисы или один)
docker compose --env-file .env.local logs -f
docker compose --env-file .env.local logs -f backend
docker compose --env-file .env.local logs -f nginx
```

---

## Production (docker-compose.prod.yml)

```bash
# Запустить стек
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Остановить
docker compose -f docker-compose.prod.yml --env-file .env.prod down

# Пересобрать и запустить
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Пересоздать контейнеры (без пересборки образов)
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate

# Перезапустить один сервис
docker compose -f docker-compose.prod.yml --env-file .env.prod restart nginx
docker compose -f docker-compose.prod.yml --env-file .env.prod restart backend

# Логи
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f backend
```

Полный набор команд (пересборка по сервисам, volumes, сброс Keycloak и т.д.) — в [docs/DOCKER_CHEATSHEET.md](docs/DOCKER_CHEATSHEET.md).

---

## Быстрые команды (копировать)

**Локально:**
```bash
docker compose --env-file .env.local up -d
docker compose --env-file .env.local down
docker compose --env-file .env.local up -d --build
```

**Production:**
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
docker compose -f docker-compose.prod.yml --env-file .env.prod down
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

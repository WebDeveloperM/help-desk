# HelpDesk Docker — see DOCKER.md and docs/DOCKER_CHEATSHEET.md
# Local: docker-compose.yml + .env.local  |  Prod: docker-compose.prod.yml + .env.prod

COMPOSE_LOCAL  = docker compose --env-file .env.local
COMPOSE_PROD   = docker compose -f docker-compose.prod.yml --env-file .env.prod

.PHONY: help \
	env-local env-prod \
	up down down-v build build-backend build-frontend recreate restart ps logs logs-backend logs-nginx \
	backend-migrate \
	prod-up prod-down prod-down-v prod-build prod-build-backend prod-build-frontend prod-recreate prod-restart prod-ps prod-logs prod-logs-backend \
	prod-backend-migrate

help:
	@echo "HelpDesk Docker — local (default) and prod targets"
	@echo ""
	@echo "Env setup:"
	@echo "  make env-local    Copy .env.local.example -> .env.local"
	@echo "  make env-prod     Copy .env.prod.example -> .env.prod"
	@echo ""
	@echo "Local (docker-compose.yml + .env.local):"
	@echo "  make up           Start stack"
	@echo "  make down         Stop and remove containers"
	@echo "  make down-v       Down + remove volumes"
	@echo "  make build        Rebuild images and start"
	@echo "  make build-backend   Rebuild backend only and start"
	@echo "  make build-frontend  Rebuild frontend, then recreate nginx"
	@echo "  make recreate     Recreate containers (no image rebuild)"
	@echo "  make restart      Restart all (or: make restart SERVICE=backend)"
	@echo "  make ps           List containers"
	@echo "  make logs         Follow all logs"
	@echo "  make logs-backend make logs-nginx"
	@echo "  make backend-migrate   Run Alembic migrations (upgrade head) in backend container"
	@echo ""
	@echo "Production (docker-compose.prod.yml + .env.prod):"
	@echo "  make prod-up      make prod-down   make prod-down-v"
	@echo "  make prod-build   make prod-build-backend   make prod-build-frontend"
	@echo "  make prod-recreate   make prod-restart   make prod-ps"
	@echo "  make prod-logs    make prod-logs-backend"
	@echo "  make prod-backend-migrate   Run Alembic migrations in prod backend container"

# --- Env file setup ---
env-local:
	cp .env.local.example .env.local
	@echo "Created .env.local — edit if needed."

env-prod:
	cp .env.prod.example .env.prod
	@echo "Created .env.prod — edit if needed."

# --- Local ---
up:
	$(COMPOSE_LOCAL) up -d

down:
	$(COMPOSE_LOCAL) down

down-v:
	$(COMPOSE_LOCAL) down -v

build:
	$(COMPOSE_LOCAL) up -d --build

build-backend:
	$(COMPOSE_LOCAL) build backend && $(COMPOSE_LOCAL) up -d

build-frontend:
	$(COMPOSE_LOCAL) up -d --build frontend
	$(COMPOSE_LOCAL) up -d --force-recreate nginx

recreate:
	$(COMPOSE_LOCAL) up -d --force-recreate

restart:
	$(COMPOSE_LOCAL) restart $(SERVICE)

ps:
	$(COMPOSE_LOCAL) ps -a

logs:
	$(COMPOSE_LOCAL) logs -f

logs-backend:
	$(COMPOSE_LOCAL) logs -f backend

logs-nginx:
	$(COMPOSE_LOCAL) logs -f nginx

backend-migrate:
	$(COMPOSE_LOCAL) exec backend poetry run alembic upgrade head

# --- Production ---
prod-up:
	$(COMPOSE_PROD) up -d

prod-down:
	$(COMPOSE_PROD) down

prod-down-v:
	$(COMPOSE_PROD) down -v

prod-build:
	$(COMPOSE_PROD) up -d --build

prod-build-backend:
	$(COMPOSE_PROD) build backend && $(COMPOSE_PROD) up -d

prod-build-frontend:
	$(COMPOSE_PROD) up -d --build frontend
	$(COMPOSE_PROD) up -d --force-recreate nginx

prod-recreate:
	$(COMPOSE_PROD) up -d --force-recreate

prod-restart:
	$(COMPOSE_PROD) restart $(SERVICE)

prod-ps:
	$(COMPOSE_PROD) ps -a

prod-logs:
	$(COMPOSE_PROD) logs -f

prod-logs-backend:
	$(COMPOSE_PROD) logs -f backend

prod-backend-migrate:
	$(COMPOSE_PROD) exec backend poetry run alembic upgrade head

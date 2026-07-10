# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

Monorepo with two apps and shared infrastructure:

- `helpDesk_back/` — FastAPI backend (Python 3.12+, Poetry, SQLAlchemy 2.0 async, Alembic, Pydantic v2).
- `helpDesk_front/` — React 19 SPA (TypeScript, Vite, Tailwind, react-router v7). Bun is the package manager (`bun.lock`).
- `nginx/`, `docker-compose.yml`, `docker-compose.prod.yml`, `.env.local.example`, `.env.prod.example` — runtime topology.
- `scripts/` — operational helpers (Keycloak bootstrap/reset, SSL helpers).
- `docs/` — Russian-language ops notes: `LOCAL_DEV.md`, `KEYCLOAK_SETUP.md`, `DOCKER_CHEATSHEET.md`, `SSL_ACTIVATION.md`.
- `.cursor/rules/helpdesk-backend.mdc` and `.cursor/rules/react-rule.mdc` — authoritative coding conventions (see "Coding conventions" below).

## Common commands

The `Makefile` is the canonical entry point for the Docker stack — run `make help` for the full list. Local stack uses `docker-compose.yml` + `.env.local`; prod stack uses `docker-compose.prod.yml` + `.env.prod`.

```bash
# First-time setup
make env-local                     # cp .env.local.example .env.local

# Local stack (nginx on :80, backend, keycloak, postgres, frontend builder)
make up                            # start
make build                         # rebuild + start
make build-backend                 # rebuild backend only
make build-frontend                # rebuild frontend, then force-recreate nginx
make logs / logs-backend / logs-nginx
make backend-migrate               # alembic upgrade head inside backend container
make down / down-v                 # down (-v also removes volumes)

# Prod equivalents are prefixed prod-: prod-up, prod-build, prod-backend-migrate, ...
```

The `frontend` service is a one-shot build container: it compiles into the `frontend_static` volume and exits — nginx serves the static output. A "Frontend static files ready" log followed by exit is normal.

### Backend (run inside the container or with Poetry locally)

```bash
# Inside the backend container
poetry run pytest                            # full suite
poetry run pytest tests/test_ticket_service.py::test_name -q   # single test
poetry run alembic upgrade head              # apply migrations
poetry run alembic revision -m "msg"         # new migration (autogenerate w/ --autogenerate if needed)
poetry run ruff check src tests              # lint
poetry run mypy src                          # type-check
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   # dev server
```

`PYTHONPATH=/app/src` in the container; tests import as `from app.…`. The Docker entrypoint runs `alembic upgrade head` before starting uvicorn.

### Frontend

```bash
cd helpDesk_front
bun install
bun run dev          # vite on :5173, proxies /api → :8000 and /auth → :8080
bun run build        # tsc -b && vite build
bun run lint         # eslint
```

Path alias `@/` → `helpDesk_front/src/`.

## Backend architecture

Single FastAPI app at `helpDesk_back/src/app/`. Composition happens in `app.main.create_app()`: it loads `Settings`, registers CORS, and includes one router per domain under `settings.api_prefix` (default `/api/v1`). `lifespan` initializes the DB engine and — if `RABBITMQ_URL` is set — spawns the outbox dispatcher background task; both are torn down on shutdown.

### Domain-module pattern

Every domain (`auth`, `user`, `ticket`, `department`, `notification`, `sla`, `system`) follows the same shape — replicate it when adding new ones:

- `models/` — SQLAlchemy models inheriting `app.core.database.BaseModel` (provides `id: UUID`, `created_at`, `updated_at` via `TimestampMixin`).
- `schemas/` — Pydantic v2 request/response models.
- `repositories/` — `interfaces.py` declares a `typing.Protocol`; `*_repo.py` is the `AsyncSession`-backed implementation. Repositories never call `commit()`/`rollback()`.
- `services/` — business logic. Receives repos (and other services) via constructor; raises domain `HTTPException` subclasses. Services don't import FastAPI except for those exceptions.
- `dependencies/` — FastAPI `Depends` wiring: factories for services/repos, plus "fetch entity by ID" dependencies that the routers consume directly.
- `routers/` — thin: parse Pydantic input, call a service, return a `response_model`. Access checks and entity lookups belong in `dependencies/`.
- `exceptions/` — domain errors that subclass `fastapi.HTTPException` with the right `status_code` (e.g. `TicketNotFoundError`, `DepartmentAlreadyExistsError`). Don't re-wrap them in routers.

`auth` is older and slightly flatter (`models/`, `routers/`, `schemas/`, `services/`, plus `dependencies.py` and `errors.py`); follow the newer `ticket`/`department` shape for new code.

### Database session contract

- `app.core.database.get_db_session` yields an `AsyncSession`, then `commit`s on success and `rollback`s on exception. Use the alias `DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]` rather than depending directly.
- Repositories receive the session via DI and never commit themselves — the request boundary handles the unit of work.
- Engine and `async_sessionmaker` are module-level singletons set up by `init_database()` in the lifespan; tests re-init by clearing `get_settings`'s `lru_cache`.

### Configuration

`app.config.Settings` (Pydantic Settings, env-loaded) is the only source of truth — never hardcode URLs/secrets. Access via `get_settings()` (cached with `lru_cache`) or `Depends(get_settings)`. Notable knobs:

- `database_url` (required), `db_pool_size`, `db_max_overflow`.
- `keycloak_url` (internal), `keycloak_public_url` / `keycloak_issuer_override` (public). A `model_validator` enforces that production deployments set a public issuer so login redirects don't leak the internal `http://keycloak:8080`.
- `frontend_url`, `auth_callback_url`, `pkce_ttl_seconds` for the BFF auth flow.
- `redis_url` (optional — when unset, PKCE verifier store falls back to in-memory and is only safe with single-worker uvicorn).
- `rabbitmq_url` (optional — when unset, the outbox dispatcher is disabled), `rabbitmq_exchange`, `rabbitmq_queue`, `outbox_batch_size`, `outbox_interval_seconds`, `outbox_max_attempts`.
- `allowed_cors_origins_raw` accepts JSON list or comma-separated.

### Notifications: transactional outbox

`notification.outbox_publisher.run_outbox_dispatcher` is started in `lifespan` when `RABBITMQ_URL` is set. Services write notification rows + outbox rows in the same DB transaction; the dispatcher polls `outbox_batch_size` rows every `outbox_interval_seconds`, publishes each to RabbitMQ (`rabbitmq_exchange` / `rabbitmq_queue`), and on failure schedules an exponential-backoff retry up to `outbox_max_attempts`. Don't publish to RabbitMQ directly from request handlers — write to the outbox.

### Auth (Keycloak BFF + PKCE)

The backend is the OAuth client. The frontend redirects to `/api/v1/auth/login`, the backend stores a PKCE verifier (TTL `pkce_ttl_seconds`) keyed by OAuth state in `app.auth.services.pkce_store`, and redirects to Keycloak; Keycloak calls back to `auth_callback_url` and the backend `GETDEL`s the verifier and exchanges the code for tokens. The store is selected at lifespan startup based on `REDIS_URL`: with Redis, multi-worker uvicorn is safe; without it, the in-memory fallback is process-local — a callback that lands on a different worker than the `/login` will produce `pkce_expired`, so single-worker only. Token refresh is exposed as `POST /api/v1/auth/refresh` and consumed by the frontend's `authorizedFetch`. JWT validation accepts both `KEYCLOAK_CLIENT_ID` and `"account"` as audiences by default; override with `KEYCLOAK_AUDIENCE`.

### Migrations

Alembic versions live in `helpDesk_back/alembic/versions/` and use a numbered prefix (`001_create_users_table.py`, `002_full_schema_migration.py`, `006_seed_sla_system_settings.py`, …). Add new migrations as new files — don't rewrite history. The container entrypoint runs `alembic upgrade head` automatically on every backend start.

### Tests

Pytest + pytest-asyncio in `helpDesk_back/tests/`. `conftest.py` provides a `settings` fixture that seeds env vars and clears `get_settings`'s cache, plus a FastAPI `TestClient`. Service/router tests mock repositories and dependencies via `AsyncMock` rather than touching a real DB.

## Frontend architecture

`helpDesk_front/src/` is split by responsibility:

- `pages/` — top-level routes (`Dashboard`, `TicketDetail`, `Department`, `Reports`, `Settings`, `Login`).
- `components/auth/`, `components/dashboard/`, `components/ticket-detail/`, `components/ui/` — shadcn-style primitives in `ui/`, feature components elsewhere.
- `contexts/` — `AuthContext` (Keycloak session + token state), `ThemeContext`.
- `api/` — typed fetch wrappers per domain (`tickets.ts`, `users.ts`, `departments.ts`) on top of `client.ts`.
- `lib/authSession.ts` — token storage + expiry helpers.
- `App.tsx` — `AuthProvider` + router; non-auth pages are wrapped in `<ProtectedRoute>`.

`api/client.ts` is the single network boundary. `authorizedFetch` attaches the bearer, retries once on 401 via a coalesced `refreshAccessToken` (so concurrent requests share one refresh), and clears tokens if the refresh fails. New API calls should go through `authorizedFetch` — don't call `fetch` with a manually attached token.

`VITE_API_URL` defaults to `/api/v1` (relative, served by nginx in Docker). Auth-related env vars (`VITE_KEYCLOAK_URL`, `VITE_KEYCLOAK_REALM`, `VITE_KEYCLOAK_CLIENT_ID`, `VITE_SILENT_CHECK_SSO_REDIRECT_URI`) are documented in `helpDesk_front/README.md`.

## Coding conventions

The Cursor rule files are the source of truth — apply them whether or not Cursor is loading them.

### Backend (`.cursor/rules/helpdesk-backend.mdc`)

- `lowercase_snake_case` for all file and folder names (`ticket_repo.py`, `department_deps.py`).
- Full type annotations including return types. Inject deps as `Annotated[T, Depends(get_t)]`.
- Async by default for I/O — sync only for pure helpers.
- Routers stay thin (parse → service call → response schema). Auth/lookup logic belongs in `dependencies/`.
- Domain HTTP errors as `HTTPException` subclasses; don't rewrap them in routers if the message already fits.
- Pagination response shape: `{items, total, page, page_size, pages}`. Use `Query(ge=1, le=100)` for paging params and a Pydantic schema for complex filters (see `TicketFilterParams`).
- Style: early returns, guard clauses, helper-verb names (`is_active`, `has_permission`, `get_ticket_by_id_accessible`), docstrings on public APIs.

### Frontend (`.cursor/rules/react-rule.mdc`)

- Tailwind only for styling — no inline CSS, no separate stylesheets beyond globals.
- Components and helpers as `const` arrow functions with explicit types when meaningful.
- Event handlers prefixed `handle` (`handleClick`, `handleKeyDown`).
- Accessibility on interactive elements: `tabIndex`, `aria-label`, keyboard handlers paired with click handlers.
- Early returns over nested conditionals; no TODOs or stubs in committed code.

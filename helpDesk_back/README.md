# HelpDesk backend

FastAPI service for the HelpDesk product: tickets, departments, users, assets, notifications, and Keycloak-backed authentication.

## Documentation

- **[Module reference](docs/MODULES.md)** — what each package under `src/app/` does and how they connect
- [Local development](docs/LOCAL_DEV.md)
- [Keycloak setup](docs/KEYCLOAK_SETUP.md)
- [Docker (repo root)](../DOCKER.md)

## Layout

- `src/app/` — application code (feature modules + `core` + `config` + `main.py`)
- `alembic/` — database migrations
- `tests/` — pytest suite

Run the API with Uvicorn (see `docs/LOCAL_DEV.md` or `DOCKER.md` for environment variables).

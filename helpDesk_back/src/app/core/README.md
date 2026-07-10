# Module: `core`

Shared **infrastructure** for the rest of the app.

## Contents

| Area | Role |
|------|------|
| `database.py` | SQLAlchemy async engine, `Base` / `BaseModel` / `TimestampMixin`, `get_db_session` dependency |
| `enums.py` | Shared enums (e.g. ticket status/priority, asset lifecycle) |
| `security.py` | Security helpers used by auth and HTTP layer |
| `http.py` | HTTP-related utilities |

## Boundaries

- No domain-specific business rules; keep **generic** primitives here.
- Other modules import from `core`; `core` should depend only on **`config`** (for DB URL) where needed.

## See also

[Module overview](../../../docs/MODULES.md#core)

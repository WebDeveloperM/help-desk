# Module: `system`

**System-wide key-value settings** stored in the database (`system_settings`).

## Responsibilities

- **`SystemService`**: read settings used across the app — notably **SLA hours per ticket priority** (`sla.low.hours`, `sla.normal.hours`, `sla.high.hours`, `sla.urgent.hours`) with sane defaults
- **`SystemRepository`**: data access for settings keys/values

## HTTP surface

No dedicated public router in the current codebase; settings are consumed internally (e.g. by **`sla`** and migrations/seeds).

## Dependencies

- **`core`** (database)

## See also

[Module overview](../../../docs/MODULES.md#system)

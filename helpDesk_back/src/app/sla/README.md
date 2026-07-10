# Module: `sla`

**Service Level Agreement** calculations: target completion time by **priority** and current **SLA status** for tickets.

## Responsibilities

- Load SLA hours per priority from **`system`** settings (`sla.low.hours`, etc.), with defaults
- **`compute_planned_completion_date`**: deadline = start time + hours for priority
- **`compute_sla_info`**: `on_track` / `at_risk` / `overdue` / `completed_on_time` / `completed_late`

## HTTP surface

**None** — this package exposes **`SlaService`** and Pydantic schemas only. The **ticket** module calls it when creating/updating tickets and when building `TicketResponse`.

## Dependencies

- **`system`** (`SystemService` for SLA hour keys)

## See also

[Module overview](../../../docs/MODULES.md#sla)

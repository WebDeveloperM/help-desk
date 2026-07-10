# Module: `ticket`

**Tickets** — the main work items: categories, assignment, workflow, progress, completion, and links to **assets**.

## Responsibilities

- Ticket CRUD, filters, pagination
- Workflow: assign, approve/reject, start progress, waiting, complete, close, etc.
- **SLA**: sets `planned_completion_date` and attaches **`sla`** (`SlaInfo`) on ticket responses via `SlaService`
- **Notifications** on key events (assignment, status changes)
- Validation of executors, departments, and asset rules (including repair constraints)

## HTTP surface

Router prefix: **`/tickets`**.

## Dependencies

- **`user`**, **`department`**, **`asset`**, **`notification`**, **`sla`**

## See also

[Module overview](../../../docs/MODULES.md#ticket) · [SLA module](../sla/README.md)

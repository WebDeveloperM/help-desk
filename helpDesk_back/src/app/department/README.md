# Module: `department`

**Departments** — organizational units used to scope users and tickets.

## Responsibilities

- Create, read, update, list departments
- Associate users with departments where applicable (see user and ticket modules)

## HTTP surface

Router prefix: **`/departments`**.

## Dependencies

- **`core`**, **`user`** (as needed for listing members or validating access patterns in routers)

## See also

[Module overview](../../../docs/MODULES.md#department)

# Module: `asset`

**Assets** — inventory items (equipment, etc.) with optional **images** stored in **MinIO**.

## Responsibilities

- Asset CRUD, filtering, cursor pagination, sorting
- Image upload and delete (object storage)
- **Department-scoped** access consistent with the current user’s permissions
- Lifecycle status and metadata used when linking assets to tickets

## HTTP surface

Router prefix: **`/assets`**.

## Dependencies

- **`auth`**, **`user`**, **`config`** (MinIO and related settings)

## See also

[Module overview](../../../docs/MODULES.md#asset)

# Module: `user`

**Application users**: profiles, roles, and permission checks that gate admin and domain APIs.

## Responsibilities

- CRUD and listing (guarded by permissions)
- **Role-based** access for operations like user create/delete
- **Repository** layer over SQLAlchemy models
- Dependencies such as **`get_current_user_model`** for routes that need the DB user row

## HTTP surface

Router prefix: **`/users`**.

## Dependencies

- **`auth`**: validated token / current user identity

## See also

[Module overview](../../../docs/MODULES.md#user)

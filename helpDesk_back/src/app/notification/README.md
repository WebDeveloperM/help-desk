# Module: `notification`

**In-app notifications** for users, with optional **async delivery** via RabbitMQ.

## Responsibilities

- Persist notifications; list and mark read for the **current user**
- **Transactional outbox** pattern: ticket flows write outbox rows; **`outbox_publisher`** (started from `main` lifespan when `RABBITMQ_URL` is set) publishes to RabbitMQ with retries/backoff

## HTTP surface

Router prefix: **`/notifications`**.

## Dependencies

- **`core`** (database), **`user`** (current user)

## See also

[Module overview](../../../docs/MODULES.md#notification)

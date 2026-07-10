"""Create in-app notifications for ticket events (assignment, status change).

Storage contract for i18n consumers
-----------------------------------
A notification row is the *event*, not pre-rendered text:

  - ``notification_type`` (NotificationType enum) is the event identifier and
    drives template selection on the consumer side (frontend ``notifications``
    namespace, email templates, etc.).
  - ``payload_json`` carries interpolation parameters for the template
    (``ticket_number``, ``title``, ``actor_full_name``, ``status`` …).
  - ``title`` / ``body`` are stored as **English fallbacks** so legacy /
    non-i18n consumers (logs, raw DB queries) still have a readable string.
    UI consumers should prefer ``notification_type`` + ``payload_json``.

The outbox payload mirrors this: ``notification_type`` + ``params`` so a
RabbitMQ subscriber can render in the recipient's language without re-querying
the DB.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID

from app.core.enums import NotificationType
from app.notification.repositories import NotificationRepository

if TYPE_CHECKING:
    pass


class TicketLike(Protocol):
    """Minimal ticket shape for notification creation (avoids circular import)."""

    id: UUID
    ticket_number: str
    title: str
    status: Any
    created_by_id: UUID
    assigned_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    executors: Any  # list of objects with .id


def _stakeholder_recipients(ticket: TicketLike) -> set[UUID]:
    """Stakeholders for ticket updates: creator, assigner and executors."""
    recipient_ids: set[UUID] = {ticket.created_by_id}
    assigner_id = getattr(ticket, "assigned_by_user_id", None)
    if assigner_id:
        recipient_ids.add(assigner_id)
    for e in ticket.executors:
        recipient_ids.add(e.id)
    return recipient_ids


def _recipients_for_assignment(
    ticket: TicketLike,
    actor_user_id: UUID,
    previous_executor_ids: set[UUID] | None = None,
) -> set[UUID]:
    """Recipients for assignment: stakeholders + previous executors, excluding actor."""
    recipient_ids = _stakeholder_recipients(ticket)
    if previous_executor_ids:
        recipient_ids.update(previous_executor_ids)
    recipient_ids.discard(actor_user_id)
    return recipient_ids


def _recipients_for_status_change(
    ticket: TicketLike,
    actor_user_id: UUID,
) -> set[UUID]:
    """Recipients for status change: all stakeholders, excluding actor."""
    recipient_ids = _stakeholder_recipients(ticket)
    recipient_ids.discard(actor_user_id)
    return recipient_ids


def _dedup_key(ticket_id: UUID, event_name: str, recipient_id: UUID, ts: datetime) -> str:
    """Idempotency key for at-least-once delivery."""
    return f"ticket:{ticket_id}:event:{event_name}:recipient:{recipient_id}:ts:{ts.isoformat()}"


def _expires_at() -> datetime:
    """Default expiry: now + 30 days."""
    return datetime.now(timezone.utc) + timedelta(days=30)


def _outbox_payload(
    notification_id: UUID,
    notification_type: NotificationType,
    recipient_id: UUID,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Build the outbox message payload.

    Carries the event identifier and full parameter map so downstream
    consumers (email senders, push services, etc.) can render in the
    recipient's language without re-querying the DB.
    """
    return {
        "notification_id": str(notification_id),
        "notification_type": notification_type.value,
        "recipient_id": str(recipient_id),
        "params": params,
    }


async def create_notifications_for_ticket_assigned(
    notification_repo: NotificationRepository,
    ticket: TicketLike,
    actor_user_id: UUID,
    actor_full_name: str | None = None,
    previous_executor_ids: set[UUID] | None = None,
) -> None:
    """
    Create in-app notifications for ticket assignment or reassignment.
    Skips the actor. Idempotent by dedup_key.
    """
    recipients = _recipients_for_assignment(
        ticket,
        actor_user_id,
        previous_executor_ids=previous_executor_ids,
    )
    if not recipients:
        return
    # English fallbacks; UI renders via notification_type + params.
    title = f"New task assigned: {ticket.title}"
    body = f"Ticket #{ticket.ticket_number} has been assigned to you."
    params: dict[str, Any] = {
        "ticket_id": str(ticket.id),
        "ticket_number": ticket.ticket_number,
        "title": ticket.title,
    }
    if actor_full_name:
        params["actor_full_name"] = actor_full_name
    ts = getattr(ticket, "updated_at", ticket.created_at)
    for user_id in recipients:
        dedup_key = _dedup_key(ticket.id, "ticket_assigned", user_id, ts)
        notification = await notification_repo.create(
            user_id=user_id,
            notification_type=NotificationType.TICKET_ASSIGNED,
            title=title,
            ticket_id=ticket.id,
            actor_user_id=actor_user_id,
            body=body,
            payload_json=params,
            dedup_key=dedup_key,
            expires_at=_expires_at(),
        )
        await notification_repo.add_outbox(
            event_type="notification_created",
            routing_key="notification.created",
            payload_json=_outbox_payload(
                notification_id=notification.id,
                notification_type=NotificationType.TICKET_ASSIGNED,
                recipient_id=user_id,
                params=params,
            ),
        )


async def create_notifications_for_ticket_status_change(
    notification_repo: NotificationRepository,
    ticket: TicketLike,
    actor_user_id: UUID,
    notification_type: NotificationType,
    title: str,
    body: str,
    actor_full_name: str | None = None,
) -> None:
    """
    Create in-app notifications for status change: all stakeholders, excluding actor.
    Idempotent by dedup_key.
    """
    recipients = _recipients_for_status_change(ticket, actor_user_id)
    if not recipients:
        return
    event_name = notification_type.value
    params: dict[str, Any] = {
        "ticket_id": str(ticket.id),
        "ticket_number": ticket.ticket_number,
        "title": ticket.title,
        "status": getattr(ticket.status, "value", str(ticket.status)),
    }
    if actor_full_name:
        params["actor_full_name"] = actor_full_name
    ts = getattr(ticket, "updated_at", ticket.created_at)
    for user_id in recipients:
        dedup_key = _dedup_key(ticket.id, event_name, user_id, ts)
        notification = await notification_repo.create(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            ticket_id=ticket.id,
            actor_user_id=actor_user_id,
            body=body,
            payload_json=params,
            dedup_key=dedup_key,
            expires_at=_expires_at(),
        )
        await notification_repo.add_outbox(
            event_type="notification_created",
            routing_key="notification.created",
            payload_json=_outbox_payload(
                notification_id=notification.id,
                notification_type=notification_type,
                recipient_id=user_id,
                params=params,
            ),
        )


async def create_notifications_for_comment_added(
    notification_repo: NotificationRepository,
    ticket: TicketLike,
    actor_user_id: UUID,
    comment_id: UUID,
    actor_full_name: str | None = None,
) -> None:
    """
    Notify ticket stakeholders about a new comment (excluding the author).
    """
    recipients = _recipients_for_status_change(ticket, actor_user_id)
    if not recipients:
        return
    title = f"New comment on ticket #{ticket.ticket_number}"
    body = f"{ticket.title}"
    payload: dict[str, Any] = {
        "ticket_id": str(ticket.id),
        "ticket_number": ticket.ticket_number,
        "title": ticket.title,
        "comment_id": str(comment_id),
    }
    if actor_full_name:
        payload["actor_full_name"] = actor_full_name
    ts = datetime.now(timezone.utc)
    event_name = f"comment_added_{comment_id}"
    for user_id in recipients:
        dedup_key = _dedup_key(ticket.id, event_name, user_id, ts)
        notification = await notification_repo.create(
            user_id=user_id,
            notification_type=NotificationType.COMMENT_ADDED,
            title=title,
            ticket_id=ticket.id,
            actor_user_id=actor_user_id,
            body=body,
            payload_json=payload,
            dedup_key=dedup_key,
            expires_at=_expires_at(),
        )
        await notification_repo.add_outbox(
            event_type="notification_created",
            routing_key="notification.created",
            payload_json={
                "notification_id": str(notification.id),
                "ticket_id": str(ticket.id),
                "recipient_id": str(user_id),
                "type": "comment_added",
            },
        )

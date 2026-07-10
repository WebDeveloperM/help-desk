"""Ticket dependencies."""

from app.ticket.dependencies.ticket_deps import (
    get_ticket_by_id,
    get_ticket_by_id_accessible,
    get_ticket_comment_repository,
    get_ticket_comment_service,
    get_ticket_repository,
    get_ticket_service,
    require_ticket_approver,
    require_ticket_closer,
    require_ticket_completer,
    require_ticket_executor,
)

__all__ = [
    "get_ticket_by_id",
    "get_ticket_by_id_accessible",
    "get_ticket_comment_repository",
    "get_ticket_comment_service",
    "get_ticket_repository",
    "get_ticket_service",
    "require_ticket_approver",
    "require_ticket_closer",
    "require_ticket_completer",
    "require_ticket_executor",
]

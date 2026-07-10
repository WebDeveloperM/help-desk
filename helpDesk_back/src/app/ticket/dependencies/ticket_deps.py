"""Ticket dependencies for dependency injection."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.auth.dependencies import get_current_user
from app.auth.schemas import TokenUser
from app.auth.services import has_any_role
from app.config import Settings, get_settings
from app.core.database import DatabaseSession
from app.core.enums import Role
from app.asset.dependencies import get_asset_repository
from app.asset.repositories import AssetRepository
from app.notification.dependencies import get_notification_repository
from app.notification.repositories import NotificationRepository
from app.sla.dependencies import get_sla_service
from app.sla.services import SlaService
from app.ticket.exceptions import TicketNotFoundError, TicketPermissionDeniedError
from app.ticket.models import Ticket
from app.ticket.repositories import (
    SQLAlchemyTicketCommentRepository,
    SQLAlchemyTicketRepository,
    TicketRepository,
)
from app.ticket.services import TicketCommentService, TicketService
from app.user.dependencies import get_current_user_model, get_user_repository
from app.user.models import User
from app.user.repositories import UserRepository


def get_ticket_comment_repository(
    session: DatabaseSession,
) -> SQLAlchemyTicketCommentRepository:
    """Return ticket comment repository."""
    return SQLAlchemyTicketCommentRepository(session)


def get_ticket_comment_service(
    comment_repository: Annotated[
        SQLAlchemyTicketCommentRepository, Depends(get_ticket_comment_repository)
    ],
    notification_repository: Annotated[
        NotificationRepository, Depends(get_notification_repository)
    ],
) -> TicketCommentService:
    """Return ticket comment service."""
    return TicketCommentService(comment_repository, notification_repository)


def get_ticket_repository(session: DatabaseSession) -> TicketRepository:
    """
    Get ticket repository instance.

    Args:
        session: Database session.

    Returns:
        Ticket repository.
    """
    return SQLAlchemyTicketRepository(session)


def get_ticket_service(
    repository: Annotated[TicketRepository, Depends(get_ticket_repository)],
    asset_repository: Annotated[AssetRepository, Depends(get_asset_repository)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    notification_repository: Annotated[
        NotificationRepository, Depends(get_notification_repository)
    ],
    sla_service: Annotated[SlaService | None, Depends(get_sla_service)] = None,
) -> TicketService:
    """
    Get ticket service instance.

    Args:
        repository: Ticket repository.
        user_repository: User repository for executor validation.
        notification_repository: Notification repository for ticket event notifications.
        sla_service: SLA service for planned completion and status.

    Returns:
        Ticket service.
    """
    return TicketService(
        repository,
        asset_repository,
        user_repository,
        notification_repository,
        sla_service=sla_service,
    )


async def get_ticket_by_id(
    ticket_id: UUID,
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> Ticket:
    """
    Get ticket by ID dependency (no department check).

    Args:
        ticket_id: Ticket UUID.
        service: Ticket service.

    Returns:
        Ticket model.

    Raises:
        TicketNotFoundError: If ticket not found.
    """
    ticket = await service.get_by_id(ticket_id)
    if not ticket:
        raise TicketNotFoundError(ticket_id=str(ticket_id))

    return ticket


def _user_can_access_ticket(ticket: Ticket, user: User) -> bool:
    """Return True if user can access the ticket (admin, same department, or creator/executor)."""
    if user.role == Role.ADMIN:
        return True
    if ticket.created_by_id == user.id:
        return True
    if ticket.assigned_by_user_id == user.id:
        return True
    executor_ids = [e.id for e in ticket.executors]
    if user.id in executor_ids:
        return True
    if user.department_id is not None:
        if ticket.creator_department_id == user.department_id:
            return True
        if ticket.assigned_department_id == user.department_id:
            return True
    return False


async def get_ticket_by_id_accessible(
    ticket_id: UUID,
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> Ticket:
    """
    Get ticket by ID only if current user can access it (same department / creator / executor).

    Args:
        ticket_id: Ticket UUID.
        current_user: Current authenticated user model.
        service: Ticket service.

    Returns:
        Ticket model.

    Raises:
        TicketNotFoundError: If ticket not found.
        TicketPermissionDeniedError: If user has no department or ticket not in scope.
    """
    ticket = await service.get_by_id(ticket_id)
    if not ticket:
        raise TicketNotFoundError(ticket_id=str(ticket_id))
    if not _user_can_access_ticket(ticket, current_user):
        raise TicketPermissionDeniedError(
            detail="You don't have permission to access this ticket"
        )
    return ticket


_PRIVILEGED_ROLES = ["department_head", "admin"]


def _user_is_privileged(token_user: TokenUser, settings: Settings) -> bool:
    """True if user has department_head or admin role."""
    return has_any_role(token_user, _PRIVILEGED_ROLES, settings)


def _user_is_executor_of(ticket: Ticket, user: User) -> bool:
    """True if user is in ticket.executors."""
    return any(executor.id == user.id for executor in ticket.executors)


async def require_ticket_approver(
    ticket: Annotated[Ticket, Depends(get_ticket_by_id_accessible)],
    token_user: Annotated[TokenUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Ticket:
    """
    Approve / reject / assign — requires `department_head` or `admin`.

    Returns the loaded Ticket so the route does not need to depend on
    `get_ticket_by_id_accessible` separately.
    """
    if not _user_is_privileged(token_user, settings):
        raise TicketPermissionDeniedError(
            detail="Only department_head or admin can approve, reject, or reassign tickets"
        )
    return ticket


async def require_ticket_executor(
    ticket: Annotated[Ticket, Depends(get_ticket_by_id_accessible)],
    current_user: Annotated[User, Depends(get_current_user_model)],
) -> Ticket:
    """
    Start-progress / progress — requires the user to be an executor of *this* ticket.
    """
    if not _user_is_executor_of(ticket, current_user):
        raise TicketPermissionDeniedError(
            detail="Only executors assigned to this ticket can perform this action"
        )
    return ticket


async def require_ticket_completer(
    ticket: Annotated[Ticket, Depends(get_ticket_by_id_accessible)],
    current_user: Annotated[User, Depends(get_current_user_model)],
    token_user: Annotated[TokenUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Ticket:
    """
    Waiting-info / complete — executor of the ticket OR `department_head`/`admin`.
    """
    if _user_is_executor_of(ticket, current_user):
        return ticket
    if _user_is_privileged(token_user, settings):
        return ticket
    raise TicketPermissionDeniedError(
        detail="Only ticket executors, department_head, or admin can complete or set waiting-info"
    )


async def require_ticket_closer(
    ticket: Annotated[Ticket, Depends(get_ticket_by_id_accessible)],
    current_user: Annotated[User, Depends(get_current_user_model)],
    token_user: Annotated[TokenUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Ticket:
    """
    Close / PATCH — ticket creator OR `department_head`/`admin`.
    Used for both close and update; field-level update granularity is a future refinement.
    """
    if ticket.created_by_id == current_user.id:
        return ticket
    if _user_is_privileged(token_user, settings):
        return ticket
    raise TicketPermissionDeniedError(
        detail="Only the ticket creator, department_head, or admin can close or modify the ticket"
    )

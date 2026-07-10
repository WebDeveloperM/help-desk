"""Ticket router with CRUD and workflow endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.asset.schemas import TicketAssetAttachRequest
from app.core.enums import Role, TicketPriority, TicketStatus
from app.ticket.dependencies import (
    get_ticket_by_id_accessible,
    get_ticket_comment_service,
    get_ticket_service,
    require_ticket_approver,
    require_ticket_closer,
    require_ticket_completer,
    require_ticket_executor,
)
from app.ticket.exceptions import TicketPermissionDeniedError
from app.ticket.models import Ticket
from app.ticket.schemas import (
    TicketApproveRequest,
    TicketAssignRequest,
    TicketCloseRequest,
    TicketCompleteRequest,
    TicketCreate,
    TicketCategoryResponse,
    TicketFilterParams,
    TicketListResponse,
    TicketProgressUpdateRequest,
    TicketRejectRequest,
    TicketResponse,
    TicketStatsResponse,
    TicketUpdate,
    TicketUpdateRequest,
    TicketWaitingInfoRequest,
)
from app.ticket.schemas.ticket_comment import (
    TicketCommentCreate,
    TicketCommentListResponse,
    TicketCommentResponse,
)
from app.ticket.services import TicketCommentService, TicketService
from app.user.dependencies import get_current_user_model
from app.user.models import User

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _visibility_scope(current_user: User) -> tuple[UUID | None, UUID | None]:
    """Return (department_scope, user_scope) for ticket list/stats.

    Admins see everything (no restriction). Everyone else is scoped to their
    department plus tickets they created / were assigned / execute.
    """
    if current_user.role == Role.ADMIN:
        return None, None
    return current_user.department_id, current_user.id


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket_endpoint(
    ticket_data: TicketCreate,
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    """
    Create a new ticket (only within your department).

    Args:
        ticket_data: Ticket creation data.
        current_user: Current authenticated user model.
        service: Ticket service.

    Returns:
        Created ticket.

    Raises:
        TicketPermissionDeniedError: If user has no department or creator_department_id is not user's department.
    """
    if current_user.department_id is None:
        raise TicketPermissionDeniedError(
            detail="You must belong to a department to create tickets"
        )
    if ticket_data.creator_department_id != current_user.department_id:
        raise TicketPermissionDeniedError(
            detail="You can only create tickets for your department"
        )
    return await service.create_ticket(ticket_data, current_user.id)


@router.get("", response_model=TicketListResponse)
async def list_tickets_endpoint(
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 100,
    status: Annotated[TicketStatus | None, Query()] = None,
    priority: Annotated[TicketPriority | None, Query()] = None,
    category_id: Annotated[UUID | None, Query()] = None,
    created_by_id: Annotated[UUID | None, Query()] = None,
    creator_department_id: Annotated[UUID | None, Query()] = None,
    assigned_department_id: Annotated[UUID | None, Query()] = None,
    is_urgent: Annotated[bool | None, Query()] = None,
    created_from: Annotated[datetime | None, Query()] = None,
    created_to: Annotated[datetime | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> TicketListResponse:
    """
    List tickets with pagination and filtering (only tickets in your department).

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page.
        status: Filter by ticket status.
        priority: Filter by ticket priority.
        category_id: Filter by category ID.
        created_by_id: Filter by creator user ID.
        creator_department_id: Filter by creator department ID.
        assigned_department_id: Filter by assigned department ID.
        is_urgent: Filter by urgent flag.
        created_from: Filter tickets created on or after this datetime (ISO 8601).
        created_to: Filter tickets created on or before this datetime (ISO 8601).
        current_user: Current authenticated user model.
        service: Ticket service.

    Returns:
        Paginated ticket list.

    """
    filters = TicketFilterParams(
        status=status,
        priority=priority,
        category_id=category_id,
        created_by_id=created_by_id,
        creator_department_id=creator_department_id,
        assigned_department_id=assigned_department_id,
        is_urgent=is_urgent,
        created_from=created_from,
        created_to=created_to,
        search=search,
    )
    dept_scope, user_scope = _visibility_scope(current_user)
    return await service.list_tickets(
        page=page,
        page_size=page_size,
        filters=filters,
        restrict_to_department_id=dept_scope,
        restrict_to_user_id=user_scope,
    )


@router.get("/categories", response_model=list[TicketCategoryResponse])
async def list_ticket_categories_endpoint(
    _: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> list[TicketCategoryResponse]:
    """
    List ticket categories (for dropdowns).

    Returns:
        List of ticket categories.
    """
    return await service.list_categories()


@router.get("/stats", response_model=TicketStatsResponse)
async def ticket_stats_endpoint(
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketStatsResponse:
    """
    Aggregated ticket analytics for the Reports page, scoped to the caller's
    visibility (same department/creator/executor scope as the ticket list).

    Returns:
        Ticket statistics: totals, status/priority/category breakdowns, overdue
        and SLA metrics, and 14-day throughput.
    """
    dept_scope, user_scope = _visibility_scope(current_user)
    stats = await service.get_stats(
        restrict_to_department_id=dept_scope,
        restrict_to_user_id=user_scope,
    )
    return TicketStatsResponse(**stats)


@router.get("/user-activity")
async def user_activity_endpoint(
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> dict[str, dict[str, int]]:
    """
    Per-user ticket activity across all tickets (admin only): for each user id,
    {created, active, completed}. Used by the admin Users page.
    """
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return await service.get_user_activity()


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket_endpoint(
    ticket: Annotated[Ticket, Depends(get_ticket_by_id_accessible)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    """
    Get ticket by ID.

    Args:
        ticket: Ticket model (with existence check).

    Returns:
        Ticket response.
    """
    return await service.get_ticket(ticket.id)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket_endpoint(
    ticket_id: UUID,
    ticket_data: TicketUpdateRequest,
    ticket: Annotated[Ticket, Depends(require_ticket_closer)],
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    """
    Update ticket.

    Args:
        ticket_id: Ticket UUID.
        ticket_data: Ticket update data.
        ticket: Ticket model (with existence check).
        current_user: Current authenticated user model.
        service: Ticket service.

    Returns:
        Updated ticket.

    Raises:
        TicketNotFoundError: If ticket not found.
    """
    internal_ticket_data = TicketUpdate.model_validate(
        ticket_data.model_dump(exclude_unset=True)
    )
    return await service.update_ticket(
        ticket_id, internal_ticket_data, updated_by_user_id=current_user.id
    )


@router.post("/{ticket_id}/approve", response_model=TicketResponse)
async def approve_ticket_endpoint(
    ticket_id: UUID,
    approve_data: TicketApproveRequest,
    ticket: Annotated[Ticket, Depends(require_ticket_approver)],
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    """
    Approve a ticket.

    Args:
        ticket_id: Ticket UUID.
        approve_data: Approval request data.
        current_user: Current authenticated user model.
        service: Ticket service.

    Returns:
        Updated ticket.

    Raises:
        TicketNotFoundError: If ticket not found.
    """
    return await service.approve_ticket(
        ticket_id, current_user.id, approve_data.comment
    )


@router.post("/{ticket_id}/reject", response_model=TicketResponse)
async def reject_ticket_endpoint(
    ticket_id: UUID,
    reject_data: TicketRejectRequest,
    ticket: Annotated[Ticket, Depends(require_ticket_approver)],
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    """
    Reject a ticket.

    Args:
        ticket_id: Ticket UUID.
        reject_data: Rejection request data.
        current_user: Current authenticated user model.
        service: Ticket service.

    Returns:
        Updated ticket.

    Raises:
        TicketNotFoundError: If ticket not found.
    """
    return await service.reject_ticket(
        ticket_id, current_user.id, reject_data.comment
    )


@router.post("/{ticket_id}/assign", response_model=TicketResponse)
async def assign_ticket_endpoint(
    ticket_id: UUID,
    assign_data: TicketAssignRequest,
    ticket: Annotated[Ticket, Depends(require_ticket_approver)],
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    """
    Assign a ticket to a department.

    Args:
        ticket_id: Ticket UUID.
        assign_data: Assignment request data.
        current_user: Current authenticated user model.
        service: Ticket service.

    Returns:
        Updated ticket.

    Raises:
        TicketNotFoundError: If ticket not found.
    """
    return await service.assign_ticket(
        ticket_id,
        assign_data.department_id,
        current_user.id,
        executor_user_ids=assign_data.executor_user_ids,
    )


@router.post("/{ticket_id}/waiting-info", response_model=TicketResponse)
async def waiting_info_ticket_endpoint(
    ticket_id: UUID,
    _waiting_data: TicketWaitingInfoRequest,
    _ticket: Annotated[Ticket, Depends(require_ticket_completer)],
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    """
    Mark ticket as waiting for information.

    Args:
        ticket_id: Ticket UUID.
        ticket: Ticket model (with existence check).
        current_user: Current authenticated user model.
        service: Ticket service.

    Returns:
        Updated ticket.
    """
    return await service.waiting_info_ticket(ticket_id, current_user.id)


@router.post("/{ticket_id}/start-progress", response_model=TicketResponse)
async def start_progress_ticket_endpoint(
    ticket_id: UUID,
    ticket: Annotated[Ticket, Depends(require_ticket_executor)],
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    """
    Mark ticket as in progress.

    Args:
        ticket_id: Ticket UUID.
        ticket: Ticket model (with existence check).
        current_user: Current authenticated user model.
        service: Ticket service.

    Returns:
        Updated ticket.

    Raises:
        TicketNotFoundError: If ticket not found.
    """
    return await service.start_progress_ticket(ticket_id, current_user.id)


@router.post("/{ticket_id}/complete", response_model=TicketResponse)
async def complete_ticket_endpoint(
    ticket_id: UUID,
    complete_data: TicketCompleteRequest,
    ticket: Annotated[Ticket, Depends(require_ticket_completer)],
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    """
    Complete a ticket.

    Args:
        ticket_id: Ticket UUID.
        complete_data: Completion request data.
        current_user: Current authenticated user model.
        service: Ticket service.

    Returns:
        Updated ticket.

    Raises:
        TicketNotFoundError: If ticket not found.
    """
    return await service.complete_ticket(
        ticket_id, current_user.id, complete_data.comment
    )


@router.post("/{ticket_id}/close", response_model=TicketResponse)
async def close_ticket_endpoint(
    ticket_id: UUID,
    close_data: TicketCloseRequest,
    ticket: Annotated[Ticket, Depends(require_ticket_closer)],
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    """
    Close a ticket.

    Args:
        ticket_id: Ticket UUID.
        close_data: Closure request data.
        current_user: Current authenticated user model.
        service: Ticket service.

    Returns:
        Updated ticket.

    Raises:
        TicketNotFoundError: If ticket not found.
    """
    return await service.close_ticket(ticket_id, current_user.id, close_data.comment)


@router.get("/{ticket_id}/comments", response_model=TicketCommentListResponse)
async def list_ticket_comments_endpoint(
    _ticket: Annotated[Ticket, Depends(get_ticket_by_id_accessible)],
    service: Annotated[TicketCommentService, Depends(get_ticket_comment_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 100,
) -> TicketCommentListResponse:
    """
    List comments on a ticket (chronological order, paginated).

    Args:
        page: Page number.
        page_size: Page size.
        service: Comment service.

    Returns:
        Paginated ticket comments.
    """
    return await service.list_comments(
        _ticket.id,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/{ticket_id}/comments",
    response_model=TicketCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ticket_comment_endpoint(
    ticket_id: UUID,
    data: TicketCommentCreate,
    ticket: Annotated[Ticket, Depends(get_ticket_by_id_accessible)],
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketCommentService, Depends(get_ticket_comment_service)],
) -> TicketCommentResponse:
    """
    Add a comment to a ticket.

    Args:
        ticket_id: Ticket UUID.
        data: Comment body.
        ticket: Accessible ticket (dependency).
        current_user: Authenticated user.
        service: Comment service.

    Returns:
        Created comment.
    """
    return await service.create_comment(ticket, current_user, data.body)


@router.post("/{ticket_id}/progress", response_model=TicketResponse)
async def update_ticket_progress_endpoint(
    ticket_id: UUID,
    progress_data: TicketProgressUpdateRequest,
    _ticket: Annotated[Ticket, Depends(require_ticket_executor)],
    _current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    """
    Update ticket implementation progress percentage.

    Args:
        ticket_id: Ticket UUID.
        progress_data: Progress update payload.
        service: Ticket service.

    Returns:
        Updated ticket.
    """
    return await service.update_ticket_progress(
        ticket_id=ticket_id,
        progress_percent=progress_data.progress_percent,
    )


@router.post("/{ticket_id}/assets", response_model=TicketResponse)
async def attach_assets_to_ticket_endpoint(
    ticket_id: UUID,
    payload: TicketAssetAttachRequest,
    _ticket: Annotated[Ticket, Depends(get_ticket_by_id_accessible)],
    _current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    """Attach assets to ticket."""
    return await service.attach_assets(ticket_id=ticket_id, asset_ids=payload.asset_ids)


@router.delete("/{ticket_id}/assets/{asset_id}", response_model=TicketResponse)
async def detach_asset_from_ticket_endpoint(
    ticket_id: UUID,
    asset_id: UUID,
    _ticket: Annotated[Ticket, Depends(get_ticket_by_id_accessible)],
    _current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[TicketService, Depends(get_ticket_service)],
) -> TicketResponse:
    """Detach single asset from ticket."""
    return await service.detach_asset(ticket_id=ticket_id, asset_id=asset_id)

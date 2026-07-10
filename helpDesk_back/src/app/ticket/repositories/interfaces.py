"""Ticket repository abstraction."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from app.core.enums import TicketStatus
from app.ticket.models import Ticket, TicketCategory

if TYPE_CHECKING:
    from app.ticket.models import TicketComment
    from app.ticket.schemas import TicketCreate, TicketFilterParams, TicketUpdate


class TicketRepository(Protocol):
    """Repository interface for ticket persistence operations."""

    async def get_by_id(self, ticket_id: UUID) -> Ticket | None:
        """Return a ticket by ID with relationships loaded."""

    async def get_by_ticket_number(self, ticket_number: str) -> Ticket | None:
        """Return a ticket by ticket number."""

    async def create(
        self,
        ticket_data: "TicketCreate",
        created_by_id: UUID,
        assigned_department_id: UUID | None,
        assigned_by_user_id: UUID,
        assigned_at: datetime | None = None,
        planned_completion_date: datetime | None = None,
    ) -> Ticket:
        """Persist a new ticket."""

    async def set_executors(self, ticket_id: UUID, user_ids: list[UUID]) -> None:
        """Replace ticket executors with the given user IDs."""

    async def set_assets(self, ticket_id: UUID, asset_ids: list[UUID]) -> None:
        """Replace ticket assets with given asset IDs."""

    async def add_assets(self, ticket_id: UUID, asset_ids: list[UUID]) -> None:
        """Attach new assets to ticket."""

    async def remove_asset(self, ticket_id: UUID, asset_id: UUID) -> None:
        """Detach one asset from ticket."""

    async def is_repair_ticket(self, ticket_id: UUID) -> bool:
        """Return True if ticket category code is 'repair'."""

    async def is_repair_category(self, category_id: UUID) -> bool:
        """Return True if category code is 'repair'."""

    async def update(
        self, ticket_id: UUID, ticket_data: "TicketUpdate"
    ) -> Ticket | None:
        """Partially update a ticket."""

    async def approve(
        self, ticket_id: UUID, approver_user_id: UUID, comment: str | None = None
    ) -> Ticket | None:
        """Approve a ticket."""

    async def reject(
        self, ticket_id: UUID, approver_user_id: UUID, comment: str
    ) -> Ticket | None:
        """Reject a ticket."""

    async def assign(
        self,
        ticket_id: UUID,
        assigned_department_id: UUID | None,
        assigned_by_user_id: UUID,
        executor_user_ids: list[UUID],
        assigned_at: datetime | None = None,
        planned_completion_date: datetime | None = None,
    ) -> Ticket | None:
        """Assign a ticket to a department and optionally set executors."""

    async def start_progress(
        self,
        ticket_id: UUID,
        progress_percent: int | None = None,
    ) -> Ticket | None:
        """Mark ticket as in progress."""

    async def waiting_info(self, ticket_id: UUID) -> Ticket | None:
        """Mark ticket as waiting for information."""

    async def complete(
        self,
        ticket_id: UUID,
        completed_by_id: UUID,
        comment: str | None = None,
        progress_percent: int | None = None,
    ) -> Ticket | None:
        """Complete a ticket."""

    async def close(
        self,
        ticket_id: UUID,
        closed_by_id: UUID,
        comment: str | None = None,
        progress_percent: int | None = None,
    ) -> Ticket | None:
        """Close a ticket."""

    async def update_progress(
        self,
        ticket_id: UUID,
        progress_percent: int,
    ) -> Ticket | None:
        """Update ticket implementation progress."""

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: "TicketFilterParams | None" = None,
        restrict_to_department_id: UUID | None = None,
        restrict_to_user_id: UUID | None = None,
    ) -> tuple[list[Ticket], int]:
        """Return paginated tickets with total count."""

    async def get_by_status(
        self, status: TicketStatus, skip: int = 0, limit: int = 100
    ) -> tuple[list[Ticket], int]:
        """Return tickets by status with total count."""

    async def get_by_creator(
        self, created_by_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[Ticket], int]:
        """Return tickets created by a user with total count."""

    async def get_by_assigned_department(
        self, department_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[Ticket], int]:
        """Return tickets assigned to a department with total count."""

    async def exists_by_id(self, ticket_id: UUID) -> bool:
        """Check if a ticket exists by ID."""

    async def exists_by_ticket_number(self, ticket_number: str) -> bool:
        """Check if a ticket exists by ticket number."""

    async def list_categories(self) -> list[TicketCategory]:
        """Return available ticket categories."""


class TicketCommentRepository(Protocol):
    """Repository interface for ticket comments."""

    async def create(
        self,
        ticket_id: UUID,
        author_id: UUID,
        body: str,
    ) -> "TicketComment":
        """Persist a new comment and return it with author loaded."""

    async def list_by_ticket(
        self,
        ticket_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list["TicketComment"], int]:
        """Return paginated comments for a ticket (newest batch by skip/limit), with authors."""

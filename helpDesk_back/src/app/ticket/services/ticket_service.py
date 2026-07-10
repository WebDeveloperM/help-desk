"""Ticket service - business logic for ticket operations."""

from datetime import datetime, timezone
from math import ceil
from uuid import UUID

from app.asset.exceptions import AssetAlreadyLinkedError
from app.asset.repositories import AssetRepository
from app.core.enums import NotificationType, TicketStatus
from app.notification.repositories import NotificationRepository
from app.notification.services.ticket_notifications import (
    create_notifications_for_ticket_assigned,
    create_notifications_for_ticket_status_change,
)
from app.sla.services import SlaService
from app.ticket.exceptions import (
    TicketNotFoundError,
    TicketStatusTransitionError,
    TicketValidationError,
)
from app.ticket.models import Ticket
from app.ticket.repositories import TicketRepository
from app.ticket.schemas import (
    TicketCategoryResponse,
    TicketCreate,
    TicketFilterParams,
    TicketListResponse,
    TicketResponse,
    TicketUpdate,
)
from app.user.repositories import UserRepository


class TicketService:
    """Service for ticket business logic operations."""

    _ALLOWED_STATUS_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
        TicketStatus.DRAFT: {TicketStatus.PENDING_APPROVAL, TicketStatus.ASSIGNED},
        TicketStatus.PENDING_APPROVAL: {TicketStatus.APPROVED, TicketStatus.REJECTED},
        TicketStatus.REJECTED: {TicketStatus.PENDING_APPROVAL, TicketStatus.ASSIGNED},
        TicketStatus.APPROVED: {TicketStatus.ASSIGNED},
        TicketStatus.ASSIGNED: {TicketStatus.IN_PROGRESS, TicketStatus.WAITING_INFO},
        TicketStatus.IN_PROGRESS: {
            TicketStatus.WAITING_INFO,
            TicketStatus.COMPLETED,
            TicketStatus.ASSIGNED,
        },
        TicketStatus.WAITING_INFO: {
            TicketStatus.IN_PROGRESS,
            TicketStatus.COMPLETED,
            TicketStatus.ASSIGNED,
        },
        TicketStatus.COMPLETED: {TicketStatus.CLOSED, TicketStatus.ASSIGNED},
        TicketStatus.CLOSED: set(),
    }

    def __init__(
        self,
        repository: TicketRepository,
        asset_repository: AssetRepository,
        user_repository: UserRepository,
        notification_repository: NotificationRepository,
        sla_service: SlaService | None = None,
    ) -> None:
        """
        Initialize ticket service.

        Args:
            repository: Ticket repository for database operations.
            user_repository: User repository for executor validation.
            notification_repository: Notification repository for ticket event notifications.
            sla_service: SLA service for planned completion and status (optional).
        """
        self.repository = repository
        self.asset_repository = asset_repository
        self.user_repository = user_repository
        self.notification_repository = notification_repository
        self.sla_service = sla_service

    @staticmethod
    def _dedupe_executor_ids(executor_user_ids: list[UUID]) -> list[UUID]:
        """Deduplicate executor IDs while preserving order."""
        return list(dict.fromkeys(executor_user_ids))

    @staticmethod
    def _dedupe_asset_ids(asset_ids: list[UUID]) -> list[UUID]:
        """Deduplicate asset IDs while preserving order."""
        return list(dict.fromkeys(asset_ids))

    @staticmethod
    def _ensure_status_transition(
        current_status: TicketStatus,
        target_status: TicketStatus,
        allowed_transitions: dict[TicketStatus, set[TicketStatus]],
        *,
        allow_same_status: bool = False,
    ) -> None:
        """Raise TicketStatusTransitionError if target status is not reachable."""
        if current_status == target_status:
            if allow_same_status:
                return
            raise TicketStatusTransitionError(
                current_status=current_status.value,
                target_status=target_status.value,
            )
        allowed_targets = allowed_transitions.get(current_status, set())
        if target_status not in allowed_targets:
            raise TicketStatusTransitionError(
                current_status=current_status.value,
                target_status=target_status.value,
            )

    @staticmethod
    def _validate_executor_users(
        executor_user_ids: list[UUID],
        users: list,
    ) -> None:
        """Raise TicketValidationError if any executor is missing or inactive."""
        found_ids = {u.id for u in users}
        missing = set(executor_user_ids) - found_ids
        if missing:
            raise TicketValidationError(
                detail=f"Executor user(s) not found: {sorted(missing)}"
            )
        inactive = [str(u.id) for u in users if not getattr(u, "is_active", True)]
        if inactive:
            raise TicketValidationError(
                detail=f"Executor user(s) are inactive: {inactive}"
            )

    @staticmethod
    def _resolve_assigned_department_id(
        users: list,
        explicit_department_id: UUID | None,
    ) -> UUID | None:
        """
        Resolve assigned department from explicit value or executor departments.

        If explicit_department_id is provided, all executors must belong to it.
        If omitted, returns the shared executor department when all executors
        belong to one department; otherwise returns None.
        """
        if explicit_department_id is not None:
            for user in users:
                if user.department_id != explicit_department_id:
                    raise TicketValidationError(
                        detail=(
                            f"Executor user {user.id} is not in department "
                            f"{explicit_department_id}"
                        )
                    )
            return explicit_department_id

        executor_department_ids = {u.department_id for u in users if u.department_id}
        if len(executor_department_ids) == 1:
            return next(iter(executor_department_ids))
        return None

    @staticmethod
    def _ensure_executors_in_department(
        users: list,
        required_department_id: UUID,
    ) -> None:
        """Ensure all executors belong to the required department."""
        for user in users:
            if user.department_id != required_department_id:
                raise TicketValidationError(
                    detail=(
                        f"Executor user {user.id} is not in department "
                        f"{required_department_id}"
                    )
                )

    @staticmethod
    def _validate_progress_by_status(status: TicketStatus, progress_percent: int) -> None:
        """Validate progress-state consistency."""
        if status in {TicketStatus.COMPLETED, TicketStatus.CLOSED} and progress_percent != 100:
            raise TicketValidationError(
                detail="Completed or closed ticket must have progress_percent=100"
            )
        if status in {TicketStatus.DRAFT, TicketStatus.PENDING_APPROVAL, TicketStatus.REJECTED} and progress_percent > 0:
            raise TicketValidationError(
                detail=(
                    "Draft, pending approval or rejected ticket cannot have progress_percent > 0"
                )
            )

    async def _require_ticket(self, ticket_id: UUID) -> Ticket:
        """Load ticket or raise TicketNotFoundError."""
        ticket = await self.repository.get_by_id(ticket_id)
        if not ticket:
            raise TicketNotFoundError(ticket_id=str(ticket_id))
        return ticket

    async def _ticket_to_response(self, ticket: Ticket) -> TicketResponse:
        """Build TicketResponse from ticket and attach SLA info if available."""
        resp = TicketResponse.model_validate(ticket)
        if self.sla_service:
            resp.sla = await self.sla_service.compute_sla_info(ticket)
        return resp

    async def _validate_assets_for_ticket(
        self,
        asset_ids: list[UUID],
        *,
        creator_department_id: UUID,
        for_repair_ticket: bool,
        exclude_ticket_id: UUID | None = None,
    ) -> None:
        """Validate linked assets for ticket operations."""
        if not asset_ids:
            return
        assets = await self.asset_repository.get_by_ids(asset_ids)
        if len(assets) != len(asset_ids):
            raise TicketValidationError(detail="Данного актива не существует")
        for asset in assets:
            if not asset.is_active:
                raise TicketValidationError(
                    detail="Нельзя привязать деактивированный актив к заявке"
                )
            if asset.department_id != creator_department_id:
                raise TicketValidationError(
                    detail="Актив должен принадлежать департаменту заявки"
                )
            if not for_repair_ticket:
                continue
            has_active_repair = await self.asset_repository.has_active_repair_ticket(
                asset.id,
                exclude_ticket_id=exclude_ticket_id,
            )
            if has_active_repair:
                raise TicketValidationError(
                    detail=(
                        f"Для актива '{asset.inventory_number}' уже есть активная "
                        "заявка на ремонт"
                    )
                )

    async def create_ticket(
        self, ticket_data: TicketCreate, created_by_id: UUID
    ) -> TicketResponse:
        """
        Create a new ticket and assign executors immediately.

        Args:
            ticket_data: Ticket creation data.
            created_by_id: ID of the user creating the ticket.

        Returns:
            Created ticket response.
        """
        executor_user_ids = self._dedupe_executor_ids(ticket_data.executor_user_ids)
        if not executor_user_ids:
            raise TicketValidationError(
                detail="At least one executor is required on ticket creation"
            )
        users = await self.user_repository.get_by_ids(executor_user_ids)
        self._validate_executor_users(executor_user_ids, users)
        # The dept that executes the work — explicit pick wins, otherwise default
        # to the creator's dept. Executors must belong to whichever dept owns
        # the work; assets remain pinned to the creator's dept.
        assigned_department_id = (
            ticket_data.assigned_department_id
            if ticket_data.assigned_department_id is not None
            else ticket_data.creator_department_id
        )
        self._ensure_executors_in_department(users, assigned_department_id)
        asset_ids = self._dedupe_asset_ids(ticket_data.asset_ids or [])
        is_repair_category = await self.repository.is_repair_category(
            ticket_data.category_id
        )
        await self._validate_assets_for_ticket(
            asset_ids,
            creator_department_id=ticket_data.creator_department_id,
            for_repair_ticket=is_repair_category,
        )
        ticket_payload = ticket_data.model_copy(
            update={"executor_user_ids": executor_user_ids, "asset_ids": asset_ids}
        )

        assigned_at = datetime.now(timezone.utc)
        planned_completion_date: datetime | None = None
        if self.sla_service:
            planned_completion_date = (
                await self.sla_service.compute_planned_completion_date(
                    ticket_data.priority,
                    from_time=assigned_at,
                )
            )

        ticket = await self.repository.create(
            ticket_payload,
            created_by_id,
            assigned_department_id=assigned_department_id,
            assigned_by_user_id=created_by_id,
            assigned_at=assigned_at,
            planned_completion_date=planned_completion_date,
        )
        await create_notifications_for_ticket_assigned(
            self.notification_repository,
            ticket,
            created_by_id,
        )
        # Load ticket with relationships so Pydantic model_validate does not trigger lazy load (MissingGreenlet)
        loaded = await self.repository.get_by_id(ticket.id)
        if not loaded:
            raise TicketNotFoundError(ticket_id=str(ticket.id))
        return await self._ticket_to_response(loaded)

    async def attach_assets(
        self,
        ticket_id: UUID,
        asset_ids: list[UUID],
    ) -> TicketResponse:
        """
        Attach assets to ticket.

        Args:
            ticket_id: Ticket UUID.
            asset_ids: Asset UUIDs.
        """
        ticket = await self._require_ticket(ticket_id)
        deduped_asset_ids = self._dedupe_asset_ids(asset_ids)
        if not deduped_asset_ids:
            raise TicketValidationError(detail="Не переданы активы для привязки")

        already_linked = {asset.id for asset in ticket.assets}
        duplicates = [asset_id for asset_id in deduped_asset_ids if asset_id in already_linked]
        if duplicates:
            raise AssetAlreadyLinkedError()

        is_repair_ticket = await self.repository.is_repair_ticket(ticket_id)
        await self._validate_assets_for_ticket(
            deduped_asset_ids,
            creator_department_id=ticket.creator_department_id,
            for_repair_ticket=is_repair_ticket,
            exclude_ticket_id=ticket_id,
        )
        await self.repository.add_assets(ticket_id, deduped_asset_ids)
        refreshed = await self._require_ticket(ticket_id)
        return await self._ticket_to_response(refreshed)

    async def detach_asset(self, ticket_id: UUID, asset_id: UUID) -> TicketResponse:
        """
        Detach single asset from ticket.

        Args:
            ticket_id: Ticket UUID.
            asset_id: Asset UUID.
        """
        await self._require_ticket(ticket_id)
        await self.repository.remove_asset(ticket_id, asset_id)
        refreshed = await self._require_ticket(ticket_id)
        return await self._ticket_to_response(refreshed)

    async def get_ticket(self, ticket_id: UUID) -> TicketResponse:
        """
        Get ticket by ID.

        Args:
            ticket_id: Ticket UUID.

        Returns:
            Ticket response.
        """
        ticket = await self._require_ticket(ticket_id)
        return await self._ticket_to_response(ticket)

    async def update_ticket(
        self,
        ticket_id: UUID,
        ticket_data: TicketUpdate,
        updated_by_user_id: UUID | None = None,
    ) -> TicketResponse:
        """
        Update ticket.

        Args:
            ticket_id: Ticket UUID.
            ticket_data: Ticket update data.
            updated_by_user_id: ID of the user performing the update.

        Returns:
            Updated ticket response.
        """
        old_ticket = await self._require_ticket(ticket_id)
        if (
            ticket_data.status is not None
            and ticket_data.status != old_ticket.status
        ):
            self._ensure_status_transition(
                old_ticket.status,
                ticket_data.status,
                self._ALLOWED_STATUS_TRANSITIONS,
            )
        target_status = ticket_data.status or old_ticket.status
        target_progress = (
            ticket_data.progress_percent
            if ticket_data.progress_percent is not None
            else old_ticket.progress_percent
        )
        self._validate_progress_by_status(target_status, target_progress)

        # Fold the SLA recompute into the same UPDATE: when priority changes,
        # compute the new planned_completion_date up front and ride it in on
        # ticket_data instead of issuing a second repo.update call.
        update_payload = ticket_data
        if (
            ticket_data.priority is not None
            and ticket_data.priority != old_ticket.priority
            and self.sla_service
        ):
            from_time = old_ticket.assigned_at or old_ticket.created_at
            planned = await self.sla_service.compute_planned_completion_date(
                ticket_data.priority,
                from_time=from_time,
            )
            update_payload = ticket_data.model_copy(
                update={"planned_completion_date": planned}
            )

        ticket = await self.repository.update(ticket_id, update_payload)
        if not ticket:
            raise TicketNotFoundError(ticket_id=str(ticket_id))
        if (
            updated_by_user_id is not None
            and ticket_data.status is not None
            and old_ticket.status != ticket.status
        ):
            await create_notifications_for_ticket_status_change(
                self.notification_repository,
                ticket,
                updated_by_user_id,
                NotificationType.STATUS_CHANGED,
                title=f"Ticket #{ticket.ticket_number} status changed",
                body=f"Status changed to {ticket.status.value}.",
            )
        return await self._ticket_to_response(ticket)

    async def get_stats(
        self,
        restrict_to_department_id: UUID | None = None,
        restrict_to_user_id: UUID | None = None,
    ) -> dict:
        """Return aggregated ticket analytics within the caller's visibility scope."""
        return await self.repository.get_stats(
            restrict_to_department_id=restrict_to_department_id,
            restrict_to_user_id=restrict_to_user_id,
        )

    async def get_user_activity(self) -> dict[str, dict[str, int]]:
        """Return per-user ticket activity across all tickets (admin overview)."""
        return await self.repository.get_user_activity()

    async def list_tickets(
        self,
        page: int = 1,
        page_size: int = 100,
        filters: TicketFilterParams | None = None,
        restrict_to_department_id: UUID | None = None,
        restrict_to_user_id: UUID | None = None,
    ) -> TicketListResponse:
        """
        List tickets with pagination.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            filters: Optional filter parameters.
            restrict_to_department_id: If set, include department-scoped tickets.
            restrict_to_user_id: If set, include creator/assigner/executor tickets.

        Returns:
            Paginated ticket list response.
        """
        skip = (page - 1) * page_size
        tickets, total = await self.repository.list(
            skip=skip,
            limit=page_size,
            filters=filters,
            restrict_to_department_id=restrict_to_department_id,
            restrict_to_user_id=restrict_to_user_id,
        )

        total = int(total) if total is not None else 0
        pages = ceil(total / page_size) if total > 0 else 0

        if total == 0 or not tickets:
            return TicketListResponse(
                items=[],
                total=total,
                page=page,
                page_size=page_size,
                pages=pages,
            )

        items = []
        for ticket in tickets:
            items.append(await self._ticket_to_response(ticket))
        return TicketListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def approve_ticket(
        self, ticket_id: UUID, approver_user_id: UUID, comment: str | None = None
    ) -> TicketResponse:
        """
        Approve a ticket.

        Args:
            ticket_id: Ticket UUID.
            approver_user_id: ID of the user approving the ticket.
            comment: Optional approver comment.

        Returns:
            Updated ticket response.
        """
        old_ticket = await self._require_ticket(ticket_id)
        self._ensure_status_transition(
            old_ticket.status,
            TicketStatus.APPROVED,
            self._ALLOWED_STATUS_TRANSITIONS,
        )
        ticket = await self.repository.approve(ticket_id, approver_user_id, comment)
        if not ticket:
            raise TicketNotFoundError(ticket_id=str(ticket_id))
        await create_notifications_for_ticket_status_change(
            self.notification_repository,
            ticket,
            approver_user_id,
            NotificationType.TICKET_APPROVED,
            title=f"Ticket #{ticket.ticket_number} approved",
            body="The ticket has been approved.",
        )
        return await self._ticket_to_response(ticket)

    async def reject_ticket(
        self, ticket_id: UUID, approver_user_id: UUID, comment: str
    ) -> TicketResponse:
        """
        Reject a ticket.

        Args:
            ticket_id: Ticket UUID.
            approver_user_id: ID of the user rejecting the ticket.
            comment: Rejection comment (required).

        Returns:
            Updated ticket response.
        """
        old_ticket = await self._require_ticket(ticket_id)
        self._ensure_status_transition(
            old_ticket.status,
            TicketStatus.REJECTED,
            self._ALLOWED_STATUS_TRANSITIONS,
        )
        ticket = await self.repository.reject(ticket_id, approver_user_id, comment)
        if not ticket:
            raise TicketNotFoundError(ticket_id=str(ticket_id))
        await create_notifications_for_ticket_status_change(
            self.notification_repository,
            ticket,
            approver_user_id,
            NotificationType.TICKET_REJECTED,
            title=f"Ticket #{ticket.ticket_number} rejected",
            body=f"Rejected: {comment or 'No comment'}",
        )
        return await self._ticket_to_response(ticket)

    async def assign_ticket(
        self,
        ticket_id: UUID,
        assigned_department_id: UUID | None,
        assigned_by_user_id: UUID,
        executor_user_ids: list[UUID],
    ) -> TicketResponse:
        """
        Assign or reassign a ticket.

        Args:
            ticket_id: Ticket UUID.
            assigned_department_id: Optional department ID.
            assigned_by_user_id: ID of the user assigning the ticket.
            executor_user_ids: Executor user IDs.

        Returns:
            Updated ticket response.
        """
        old_ticket = await self._require_ticket(ticket_id)
        self._ensure_status_transition(
            old_ticket.status,
            TicketStatus.ASSIGNED,
            self._ALLOWED_STATUS_TRANSITIONS,
            allow_same_status=True,
        )

        deduped_executor_ids = self._dedupe_executor_ids(executor_user_ids)
        if not deduped_executor_ids:
            raise TicketValidationError(
                detail="At least one executor is required for assignment"
            )
        users = await self.user_repository.get_by_ids(deduped_executor_ids)
        self._validate_executor_users(deduped_executor_ids, users)
        # Reassignment can move the ticket to a different dept; fall back to
        # the ticket's existing assigned dept, then to the creator's dept.
        resolved_department_id = (
            assigned_department_id
            if assigned_department_id is not None
            else (old_ticket.assigned_department_id or old_ticket.creator_department_id)
        )
        self._ensure_executors_in_department(users, resolved_department_id)
        previous_executor_ids = {executor.id for executor in old_ticket.executors}

        # Compute SLA up front against the same `assigned_at` we'll write so
        # the deadline and the assignment timestamp stay consistent in a
        # single UPDATE.
        assigned_at = datetime.now(timezone.utc)
        planned_completion_date: datetime | None = None
        if self.sla_service:
            planned_completion_date = (
                await self.sla_service.compute_planned_completion_date(
                    old_ticket.priority,
                    from_time=assigned_at,
                )
            )

        ticket = await self.repository.assign(
            ticket_id,
            resolved_department_id,
            assigned_by_user_id,
            executor_user_ids=deduped_executor_ids,
            assigned_at=assigned_at,
            planned_completion_date=planned_completion_date,
        )
        if not ticket:
            raise TicketNotFoundError(ticket_id=str(ticket_id))
        await create_notifications_for_ticket_assigned(
            self.notification_repository,
            ticket,
            assigned_by_user_id,
            previous_executor_ids=previous_executor_ids,
        )
        return await self._ticket_to_response(ticket)

    async def start_progress_ticket(
        self, ticket_id: UUID, started_by_user_id: UUID
    ) -> TicketResponse:
        """
        Mark ticket as in progress.

        Args:
            ticket_id: Ticket UUID.
            started_by_user_id: ID of the user who started progress.

        Returns:
            Updated ticket response.
        """
        old_ticket = await self._require_ticket(ticket_id)
        self._ensure_status_transition(
            old_ticket.status,
            TicketStatus.IN_PROGRESS,
            self._ALLOWED_STATUS_TRANSITIONS,
        )
        # Bump progress 0 → 10 in the same UPDATE that flips the status.
        progress_bump = 10 if old_ticket.progress_percent == 0 else None
        ticket = await self.repository.start_progress(
            ticket_id, progress_percent=progress_bump
        )
        if not ticket:
            raise TicketNotFoundError(ticket_id=str(ticket_id))
        await create_notifications_for_ticket_status_change(
            self.notification_repository,
            ticket,
            started_by_user_id,
            NotificationType.STATUS_CHANGED,
            title=f"Ticket #{ticket.ticket_number} in progress",
            body="The ticket is now in progress.",
        )
        return await self._ticket_to_response(ticket)

    async def waiting_info_ticket(
        self, ticket_id: UUID, waiting_by_user_id: UUID
    ) -> TicketResponse:
        """
        Mark ticket as waiting for information.

        Args:
            ticket_id: Ticket UUID.
            waiting_by_user_id: ID of the user requesting information.

        Returns:
            Updated ticket response.
        """
        old_ticket = await self._require_ticket(ticket_id)
        self._ensure_status_transition(
            old_ticket.status,
            TicketStatus.WAITING_INFO,
            self._ALLOWED_STATUS_TRANSITIONS,
        )
        ticket = await self.repository.waiting_info(ticket_id)
        if not ticket:
            raise TicketNotFoundError(ticket_id=str(ticket_id))
        await create_notifications_for_ticket_status_change(
            self.notification_repository,
            ticket,
            waiting_by_user_id,
            NotificationType.STATUS_CHANGED,
            title=f"Ticket #{ticket.ticket_number} waiting for info",
            body="The ticket is waiting for additional information.",
        )
        return await self._ticket_to_response(ticket)

    async def complete_ticket(
        self, ticket_id: UUID, completed_by_id: UUID, comment: str | None = None
    ) -> TicketResponse:
        """
        Complete a ticket.

        Args:
            ticket_id: Ticket UUID.
            completed_by_id: ID of the user completing the ticket.
            comment: Optional completion comment.

        Returns:
            Updated ticket response.
        """
        old_ticket = await self._require_ticket(ticket_id)
        self._ensure_status_transition(
            old_ticket.status,
            TicketStatus.COMPLETED,
            self._ALLOWED_STATUS_TRANSITIONS,
        )
        # Force progress to 100 in the same UPDATE that flips the status.
        progress_target = (
            None if old_ticket.progress_percent == 100 else 100
        )
        ticket = await self.repository.complete(
            ticket_id,
            completed_by_id,
            comment,
            progress_percent=progress_target,
        )
        if not ticket:
            raise TicketNotFoundError(ticket_id=str(ticket_id))
        await create_notifications_for_ticket_status_change(
            self.notification_repository,
            ticket,
            completed_by_id,
            NotificationType.TICKET_COMPLETED,
            title=f"Ticket #{ticket.ticket_number} completed",
            body="The ticket has been completed.",
        )
        return await self._ticket_to_response(ticket)

    async def close_ticket(
        self, ticket_id: UUID, closed_by_id: UUID, comment: str | None = None
    ) -> TicketResponse:
        """
        Close a ticket.

        Args:
            ticket_id: Ticket UUID.
            closed_by_id: ID of the user closing the ticket.
            comment: Optional closure comment.

        Returns:
            Updated ticket response.
        """
        old_ticket = await self._require_ticket(ticket_id)
        self._ensure_status_transition(
            old_ticket.status,
            TicketStatus.CLOSED,
            self._ALLOWED_STATUS_TRANSITIONS,
        )
        # Force progress to 100 in the same UPDATE that flips the status.
        progress_target = (
            None if old_ticket.progress_percent == 100 else 100
        )
        ticket = await self.repository.close(
            ticket_id,
            closed_by_id,
            comment,
            progress_percent=progress_target,
        )
        if not ticket:
            raise TicketNotFoundError(ticket_id=str(ticket_id))
        await create_notifications_for_ticket_status_change(
            self.notification_repository,
            ticket,
            closed_by_id,
            NotificationType.STATUS_CHANGED,
            title=f"Ticket #{ticket.ticket_number} closed",
            body="The ticket has been closed.",
        )
        return await self._ticket_to_response(ticket)

    # Delegate repository methods for direct access when needed
    async def get_by_id(self, ticket_id: UUID) -> Ticket | None:
        """Get ticket entity by ID."""
        return await self.repository.get_by_id(ticket_id)

    async def get_by_ticket_number(self, ticket_number: str) -> Ticket | None:
        """Get ticket entity by ticket number."""
        return await self.repository.get_by_ticket_number(ticket_number)

    async def update_ticket_progress(
        self,
        ticket_id: UUID,
        progress_percent: int,
    ) -> TicketResponse:
        """
        Update ticket implementation progress.

        Args:
            ticket_id: Ticket UUID.
            progress_percent: Progress percentage [0..100].

        Returns:
            Updated ticket response.
        """
        ticket = await self._require_ticket(ticket_id)
        self._validate_progress_by_status(ticket.status, progress_percent)
        updated_ticket = await self.repository.update_progress(ticket_id, progress_percent)
        if not updated_ticket:
            raise TicketNotFoundError(ticket_id=str(ticket_id))
        return await self._ticket_to_response(updated_ticket)

    async def list_categories(self) -> list[TicketCategoryResponse]:
        """List available ticket categories."""
        categories = await self.repository.list_categories()
        return [TicketCategoryResponse.model_validate(category) for category in categories]

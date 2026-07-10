"""Ticket repository - isolated database queries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import case, delete, extract, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import TicketPriority, TicketStatus
from app.ticket.models import (
    Ticket,
    TicketCategory,
    ticket_assets_table,
    ticket_executors_table,
)

if TYPE_CHECKING:
    from app.ticket.schemas import TicketCreate, TicketFilterParams, TicketUpdate


class SQLAlchemyTicketRepository:
    """SQLAlchemy-based repository for ticket database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize ticket repository.

        Args:
            session: Database session.
        """
        self.session = session

    async def get_by_id(self, ticket_id: UUID) -> Ticket | None:
        """
        Get ticket by ID with relationships loaded.

        Args:
            ticket_id: Ticket UUID.

        Returns:
            Ticket if found, None otherwise.
        """
        result = await self.session.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.created_by),
                selectinload(Ticket.creator_department),
                selectinload(Ticket.assigned_department),
                selectinload(Ticket.approver),
                selectinload(Ticket.assigned_by),
                selectinload(Ticket.completed_by),
                selectinload(Ticket.closed_by),
                selectinload(Ticket.executors),
                selectinload(Ticket.assets),
            )
            .where(Ticket.id == ticket_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ticket_number(self, ticket_number: str) -> Ticket | None:
        """
        Get ticket by ticket number.

        Args:
            ticket_number: Ticket number.

        Returns:
            Ticket if found, None otherwise.
        """
        result = await self.session.execute(
            select(Ticket).where(Ticket.ticket_number == ticket_number)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        ticket_data: "TicketCreate",
        created_by_id: UUID,
        assigned_department_id: UUID | None,
        assigned_by_user_id: UUID,
        assigned_at: datetime | None = None,
        planned_completion_date: datetime | None = None,
    ) -> Ticket:
        """
        Create a new ticket record in database.

        Args:
            ticket_data: Ticket creation data.
            created_by_id: ID of the user creating the ticket.
            assigned_department_id: Assigned department ID.
            assigned_by_user_id: User who assigned the ticket.
            assigned_at: Assignment timestamp.
            planned_completion_date: Optional SLA-based planned completion date.

        Returns:
            Created ticket.
        """
        resolved_assigned_at = assigned_at or datetime.now(timezone.utc)
        ticket = Ticket(
            title=ticket_data.title,
            description=ticket_data.description,
            category_id=ticket_data.category_id,
            template_id=ticket_data.template_id,
            priority=ticket_data.priority,
            created_by_id=created_by_id,
            creator_department_id=ticket_data.creator_department_id,
            status=TicketStatus.ASSIGNED,
            assigned_department_id=assigned_department_id,
            assigned_by_user_id=assigned_by_user_id,
            assigned_at=resolved_assigned_at,
            desired_completion_date=ticket_data.desired_completion_date,
            planned_completion_date=planned_completion_date,
            ticket_metadata=ticket_data.ticket_metadata,
        )

        self.session.add(ticket)
        await self.session.flush()
        await self.session.refresh(ticket)
        await self.set_executors(ticket.id, ticket_data.executor_user_ids)
        await self.set_assets(ticket.id, ticket_data.asset_ids or [])
        await self.session.refresh(ticket)
        return ticket

    async def set_executors(self, ticket_id: UUID, user_ids: list[UUID]) -> None:
        """
        Replace ticket executors with the given user IDs.

        Args:
            ticket_id: Ticket UUID.
            user_ids: List of executor user UUIDs.
        """
        await self.session.execute(
            delete(ticket_executors_table).where(
                ticket_executors_table.c.ticket_id == ticket_id
            )
        )
        if user_ids:
            await self.session.execute(
                insert(ticket_executors_table),
                [{"ticket_id": ticket_id, "user_id": uid} for uid in user_ids],
            )
        await self.session.flush()

    async def set_assets(self, ticket_id: UUID, asset_ids: list[UUID]) -> None:
        """
        Replace ticket assets with given asset IDs.

        Args:
            ticket_id: Ticket UUID.
            asset_ids: List of asset UUIDs.
        """
        await self.session.execute(
            delete(ticket_assets_table).where(ticket_assets_table.c.ticket_id == ticket_id)
        )
        await self.session.flush()
        for asset_id in dict.fromkeys(asset_ids):
            await self.session.execute(
                insert(ticket_assets_table).values(ticket_id=ticket_id, asset_id=asset_id)
            )
        await self.session.flush()

    async def add_assets(self, ticket_id: UUID, asset_ids: list[UUID]) -> None:
        """
        Attach assets to ticket, skipping existing links.

        Args:
            ticket_id: Ticket UUID.
            asset_ids: List of asset UUIDs.
        """
        if not asset_ids:
            return
        existing_result = await self.session.execute(
            select(ticket_assets_table.c.asset_id).where(
                ticket_assets_table.c.ticket_id == ticket_id
            )
        )
        existing_ids = set(existing_result.scalars().all())
        for asset_id in dict.fromkeys(asset_ids):
            if asset_id in existing_ids:
                continue
            await self.session.execute(
                insert(ticket_assets_table).values(ticket_id=ticket_id, asset_id=asset_id)
            )
        await self.session.flush()

    async def remove_asset(self, ticket_id: UUID, asset_id: UUID) -> None:
        """
        Remove ticket-asset link.

        Args:
            ticket_id: Ticket UUID.
            asset_id: Asset UUID.
        """
        await self.session.execute(
            delete(ticket_assets_table)
            .where(ticket_assets_table.c.ticket_id == ticket_id)
            .where(ticket_assets_table.c.asset_id == asset_id)
        )
        await self.session.flush()

    async def is_repair_ticket(self, ticket_id: UUID) -> bool:
        """
        Return whether ticket category is 'repair'.

        Args:
            ticket_id: Ticket UUID.
        """
        result = await self.session.execute(
            select(TicketCategory.code)
            .select_from(Ticket)
            .join(TicketCategory, TicketCategory.id == Ticket.category_id)
            .where(Ticket.id == ticket_id)
        )
        code = result.scalar_one_or_none()
        return code == "repair"

    async def is_repair_category(self, category_id: UUID) -> bool:
        """
        Return whether category code is 'repair'.

        Args:
            category_id: Ticket category UUID.
        """
        result = await self.session.execute(
            select(TicketCategory.code).where(TicketCategory.id == category_id)
        )
        code = result.scalar_one_or_none()
        return code == "repair"

    async def update(
        self, ticket_id: UUID, ticket_data: "TicketUpdate"
    ) -> Ticket | None:
        """
        Update ticket record in database.

        Args:
            ticket_id: Ticket UUID.
            ticket_data: Ticket update data.

        Returns:
            Updated ticket if found, None otherwise.
        """
        update_data: dict[str, Any] = {
            k: v for k, v in ticket_data.model_dump(exclude_unset=True).items()
        }

        if not update_data:
            return await self.get_by_id(ticket_id)

        await self.session.execute(
            update(Ticket).where(Ticket.id == ticket_id).values(**update_data)
        )
        await self.session.flush()

        return await self.get_by_id(ticket_id)

    async def approve(
        self, ticket_id: UUID, approver_user_id: UUID, comment: str | None = None
    ) -> Ticket | None:
        """
        Approve a ticket.

        Args:
            ticket_id: Ticket UUID.
            approver_user_id: ID of the user approving the ticket.
            comment: Optional approver comment.

        Returns:
            Updated ticket if found, None otherwise.
        """
        update_data = {
            "status": TicketStatus.APPROVED,
            "approver_user_id": approver_user_id,
            "approved_at": datetime.now(timezone.utc),
            "approver_comment": comment,
        }

        await self.session.execute(
            update(Ticket).where(Ticket.id == ticket_id).values(**update_data)
        )
        await self.session.flush()

        return await self.get_by_id(ticket_id)

    async def reject(
        self, ticket_id: UUID, approver_user_id: UUID, comment: str
    ) -> Ticket | None:
        """
        Reject a ticket.

        Args:
            ticket_id: Ticket UUID.
            approver_user_id: ID of the user rejecting the ticket.
            comment: Rejection comment (required).

        Returns:
            Updated ticket if found, None otherwise.
        """
        update_data = {
            "status": TicketStatus.REJECTED,
            "approver_user_id": approver_user_id,
            "approved_at": datetime.now(timezone.utc),
            "approver_comment": comment,
        }

        await self.session.execute(
            update(Ticket).where(Ticket.id == ticket_id).values(**update_data)
        )
        await self.session.flush()

        return await self.get_by_id(ticket_id)

    async def assign(
        self,
        ticket_id: UUID,
        assigned_department_id: UUID | None,
        assigned_by_user_id: UUID,
        executor_user_ids: list[UUID],
        assigned_at: datetime | None = None,
        planned_completion_date: datetime | None = None,
    ) -> Ticket | None:
        """
        Assign a ticket to a department and optionally set executors.

        Args:
            ticket_id: Ticket UUID.
            assigned_department_id: Department ID to assign ticket to.
            assigned_by_user_id: ID of the user assigning the ticket.
            executor_user_ids: Optional list of executor user UUIDs.
            assigned_at: Optional explicit assignment timestamp; defaults to now.
                Pass an explicit value when the caller has already used it for
                an SLA calculation so both stay in sync.
            planned_completion_date: Optional SLA-derived deadline written in
                the same UPDATE so the service does not need a follow-up call.

        Returns:
            Updated ticket if found, None otherwise.
        """
        update_data: dict[str, Any] = {
            "status": TicketStatus.ASSIGNED,
            "assigned_department_id": assigned_department_id,
            "assigned_by_user_id": assigned_by_user_id,
            "assigned_at": assigned_at or datetime.now(timezone.utc),
        }
        if planned_completion_date is not None:
            update_data["planned_completion_date"] = planned_completion_date

        await self.session.execute(
            update(Ticket).where(Ticket.id == ticket_id).values(**update_data)
        )
        await self.session.flush()
        await self.set_executors(ticket_id, executor_user_ids)

        return await self.get_by_id(ticket_id)

    async def start_progress(
        self,
        ticket_id: UUID,
        progress_percent: int | None = None,
    ) -> Ticket | None:
        """
        Mark ticket as in progress.

        Args:
            ticket_id: Ticket UUID.
            progress_percent: Optional new progress value written in the same
                UPDATE; pass when the service wants to bump 0 → 10 atomically.

        Returns:
            Updated ticket if found, None otherwise.
        """
        update_data: dict[str, Any] = {"status": TicketStatus.IN_PROGRESS}
        if progress_percent is not None:
            update_data["progress_percent"] = progress_percent

        await self.session.execute(
            update(Ticket).where(Ticket.id == ticket_id).values(**update_data)
        )
        await self.session.flush()

        return await self.get_by_id(ticket_id)

    async def waiting_info(self, ticket_id: UUID) -> Ticket | None:
        """
        Mark ticket as waiting for additional information.

        Args:
            ticket_id: Ticket UUID.

        Returns:
            Updated ticket if found, None otherwise.
        """
        update_data = {"status": TicketStatus.WAITING_INFO}

        await self.session.execute(
            update(Ticket).where(Ticket.id == ticket_id).values(**update_data)
        )
        await self.session.flush()

        return await self.get_by_id(ticket_id)

    async def complete(
        self,
        ticket_id: UUID,
        completed_by_id: UUID,
        comment: str | None = None,
        progress_percent: int | None = None,
    ) -> Ticket | None:
        """
        Complete a ticket.

        Args:
            ticket_id: Ticket UUID.
            completed_by_id: ID of the user completing the ticket.
            comment: Optional completion comment.
            progress_percent: Optional progress value (typically 100) written
                in the same UPDATE so the service avoids a follow-up call.

        Returns:
            Updated ticket if found, None otherwise.
        """
        now = datetime.now(timezone.utc)
        update_data: dict[str, Any] = {
            "status": TicketStatus.COMPLETED,
            "completed_by_id": completed_by_id,
            "completed_at": now,
            "actual_completion_date": now,
            "completion_comment": comment,
        }
        if progress_percent is not None:
            update_data["progress_percent"] = progress_percent

        await self.session.execute(
            update(Ticket).where(Ticket.id == ticket_id).values(**update_data)
        )
        await self.session.flush()

        return await self.get_by_id(ticket_id)

    async def close(
        self,
        ticket_id: UUID,
        closed_by_id: UUID,
        comment: str | None = None,
        progress_percent: int | None = None,
    ) -> Ticket | None:
        """
        Close a ticket.

        Args:
            ticket_id: Ticket UUID.
            closed_by_id: ID of the user closing the ticket.
            comment: Optional closure comment.
            progress_percent: Optional progress value (typically 100) written
                in the same UPDATE so the service avoids a follow-up call.

        Returns:
            Updated ticket if found, None otherwise.
        """
        update_data: dict[str, Any] = {
            "status": TicketStatus.CLOSED,
            "closed_by_id": closed_by_id,
            "closed_at": datetime.now(timezone.utc),
            "closed_comment": comment,
        }
        if progress_percent is not None:
            update_data["progress_percent"] = progress_percent

        await self.session.execute(
            update(Ticket).where(Ticket.id == ticket_id).values(**update_data)
        )
        await self.session.flush()

        return await self.get_by_id(ticket_id)

    async def update_progress(
        self,
        ticket_id: UUID,
        progress_percent: int,
    ) -> Ticket | None:
        """
        Update ticket implementation progress percentage.

        Args:
            ticket_id: Ticket UUID.
            progress_percent: Progress value in [0..100].

        Returns:
            Updated ticket if found, None otherwise.
        """
        await self.session.execute(
            update(Ticket)
            .where(Ticket.id == ticket_id)
            .values(progress_percent=progress_percent)
        )
        await self.session.flush()
        return await self.get_by_id(ticket_id)

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: "TicketFilterParams | None" = None,
        restrict_to_department_id: UUID | None = None,
        restrict_to_user_id: UUID | None = None,
    ) -> tuple[list[Ticket], int]:
        """
        List tickets with pagination and filtering.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            filters: Optional filter parameters.
            restrict_to_department_id: If set, only tickets in this department (creator or assigned).

        Returns:
            Tuple of (tickets list, total count).
        """
        query = select(Ticket).options(
            selectinload(Ticket.created_by),
            selectinload(Ticket.creator_department),
            selectinload(Ticket.assigned_department),
            selectinload(Ticket.executors),
            selectinload(Ticket.assets),
            selectinload(Ticket.approver),
            selectinload(Ticket.assigned_by),
            selectinload(Ticket.completed_by),
            selectinload(Ticket.closed_by),
        )

        count_query = select(func.count()).select_from(Ticket)

        scope_filter = None
        if restrict_to_department_id is not None:
            scope_filter = (
                (Ticket.creator_department_id == restrict_to_department_id)
                | (Ticket.assigned_department_id == restrict_to_department_id)
            )
        if restrict_to_user_id is not None:
            executor_ticket_ids = select(ticket_executors_table.c.ticket_id).where(
                ticket_executors_table.c.user_id == restrict_to_user_id
            )
            user_scope = (
                (Ticket.created_by_id == restrict_to_user_id)
                | (Ticket.assigned_by_user_id == restrict_to_user_id)
                | (Ticket.id.in_(executor_ticket_ids))
            )
            scope_filter = user_scope if scope_filter is None else (scope_filter | user_scope)
        if scope_filter is not None:
            query = query.where(scope_filter)
            count_query = count_query.where(scope_filter)

        # Apply filters
        if filters:
            if filters.status is not None:
                query = query.where(Ticket.status == filters.status)
                count_query = count_query.where(Ticket.status == filters.status)

            if filters.priority is not None:
                query = query.where(Ticket.priority == filters.priority)
                count_query = count_query.where(Ticket.priority == filters.priority)

            if filters.category_id is not None:
                query = query.where(Ticket.category_id == filters.category_id)
                count_query = count_query.where(
                    Ticket.category_id == filters.category_id
                )

            if filters.created_by_id is not None:
                query = query.where(Ticket.created_by_id == filters.created_by_id)
                count_query = count_query.where(
                    Ticket.created_by_id == filters.created_by_id
                )

            if filters.creator_department_id is not None:
                query = query.where(
                    Ticket.creator_department_id == filters.creator_department_id
                )
                count_query = count_query.where(
                    Ticket.creator_department_id == filters.creator_department_id
                )

            if filters.assigned_department_id is not None:
                query = query.where(
                    Ticket.assigned_department_id == filters.assigned_department_id
                )
                count_query = count_query.where(
                    Ticket.assigned_department_id == filters.assigned_department_id
                )

            if filters.is_urgent is not None:
                query = query.where(Ticket.is_urgent == filters.is_urgent)
                count_query = count_query.where(Ticket.is_urgent == filters.is_urgent)

            if filters.created_from is not None:
                query = query.where(Ticket.created_at >= filters.created_from)
                count_query = count_query.where(
                    Ticket.created_at >= filters.created_from
                )

            if filters.created_to is not None:
                query = query.where(Ticket.created_at <= filters.created_to)
                count_query = count_query.where(Ticket.created_at <= filters.created_to)

            if filters.search:
                term = f"%{filters.search.strip()}%"
                search_filter = (
                    Ticket.title.ilike(term)
                    | Ticket.description.ilike(term)
                    | Ticket.ticket_number.ilike(term)
                )
                query = query.where(search_filter)
                count_query = count_query.where(search_filter)

        total_result = await self.session.execute(count_query)
        raw_total = total_result.scalar()
        total = int(raw_total) if raw_total is not None else 0

        query = query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        tickets = list(result.scalars().all())

        return tickets, total

    def _visibility_filter(
        self,
        restrict_to_department_id: UUID | None,
        restrict_to_user_id: UUID | None,
    ):
        """Build the same department/user visibility filter used by list()."""
        scope_filter = None
        if restrict_to_department_id is not None:
            scope_filter = (
                (Ticket.creator_department_id == restrict_to_department_id)
                | (Ticket.assigned_department_id == restrict_to_department_id)
            )
        if restrict_to_user_id is not None:
            executor_ticket_ids = select(ticket_executors_table.c.ticket_id).where(
                ticket_executors_table.c.user_id == restrict_to_user_id
            )
            user_scope = (
                (Ticket.created_by_id == restrict_to_user_id)
                | (Ticket.assigned_by_user_id == restrict_to_user_id)
                | (Ticket.id.in_(executor_ticket_ids))
            )
            scope_filter = (
                user_scope if scope_filter is None else (scope_filter | user_scope)
            )
        return scope_filter

    async def get_stats(
        self,
        restrict_to_department_id: UUID | None = None,
        restrict_to_user_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Aggregate ticket analytics within the caller's visibility scope."""
        now = datetime.now(timezone.utc)
        scope = self._visibility_filter(restrict_to_department_id, restrict_to_user_id)

        def scoped(query):
            return query.where(scope) if scope is not None else query

        closed_statuses = [TicketStatus.COMPLETED, TicketStatus.CLOSED]

        # Counts grouped by status.
        status_rows = (
            await self.session.execute(
                scoped(select(Ticket.status, func.count()).group_by(Ticket.status))
            )
        ).all()
        by_status = [{"status": s.value, "count": int(c)} for s, c in status_rows]
        status_map = {s.value: int(c) for s, c in status_rows}
        total = sum(status_map.values())
        completed = status_map.get(TicketStatus.COMPLETED.value, 0)
        closed = status_map.get(TicketStatus.CLOSED.value, 0)
        in_progress = status_map.get(TicketStatus.IN_PROGRESS.value, 0)

        # Counts grouped by priority.
        priority_rows = (
            await self.session.execute(
                scoped(
                    select(Ticket.priority, func.count()).group_by(Ticket.priority)
                )
            )
        ).all()
        by_priority = [{"priority": p.value, "count": int(c)} for p, c in priority_rows]

        # Top categories.
        category_rows = (
            await self.session.execute(
                scoped(
                    select(
                        TicketCategory.id, TicketCategory.name, func.count(Ticket.id)
                    )
                    .join(TicketCategory, TicketCategory.id == Ticket.category_id)
                    .group_by(TicketCategory.id, TicketCategory.name)
                    .order_by(func.count(Ticket.id).desc())
                    .limit(6)
                )
            )
        ).all()
        by_category = [
            {"category_id": str(cid), "name": name, "count": int(c)}
            for cid, name, c in category_rows
        ]

        async def scalar_count(condition) -> int:
            q = scoped(select(func.count()).select_from(Ticket)).where(condition)
            return int((await self.session.execute(q)).scalar() or 0)

        open_condition = Ticket.status.notin_(closed_statuses)
        overdue = await scalar_count(
            open_condition
            & (Ticket.planned_completion_date.isnot(None))
            & (Ticket.planned_completion_date < now)
        )
        urgent_open = await scalar_count(
            open_condition & (Ticket.priority == TicketPriority.URGENT)
        )
        created_last_7d = await scalar_count(Ticket.created_at >= now - timedelta(days=7))
        completed_last_7d = await scalar_count(
            (Ticket.completed_at.isnot(None))
            & (Ticket.completed_at >= now - timedelta(days=7))
        )

        # Average resolution time (hours) over completed tickets.
        avg_seconds = (
            await self.session.execute(
                scoped(
                    select(
                        func.avg(
                            extract("epoch", Ticket.completed_at - Ticket.created_at)
                        )
                    ).where(Ticket.completed_at.isnot(None))
                )
            )
        ).scalar()
        avg_resolution_hours = (
            round(float(avg_seconds) / 3600.0, 1) if avg_seconds is not None else None
        )

        # SLA compliance: of completed tickets with a planned date, how many on time.
        sla_row = (
            await self.session.execute(
                scoped(
                    select(
                        func.count(),
                        func.sum(
                            case(
                                (
                                    Ticket.completed_at
                                    <= Ticket.planned_completion_date,
                                    1,
                                ),
                                else_=0,
                            )
                        ),
                    ).where(
                        (Ticket.completed_at.isnot(None))
                        & (Ticket.planned_completion_date.isnot(None))
                    )
                )
            )
        ).first()
        sla_total = int(sla_row[0] or 0) if sla_row else 0
        sla_on_time = int(sla_row[1] or 0) if sla_row else 0
        sla_compliance_pct = (
            round(sla_on_time / sla_total * 100, 1) if sla_total > 0 else None
        )

        # Throughput for the last 14 days (created vs completed per day).
        since = now - timedelta(days=13)
        created_day_rows = (
            await self.session.execute(
                scoped(
                    select(func.date(Ticket.created_at), func.count())
                    .where(Ticket.created_at >= since)
                    .group_by(func.date(Ticket.created_at))
                )
            )
        ).all()
        completed_day_rows = (
            await self.session.execute(
                scoped(
                    select(func.date(Ticket.completed_at), func.count())
                    .where(Ticket.completed_at.isnot(None))
                    .where(Ticket.completed_at >= since)
                    .group_by(func.date(Ticket.completed_at))
                )
            )
        ).all()
        created_by_day = {str(d): int(c) for d, c in created_day_rows}
        completed_by_day = {str(d): int(c) for d, c in completed_day_rows}
        throughput = []
        for offset in range(14):
            day = (since + timedelta(days=offset)).date().isoformat()
            throughput.append(
                {
                    "date": day,
                    "created": created_by_day.get(day, 0),
                    "completed": completed_by_day.get(day, 0),
                }
            )

        return {
            "total": total,
            "open": total - completed - closed,
            "in_progress": in_progress,
            "completed": completed,
            "closed": closed,
            "overdue": overdue,
            "urgent_open": urgent_open,
            "created_last_7d": created_last_7d,
            "completed_last_7d": completed_last_7d,
            "avg_resolution_hours": avg_resolution_hours,
            "sla_compliance_pct": sla_compliance_pct,
            "by_status": by_status,
            "by_priority": by_priority,
            "by_category": by_category,
            "throughput": throughput,
        }

    async def get_user_activity(self) -> dict[str, dict[str, int]]:
        """Per-user ticket activity across ALL tickets (admin overview).

        Returns {user_id: {created, active, completed}} where active/completed
        count tickets the user executes (from ticket_executors), split by status.
        """
        closed = [TicketStatus.COMPLETED, TicketStatus.CLOSED]
        result: dict[str, dict[str, int]] = {}

        def _entry(uid: str) -> dict[str, int]:
            return result.setdefault(uid, {"created": 0, "active": 0, "completed": 0})

        created_rows = (
            await self.session.execute(
                select(Ticket.created_by_id, func.count()).group_by(
                    Ticket.created_by_id
                )
            )
        ).all()
        for uid, count in created_rows:
            _entry(str(uid))["created"] = int(count)

        exec_rows = (
            await self.session.execute(
                select(
                    ticket_executors_table.c.user_id,
                    func.count().filter(Ticket.status.notin_(closed)),
                    func.count().filter(Ticket.status.in_(closed)),
                )
                .select_from(
                    ticket_executors_table.join(
                        Ticket, Ticket.id == ticket_executors_table.c.ticket_id
                    )
                )
                .group_by(ticket_executors_table.c.user_id)
            )
        ).all()
        for uid, active, completed in exec_rows:
            entry = _entry(str(uid))
            entry["active"] = int(active or 0)
            entry["completed"] = int(completed or 0)

        return result

    async def get_by_status(
        self, status: TicketStatus, skip: int = 0, limit: int = 100
    ) -> tuple[list[Ticket], int]:
        """
        Get tickets by status.

        Args:
            status: Ticket status.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Tuple of (tickets list, total count).
        """
        query = select(Ticket).where(Ticket.status == status)
        count_query = select(func.count()).select_from(Ticket).where(
            Ticket.status == status
        )

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        tickets = list(result.scalars().all())

        return tickets, total

    async def get_by_creator(
        self, created_by_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[Ticket], int]:
        """
        Get tickets created by a specific user.

        Args:
            created_by_id: User UUID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Tuple of (tickets list, total count).
        """
        query = select(Ticket).where(Ticket.created_by_id == created_by_id)
        count_query = select(func.count()).select_from(Ticket).where(
            Ticket.created_by_id == created_by_id
        )

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        tickets = list(result.scalars().all())

        return tickets, total

    async def get_by_assigned_department(
        self, department_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[Ticket], int]:
        """
        Get tickets assigned to a specific department.

        Args:
            department_id: Department UUID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Tuple of (tickets list, total count).
        """
        query = select(Ticket).where(Ticket.assigned_department_id == department_id)
        count_query = select(func.count()).select_from(Ticket).where(
            Ticket.assigned_department_id == department_id
        )

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        tickets = list(result.scalars().all())

        return tickets, total

    async def exists_by_id(self, ticket_id: UUID) -> bool:
        """Check if ticket with ID exists."""
        ticket = await self.get_by_id(ticket_id)
        return ticket is not None

    async def exists_by_ticket_number(self, ticket_number: str) -> bool:
        """Check if ticket with ticket_number exists."""
        ticket = await self.get_by_ticket_number(ticket_number)
        return ticket is not None

    async def list_categories(self) -> list[TicketCategory]:
        """Return ticket categories ordered by name."""
        result = await self.session.execute(
            select(TicketCategory).order_by(TicketCategory.name)
        )
        return list(result.scalars().all())

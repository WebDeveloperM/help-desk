"""SLA service - deadline and status calculation by priority."""

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from app.core.enums import TicketPriority, TicketStatus
from app.sla.schemas import SlaConfig, SlaInfo, SlaPriorityRule, SlaStatus
from app.sla.schemas.sla import AT_RISK_FRACTION
from app.system.services import SystemService

if TYPE_CHECKING:
    from app.ticket.models import Ticket


def _utc_now() -> datetime:
    """Current UTC time."""
    return datetime.now(timezone.utc)


class SlaService:
    """Calculates planned completion date and SLA status from ticket priority and lifecycle."""

    def __init__(self, system_service: SystemService) -> None:
        """
        Initialize SLA service.

        Args:
            system_service: Service to read SLA hours from system_settings.
        """
        self.system_service = system_service
        self._hours_cache: dict[TicketPriority, int] | None = None

    async def _get_hours_by_priority(self) -> dict[TicketPriority, int]:
        # Memoize per SlaService instance. SlaService is constructed per request
        # via Depends, so this caches one read of system_settings per request.
        if self._hours_cache is None:
            self._hours_cache = await self.system_service.get_sla_hours_by_priority()
        return self._hours_cache

    async def get_sla_config(self) -> SlaConfig:
        """
        Load normalized SLA configuration for all priorities.

        Returns:
            SLA configuration with rules per priority.
        """
        hours_by_priority = await self._get_hours_by_priority()
        rules = [
            SlaPriorityRule(priority=priority, target_hours=hours)
            for priority, hours in hours_by_priority.items()
        ]
        return SlaConfig(rules=rules)

    async def compute_planned_completion_date(
        self,
        priority: TicketPriority,
        from_time: datetime | None = None,
    ) -> datetime:
        """
        Compute planned completion datetime from priority.

        Args:
            priority: Ticket priority.
            from_time: Start of SLA window (default: now UTC).

        Returns:
            planned_completion_date in UTC.
        """
        base = from_time if from_time is not None else _utc_now()
        if base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)
        hours_by_priority = await self._get_hours_by_priority()
        hours = hours_by_priority.get(priority, 48)
        return base + timedelta(hours=hours)

    async def compute_sla_info(self, ticket: "Ticket") -> SlaInfo:
        """
        Compute current SLA status and planned date for a ticket.

        For completed/closed tickets: completed_on_time vs completed_late.
        For active tickets: on_track, at_risk, or overdue based on now vs planned_completion_date.

        Args:
            ticket: Ticket model (with priority, status, planned_completion_date, etc.).

        Returns:
            SlaInfo with status and planned_completion_date.
        """
        planned = getattr(ticket, "planned_completion_date", None) or None
        status_enum = getattr(ticket, "status", None)
        actual_completion = getattr(ticket, "actual_completion_date", None) or getattr(
            ticket, "completed_at", None
        )
        now = _utc_now()

        completed_statuses = {TicketStatus.COMPLETED, TicketStatus.CLOSED}
        is_completed = status_enum in completed_statuses if status_enum else False

        if is_completed and actual_completion is not None and planned is not None:
            if actual_completion.tzinfo is None:
                actual_completion = actual_completion.replace(tzinfo=timezone.utc)
            sla_status = (
                SlaStatus.COMPLETED_ON_TIME
                if actual_completion <= planned
                else SlaStatus.COMPLETED_LATE
            )
            return SlaInfo(status=sla_status, planned_completion_date=planned)

        if is_completed:
            return SlaInfo(
                status=SlaStatus.COMPLETED_ON_TIME,
                planned_completion_date=planned,
            )

        if planned is None:
            return SlaInfo(status=SlaStatus.ON_TRACK, planned_completion_date=None)

        if planned.tzinfo is None:
            planned = planned.replace(tzinfo=timezone.utc)

        if now > planned:
            return SlaInfo(status=SlaStatus.OVERDUE, planned_completion_date=planned)

        # Active and not overdue: at_risk if less than 25% of original window remains
        assigned_at = getattr(ticket, "assigned_at", None) or getattr(
            ticket, "created_at", None
        )
        if assigned_at and planned:
            if getattr(assigned_at, "tzinfo", None) is None:
                assigned_at = assigned_at.replace(tzinfo=timezone.utc)
            total_seconds = (planned - assigned_at).total_seconds()
            remaining = (planned - now).total_seconds()
            if total_seconds > 0 and remaining <= total_seconds * AT_RISK_FRACTION:
                return SlaInfo(status=SlaStatus.AT_RISK, planned_completion_date=planned)

        return SlaInfo(status=SlaStatus.ON_TRACK, planned_completion_date=planned)

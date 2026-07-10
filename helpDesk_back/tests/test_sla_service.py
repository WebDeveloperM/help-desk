"""Unit tests for SLA service (deadline and status calculation)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.enums import TicketPriority, TicketStatus
from app.sla.schemas import SlaConfig, SlaStatus
from app.sla.services.sla_service import SlaService


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@pytest.fixture
def mock_system_service() -> MagicMock:
    """System service mock returning SLA hours."""
    svc = MagicMock()
    svc.get_sla_hours_by_priority = AsyncMock(
        return_value={
            TicketPriority.LOW: 72,
            TicketPriority.NORMAL: 48,
            TicketPriority.HIGH: 24,
            TicketPriority.URGENT: 8,
        }
    )
    return svc


@pytest.fixture
def sla_service(mock_system_service: MagicMock) -> SlaService:
    """SLA service with mocked system service."""
    return SlaService(mock_system_service)


@pytest.mark.asyncio
async def test_get_sla_config_returns_rules(
    sla_service: SlaService,
) -> None:
    """SLA config exposes normalized rules for every priority."""
    config = await sla_service.get_sla_config()

    assert isinstance(config, SlaConfig)
    assert len(config.rules) == 4
    assert {rule.priority for rule in config.rules} == set(TicketPriority)


@pytest.mark.asyncio
async def test_compute_planned_completion_date(
    sla_service: SlaService,
) -> None:
    """Planned completion is base time + hours for priority."""
    base = datetime(2026, 3, 5, 12, 0, 0, tzinfo=timezone.utc)
    planned = await sla_service.compute_planned_completion_date(
        TicketPriority.NORMAL,
        from_time=base,
    )
    assert planned == base + timedelta(hours=48)
    planned_low = await sla_service.compute_planned_completion_date(
        TicketPriority.LOW,
        from_time=base,
    )
    assert planned_low == base + timedelta(hours=72)


@pytest.mark.asyncio
async def test_compute_sla_info_completed_on_time(
    sla_service: SlaService,
) -> None:
    """Completed ticket with actual <= planned is completed_on_time."""
    planned = _utc(datetime(2026, 3, 10, 12, 0, 0))
    actual = _utc(datetime(2026, 3, 9, 10, 0, 0))
    ticket = SimpleNamespace(
        status=TicketStatus.COMPLETED,
        planned_completion_date=planned,
        actual_completion_date=actual,
        completed_at=actual,
        assigned_at=None,
        created_at=None,
    )
    info = await sla_service.compute_sla_info(ticket)
    assert info.status == SlaStatus.COMPLETED_ON_TIME
    assert info.planned_completion_date == planned


@pytest.mark.asyncio
async def test_compute_sla_info_completed_late(
    sla_service: SlaService,
) -> None:
    """Completed ticket with actual > planned is completed_late."""
    planned = _utc(datetime(2026, 3, 8, 12, 0, 0))
    actual = _utc(datetime(2026, 3, 10, 12, 0, 0))
    ticket = SimpleNamespace(
        status=TicketStatus.COMPLETED,
        planned_completion_date=planned,
        actual_completion_date=actual,
        completed_at=actual,
        assigned_at=None,
        created_at=None,
    )
    info = await sla_service.compute_sla_info(ticket)
    assert info.status == SlaStatus.COMPLETED_LATE
    assert info.planned_completion_date == planned


@pytest.mark.asyncio
async def test_compute_sla_info_at_risk(
    sla_service: SlaService,
) -> None:
    """Active ticket close to deadline is marked at_risk."""
    assigned = _utc(datetime(2026, 3, 1, 12, 0, 0))
    planned = _utc(datetime(2026, 3, 5, 12, 0, 0))
    ticket = SimpleNamespace(
        status=TicketStatus.IN_PROGRESS,
        planned_completion_date=planned,
        actual_completion_date=None,
        completed_at=None,
        assigned_at=assigned,
        created_at=assigned,
    )
    with patch(
        "app.sla.services.sla_service._utc_now",
        return_value=_utc(datetime(2026, 3, 4, 18, 0, 0)),
    ):
        info = await sla_service.compute_sla_info(ticket)

    assert info.status == SlaStatus.AT_RISK
    assert info.planned_completion_date == planned


@pytest.mark.asyncio
async def test_compute_sla_info_overdue(
    sla_service: SlaService,
) -> None:
    """Active ticket with now > planned is overdue."""
    planned = _utc(datetime(2026, 3, 1, 12, 0, 0))
    ticket = SimpleNamespace(
        status=TicketStatus.IN_PROGRESS,
        planned_completion_date=planned,
        actual_completion_date=None,
        completed_at=None,
        assigned_at=None,
        created_at=None,
    )
    with patch(
        "app.sla.services.sla_service._utc_now",
        return_value=_utc(datetime(2026, 3, 5, 12, 0, 0)),
    ):
        info = await sla_service.compute_sla_info(ticket)
    assert info.status == SlaStatus.OVERDUE
    assert info.planned_completion_date == planned


@pytest.mark.asyncio
async def test_compute_sla_info_on_track(
    sla_service: SlaService,
) -> None:
    """Active ticket with enough time left is on_track."""
    assigned = _utc(datetime(2026, 3, 1, 12, 0, 0))
    planned = _utc(datetime(2026, 3, 5, 12, 0, 0))
    ticket = SimpleNamespace(
        status=TicketStatus.ASSIGNED,
        planned_completion_date=planned,
        actual_completion_date=None,
        completed_at=None,
        assigned_at=assigned,
        created_at=assigned,
    )
    with patch(
        "app.sla.services.sla_service._utc_now",
        return_value=_utc(datetime(2026, 3, 2, 12, 0, 0)),
    ):
        info = await sla_service.compute_sla_info(ticket)
    assert info.status == SlaStatus.ON_TRACK
    assert info.planned_completion_date == planned


@pytest.mark.asyncio
async def test_compute_sla_info_no_planned_returns_on_track(
    sla_service: SlaService,
) -> None:
    """Ticket without planned_completion_date returns on_track and no planned date."""
    ticket = SimpleNamespace(
        status=TicketStatus.ASSIGNED,
        planned_completion_date=None,
        actual_completion_date=None,
        completed_at=None,
        assigned_at=None,
        created_at=None,
    )
    info = await sla_service.compute_sla_info(ticket)
    assert info.status == SlaStatus.ON_TRACK
    assert info.planned_completion_date is None


@pytest.mark.asyncio
async def test_sla_hours_fetched_once_per_instance(
    sla_service: SlaService,
    mock_system_service: MagicMock,
) -> None:
    """SLA hours are read from SystemService once per SlaService (request) regardless of how many callers ask."""
    base = datetime(2026, 3, 5, 12, 0, 0, tzinfo=timezone.utc)
    await sla_service.get_sla_config()
    await sla_service.compute_planned_completion_date(TicketPriority.HIGH, from_time=base)
    await sla_service.compute_planned_completion_date(TicketPriority.LOW, from_time=base)
    await sla_service.compute_planned_completion_date(TicketPriority.NORMAL, from_time=base)

    assert mock_system_service.get_sla_hours_by_priority.await_count == 1

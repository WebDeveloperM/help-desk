"""Unit tests for ticket service workflow rules."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.enums import TicketStatus
from app.ticket.exceptions import TicketStatusTransitionError, TicketValidationError
from app.ticket.schemas import TicketCreate
from app.ticket.services.ticket_service import TicketService


def _ticket(status: TicketStatus, executors: list | None = None) -> SimpleNamespace:
    """Build a minimal ticket-like object used by service tests."""
    return SimpleNamespace(
        id=uuid4(),
        ticket_number="HD-1",
        title="Test ticket",
        status=status,
        created_by_id=uuid4(),
        creator_department_id=uuid4(),
        assigned_by_user_id=uuid4(),
        created_at=None,
        updated_at=None,
        executors=executors or [],
        progress_percent=0,
    )


@pytest.fixture
def mock_repository() -> MagicMock:
    """Ticket repository mock."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.create = AsyncMock()
    repo.update = AsyncMock()
    repo.assign = AsyncMock()
    repo.start_progress = AsyncMock()
    repo.waiting_info = AsyncMock()
    repo.complete = AsyncMock()
    repo.close = AsyncMock()
    repo.list = AsyncMock()
    return repo


@pytest.fixture
def mock_user_repository() -> MagicMock:
    """User repository mock."""
    repo = MagicMock()
    repo.get_by_ids = AsyncMock()
    return repo


@pytest.fixture
def mock_notification_repository() -> MagicMock:
    """Notification repository mock."""
    return MagicMock()


@pytest.fixture
def service(
    mock_repository: MagicMock,
    mock_user_repository: MagicMock,
    mock_notification_repository: MagicMock,
) -> TicketService:
    """Ticket service with mocked dependencies."""
    return TicketService(
        mock_repository,
        mock_user_repository,
        mock_notification_repository,
    )


@pytest.mark.asyncio
async def test_complete_ticket_invalid_transition(
    service: TicketService,
    mock_repository: MagicMock,
) -> None:
    """Completing from ASSIGNED status is rejected."""
    ticket_id = uuid4()
    mock_repository.get_by_id.return_value = _ticket(TicketStatus.ASSIGNED)

    with pytest.raises(TicketStatusTransitionError):
        await service.complete_ticket(ticket_id, completed_by_id=uuid4())

    mock_repository.complete.assert_not_called()


@pytest.mark.asyncio
async def test_assign_ticket_reassignment_notifies_previous_executors(
    service: TicketService,
    mock_repository: MagicMock,
    mock_user_repository: MagicMock,
) -> None:
    """Reassigning in ASSIGNED state is allowed and includes previous executors."""
    old_executor_id = uuid4()
    new_executor_id = uuid4()
    department_id = uuid4()
    old_ticket = _ticket(
        TicketStatus.ASSIGNED,
        executors=[SimpleNamespace(id=old_executor_id)],
    )
    old_ticket.creator_department_id = department_id
    new_ticket = _ticket(
        TicketStatus.ASSIGNED,
        executors=[SimpleNamespace(id=new_executor_id)],
    )
    new_ticket.assigned_by_user_id = uuid4()
    mock_repository.get_by_id.return_value = old_ticket
    mock_repository.assign.return_value = new_ticket
    mock_user_repository.get_by_ids.return_value = [
        SimpleNamespace(
            id=new_executor_id,
            department_id=department_id,
            is_active=True,
        )
    ]

    with (
        patch(
            "app.ticket.services.ticket_service.create_notifications_for_ticket_assigned",
            new=AsyncMock(),
        ) as notify_mock,
        patch(
            "app.ticket.services.ticket_service.TicketResponse.model_validate",
            return_value=MagicMock(),
        ),
    ):
        await service.assign_ticket(
            ticket_id=uuid4(),
            assigned_department_id=department_id,
            assigned_by_user_id=uuid4(),
            executor_user_ids=[new_executor_id],
        )

    notify_mock.assert_awaited_once()
    notify_call = notify_mock.await_args.kwargs
    assert notify_call["previous_executor_ids"] == {old_executor_id}


@pytest.mark.asyncio
async def test_create_ticket_assigns_immediately(
    service: TicketService,
    mock_repository: MagicMock,
    mock_user_repository: MagicMock,
) -> None:
    """Creating a ticket sets assignment metadata immediately."""
    creator_id = uuid4()
    executor_id = uuid4()
    assigned_department_id = uuid4()
    mock_user_repository.get_by_ids.return_value = [
        SimpleNamespace(
            id=executor_id,
            department_id=assigned_department_id,
            is_active=True,
        )
    ]
    mock_repository.create.return_value = _ticket(
        TicketStatus.ASSIGNED,
        executors=[SimpleNamespace(id=executor_id)],
    )

    ticket_data = TicketCreate(
        title="Task",
        description="Task description",
        category_id=uuid4(),
        creator_department_id=assigned_department_id,
        assigned_department_id=assigned_department_id,
        executor_user_ids=[executor_id],
    )

    with (
        patch(
            "app.ticket.services.ticket_service.create_notifications_for_ticket_assigned",
            new=AsyncMock(),
        ),
        patch(
            "app.ticket.services.ticket_service.TicketResponse.model_validate",
            return_value=MagicMock(),
        ),
    ):
        await service.create_ticket(ticket_data, created_by_id=creator_id)

    create_call = mock_repository.create.await_args
    assert create_call.kwargs["assigned_by_user_id"] == creator_id
    assert create_call.kwargs["assigned_department_id"] == assigned_department_id


@pytest.mark.asyncio
async def test_create_ticket_rejects_cross_department_executor(
    service: TicketService,
    mock_user_repository: MagicMock,
) -> None:
    """Creating ticket for executor from another department is rejected."""
    creator_department_id = uuid4()
    executor_id = uuid4()
    mock_user_repository.get_by_ids.return_value = [
        SimpleNamespace(
            id=executor_id,
            department_id=uuid4(),
            is_active=True,
        )
    ]
    ticket_data = TicketCreate(
        title="Task",
        description="Task description",
        category_id=uuid4(),
        creator_department_id=creator_department_id,
        assigned_department_id=creator_department_id,
        executor_user_ids=[executor_id],
    )

    with pytest.raises(TicketValidationError):
        await service.create_ticket(ticket_data, created_by_id=uuid4())


@pytest.mark.asyncio
async def test_update_ticket_progress_validates_status(
    service: TicketService,
    mock_repository: MagicMock,
) -> None:
    """Progress update for draft ticket with non-zero value is rejected."""
    ticket_id = uuid4()
    mock_repository.get_by_id.return_value = _ticket(TicketStatus.DRAFT)

    with pytest.raises(TicketValidationError):
        await service.update_ticket_progress(ticket_id=ticket_id, progress_percent=10)


@pytest.mark.asyncio
async def test_create_ticket_with_sla_service_sets_planned_completion_date(
    mock_repository: MagicMock,
    mock_user_repository: MagicMock,
    mock_notification_repository: MagicMock,
) -> None:
    """When SLA service is injected, create_ticket passes planned_completion_date to repo."""
    from datetime import datetime, timezone
    from app.core.enums import TicketPriority
    from app.sla.services import SlaService

    creator_id = uuid4()
    executor_id = uuid4()
    assigned_department_id = uuid4()
    mock_user_repository.get_by_ids.return_value = [
        SimpleNamespace(
            id=executor_id,
            department_id=assigned_department_id,
            is_active=True,
        )
    ]
    planned = datetime(2026, 3, 7, 12, 0, 0, tzinfo=timezone.utc)
    mock_sla = MagicMock(spec=SlaService)
    mock_sla.compute_planned_completion_date = AsyncMock(return_value=planned)
    mock_sla.compute_sla_info = AsyncMock(
        return_value=MagicMock(status="on_track", planned_completion_date=planned)
    )

    service_with_sla = TicketService(
        mock_repository,
        mock_user_repository,
        mock_notification_repository,
        sla_service=mock_sla,
    )
    mock_repository.create.return_value = _ticket(
        TicketStatus.ASSIGNED,
        executors=[SimpleNamespace(id=executor_id)],
    )

    ticket_data = TicketCreate(
        title="Task",
        description="Task description",
        category_id=uuid4(),
        creator_department_id=assigned_department_id,
        assigned_department_id=assigned_department_id,
        executor_user_ids=[executor_id],
    )

    with patch(
        "app.ticket.services.ticket_service.create_notifications_for_ticket_assigned",
        new=AsyncMock(),
    ):
        await service_with_sla.create_ticket(ticket_data, created_by_id=creator_id)

    create_call = mock_repository.create.await_args
    assert create_call.kwargs.get("planned_completion_date") == planned
    assert create_call.kwargs.get("assigned_at") is not None


@pytest.mark.asyncio
async def test_get_ticket_with_sla_service_returns_sla_info(
    mock_repository: MagicMock,
    mock_user_repository: MagicMock,
    mock_notification_repository: MagicMock,
) -> None:
    """When SLA service is injected, get_ticket response includes sla block."""
    from app.sla.schemas import SlaInfo, SlaStatus
    from app.sla.services import SlaService

    ticket_id = uuid4()
    t = _ticket(TicketStatus.ASSIGNED)
    t.id = ticket_id
    mock_repository.get_by_id.return_value = t

    sla_info = SlaInfo(status=SlaStatus.ON_TRACK, planned_completion_date=None)
    mock_sla = MagicMock(spec=SlaService)
    mock_sla.compute_sla_info = AsyncMock(return_value=sla_info)

    service_with_sla = TicketService(
        mock_repository,
        mock_user_repository,
        mock_notification_repository,
        sla_service=mock_sla,
    )

    with patch(
        "app.ticket.services.ticket_service.TicketResponse.model_validate",
        return_value=MagicMock(),
    ):
        response = await service_with_sla.get_ticket(ticket_id)

    assert response.sla is not None
    assert response.sla.status == SlaStatus.ON_TRACK

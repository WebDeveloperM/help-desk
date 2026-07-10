"""Tests for notification module: recipient logic, deduplication, mark-read APIs, outbox retry."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock

try:
    from app.notification.outbox_publisher import next_retry_at
except ModuleNotFoundError:
    next_retry_at = None
from app.notification.services.notification_service import NotificationService
from app.notification.services.ticket_notifications import (
    _recipients_for_assignment,
    _recipients_for_status_change,
)


# ----- Ticket-like mocks for recipient logic -----


def _make_mock_executor(user_id):
    u = MagicMock()
    u.id = user_id
    return u


def test_recipients_for_assignment_excludes_actor() -> None:
    """Assignment recipients: creator/assigner/executors, excluding actor."""
    actor_id = uuid4()
    creator_id = uuid4()
    executor_id = uuid4()
    ticket = MagicMock()
    ticket.created_by_id = creator_id
    ticket.assigned_by_user_id = actor_id
    ticket.executors = [_make_mock_executor(executor_id)]
    recipients = _recipients_for_assignment(ticket, actor_id)
    assert recipients == {creator_id, executor_id}
    assert actor_id not in recipients


def test_recipients_for_assignment_includes_previous_executors() -> None:
    """Reassignment recipients include previous executors too."""
    actor_id = uuid4()
    creator_id = uuid4()
    assigner_id = uuid4()
    new_executor_id = uuid4()
    old_executor_id = uuid4()
    ticket = MagicMock()
    ticket.created_by_id = creator_id
    ticket.assigned_by_user_id = assigner_id
    ticket.executors = [_make_mock_executor(new_executor_id)]
    recipients = _recipients_for_assignment(
        ticket,
        actor_id,
        previous_executor_ids={old_executor_id},
    )
    assert recipients == {creator_id, assigner_id, new_executor_id, old_executor_id}


def test_recipients_for_status_change_includes_all_stakeholders() -> None:
    """Status change notifies creator, assigner, and executors (except actor)."""
    actor_id = uuid4()
    creator_id = uuid4()
    assigner_id = uuid4()
    executor_id = uuid4()
    ticket = MagicMock()
    ticket.created_by_id = creator_id
    ticket.executors = [_make_mock_executor(executor_id)]
    ticket.assigned_by_user_id = assigner_id
    recipients = _recipients_for_status_change(ticket, actor_id)
    assert recipients == {creator_id, assigner_id, executor_id}


def test_recipients_for_status_change_skip_self() -> None:
    """Status change: actor is never in recipients."""
    actor_id = uuid4()
    ticket = MagicMock()
    ticket.created_by_id = actor_id
    ticket.executors = []
    ticket.assigned_by_user_id = None
    recipients = _recipients_for_status_change(ticket, actor_id)
    assert actor_id not in recipients


# ----- next_retry_at (outbox retry) -----


@pytest.mark.skipif(next_retry_at is None, reason="aio_pika is not installed")
def test_next_retry_at_max_attempts() -> None:
    """next_retry_at returns None when attempts >= max_attempts."""
    assert next_retry_at(5, 5) is None
    assert next_retry_at(6, 5) is None


@pytest.mark.skipif(next_retry_at is None, reason="aio_pika is not installed")
def test_next_retry_at_exponential_backoff() -> None:
    """next_retry_at returns future time with increasing delay."""
    t0 = datetime.now(timezone.utc)
    t1 = next_retry_at(0, 5)
    t2 = next_retry_at(1, 5)
    assert t1 is not None
    assert t2 is not None
    assert t1 > t0
    assert t2 > t1
    assert (t1 - t0).total_seconds() >= 1
    assert (t2 - t0).total_seconds() >= 2


# ----- NotificationService (mark-read, list) with mocked repo -----


@pytest.fixture
def mock_notification_repo() -> AsyncMock:
    """Mock NotificationRepository for service tests."""
    return AsyncMock()


@pytest.fixture
def notification_service(mock_notification_repo: AsyncMock) -> NotificationService:
    """NotificationService with mocked repository."""
    return NotificationService(mock_notification_repo)


@pytest.mark.asyncio
async def test_mark_all_read_returns_count(
    notification_service: NotificationService,
    mock_notification_repo: AsyncMock,
) -> None:
    """mark_all_read calls repo and returns count."""
    mock_notification_repo.mark_all_read.return_value = 3
    user_id = uuid4()
    count = await notification_service.mark_all_read(user_id)
    assert count == 3
    mock_notification_repo.mark_all_read.assert_called_once_with(user_id)


@pytest.mark.asyncio
async def test_list_notifications_pagination(
    notification_service: NotificationService,
    mock_notification_repo: AsyncMock,
) -> None:
    """list_notifications calls repo with skip/limit and returns paginated response."""
    user_id = uuid4()
    mock_notification_repo.list_by_user_id.return_value = ([], 0)
    result = await notification_service.list_notifications(
        user_id=user_id,
        page=2,
        page_size=20,
    )
    assert result.total == 0
    assert len(result.items) == 0
    assert result.page == 2
    assert result.page_size == 20
    assert result.pages == 0
    mock_notification_repo.list_by_user_id.assert_called_once()
    call_kw = mock_notification_repo.list_by_user_id.call_args[1]
    assert call_kw["user_id"] == user_id
    assert call_kw["skip"] == 20
    assert call_kw["limit"] == 20


@pytest.mark.asyncio
async def test_mark_read_permission_denied(
    notification_service: NotificationService,
    mock_notification_repo: AsyncMock,
) -> None:
    """mark_read raises NotificationPermissionDeniedError when notification belongs to another user."""
    from app.notification.exceptions import NotificationPermissionDeniedError
    from app.notification.models import Notification

    notif_id = uuid4()
    owner_id = uuid4()
    current_user_id = uuid4()
    n = MagicMock(spec=Notification)
    n.id = notif_id
    n.user_id = owner_id
    mock_notification_repo.get_by_id.return_value = n
    with pytest.raises(NotificationPermissionDeniedError):
        await notification_service.mark_read(notif_id, current_user_id)
    mock_notification_repo.get_by_id.assert_called_once_with(notif_id)


@pytest.mark.asyncio
async def test_mark_read_not_found(
    notification_service: NotificationService,
    mock_notification_repo: AsyncMock,
) -> None:
    """mark_read raises NotificationNotFoundError when notification does not exist."""
    from app.notification.exceptions import NotificationNotFoundError

    mock_notification_repo.get_by_id.return_value = None
    with pytest.raises(NotificationNotFoundError):
        await notification_service.mark_read(uuid4(), uuid4())

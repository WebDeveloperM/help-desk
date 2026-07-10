"""Tests for ticket comments (schemas, service, notifications, HTTP API)."""

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.enums import NotificationType, TicketStatus
from app.notification.services.ticket_notifications import create_notifications_for_comment_added
from app.ticket.exceptions import TicketValidationError
from app.ticket.schemas.ticket_comment import (
    TicketCommentCreate,
    TicketCommentListResponse,
    TicketCommentResponse,
)
from app.ticket.services.ticket_comment_service import TicketCommentService

if TYPE_CHECKING:
    from app.config import Settings


def test_ticket_comment_create_rejects_empty_body() -> None:
    """Pydantic should reject empty comment body."""
    with pytest.raises(ValidationError):
        TicketCommentCreate(body="")


def test_ticket_comment_create_respects_max_length() -> None:
    """Body must not exceed 1000 characters."""
    TicketCommentCreate(body="x" * 1000)
    with pytest.raises(ValidationError):
        TicketCommentCreate(body="x" * 1001)


@pytest.mark.asyncio
async def test_create_notifications_for_comment_added_notifies_stakeholders_except_actor() -> None:
    """COMMENT_ADDED notifications go to creator/assigner/executors minus author."""
    creator_id = uuid4()
    assigner_id = uuid4()
    executor_id = uuid4()
    actor_id = creator_id
    comment_id = uuid4()
    ticket_id = uuid4()
    now = datetime.now(timezone.utc)

    exec_mock = MagicMock()
    exec_mock.id = executor_id

    ticket = SimpleNamespace(
        id=ticket_id,
        ticket_number="HD-1",
        title="Paper jam",
        status=TicketStatus.IN_PROGRESS,
        created_by_id=creator_id,
        assigned_by_user_id=assigner_id,
        created_at=now,
        updated_at=now,
        executors=[exec_mock],
    )

    notif_repo = MagicMock()
    notif = MagicMock()
    notif.id = uuid4()
    notif_repo.create = AsyncMock(return_value=notif)
    notif_repo.add_outbox = AsyncMock()

    await create_notifications_for_comment_added(
        notif_repo,
        ticket,
        actor_user_id=actor_id,
        comment_id=comment_id,
        actor_full_name="Author",
    )

    assert notif_repo.create.await_count == 2
    recipient_ids = {c.kwargs["user_id"] for c in notif_repo.create.await_args_list}
    assert recipient_ids == {assigner_id, executor_id}
    assert actor_id not in recipient_ids
    first_call = notif_repo.create.await_args_list[0]
    assert first_call.kwargs["notification_type"] == NotificationType.COMMENT_ADDED


@pytest.mark.asyncio
async def test_ticket_comment_service_rejects_whitespace_only() -> None:
    """Stripped empty body raises TicketValidationError."""
    comment_repo = MagicMock()
    notif_repo = MagicMock()
    service = TicketCommentService(comment_repo, notif_repo)

    ticket = SimpleNamespace(id=uuid4())
    author = SimpleNamespace(id=uuid4(), full_name="User")

    with pytest.raises(TicketValidationError, match="empty"):
        await service.create_comment(ticket, author, "   \n\t  ")


@pytest.mark.asyncio
async def test_ticket_comment_service_create_calls_repository_and_notifications() -> None:
    """Successful create persists comment and notifies stakeholders."""
    ticket_id = uuid4()
    author_id = uuid4()
    comment_id = uuid4()
    now = datetime.now(timezone.utc)

    ticket = SimpleNamespace(
        id=ticket_id,
        ticket_number="HD-99",
        title="Fix printer",
        status=TicketStatus.ASSIGNED,
        created_by_id=uuid4(),
        assigned_by_user_id=uuid4(),
        created_at=now,
        updated_at=now,
        executors=[],
    )
    author = SimpleNamespace(id=author_id, full_name="Bob")

    author_user = SimpleNamespace(id=author_id, full_name="Bob")
    comment_row = SimpleNamespace(
        id=comment_id,
        ticket_id=ticket_id,
        author_id=author_id,
        body="Please check toner",
        created_at=now,
        author=author_user,
    )

    comment_repo = MagicMock()
    comment_repo.create = AsyncMock(return_value=comment_row)
    notif_repo = MagicMock()

    service = TicketCommentService(comment_repo, notif_repo)

    with patch(
        "app.ticket.services.ticket_comment_service.create_notifications_for_comment_added",
        new_callable=AsyncMock,
    ) as mock_notify:
        result = await service.create_comment(ticket, author, "  Please check toner  ")

    comment_repo.create.assert_awaited_once_with(
        ticket_id=ticket_id,
        author_id=author_id,
        body="Please check toner",
    )
    mock_notify.assert_awaited_once()
    assert result.id == comment_id
    assert result.body == "Please check toner"
    assert result.author_full_name == "Bob"


@pytest.mark.asyncio
async def test_ticket_comment_service_list_pagination() -> None:
    """List response includes correct page metadata."""
    ticket_id = uuid4()
    now = datetime.now(timezone.utc)
    author = SimpleNamespace(full_name="Ann")
    c = SimpleNamespace(
        id=uuid4(),
        ticket_id=ticket_id,
        author_id=uuid4(),
        body="x",
        created_at=now,
        author=author,
    )
    comment_repo = MagicMock()
    comment_repo.list_by_ticket = AsyncMock(return_value=([c], 25))
    notif_repo = MagicMock()

    service = TicketCommentService(comment_repo, notif_repo)
    out = await service.list_comments(ticket_id, page=2, page_size=10)

    comment_repo.list_by_ticket.assert_awaited_once_with(ticket_id, skip=10, limit=10)
    assert out.total == 25
    assert out.page == 2
    assert out.page_size == 10
    assert out.pages == 3
    assert len(out.items) == 1


@pytest.fixture
def ticket_comment_client(
    settings: "Settings",
) -> tuple[TestClient, UUID, MagicMock]:
    """HTTP client with ticket/comment dependencies mocked (no database)."""
    from fastapi import FastAPI

    from app.ticket.dependencies.ticket_deps import (
        get_ticket_by_id_accessible,
        get_ticket_comment_service,
    )
    from app.ticket.routers.tickets import router as ticket_router
    from app.user.dependencies.auth import get_current_user_model

    ticket_id = uuid4()
    user_id = uuid4()
    dept_id = uuid4()
    now = datetime.now(timezone.utc)

    mock_ticket = MagicMock()
    mock_ticket.id = ticket_id
    mock_ticket.created_by_id = user_id
    mock_ticket.assigned_by_user_id = None
    mock_ticket.executors = []
    mock_ticket.creator_department_id = dept_id
    mock_ticket.assigned_department_id = dept_id

    async def override_accessible() -> MagicMock:
        return mock_ticket

    mock_user = MagicMock()
    mock_user.id = user_id
    mock_user.full_name = "API User"
    mock_user.department_id = dept_id

    async def override_user() -> MagicMock:
        return mock_user

    cid = uuid4()
    list_resp = TicketCommentListResponse(
        items=[
            TicketCommentResponse(
                id=cid,
                ticket_id=ticket_id,
                author_id=user_id,
                author_full_name="API User",
                body="thread message",
                created_at=now,
            )
        ],
        total=1,
        page=1,
        page_size=100,
        pages=1,
    )
    create_resp = TicketCommentResponse(
        id=uuid4(),
        ticket_id=ticket_id,
        author_id=user_id,
        author_full_name="API User",
        body="fresh",
        created_at=now,
    )

    mock_comment_svc = MagicMock()
    mock_comment_svc.list_comments = AsyncMock(return_value=list_resp)
    mock_comment_svc.create_comment = AsyncMock(return_value=create_resp)

    def override_comment_service() -> MagicMock:
        return mock_comment_svc

    app = FastAPI()
    app.include_router(ticket_router, prefix="/api/v1")
    app.dependency_overrides[get_ticket_by_id_accessible] = override_accessible
    app.dependency_overrides[get_ticket_comment_service] = override_comment_service
    app.dependency_overrides[get_current_user_model] = override_user

    with TestClient(app) as client:
        yield client, ticket_id, mock_comment_svc

    app.dependency_overrides.clear()


def test_ticket_comments_get_endpoint(
    ticket_comment_client: tuple[TestClient, UUID, MagicMock],
) -> None:
    """GET /tickets/{id}/comments returns paginated JSON."""
    client, ticket_id, mock_svc = ticket_comment_client
    response = client.get(f"/api/v1/tickets/{ticket_id}/comments")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["body"] == "thread message"
    mock_svc.list_comments.assert_awaited_once()


def test_ticket_comments_post_endpoint(
    ticket_comment_client: tuple[TestClient, UUID, MagicMock],
) -> None:
    """POST /tickets/{id}/comments creates a comment."""
    client, ticket_id, mock_svc = ticket_comment_client
    response = client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        json={"body": "Hello from test"},
    )
    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()
    assert body["body"] == "fresh"
    mock_svc.create_comment.assert_awaited_once()
    call = mock_svc.create_comment.await_args
    assert call.args[2] == "Hello from test"

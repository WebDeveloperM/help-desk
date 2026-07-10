"""Unit tests for ticket workflow role-gate dependencies (GAU-235).

These tests call the dep functions directly rather than going through the FastAPI
router. That keeps them fast and side-step the DB-connection problem we hit when
trying to exercise the router happy path against a stubbed-out database.
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.auth.schemas import TokenUser
from app.config import Settings
from app.ticket.dependencies.ticket_deps import (
    require_ticket_approver,
    require_ticket_closer,
    require_ticket_completer,
    require_ticket_executor,
)
from app.ticket.exceptions import TicketPermissionDeniedError


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://t:t@localhost/t",
        jwt_secret="test-secret-key",
    )


def _token_user(roles: list[str]) -> TokenUser:
    return TokenUser(
        sub="u1",
        email="t@example.com",
        preferred_username="t",
        realm_access={"roles": roles},
        email_verified=True,
        exp=9999999999,
        iat=1234567800,
    )


def _stub_ticket(*, created_by_id, executor_ids):
    """Minimal stand-in for Ticket — only the attributes the gates read."""
    return SimpleNamespace(
        created_by_id=created_by_id,
        executors=[SimpleNamespace(id=eid) for eid in executor_ids],
    )


def _stub_user(user_id):
    """Minimal stand-in for User — only `id` is read by the gates."""
    return SimpleNamespace(id=user_id, department_id=uuid4())


# ---------------------------------------------------------------------------
# require_ticket_approver — approve / reject / assign require admin or department_head
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approver_denies_plain_user() -> None:
    ticket = _stub_ticket(created_by_id=uuid4(), executor_ids=[])
    with pytest.raises(TicketPermissionDeniedError) as exc:
        await require_ticket_approver(
            ticket=ticket,
            token_user=_token_user(["user"]),
            settings=_settings(),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_approver_allows_admin() -> None:
    ticket = _stub_ticket(created_by_id=uuid4(), executor_ids=[])
    result = await require_ticket_approver(
        ticket=ticket,
        token_user=_token_user(["admin"]),
        settings=_settings(),
    )
    assert result is ticket


@pytest.mark.asyncio
async def test_approver_allows_department_head() -> None:
    ticket = _stub_ticket(created_by_id=uuid4(), executor_ids=[])
    result = await require_ticket_approver(
        ticket=ticket,
        token_user=_token_user(["department_head"]),
        settings=_settings(),
    )
    assert result is ticket


# ---------------------------------------------------------------------------
# require_ticket_executor — start-progress / progress require executor membership
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_executor_denies_non_executor() -> None:
    user_id = uuid4()
    ticket = _stub_ticket(created_by_id=uuid4(), executor_ids=[uuid4()])
    with pytest.raises(TicketPermissionDeniedError) as exc:
        await require_ticket_executor(
            ticket=ticket,
            current_user=_stub_user(user_id),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_executor_allows_assigned_executor() -> None:
    user_id = uuid4()
    ticket = _stub_ticket(created_by_id=uuid4(), executor_ids=[user_id])
    result = await require_ticket_executor(
        ticket=ticket,
        current_user=_stub_user(user_id),
    )
    assert result is ticket


# ---------------------------------------------------------------------------
# require_ticket_completer — waiting-info / complete: executor OR department_head/admin
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_completer_denies_plain_user_who_is_not_executor() -> None:
    user_id = uuid4()
    ticket = _stub_ticket(created_by_id=uuid4(), executor_ids=[uuid4()])
    with pytest.raises(TicketPermissionDeniedError) as exc:
        await require_ticket_completer(
            ticket=ticket,
            current_user=_stub_user(user_id),
            token_user=_token_user(["user"]),
            settings=_settings(),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_completer_allows_executor_even_without_role() -> None:
    """Executor of the ticket should pass even with only the plain `user` role."""
    user_id = uuid4()
    ticket = _stub_ticket(created_by_id=uuid4(), executor_ids=[user_id])
    result = await require_ticket_completer(
        ticket=ticket,
        current_user=_stub_user(user_id),
        token_user=_token_user(["user"]),
        settings=_settings(),
    )
    assert result is ticket


@pytest.mark.asyncio
async def test_completer_allows_department_head_who_is_not_executor() -> None:
    """department_head should pass even when not assigned as executor."""
    ticket = _stub_ticket(created_by_id=uuid4(), executor_ids=[uuid4()])
    result = await require_ticket_completer(
        ticket=ticket,
        current_user=_stub_user(uuid4()),
        token_user=_token_user(["department_head"]),
        settings=_settings(),
    )
    assert result is ticket


# ---------------------------------------------------------------------------
# require_ticket_closer — close / PATCH: creator OR department_head/admin
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_closer_denies_plain_user_who_is_not_creator() -> None:
    ticket = _stub_ticket(created_by_id=uuid4(), executor_ids=[])
    with pytest.raises(TicketPermissionDeniedError) as exc:
        await require_ticket_closer(
            ticket=ticket,
            current_user=_stub_user(uuid4()),
            token_user=_token_user(["user"]),
            settings=_settings(),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_closer_allows_creator_even_without_role() -> None:
    """The ticket's creator should pass with only the plain `user` role."""
    user_id = uuid4()
    ticket = _stub_ticket(created_by_id=user_id, executor_ids=[])
    result = await require_ticket_closer(
        ticket=ticket,
        current_user=_stub_user(user_id),
        token_user=_token_user(["user"]),
        settings=_settings(),
    )
    assert result is ticket


@pytest.mark.asyncio
async def test_closer_allows_admin_who_is_not_creator() -> None:
    """admin should pass even when not the creator."""
    ticket = _stub_ticket(created_by_id=uuid4(), executor_ids=[])
    result = await require_ticket_closer(
        ticket=ticket,
        current_user=_stub_user(uuid4()),
        token_user=_token_user(["admin"]),
        settings=_settings(),
    )
    assert result is ticket

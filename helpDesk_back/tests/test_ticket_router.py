"""Unit tests for ticket router request/response wiring."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.ticket.routers.tickets import get_ticket_endpoint
from app.ticket.schemas import TicketUpdateRequest


@pytest.mark.asyncio
async def test_get_ticket_endpoint_uses_service_response() -> None:
    """Ticket detail endpoint should return the SLA-enriched service response."""
    ticket_id = uuid4()
    ticket = SimpleNamespace(id=ticket_id)
    service = AsyncMock()
    expected_response = object()
    service.get_ticket.return_value = expected_response

    response = await get_ticket_endpoint(ticket=ticket, service=service)

    service.get_ticket.assert_awaited_once_with(ticket_id)
    assert response is expected_response


def test_ticket_update_request_rejects_planned_completion_date() -> None:
    """Clients must not send SLA-managed planned completion values."""
    with pytest.raises(ValidationError):
        TicketUpdateRequest.model_validate(
            {"planned_completion_date": "2026-03-10T10:00:00Z"}
        )

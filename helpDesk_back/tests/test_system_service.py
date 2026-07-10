"""Unit tests for system service (read-only system_settings)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.enums import TicketPriority
from app.system.services.system_service import (
    DEFAULT_SLA_HOURS,
    SystemService,
)


@pytest.fixture
def mock_system_repository() -> MagicMock:
    """System repository mock."""
    repo = MagicMock()
    repo.get_value = AsyncMock()
    repo.get_values_by_keys = AsyncMock()
    return repo


@pytest.fixture
def system_service(mock_system_repository: MagicMock) -> SystemService:
    """System service with mocked repository."""
    return SystemService(mock_system_repository)


@pytest.mark.asyncio
async def test_get_sla_hours_by_priority_uses_defaults_when_empty(
    system_service: SystemService,
    mock_system_repository: MagicMock,
) -> None:
    """When system_settings has no SLA keys, defaults are returned."""
    mock_system_repository.get_values_by_keys.return_value = {}

    result = await system_service.get_sla_hours_by_priority()

    assert result == DEFAULT_SLA_HOURS
    for p in TicketPriority:
        assert result[p] == DEFAULT_SLA_HOURS[p]


@pytest.mark.asyncio
async def test_get_sla_hours_by_priority_uses_stored_values(
    system_service: SystemService,
    mock_system_repository: MagicMock,
) -> None:
    """When system_settings has SLA keys, stored values are used."""
    mock_system_repository.get_values_by_keys.return_value = {
        "sla.low.hours": "96",
        "sla.normal.hours": "48",
        "sla.high.hours": "12",
        "sla.urgent.hours": "4",
    }

    result = await system_service.get_sla_hours_by_priority()

    assert result[TicketPriority.LOW] == 96
    assert result[TicketPriority.NORMAL] == 48
    assert result[TicketPriority.HIGH] == 12
    assert result[TicketPriority.URGENT] == 4


@pytest.mark.asyncio
async def test_get_sla_hours_by_priority_invalid_value_falls_back(
    system_service: SystemService,
    mock_system_repository: MagicMock,
) -> None:
    """Invalid or non-positive values fall back to default."""
    mock_system_repository.get_values_by_keys.return_value = {
        "sla.low.hours": "invalid",
        "sla.normal.hours": "0",
        "sla.high.hours": "-1",
        "sla.urgent.hours": " 24 ",
    }

    result = await system_service.get_sla_hours_by_priority()

    assert result[TicketPriority.LOW] == DEFAULT_SLA_HOURS[TicketPriority.LOW]
    assert result[TicketPriority.NORMAL] == DEFAULT_SLA_HOURS[TicketPriority.NORMAL]
    assert result[TicketPriority.HIGH] == DEFAULT_SLA_HOURS[TicketPriority.HIGH]
    assert result[TicketPriority.URGENT] == 24

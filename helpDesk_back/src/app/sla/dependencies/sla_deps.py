"""SLA dependencies for dependency injection."""

from typing import Annotated

from fastapi import Depends

from app.sla.services import SlaService
from app.system.dependencies import get_system_service
from app.system.services import SystemService


def get_sla_service(
    system_service: Annotated[SystemService, Depends(get_system_service)],
) -> SlaService:
    """
    Get SLA service instance.

    Args:
        system_service: System service (for SLA hours from system_settings).

    Returns:
        SLA service.
    """
    return SlaService(system_service)

"""System service - read-only access to system settings."""

from app.core.enums import TicketPriority
from app.system.repositories import SystemRepository

SLA_HOURS_KEYS: dict[TicketPriority, str] = {
    TicketPriority.LOW: "sla.low.hours",
    TicketPriority.NORMAL: "sla.normal.hours",
    TicketPriority.HIGH: "sla.high.hours",
    TicketPriority.URGENT: "sla.urgent.hours",
}

DEFAULT_SLA_HOURS: dict[TicketPriority, int] = {
    TicketPriority.LOW: 72,
    TicketPriority.NORMAL: 48,
    TicketPriority.HIGH: 24,
    TicketPriority.URGENT: 8,
}


class SystemService:
    """Read-only service for system settings (e.g. SLA configuration)."""

    def __init__(self, repository: SystemRepository) -> None:
        """
        Initialize system service.

        Args:
            repository: System settings repository.
        """
        self.repository = repository

    async def get_setting(self, key: str) -> str | None:
        """
        Get raw setting value by key.

        Args:
            key: Setting key.

        Returns:
            Value if found, None otherwise.
        """
        return await self.repository.get_value(key)

    async def get_sla_hours_by_priority(self) -> dict[TicketPriority, int]:
        """
        Get SLA hours per ticket priority from system_settings.

        Uses keys: sla.low.hours, sla.normal.hours, sla.high.hours, sla.urgent.hours.
        Missing or invalid values fall back to DEFAULT_SLA_HOURS.

        Returns:
            Map of TicketPriority -> hours (positive integers).
        """
        keys = [SLA_HOURS_KEYS[p] for p in TicketPriority]
        raw = await self.repository.get_values_by_keys(keys)
        result: dict[TicketPriority, int] = {}
        for priority in TicketPriority:
            key = SLA_HOURS_KEYS[priority]
            val = raw.get(key)
            if val is not None:
                try:
                    hours = int(val.strip())
                    if hours > 0:
                        result[priority] = hours
                        continue
                except ValueError:
                    pass
            result[priority] = DEFAULT_SLA_HOURS[priority]
        return result

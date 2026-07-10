"""System repository protocol."""

from typing import Protocol


class SystemRepository(Protocol):
    """Protocol for system settings storage."""

    async def get_value(self, key: str) -> str | None:
        """
        Get setting value by key.

        Args:
            key: Setting key.

        Returns:
            Value if found, None otherwise.
        """
        ...

    async def get_values_by_keys(self, keys: list[str]) -> dict[str, str | None]:
        """
        Get multiple setting values by keys.

        Args:
            keys: List of setting keys.

        Returns:
            Map of key -> value (missing keys may be absent or None).
        """
        ...

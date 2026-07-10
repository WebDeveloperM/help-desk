"""System repository - read-only access to system_settings."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.system.models import SystemSetting


class SQLAlchemySystemRepository:
    """SQLAlchemy-based read-only repository for system_settings."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize system repository.

        Args:
            session: Database session.
        """
        self.session = session

    async def get_value(self, key: str) -> str | None:
        """
        Get setting value by key.

        Args:
            key: Setting key.

        Returns:
            Value if found, None otherwise.
        """
        result = await self.session.execute(
            select(SystemSetting.value).where(SystemSetting.key == key)
        )
        row = result.scalar_one_or_none()
        return row

    async def get_values_by_keys(self, keys: list[str]) -> dict[str, str | None]:
        """
        Get multiple setting values by keys.

        Args:
            keys: List of setting keys.

        Returns:
            Map of key -> value. Keys not found have value None.
        """
        if not keys:
            return {}
        result = await self.session.execute(
            select(SystemSetting.key, SystemSetting.value).where(
                SystemSetting.key.in_(keys)
            )
        )
        return {row[0]: row[1] for row in result.all()}

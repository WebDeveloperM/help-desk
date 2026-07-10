"""Asset repository abstraction."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.asset.models import Asset
from app.asset.schemas import AssetCreate, AssetFilterParams, AssetUpdate


class AssetRepository(Protocol):
    """Repository interface for asset persistence operations."""

    async def get_by_id(self, asset_id: UUID) -> Asset | None:
        """Return an asset by ID with relationships loaded."""

    async def get_by_ids(self, asset_ids: list[UUID]) -> list[Asset]:
        """Return assets by IDs."""

    async def get_by_inventory_number(self, inventory_number: str) -> Asset | None:
        """Return asset by unique inventory number."""

    async def create(
        self,
        asset_data: AssetCreate,
        embedding: list[float],
    ) -> Asset:
        """Persist a new asset."""

    async def update(
        self,
        asset_id: UUID,
        asset_data: AssetUpdate,
        embedding: list[float] | None = None,
    ) -> Asset | None:
        """Partially update an asset."""

    async def soft_delete(self, asset_id: UUID) -> Asset | None:
        """Soft-delete an asset by setting is_active=False."""

    async def list_with_cursor(
        self,
        filters: AssetFilterParams,
        *,
        restrict_department_id: UUID | None,
        similarity_embedding: list[float] | None,
        cursor_value: str | None,
        cursor_id: UUID | None,
    ) -> tuple[list[Asset], str | None, UUID | None]:
        """Return cursor-based assets and metadata for next cursor."""

    async def append_image_url(self, asset_id: UUID, image_url: str) -> Asset | None:
        """Append image URL to asset and return updated model."""

    async def remove_image_url(self, asset_id: UUID, image_url: str) -> Asset | None:
        """Remove image URL from asset and return updated model."""

    async def has_active_repair_ticket(
        self,
        asset_id: UUID,
        exclude_ticket_id: UUID | None = None,
    ) -> bool:
        """Check whether asset has an active repair ticket."""

    async def set_ticket_assets(self, ticket_id: UUID, asset_ids: list[UUID]) -> None:
        """Replace ticket-asset links for ticket."""

    async def add_ticket_assets(self, ticket_id: UUID, asset_ids: list[UUID]) -> None:
        """Add ticket-asset links and skip duplicates."""

    async def remove_ticket_asset(self, ticket_id: UUID, asset_id: UUID) -> None:
        """Remove single ticket-asset link."""

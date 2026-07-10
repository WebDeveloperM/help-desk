"""Asset service abstraction."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from fastapi import UploadFile

from app.asset.models import Asset
from app.asset.schemas import (
    AssetCreate,
    AssetCursorPageResponse,
    AssetFilterParams,
    AssetResponse,
    AssetUpdate,
)
from app.auth.schemas import TokenUser
from app.user.models import User


class AssetService(Protocol):
    """Service interface for asset business logic."""

    async def get_by_id(self, asset_id: UUID) -> Asset | None:
        """Return asset entity by ID."""

    async def get_asset(
        self,
        asset_id: UUID,
        *,
        current_user: User,
        token_user: TokenUser,
    ) -> AssetResponse:
        """Return asset response by ID."""

    async def create_asset(
        self,
        asset_data: AssetCreate,
        *,
        current_user: User,
        token_user: TokenUser,
    ) -> AssetResponse:
        """Create a new asset."""

    async def update_asset(
        self,
        asset_id: UUID,
        asset_data: AssetUpdate,
        *,
        current_user: User,
        token_user: TokenUser,
    ) -> AssetResponse:
        """Update an existing asset."""

    async def delete_asset(
        self,
        asset_id: UUID,
        *,
        current_user: User,
        token_user: TokenUser,
    ) -> AssetResponse:
        """Soft-delete asset."""

    async def list_assets(
        self,
        filters: AssetFilterParams,
        *,
        current_user: User,
        token_user: TokenUser,
    ) -> AssetCursorPageResponse:
        """Return cursor-based asset list."""

    async def upload_asset_image(
        self,
        asset_id: UUID,
        file: UploadFile,
        *,
        current_user: User,
        token_user: TokenUser,
    ) -> str:
        """Upload image for asset and return URL."""

    async def delete_asset_image(
        self,
        asset_id: UUID,
        image_url: str,
        *,
        current_user: User,
        token_user: TokenUser,
    ) -> AssetResponse:
        """Delete image from storage and from asset URL list."""

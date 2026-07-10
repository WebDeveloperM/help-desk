"""Asset Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AssetLifecycleStatus, TicketStatus


AssetSortField = Literal["name", "status"]
SortOrder = Literal["asc", "desc"]


class AssetBase(BaseModel):
    """Base schema with common asset fields."""

    name: str = Field(..., min_length=1, max_length=255)
    asset_type: str = Field(..., min_length=1, max_length=100)
    inventory_number: str = Field(..., min_length=1, max_length=100)
    serial_number: str | None = Field(None, max_length=100)
    department_id: UUID
    assigned_user_id: UUID | None = None
    status: AssetLifecycleStatus = AssetLifecycleStatus.ACTIVE
    location: str | None = Field(None, max_length=255)
    purchase_date: datetime | None = None
    warranty_until: datetime | None = None
    notes: str | None = None


class AssetCreate(AssetBase):
    """Schema for creating an asset."""


class AssetUpdate(BaseModel):
    """Schema for partially updating an asset."""

    name: str | None = Field(None, min_length=1, max_length=255)
    asset_type: str | None = Field(None, min_length=1, max_length=100)
    inventory_number: str | None = Field(None, min_length=1, max_length=100)
    serial_number: str | None = Field(None, max_length=100)
    department_id: UUID | None = None
    assigned_user_id: UUID | None = None
    status: AssetLifecycleStatus | None = None
    location: str | None = Field(None, max_length=255)
    purchase_date: datetime | None = None
    warranty_until: datetime | None = None
    notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class AssetOwnerInfo(BaseModel):
    """Owner info in asset response."""

    id: UUID
    full_name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class AssetDepartmentInfo(BaseModel):
    """Department info in asset response."""

    id: UUID
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class AssetTicketInfo(BaseModel):
    """Ticket info in asset response."""

    id: UUID
    ticket_number: str
    title: str
    status: TicketStatus

    model_config = ConfigDict(from_attributes=True)


class AssetResponse(AssetBase):
    """Schema for asset response."""

    id: UUID
    image_urls: list[str] = Field(default_factory=list)
    is_active: bool
    created_at: datetime
    updated_at: datetime
    assigned_user: AssetOwnerInfo | None = None
    department: AssetDepartmentInfo | None = None
    tickets: list[AssetTicketInfo] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class AssetFilterParams(BaseModel):
    """Asset filtering params for list endpoint."""

    asset_type: str | None = None
    status: AssetLifecycleStatus | None = None
    department_id: UUID | None = None
    search: str | None = None
    similarity_query: str | None = None
    include_inactive: bool = False
    sort_by: AssetSortField = "name"
    sort_order: SortOrder = "asc"
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = None


class AssetCursorPageResponse(BaseModel):
    """Cursor-based asset list response."""

    items: list[AssetResponse]
    next_cursor: str | None = None
    has_more: bool


class AssetImageUploadResponse(BaseModel):
    """Image upload response."""

    image_url: str


class AssetImageDeleteRequest(BaseModel):
    """Image delete request."""

    image_url: str = Field(..., min_length=1)


class TicketAssetAttachRequest(BaseModel):
    """Request payload for attaching assets to a ticket."""

    asset_ids: list[UUID] = Field(..., min_length=1)

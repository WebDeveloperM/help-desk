"""Ticket Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import AssetLifecycleStatus, TicketPriority, TicketStatus
from app.sla.schemas import SlaInfo


class TicketBase(BaseModel):
    """Base ticket schema with common fields."""

    title: str = Field(..., min_length=1, max_length=500, description="Ticket title")
    description: str = Field(..., min_length=1, description="Ticket description")
    category_id: UUID = Field(..., description="Ticket category ID")
    template_id: UUID | None = Field(None, description="Ticket template ID")
    priority: TicketPriority = Field(
        default=TicketPriority.NORMAL, description="Ticket priority"
    )
    desired_completion_date: datetime | None = Field(
        None, description="Desired completion date"
    )
    ticket_metadata: dict[str, Any] | None = Field(
        None,
        description="Additional metadata",
        validation_alias="metadata",
    )

    model_config = ConfigDict(populate_by_name=True)


class TicketCreate(TicketBase):
    """Schema for creating a new ticket."""

    creator_department_id: UUID = Field(
        ..., description="Department ID of the ticket creator"
    )
    assigned_department_id: UUID | None = Field(
        None,
        description="Optional department assignment for the ticket",
    )
    executor_user_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="Executor user IDs assigned immediately on create",
    )
    asset_ids: list[UUID] | None = Field(
        None,
        description="Optional asset IDs linked to ticket",
    )


class TicketUpdateRequest(BaseModel):
    """Public schema for updating ticket (partial update)."""

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, min_length=1)
    category_id: UUID | None = None
    template_id: UUID | None = None
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assigned_department_id: UUID | None = None
    desired_completion_date: datetime | None = None
    ticket_metadata: dict[str, Any] | None = Field(
        None,
        validation_alias="metadata",
        description="Additional metadata",
    )
    is_urgent: bool | None = None
    progress_percent: int | None = Field(
        None,
        ge=0,
        le=100,
        description="Implementation progress percentage [0..100]",
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class TicketUpdate(TicketUpdateRequest):
    """Internal update schema that allows service-managed SLA fields."""

    planned_completion_date: datetime | None = None


class TicketApproveRequest(BaseModel):
    """Schema for approving a ticket."""

    comment: str | None = Field(None, max_length=1000, description="Approver comment")


class TicketRejectRequest(BaseModel):
    """Schema for rejecting a ticket."""

    comment: str = Field(..., min_length=1, max_length=1000, description="Rejection reason")


class TicketAssignRequest(BaseModel):
    """Schema for assigning a ticket."""

    department_id: UUID | None = Field(
        None, description="Optional department to assign ticket to"
    )
    executor_user_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="Specific executor user IDs",
    )


class TicketCompleteRequest(BaseModel):
    """Schema for completing a ticket."""

    comment: str | None = Field(None, max_length=1000, description="Completion comment")


class TicketProgressUpdateRequest(BaseModel):
    """Schema for updating ticket implementation progress."""

    progress_percent: int = Field(
        ...,
        ge=0,
        le=100,
        description="Implementation progress percentage [0..100]",
    )


class TicketWaitingInfoRequest(BaseModel):
    """Schema for moving ticket to waiting info state."""

    comment: str | None = Field(
        None,
        max_length=1000,
        description="Optional note why more information is required",
    )


class TicketCloseRequest(BaseModel):
    """Schema for closing a ticket."""

    comment: str | None = Field(None, max_length=1000, description="Closure comment")


class TicketUserInfo(BaseModel):
    """Schema for user information in ticket response."""

    id: UUID
    full_name: str
    email: str

    model_config = {"from_attributes": True}


class TicketDepartmentInfo(BaseModel):
    """Schema for department information in ticket response."""

    id: UUID
    name: str
    code: str

    model_config = {"from_attributes": True}


class TicketAssetInfo(BaseModel):
    """Schema for asset information in ticket response."""

    id: UUID
    name: str
    inventory_number: str
    asset_type: str
    status: AssetLifecycleStatus
    is_active: bool

    model_config = {"from_attributes": True}


class TicketResponse(TicketBase):
    """Schema for ticket response.

    Overrides ticket_metadata: no validation_alias (avoids SQLAlchemy ticket.metadata),
    serialization_alias="metadata" for JSON. Validator coerces non-dict to None.
    """

    ticket_metadata: dict[str, Any] | None = Field(
        None,
        description="Additional metadata",
        serialization_alias="metadata",
    )
    id: UUID
    ticket_number: str
    status: TicketStatus
    created_by_id: UUID
    creator_department_id: UUID
    assigned_department_id: UUID | None = None
    assigned_by_user_id: UUID | None = None
    approver_user_id: UUID | None = None
    completed_by_id: UUID | None = None
    closed_by_id: UUID | None = None
    approved_at: datetime | None = None
    assigned_at: datetime | None = None
    planned_completion_date: datetime | None = None
    actual_completion_date: datetime | None = None
    completed_at: datetime | None = None
    closed_at: datetime | None = None
    approver_comment: str | None = None
    completion_comment: str | None = None
    closed_comment: str | None = None
    is_urgent: bool
    progress_percent: int = Field(
        ...,
        ge=0,
        le=100,
        description="Implementation progress percentage [0..100]",
    )
    created_at: datetime
    updated_at: datetime

    # Optional related objects (loaded when needed)
    created_by: TicketUserInfo | None = None
    creator_department: TicketDepartmentInfo | None = None
    assigned_department: TicketDepartmentInfo | None = None
    approver: TicketUserInfo | None = None
    assigned_by: TicketUserInfo | None = None
    completed_by: TicketUserInfo | None = None
    closed_by: TicketUserInfo | None = None
    executors: list[TicketUserInfo] = Field(
        default_factory=list,
        description="Assigned executor users",
    )
    assets: list[TicketAssetInfo] = Field(
        default_factory=list,
        description="Linked assets",
    )
    sla: SlaInfo | None = Field(
        default=None,
        description="SLA status and planned completion (computed)",
    )

    @field_validator("ticket_metadata", mode="before")
    @classmethod
    def _coerce_metadata_dict(cls, v: Any) -> dict[str, Any] | None:
        """Accept only dict; ORM may expose SQLAlchemy MetaData as 'metadata'."""
        if isinstance(v, dict):
            return v
        return None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TicketListResponse(BaseModel):
    """Schema for paginated ticket list response."""

    items: list[TicketResponse]
    total: int
    page: int
    page_size: int
    pages: int


class TicketCategoryResponse(BaseModel):
    """Schema for ticket category (list)."""

    id: UUID
    name: str
    code: str | None

    model_config = {"from_attributes": True}


class TicketFilterParams(BaseModel):
    """Schema for ticket filtering parameters."""

    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    category_id: UUID | None = None
    created_by_id: UUID | None = None
    creator_department_id: UUID | None = None
    assigned_department_id: UUID | None = None
    is_urgent: bool | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    search: str | None = None


class StatusCount(BaseModel):
    """Ticket count for one status."""

    status: str
    count: int


class PriorityCount(BaseModel):
    """Ticket count for one priority."""

    priority: str
    count: int


class CategoryCount(BaseModel):
    """Ticket count for one category (top categories)."""

    category_id: str
    name: str
    count: int


class ThroughputPoint(BaseModel):
    """Created vs completed tickets for a single day."""

    date: str
    created: int
    completed: int


class TicketStatsResponse(BaseModel):
    """Aggregated ticket analytics for the Reports dashboard (department-scoped)."""

    total: int
    open: int
    in_progress: int
    completed: int
    closed: int
    overdue: int
    urgent_open: int
    created_last_7d: int
    completed_last_7d: int
    avg_resolution_hours: float | None
    sla_compliance_pct: float | None
    by_status: list[StatusCount]
    by_priority: list[PriorityCount]
    by_category: list[CategoryCount]
    throughput: list[ThroughputPoint]

"""Department Pydantic schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DepartmentBase(BaseModel):
    """Base department schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Department name")
    name_uz: str | None = Field(None, max_length=255, description="Department name in Uzbek")
    code: str = Field(..., min_length=1, max_length=50, description="Department code")
    parent_id: UUID | None = Field(None, description="Parent department ID")
    head_user_id: UUID | None = Field(None, description="Department head user ID")
    ad_path: str | None = Field(None, description="Active Directory path")
    is_active: bool = Field(default=True, description="Whether department is active")


class DepartmentCreate(DepartmentBase):
    """Schema for creating a new department."""

    pass


class DepartmentUpdate(BaseModel):
    """Schema for updating department (partial update)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    name_uz: str | None = Field(None, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=50)
    parent_id: UUID | None = None
    head_user_id: UUID | None = None
    ad_path: str | None = None
    is_active: bool | None = None


class DepartmentUserInfo(BaseModel):
    """Schema for user information in department response."""

    id: UUID
    full_name: str
    email: str

    model_config = {"from_attributes": True}


class DepartmentInfo(BaseModel):
    """Schema for department information in nested responses."""

    id: UUID
    number: int
    name: str
    code: str

    model_config = {"from_attributes": True}


class DepartmentResponse(BaseModel):
    """Schema for department response."""

    id: UUID
    number: int
    name: str
    name_uz: str | None
    code: str
    parent_id: UUID | None
    parent: DepartmentInfo | None = None
    head_user_id: UUID | None
    head_user: DepartmentUserInfo | None = None
    ad_path: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DepartmentListResponse(BaseModel):
    """Schema for paginated department list response."""

    items: list[DepartmentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

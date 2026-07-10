"""User Pydantic schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.core.enums import Role


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    full_name_uz: str | None = Field(None, max_length=255)
    tabel_number: str | None = Field(None, max_length=50)
    ad_username: str | None = Field(None, max_length=100)
    department_id: UUID | None = None
    position: str | None = Field(None, max_length=255)
    position_uz: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    ad_guid: str | None = Field(None, max_length=100)
    ad_distinguished_name: str | None = None


class UserCreate(UserBase):
    """Schema for creating a new user."""

    username: str = Field(..., min_length=1, max_length=100)
    password_hash: str | None = Field(default=None, max_length=255)
    role: Role = Field(default=Role.USER)
    # Stable internal subject id (JWT sub). When omitted, the repository
    # defaults it to the generated row id.
    keycloak_id: str | None = Field(default=None, max_length=255)
    email_verified: bool = Field(default=False)


class UserAdminCreate(BaseModel):
    """Schema for admin creating a user end-to-end (Keycloak + local DB)."""

    username: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    full_name_uz: str | None = Field(None, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)
    role: Role = Field(default=Role.USER)
    department_id: UUID | None = None
    tabel_number: str | None = Field(None, max_length=50)
    position: str | None = Field(None, max_length=255)
    position_uz: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)


class UserUpdate(BaseModel):
    """Schema for updating user (partial update)."""

    email: EmailStr | None = None
    full_name: str | None = Field(None, min_length=1, max_length=255)
    role: Role | None = None
    tabel_number: str | None = Field(None, max_length=50)
    full_name_uz: str | None = Field(None, max_length=255)
    ad_username: str | None = Field(None, max_length=100)
    department_id: UUID | None = None
    position: str | None = Field(None, max_length=255)
    position_uz: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    ad_guid: str | None = Field(None, max_length=100)
    ad_distinguished_name: str | None = None
    email_verified: bool | None = None
    is_active: bool | None = None


class UserRoleResponse(BaseModel):
    """Schema for user role response."""

    user_id: UUID
    role: Role
    department_id: UUID | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserResponse(UserBase):
    """Schema for user response."""

    id: UUID
    username: str
    role: Role
    keycloak_id: str
    email_verified: bool
    is_active: bool
    last_sync_at: datetime | None = None
    roles: list[UserRoleResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Schema for paginated user list response."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int


class UserSyncRequest(BaseModel):
    """Schema for user sync request (optional)."""

    force: bool = Field(default=False, description="Force sync even if user exists")


class UserPasswordResetRequest(BaseModel):
    """Schema for admin-driven password reset."""

    password: str = Field(..., min_length=8, max_length=255)


class UserPasswordResetResponse(BaseModel):
    """Schema for password reset response (returned to admin once)."""

    password: str

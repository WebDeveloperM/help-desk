"""User service abstraction."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.auth.schemas import TokenUser
from app.user.models import User
from app.user.schemas import (
    UserAdminCreate,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)


class UserService(Protocol):
    """Service interface for user business logic."""

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """Create a new user."""

    async def admin_create_user(self, data: UserAdminCreate) -> UserResponse:
        """Admin creates a user directly in the local DB (hashed password + role)."""

    async def admin_reset_password(self, user_id: UUID, password: str) -> None:
        """Admin resets a user's password (stored as a bcrypt hash)."""

    async def get_user(self, user_id: UUID) -> UserResponse:
        """Return user by ID or raise if missing."""

    async def get_user_or_none(self, user_id: UUID) -> UserResponse | None:
        """Return user by ID or None."""

    async def get_user_by_keycloak_id(self, keycloak_id: str) -> UserResponse | None:
        """Return user by Keycloak subject or None."""

    async def update_user(self, user_id: UUID, user_data: UserUpdate) -> UserResponse:
        """Update a user."""

    async def delete_user(self, user_id: UUID) -> bool:
        """Soft-delete a user."""

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 100,
        is_active: bool | None = None,
    ) -> UserListResponse:
        """Return paginated users."""

    async def ensure_user_exists(self, token_user: TokenUser) -> User:
        """Return the persisted user for a token subject, or raise if missing."""

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return user entity by ID."""

    async def get_by_keycloak_id(self, keycloak_id: str) -> User | None:
        """Return user entity by Keycloak subject."""

    async def get_by_email(self, email: str) -> User | None:
        """Return user entity by email."""

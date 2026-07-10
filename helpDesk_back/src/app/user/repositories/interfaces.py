"""User repository abstraction."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.user.models import User, UserRole
from app.user.schemas import UserCreate, UserUpdate


class UserRepository(Protocol):
    """Repository interface for user persistence operations."""

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return a user by database ID."""

    async def get_by_ids(self, user_ids: list[UUID]) -> list[User]:
        """Return users by database IDs (only existing ones)."""

    async def get_by_keycloak_id(self, keycloak_id: str) -> User | None:
        """Return a user by Keycloak subject."""

    async def get_by_email(self, email: str) -> User | None:
        """Return a user by email address."""

    async def get_by_username(self, username: str) -> User | None:
        """Return a user by login username."""

    async def get_by_ad_username(self, ad_username: str) -> User | None:
        """Return a user by AD username."""

    async def get_by_department_id(
        self, department_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[list[User], int]:
        """Return users for a department with total count."""

    async def create(self, user_data: UserCreate) -> User:
        """Persist a new user."""

    async def set_password_hash(self, user_id: UUID, password_hash: str) -> bool:
        """Update a user's password hash; return True if the user existed."""

    async def update(self, user_id: UUID, user_data: UserUpdate) -> User | None:
        """Partially update a user."""

    async def soft_delete(self, user_id: UUID) -> bool:
        """Soft-delete a user and return True if it existed."""

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> tuple[list[User], int]:
        """Return paginated users with total count."""

    async def exists_by_keycloak_id(self, keycloak_id: str) -> bool:
        """Check if a user exists for the given Keycloak subject."""

    async def exists_by_email(self, email: str) -> bool:
        """Check if a user exists for the given email."""

    async def exists_by_ad_username(self, ad_username: str) -> bool:
        """Check if a user exists for the given AD username."""

    async def sync_user_roles(
        self, user_id: UUID, roles: list[str], department_id: UUID | None = None
    ) -> None:
        """Replace user roles with the provided set."""

    async def get_user_roles(
        self, user_id: UUID, department_id: UUID | None = None
    ) -> list[UserRole]:
        """Return roles for a user, optionally scoped to a department."""

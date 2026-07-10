"""User service - business logic for user operations."""

from __future__ import annotations

from math import ceil
from typing import TYPE_CHECKING
from uuid import UUID

from app.auth.errors import AuthenticationError
from app.auth.schemas import TokenUser
from app.auth.services import hash_password

if TYPE_CHECKING:
    from app.department.repositories import DepartmentRepository

from app.user.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.user.models import User
from app.user.repositories import UserRepository
from app.user.services.interfaces import UserService
from app.user.schemas import (
    UserAdminCreate,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)


class UserServiceImpl(UserService):
    """Default implementation of user business logic operations."""

    def __init__(
        self,
        repository: UserRepository,
        department_repository: "DepartmentRepository | None" = None,
    ) -> None:
        """
        Initialize user service.

        Args:
            repository: User repository for database operations.
            department_repository: Optional department repository for resolving
                a department reference to department_id.
        """
        self.repository = repository
        self.department_repository = department_repository

    async def _resolve_department_id(self, department_value: str | None) -> UUID | None:
        """Resolve Keycloak department (UUID, sequential number, or code) to department_id."""
        if not department_value or not self.department_repository:
            return None
        raw = department_value.strip()
        if not raw:
            return None
        try:
            uid = UUID(raw)
            dept = await self.department_repository.get_by_id(uid)
            if dept:
                return dept.id
        except (ValueError, TypeError):
            pass
        if raw.isdigit():
            dept = await self.department_repository.get_by_number(int(raw))
            if dept:
                return dept.id
        dept = await self.department_repository.get_by_code(raw)
        if dept:
            return dept.id
        return None

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """
        Create a new user.

        Args:
            user_data: User creation data.

        Returns:
            Created user response.

        Raises:
            UserAlreadyExistsError: If user already exists.
        """
        # Check for existing user by email
        if await self.repository.exists_by_email(user_data.email):
            raise UserAlreadyExistsError(field="email", value=user_data.email)

        user = await self.repository.create(user_data)
        return UserResponse.model_validate(user)

    async def admin_create_user(self, data: UserAdminCreate) -> UserResponse:
        """Admin creates a user directly in the local DB.

        Steps:
            1. Validate username and email are not already taken.
            2. Hash the password (bcrypt) and persist the user with its role.

        Raises:
            UserAlreadyExistsError: Username or email already exists.
        """
        if await self.repository.get_by_username(data.username):
            raise UserAlreadyExistsError(field="username", value=data.username)
        if await self.repository.exists_by_email(data.email):
            raise UserAlreadyExistsError(field="email", value=data.email)

        create_data = UserCreate(
            username=data.username,
            password_hash=hash_password(data.password),
            role=data.role,
            email=data.email,
            full_name=data.full_name,
            full_name_uz=data.full_name_uz,
            tabel_number=data.tabel_number,
            department_id=data.department_id,
            position=data.position,
            position_uz=data.position_uz,
            phone=data.phone,
            email_verified=True,
        )
        user = await self.repository.create(create_data)
        return UserResponse.model_validate(user)

    async def admin_reset_password(self, user_id: UUID, password: str) -> None:
        """Reset a user's password (stored as a bcrypt hash).

        Raises:
            UserNotFoundError: If the user does not exist.
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id=str(user_id))

        await self.repository.set_password_hash(user_id, hash_password(password))

    async def get_user(self, user_id: UUID) -> UserResponse:
        """
        Get user by ID.

        Args:
            user_id: User UUID.

        Returns:
            User response.

        Raises:
            UserNotFoundError: If user not found.
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id=str(user_id))

        return UserResponse.model_validate(user)

    async def get_user_or_none(self, user_id: UUID) -> UserResponse | None:
        """
        Get user by ID, returning None if not found.

        Args:
            user_id: User UUID.

        Returns:
            User response if found, None otherwise.
        """
        user = await self.repository.get_by_id(user_id)
        if not user:
            return None

        return UserResponse.model_validate(user)

    async def get_user_by_keycloak_id(self, keycloak_id: str) -> UserResponse | None:
        """
        Get user by Keycloak ID.

        Args:
            keycloak_id: Keycloak user ID.

        Returns:
            User response if found, None otherwise.
        """
        user = await self.repository.get_by_keycloak_id(keycloak_id)
        if not user:
            return None

        return UserResponse.model_validate(user)

    async def update_user(self, user_id: UUID, user_data: UserUpdate) -> UserResponse:
        """
        Update user.

        Args:
            user_id: User UUID.
            user_data: User update data.

        Returns:
            Updated user response.

        Raises:
            UserNotFoundError: If user not found.
        """
        previous = await self.repository.get_by_id(user_id)
        if not previous:
            raise UserNotFoundError(user_id=str(user_id))

        user = await self.repository.update(user_id, user_data)
        if not user:
            raise UserNotFoundError(user_id=str(user_id))

        return UserResponse.model_validate(user)

    async def delete_user(self, user_id: UUID) -> bool:
        """
        Soft delete user.

        Args:
            user_id: User UUID.

        Returns:
            True if user was deleted.

        Raises:
            UserNotFoundError: If user not found.
        """
        deleted = await self.repository.soft_delete(user_id)
        if not deleted:
            raise UserNotFoundError(user_id=str(user_id))
        return True

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 100,
        is_active: bool | None = None,
    ) -> UserListResponse:
        """
        List users with pagination.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            is_active: Filter by active status.

        Returns:
            Paginated user list response.
        """
        skip = (page - 1) * page_size
        users, total = await self.repository.list(
            skip=skip, limit=page_size, is_active=is_active
        )

        pages = ceil(total / page_size) if total > 0 else 0

        return UserListResponse(
            items=[UserResponse.model_validate(user) for user in users],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def ensure_user_exists(self, token_user: TokenUser) -> User:
        """
        Return the persisted user for a token subject.

        With local auth, users are created up-front by an admin, so a valid
        token always maps to an existing row. A missing row means the user was
        deleted after the token was issued.

        Args:
            token_user: Authenticated user from the access token.

        Returns:
            User model from database.

        Raises:
            AuthenticationError: If no user exists for the token subject.
        """
        user = await self.repository.get_by_keycloak_id(token_user.sub)
        if not user:
            raise AuthenticationError("User no longer exists")
        return user

    # Delegate repository methods for direct access when needed
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user entity by ID."""
        return await self.repository.get_by_id(user_id)

    async def get_by_keycloak_id(self, keycloak_id: str) -> User | None:
        """Get user entity by Keycloak ID."""
        return await self.repository.get_by_keycloak_id(keycloak_id)

    async def get_by_email(self, email: str) -> User | None:
        """Get user entity by email."""
        return await self.repository.get_by_email(email)

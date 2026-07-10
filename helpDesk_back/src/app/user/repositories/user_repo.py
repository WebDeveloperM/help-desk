"""SQLAlchemy implementation of the user repository."""

from __future__ import annotations

from typing import Any, List
from uuid import UUID, uuid4

from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.user.models import User, UserRole
from app.user.repositories.interfaces import UserRepository
from app.user.schemas import UserCreate, UserUpdate


class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy-based repository for user database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize user repository.

        Args:
            session: Database session.
        """
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """
        Get user by ID with roles loaded.

        Args:
            user_id: User UUID.

        Returns:
            User if found, None otherwise.
        """
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_ids(self, user_ids: list[UUID]) -> list[User]:
        """
        Get users by list of IDs.

        Args:
            user_ids: List of user UUIDs.

        Returns:
            List of users that exist (order not guaranteed).
        """
        if not user_ids:
            return []
        result = await self.session.execute(
            select(User).where(User.id.in_(user_ids))
        )
        return list(result.scalars().all())

    async def get_by_keycloak_id(self, keycloak_id: str) -> User | None:
        """
        Get user by Keycloak ID with roles loaded.

        Args:
            keycloak_id: Keycloak user ID (sub claim).

        Returns:
            User if found, None otherwise.
        """
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.keycloak_id == keycloak_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """
        Get user by email.

        Args:
            email: User email address.

        Returns:
            User if found, None otherwise.
        """
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """
        Get user by login username with roles loaded.

        Args:
            username: Login username.

        Returns:
            User if found, None otherwise.
        """
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.roles))
            .where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_ad_username(self, ad_username: str) -> User | None:
        """
        Get user by Active Directory username.

        Args:
            ad_username: Active Directory username.

        Returns:
            User if found, None otherwise.
        """
        result = await self.session.execute(
            select(User).where(User.ad_username == ad_username)
        )
        return result.scalar_one_or_none()

    async def get_by_department_id(
        self, department_id: UUID, skip: int = 0, limit: int = 100
    ) -> tuple[List[User], int]:
        """
        Get users by department ID.

        Args:
            department_id: Department UUID.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            Tuple of (users list, total count).
        """
        query = select(User).where(User.department_id == department_id)
        count_query = select(func.count()).select_from(User).where(
            User.department_id == department_id
        )

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        users = list[Any](result.scalars().all())

        return users, total

    async def create(self, user_data: UserCreate) -> User:
        """
        Create a new user record in database.

        Uses explicit insert to avoid SQLAlchemy insertmanyvalues ZeroDivisionError
        (ORM flush with defaulted columns can trigger num_params_per_batch=0).

        Args:
            user_data: User creation data.

        Returns:
            Created user.
        """
        user_id = uuid4()
        # keycloak_id is now a stable internal subject id; default it to the row id.
        subject = user_data.keycloak_id or str(user_id)
        await self.session.execute(
            insert(User).values(
                id=user_id,
                keycloak_id=subject,
                username=user_data.username,
                password_hash=user_data.password_hash,
                role=user_data.role,
                tabel_number=user_data.tabel_number,
                email=user_data.email,
                full_name=user_data.full_name,
                full_name_uz=user_data.full_name_uz,
                ad_username=user_data.ad_username,
                department_id=user_data.department_id,
                position=user_data.position,
                position_uz=user_data.position_uz,
                phone=user_data.phone,
                ad_guid=user_data.ad_guid,
                ad_distinguished_name=user_data.ad_distinguished_name,
                email_verified=user_data.email_verified,
                is_active=True,
            )
        )
        await self.session.flush()
        return await self.get_by_id(user_id)

    async def set_password_hash(self, user_id: UUID, password_hash: str) -> bool:
        """Update a user's password hash. Returns True if a row was updated."""
        result = await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(password_hash=password_hash)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def update(self, user_id: UUID, user_data: UserUpdate) -> User | None:
        """
        Update user record in database.

        Args:
            user_id: User UUID.
            user_data: User update data.

        Returns:
            Updated user if found, None otherwise.
        """
        update_data: dict[str, Any] = {
            k: v for k, v in user_data.model_dump(exclude_unset=True).items()
        }

        if not update_data:
            return await self.get_by_id(user_id)

        await self.session.execute(
            update(User).where(User.id == user_id).values(**update_data)
        )
        await self.session.flush()

        return await self.get_by_id(user_id)

    async def soft_delete(self, user_id: UUID) -> bool:
        """
        Soft delete user (set is_active=False).

        Args:
            user_id: User UUID.

        Returns:
            True if user was deleted, False if not found.
        """
        user = await self.get_by_id(user_id)
        if not user:
            return False

        await self.session.execute(
            update(User).where(User.id == user_id).values(is_active=False)
        )
        await self.session.flush()
        return True

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: bool | None = None,
    ) -> tuple[List[User], int]:
        """
        List users with pagination and filtering.

        Args:
            skip: Number of records to skip.
            limit: Maximum number of records to return.
            is_active: Filter by active status.

        Returns:
            Tuple of (users list, total count).
        """
        query = select(User).options(selectinload(User.roles))

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        count_query = select(func.count()).select_from(User)
        if is_active is not None:
            count_query = count_query.where(User.is_active == is_active)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        users = list(result.scalars().all())

        return users, total

    async def exists_by_keycloak_id(self, keycloak_id: str) -> bool:
        """Check if user with keycloak_id exists."""
        user = await self.get_by_keycloak_id(keycloak_id)
        return user is not None

    async def exists_by_email(self, email: str) -> bool:
        """Check if user with email exists."""
        user = await self.get_by_email(email)
        return user is not None

    async def exists_by_ad_username(self, ad_username: str) -> bool:
        """Check if user with ad_username exists."""
        user = await self.get_by_ad_username(ad_username)
        return user is not None

    async def sync_user_roles(
        self, user_id: UUID, roles: List[str], department_id: UUID | None = None
    ) -> None:
        """
        Sync user roles from Keycloak to database.

        Args:
            user_id: User UUID.
            roles: List of role names from Keycloak.
            department_id: Optional department ID for department-specific roles.
        """
        from app.core.enums import Role

        # Map Keycloak roles to database roles
        role_mapping: dict[str, Role] = {
            "user": Role.USER,
            "department_head": Role.DEPARTMENT_HEAD,
            "executor": Role.EXECUTOR,
            "admin": Role.ADMIN,
        }

        # Convert Keycloak roles to database roles
        db_roles: List[Role] = []
        for role_name in roles:
            role_name_lower = role_name.lower()
            if role_name_lower in role_mapping:
                db_roles.append(role_mapping[role_name_lower])
            else:
                # Default to USER if role not found
                db_roles.append(Role.USER)
        # Ensure unique roles to avoid unique constraint violations
        db_roles = list(dict.fromkeys(db_roles))

        # Delete existing roles for this user (and department if specified)
        delete_query = delete(UserRole).where(UserRole.user_id == user_id)
        if department_id is not None:
            delete_query = delete_query.where(UserRole.department_id == department_id)
        else:
            delete_query = delete_query.where(UserRole.department_id.is_(None))

        await self.session.execute(delete_query)
        await self.session.flush()

        # Insert row-by-row using raw SQL so the role is sent as the enum value
        # (e.g. "user") not the Python enum name ("USER"). Use CAST to avoid
        # SQLAlchemy misparsing "::" in :role::role as bind parameter syntax.
        if db_roles:
            for role in db_roles:
                await self.session.execute(
                    text(
                        "INSERT INTO user_roles (user_id, role, department_id) "
                        "VALUES (:user_id, CAST(:role AS \"role\"), CAST(:department_id AS uuid))"
                    ),
                    {
                        "user_id": user_id,
                        "role": role.value,
                        "department_id": department_id,
                    },
                )

    async def get_user_roles(
        self, user_id: UUID, department_id: UUID | None = None
    ) -> List[UserRole]:
        """
        Get user roles.

        Args:
            user_id: User UUID.
            department_id: Optional department ID to filter roles.

        Returns:
            List of user roles.
        """
        query = select(UserRole).where(UserRole.user_id == user_id)
        if department_id is not None:
            query = query.where(UserRole.department_id == department_id)
        else:
            query = query.where(UserRole.department_id.is_(None))

        result = await self.session.execute(query)
        return list(result.scalars().all())

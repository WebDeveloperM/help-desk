"""User authentication and authorization dependencies."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.auth.dependencies import get_current_user, require_any_role
from app.auth.schemas import TokenUser
from app.config import Settings, get_settings
from app.core.database import DatabaseSession
from app.department.dependencies import get_department_repository
from app.department.repositories import DepartmentRepository
from app.user.exceptions import UserNotFoundError, UserPermissionDeniedError
from app.user.repositories import SQLAlchemyUserRepository, UserRepository
from app.user.services import UserService, UserServiceImpl


def get_user_repository(session: DatabaseSession) -> UserRepository:
    """
    Get user repository instance.

    Args:
        session: Database session.

    Returns:
        User repository.
    """
    return SQLAlchemyUserRepository(session)


def get_user_service(
    repository: Annotated[UserRepository, Depends(get_user_repository)],
    department_repository: Annotated[
        DepartmentRepository, Depends(get_department_repository)
    ],
) -> UserService:
    """
    Get user service instance.

    Args:
        repository: User repository.
        department_repository: Department repository (for resolving department_id).

    Returns:
        User service.
    """
    return UserServiceImpl(repository, department_repository)


async def get_user_by_id(
    user_id: UUID,
    service: Annotated[UserService, Depends(get_user_service)],
):
    """
    Get user by ID dependency.

    Args:
        user_id: User UUID.
        service: User service.

    Returns:
        User model.

    Raises:
        UserNotFoundError: If user not found.
    """
    user = await service.get_by_id(user_id)
    if not user:
        raise UserNotFoundError(user_id=str(user_id))

    return user


async def get_current_user_model(
    current_user: Annotated[TokenUser, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
):
    """
    Get current user model from database, auto-creating if needed.

    Args:
        current_user: Current authenticated user from token.
        service: User service.

    Returns:
        User model from database.
    """
    return await service.ensure_user_exists(current_user)


async def require_user_permission(
    user_id: UUID,
    current_user: Annotated[TokenUser, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """
    Check if current user can access/modify the target user.

    Args:
        user_id: Target user ID.
        current_user: Current authenticated user.
        service: User service.
        settings: Application settings.

    Returns:
        Target user model.

    Raises:
        UserNotFoundError: If user not found.
        UserPermissionDeniedError: If permission denied.
    """
    from app.auth.services import has_any_role

    user = await service.get_by_id(user_id)
    if not user:
        raise UserNotFoundError(user_id=str(user_id))

    current_user_model = await service.ensure_user_exists(current_user)

    can_access = False

    if current_user_model and current_user_model.id == user_id:
        can_access = True
    else:
        # User roles disabled: use Keycloak token roles only.
        if has_any_role(current_user, ["user_manager", "admin"], settings):
            can_access = True

    if not can_access:
        raise UserPermissionDeniedError(
            detail="You don't have permission to access this user"
        )

    return user


async def require_user_list_permission(
    current_user: Annotated[TokenUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenUser:
    """
    Check if current user can list all users.

    Args:
        current_user: Current authenticated user.
        settings: Application settings.

    Returns:
        Current user if authorized.

    Raises:
        UserPermissionDeniedError: If permission denied.
    """
    from app.auth.services import has_any_role

    if not has_any_role(current_user, ["user_manager", "admin"], settings):
        raise UserPermissionDeniedError(
            detail="You don't have permission to list users"
        )

    return current_user


def require_user_create_permission(
    current_user: Annotated[TokenUser, Depends(require_any_role("admin"))],
) -> TokenUser:
    """
    Check if current user can create users.

    Args:
        current_user: Current authenticated user (must be admin).

    Returns:
        Current user.
    """
    return current_user


def require_user_delete_permission(
    current_user: Annotated[TokenUser, Depends(require_any_role("admin"))],
) -> TokenUser:
    """
    Check if current user can delete users.

    Args:
        current_user: Current authenticated user (must be admin).

    Returns:
        Current user.
    """
    return current_user

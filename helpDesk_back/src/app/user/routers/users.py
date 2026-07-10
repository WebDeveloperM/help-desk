"""User router with CRUD endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.auth.schemas import TokenUser
from app.user.dependencies import (
    get_current_user_model,
    get_user_service,
    require_user_create_permission,
    require_user_delete_permission,
    require_user_list_permission,
    require_user_permission,
)
from app.user.schemas import (
    UserAdminCreate,
    UserListResponse,
    UserPasswordResetRequest,
    UserPasswordResetResponse,
    UserResponse,
    UserUpdate,
)
from app.user.services import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_data: UserAdminCreate,
    current_user: Annotated[TokenUser, Depends(require_user_create_permission)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """
    Admin creates a user directly in the local DB (hashed password + role).

    Returns:
        Created user.

    Raises:
        UserAlreadyExistsError: Username or email already exists.
    """
    return await service.admin_create_user(user_data)


@router.get("", response_model=UserListResponse)
async def list_users_endpoint(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 100,
    is_active: Annotated[bool | None, Query()] = None,
    current_user: Annotated[TokenUser, Depends(require_user_list_permission)] = None,
    service: Annotated[UserService, Depends(get_user_service)] = None,
) -> UserListResponse:
    """
    List users with pagination (user_manager/admin only).

    Args:
        page: Page number (1-indexed).
        page_size: Number of items per page.
        is_active: Filter by active status.
        current_user: Current authenticated user.
        service: User service.

    Returns:
        Paginated user list.
    """
    return await service.list_users(page=page, page_size=page_size, is_active=is_active)


@router.get("/me", response_model=UserResponse)
async def get_current_user_endpoint(
    current_user_model: Annotated[dict, Depends(get_current_user_model)],
) -> UserResponse:
    """
    Get current authenticated user.

    Args:
        current_user_model: Current user model from database.

    Returns:
        Current user.
    """
    return UserResponse.model_validate(current_user_model)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_endpoint(
    user: Annotated[dict, Depends(require_user_permission)],
) -> UserResponse:
    """
    Get user by ID.

    Args:
        user: User model (with permission check).

    Returns:
        User response.
    """
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user_endpoint(
    user_id: UUID,
    user_data: UserUpdate,
    user: Annotated[dict, Depends(require_user_permission)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserResponse:
    """
    Update user (self or user_manager/admin).

    Args:
        user_id: User UUID.
        user_data: User update data.
        user: User model (with permission check).
        service: User service.

    Returns:
        Updated user.

    Raises:
        UserNotFoundError: If user not found.
    """
    return await service.update_user(user_id, user_data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: UUID,
    current_user: Annotated[TokenUser, Depends(require_user_delete_permission)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    """
    Delete user (admin only).

    Args:
        user_id: User UUID.
        current_user: Current authenticated user (must be admin).
        service: User service.

    Raises:
        UserNotFoundError: If user not found.
    """
    await service.delete_user(user_id)


@router.post("/{user_id}/reset-password", response_model=UserPasswordResetResponse)
async def reset_user_password_endpoint(
    user_id: UUID,
    payload: UserPasswordResetRequest,
    _admin: Annotated[TokenUser, Depends(require_user_create_permission)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserPasswordResetResponse:
    """
    Admin resets a user's password. The new password is stored as a bcrypt
    hash and echoed back once so the admin can hand it to the user.

    Raises:
        UserNotFoundError: User does not exist.
    """
    await service.admin_reset_password(user_id, payload.password)
    return UserPasswordResetResponse(password=payload.password)

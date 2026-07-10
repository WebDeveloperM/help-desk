"""Department router with CRUD endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.auth.schemas import TokenUser
from app.department.dependencies import (
    get_department_by_id,
    get_department_by_number,
    get_department_service,
    require_department_admin,
)
from app.department.models import Department
from app.department.schemas import (
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdate,
    DepartmentUserInfo,
)
from app.department.services import DepartmentService
from app.user.dependencies import get_current_user_model, get_user_repository
from app.user.models import User
from app.user.repositories import UserRepository

router = APIRouter(prefix="/departments", tags=["departments"])


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_department_endpoint(
    department_data: DepartmentCreate,
    _admin: Annotated[TokenUser, Depends(require_department_admin)],
    service: Annotated[DepartmentService, Depends(get_department_service)],
) -> DepartmentResponse:
    """
    Create a new department. Admin only.

    Args:
        department_data: Department creation data.
        _admin: Admin role gate.
        service: Department service.

    Returns:
        Created department.
    """
    return await service.create_department(department_data)


@router.get("", response_model=DepartmentListResponse)
async def list_departments_endpoint(
    _current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[DepartmentService, Depends(get_department_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 100,
    is_active: Annotated[bool | None, Query()] = None,
) -> DepartmentListResponse:
    """
    List departments with pagination and filtering. Authenticated users only.

    Args:
        _current_user: Current authenticated user.
        page: Page number (1-indexed).
        page_size: Number of items per page.
        is_active: Filter by active status.
        service: Department service.

    Returns:
        Paginated department list.
    """
    return await service.list_departments(
        page=page, page_size=page_size, is_active=is_active
    )


@router.get("/by-number/{number}", response_model=DepartmentResponse)
async def get_department_by_number_endpoint(
    _current_user: Annotated[User, Depends(get_current_user_model)],
    department: Annotated[Department, Depends(get_department_by_number)],
) -> DepartmentResponse:
    """
    Get department by admin-friendly number. Authenticated users only.

    Args:
        _current_user: Current authenticated user.
        department: Department model (resolved by number).

    Returns:
        Department response.
    """
    return DepartmentResponse.model_validate(department)


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department_endpoint(
    _current_user: Annotated[User, Depends(get_current_user_model)],
    department: Annotated[Department, Depends(get_department_by_id)],
) -> DepartmentResponse:
    """
    Get department by ID. Authenticated users only.

    Args:
        _current_user: Current authenticated user.
        department: Department model (with existence check).

    Returns:
        Department response.
    """
    return DepartmentResponse.model_validate(department)


@router.get("/{department_id}/users", response_model=list[DepartmentUserInfo])
async def list_department_users_endpoint(
    department_id: UUID,
    _current_user: Annotated[User, Depends(get_current_user_model)],
    _department: Annotated[Department, Depends(get_department_by_id)],
    service: Annotated[DepartmentService, Depends(get_department_service)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> list[DepartmentUserInfo]:
    """
    List users in a department for ticket assignment flows. Any authenticated user.

    Args:
        department_id: Department UUID.
        _current_user: Current authenticated user (auth gate).
        _department: Department model (validates existence).
        service: Department service.
        user_repository: User repository.

    Returns:
        List of users (id, full_name, email) in the department.
    """
    return await service.list_department_users(department_id, user_repository)


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department_endpoint(
    department_id: UUID,
    department_data: DepartmentUpdate,
    _admin: Annotated[TokenUser, Depends(require_department_admin)],
    department: Annotated[Department, Depends(get_department_by_id)],
    service: Annotated[DepartmentService, Depends(get_department_service)],
) -> DepartmentResponse:
    """
    Update department. Admin only.

    Args:
        department_id: Department UUID.
        department_data: Department update data.
        department: Department model (with existence check).
        _admin: Admin role gate.
        service: Department service.

    Returns:
        Updated department.

    Raises:
        DepartmentNotFoundError: If department not found.
    """
    return await service.update_department(department_id, department_data)


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department_endpoint(
    department_id: UUID,
    _admin: Annotated[TokenUser, Depends(require_department_admin)],
    department: Annotated[Department, Depends(get_department_by_id)],
    service: Annotated[DepartmentService, Depends(get_department_service)],
) -> None:
    """
    Delete department. Admin only.

    Args:
        department_id: Department UUID.
        department: Department model (with existence check).
        _admin: Admin role gate.
        service: Department service.

    Raises:
        DepartmentNotFoundError: If department not found.
    """
    await service.delete_department(department_id)

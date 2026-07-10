"""Department dependencies for dependency injection."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.auth.dependencies import require_any_role
from app.auth.schemas import TokenUser
from app.core.database import DatabaseSession
from app.department.exceptions import DepartmentNotFoundError
from app.department.models import Department
from app.department.repositories import (
    DepartmentRepository,
    SQLAlchemyDepartmentRepository,
)
from app.department.services import DepartmentService


def get_department_repository(session: DatabaseSession) -> DepartmentRepository:
    """
    Get department repository instance.

    Args:
        session: Database session.

    Returns:
        Department repository.
    """
    return SQLAlchemyDepartmentRepository(session)


def get_department_service(
    repository: Annotated[DepartmentRepository, Depends(get_department_repository)],
) -> DepartmentService:
    """
    Get department service instance.

    Args:
        repository: Department repository.

    Returns:
        Department service.
    """
    return DepartmentService(repository)


def require_department_admin(
    current_user: Annotated[TokenUser, Depends(require_any_role("admin"))],
) -> TokenUser:
    """Require admin role for department mutations (POST, PUT, DELETE)."""
    return current_user


async def get_department_by_id(
    department_id: UUID,
    repository: Annotated[DepartmentRepository, Depends(get_department_repository)],
) -> Department:
    """
    Get department by ID dependency.

    Args:
        department_id: Department UUID.
        repository: Department repository.

    Returns:
        Department model.

    Raises:
        DepartmentNotFoundError: If department not found.
    """
    department = await repository.get_by_id(department_id)
    if not department:
        raise DepartmentNotFoundError(department_id=str(department_id))

    return department


async def get_department_by_number(
    number: int,
    repository: Annotated[DepartmentRepository, Depends(get_department_repository)],
) -> Department:
    """
    Get department by sequential number dependency.

    Args:
        number: Department number.
        repository: Department repository.

    Returns:
        Department model.

    Raises:
        DepartmentNotFoundError: If department not found.
    """
    department = await repository.get_by_number(number)
    if not department:
        raise DepartmentNotFoundError(department_id=f"#{number}")

    return department

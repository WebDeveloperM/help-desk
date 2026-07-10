"""Department service - business logic for department operations."""

from math import ceil
from typing import TYPE_CHECKING
from uuid import UUID

from app.department.exceptions import DepartmentAlreadyExistsError, DepartmentNotFoundError
from app.department.models import Department
from app.department.repositories import DepartmentRepository
from app.department.schemas import (
    DepartmentCreate,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdate,
    DepartmentUserInfo,
)

if TYPE_CHECKING:
    from app.user.repositories import UserRepository


class DepartmentService:
    """Service for department business logic operations."""

    def __init__(self, repository: DepartmentRepository) -> None:
        """
        Initialize department service.

        Args:
            repository: Department repository for database operations.
        """
        self.repository = repository

    async def create_department(
        self, department_data: DepartmentCreate
    ) -> DepartmentResponse:
        """
        Create a new department.

        Args:
            department_data: Department creation data.

        Returns:
            Created department response.
        """
        # Check if code already exists
        existing = await self.repository.get_by_code(department_data.code)
        if existing:
            raise DepartmentAlreadyExistsError(code=department_data.code)

        department = await self.repository.create(department_data)
        return DepartmentResponse.model_validate(department)

    async def get_department(self, department_id: UUID) -> DepartmentResponse:
        """
        Get department by ID.

        Args:
            department_id: Department UUID.

        Returns:
            Department response.

        Raises:
            DepartmentNotFoundError: If department not found.
        """
        department = await self.repository.get_by_id(department_id)
        if not department:
            raise DepartmentNotFoundError(department_id=str(department_id))

        return DepartmentResponse.model_validate(department)

    async def update_department(
        self, department_id: UUID, department_data: DepartmentUpdate
    ) -> DepartmentResponse:
        """
        Update department.

        Args:
            department_id: Department UUID.
            department_data: Department update data.

        Returns:
            Updated department response.

        Raises:
            DepartmentNotFoundError: If department not found.
        """
        # If code is being updated, check if new code already exists
        if department_data.code:
            existing = await self.repository.get_by_code(department_data.code)
            if existing and existing.id != department_id:
                raise DepartmentAlreadyExistsError(code=department_data.code)

        department = await self.repository.update(department_id, department_data)
        if not department:
            raise DepartmentNotFoundError(department_id=str(department_id))

        return DepartmentResponse.model_validate(department)

    async def delete_department(self, department_id: UUID) -> None:
        """
        Delete department.

        Args:
            department_id: Department UUID.

        Raises:
            DepartmentNotFoundError: If department not found.
        """
        deleted = await self.repository.delete(department_id)
        if not deleted:
            raise DepartmentNotFoundError(department_id=str(department_id))

    async def list_departments(
        self,
        page: int = 1,
        page_size: int = 100,
        is_active: bool | None = None,
    ) -> DepartmentListResponse:
        """
        List departments with pagination and filtering.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            is_active: Filter by active status.

        Returns:
            Paginated department list.
        """
        departments, total = await self.repository.list(
            page=page, page_size=page_size, is_active=is_active
        )

        total_pages = ceil(total / page_size) if total > 0 else 0

        return DepartmentListResponse(
            items=[DepartmentResponse.model_validate(dept) for dept in departments],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def list_department_users(
        self,
        department_id: UUID,
        user_repository: "UserRepository",
    ) -> list[DepartmentUserInfo]:
        """
        List department users for ticket assignment workflows.

        Args:
            department_id: Department UUID.
            user_repository: User repository.

        Returns:
            List of users in department.
        """
        users, _ = await user_repository.get_by_department_id(
            department_id,
            skip=0,
            limit=500,
        )
        return [DepartmentUserInfo.model_validate(user) for user in users]

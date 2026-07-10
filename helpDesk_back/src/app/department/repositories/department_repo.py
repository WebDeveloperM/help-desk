"""Department repository - isolated database queries."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.department.models import Department

if TYPE_CHECKING:
    from app.department.schemas import DepartmentCreate, DepartmentUpdate


class SQLAlchemyDepartmentRepository:
    """Repository for department database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """
        Initialize department repository.

        Args:
            session: Database session.
        """
        self.session = session

    async def get_by_id(self, department_id: UUID) -> Department | None:
        """
        Get department by ID with relationships loaded.

        Args:
            department_id: Department UUID.

        Returns:
            Department if found, None otherwise.
        """
        result = await self.session.execute(
            select(Department)
            .options(
                selectinload(Department.parent),
                selectinload(Department.head_user),
            )
            .where(Department.id == department_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Department | None:
        """
        Get department by code.

        Args:
            code: Department code.

        Returns:
            Department if found, None otherwise.
        """
        result = await self.session.execute(
            select(Department).where(Department.code == code)
        )
        return result.scalar_one_or_none()

    async def get_by_number(self, number: int) -> Department | None:
        """
        Get department by admin-friendly number with relationships loaded.

        Args:
            number: Sequential department number.

        Returns:
            Department if found, None otherwise.
        """
        result = await self.session.execute(
            select(Department)
            .options(
                selectinload(Department.parent),
                selectinload(Department.head_user),
            )
            .where(Department.number == number)
        )
        return result.scalar_one_or_none()

    async def create(self, department_data: "DepartmentCreate") -> Department:
        """
        Create a new department record in database.

        Args:
            department_data: Department creation data.

        Returns:
            Created department.
        """
        department = Department(**department_data.model_dump())
        self.session.add(department)
        await self.session.flush()
        await self.session.refresh(department)
        return department

    async def update(
        self, department_id: UUID, department_data: "DepartmentUpdate"
    ) -> Department | None:
        """
        Update department.

        Args:
            department_id: Department UUID.
            department_data: Department update data.

        Returns:
            Updated department if found, None otherwise.
        """
        department = await self.get_by_id(department_id)
        if not department:
            return None

        update_data = department_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(department, key, value)

        await self.session.flush()
        await self.session.refresh(department)
        return department

    async def delete(self, department_id: UUID) -> bool:
        """
        Delete department.

        Args:
            department_id: Department UUID.

        Returns:
            True if deleted, False if not found.
        """
        department = await self.get_by_id(department_id)
        if not department:
            return False

        await self.session.delete(department)
        await self.session.flush()
        return True

    async def list(
        self,
        page: int = 1,
        page_size: int = 100,
        is_active: bool | None = None,
    ) -> tuple[list[Department], int]:
        """
        List departments with pagination and filtering.

        Args:
            page: Page number (1-indexed).
            page_size: Number of items per page.
            is_active: Filter by active status.

        Returns:
            Tuple of (departments list, total count).
        """
        query = select(Department).options(
            selectinload(Department.parent),
            selectinload(Department.head_user),
        )

        if is_active is not None:
            query = query.where(Department.is_active == is_active)

        # Get total count
        count_query = select(Department)
        if is_active is not None:
            count_query = count_query.where(Department.is_active == is_active)
        total_result = await self.session.execute(
            select(func.count()).select_from(count_query.subquery())
        )
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.limit(page_size).offset(offset)

        result = await self.session.execute(query)
        departments = list(result.scalars().all())

        return departments, total

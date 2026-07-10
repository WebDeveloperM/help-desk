"""Department repository abstraction."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.department.models import Department
from app.department.schemas import DepartmentCreate, DepartmentUpdate


class DepartmentRepository(Protocol):
    """Repository interface for department persistence operations."""

    async def get_by_id(self, department_id: UUID) -> Department | None:
        """Return a department by ID."""

    async def get_by_code(self, code: str) -> Department | None:
        """Return a department by code."""

    async def get_by_number(self, number: int) -> Department | None:
        """Return a department by sequential number."""

    async def create(self, department_data: DepartmentCreate) -> Department:
        """Persist a new department."""

    async def update(
        self, department_id: UUID, department_data: DepartmentUpdate
    ) -> Department | None:
        """Partially update a department."""

    async def delete(self, department_id: UUID) -> bool:
        """Delete a department and return True if it existed."""

    async def list(
        self,
        page: int = 1,
        page_size: int = 100,
        is_active: bool | None = None,
    ) -> tuple[list[Department], int]:
        """Return paginated departments with total count."""

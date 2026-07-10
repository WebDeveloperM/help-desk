"""Department repositories."""

from app.department.repositories.department_repo import SQLAlchemyDepartmentRepository
from app.department.repositories.interfaces import DepartmentRepository

__all__ = ["DepartmentRepository", "SQLAlchemyDepartmentRepository"]

"""Department exceptions."""

from app.department.exceptions.department_exceptions import (
    DepartmentAlreadyExistsError,
    DepartmentNotFoundError,
)

__all__ = ["DepartmentNotFoundError", "DepartmentAlreadyExistsError"]

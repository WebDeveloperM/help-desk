"""Department dependencies for dependency injection."""

from app.department.dependencies.department_deps import (
    get_department_by_id,
    get_department_by_number,
    get_department_repository,
    get_department_service,
    require_department_admin,
)

__all__ = [
    "get_department_repository",
    "get_department_service",
    "get_department_by_id",
    "get_department_by_number",
    "require_department_admin",
]

"""Department domain exceptions with HTTP mapping."""

from fastapi import status

from app.core.exceptions import DomainError


class DepartmentNotFoundError(DomainError):
    """Raised when department is not found."""

    def __init__(
        self,
        department_id: str | None = None,
        detail: str | None = None,
    ) -> None:
        message = detail or (
            f"Department with id {department_id} not found"
            if department_id
            else "Department not found"
        )
        params = {"department_id": department_id} if department_id else {}
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="department.not_found",
            detail=message,
            error_params=params,
        )


class DepartmentAlreadyExistsError(DomainError):
    """Raised when department with same code already exists."""

    def __init__(self, code: str) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="department.already_exists",
            detail=f"Department with code '{code}' already exists",
            error_params={"code": code},
        )

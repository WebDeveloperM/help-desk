"""User domain exceptions with HTTP mapping."""

from fastapi import status

from app.core.exceptions import DomainError


class UserNotFoundError(DomainError):
    """Raised when user is not found."""

    def __init__(self, user_id: str | None = None, detail: str | None = None) -> None:
        message = detail or (
            f"User with id {user_id} not found" if user_id else "User not found"
        )
        params = {"user_id": user_id} if user_id else {}
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="user.not_found",
            detail=message,
            error_params=params,
        )


class UserAlreadyExistsError(DomainError):
    """Raised when user already exists."""

    def __init__(self, field: str = "email", value: str | None = None) -> None:
        message = (
            f"User with {field} '{value}' already exists"
            if value
            else f"User with this {field} already exists"
        )
        params: dict[str, str] = {"field": field}
        if value:
            params["value"] = value
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="user.already_exists",
            detail=message,
            error_params=params,
        )


class UserPermissionDeniedError(DomainError):
    """Raised when user doesn't have permission."""

    def __init__(self, detail: str = "You don't have permission to perform this action") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="user.permission_denied",
            detail=detail,
        )


class UserValidationError(DomainError):
    """Raised when user data validation fails."""

    def __init__(self, detail: str = "User data validation failed") -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="user.validation_failed",
            detail=detail,
        )


class UserInactiveError(DomainError):
    """Raised when trying to access inactive user."""

    def __init__(self, detail: str = "User account is inactive") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="user.inactive",
            detail=detail,
        )


class UserKeycloakSyncError(DomainError):
    """Raised when pushing user changes to Keycloak fails (e.g. network, auth)."""

    def __init__(self, detail: str = "Failed to sync user with Keycloak") -> None:
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="user.keycloak_sync_failed",
            detail=detail,
        )

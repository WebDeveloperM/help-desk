"""User exceptions package."""

from app.user.exceptions.user_exceptions import (
    UserAlreadyExistsError,
    UserInactiveError,
    UserKeycloakSyncError,
    UserNotFoundError,
    UserPermissionDeniedError,
    UserValidationError,
)

__all__ = [
    "UserAlreadyExistsError",
    "UserInactiveError",
    "UserKeycloakSyncError",
    "UserNotFoundError",
    "UserPermissionDeniedError",
    "UserValidationError",
]

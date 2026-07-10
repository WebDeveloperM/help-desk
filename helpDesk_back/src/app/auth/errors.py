"""Authentication and authorization exceptions."""

from fastapi import status

from app.core.exceptions import DomainError


class AuthenticationError(DomainError):
    """Raised when authentication fails."""

    def __init__(
        self,
        detail: str = "Authentication failed",
        error_code: str = "auth.authentication_failed",
    ) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code=error_code,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class AuthorizationError(DomainError):
    """Raised when authorization fails."""

    def __init__(self, detail: str = "Insufficient permissions") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="auth.authorization_failed",
            detail=detail,
        )


class TokenValidationError(AuthenticationError):
    """Raised when token validation fails."""

    def __init__(self, detail: str = "Invalid or expired token") -> None:
        super().__init__(detail=detail, error_code="auth.invalid_token")

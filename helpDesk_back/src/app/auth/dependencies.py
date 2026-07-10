"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.errors import AuthenticationError, AuthorizationError
from app.auth.schemas import TokenUser
from app.auth.services import (
    decode_access_token,
    extract_user_from_token,
    has_all_roles,
    has_any_role,
)
from app.config import Settings, get_settings

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenUser:
    """
    Dependency to get current authenticated user from a backend-issued JWT.

    Args:
        credentials: HTTPBearer credentials from Authorization header.
        settings: Application settings.

    Returns:
        TokenUser instance with user information.

    Raises:
        AuthenticationError: If token is missing or invalid.
    """
    token = credentials.credentials

    try:
        token_payload = decode_access_token(token, settings)
        return extract_user_from_token(token_payload, "")
    except Exception as e:
        if isinstance(e, AuthenticationError):
            raise
        raise AuthenticationError(f"Token validation failed: {str(e)}")


def require_roles(*required_roles: str, require_all: bool = False):
    """
    Dependency factory to require specific roles.

    Args:
        *required_roles: Role names that must be present.
        require_all: If True, user must have all roles. If False, any role is sufficient.

    Returns:
        Dependency function that checks roles.
    """

    async def role_checker(
        current_user: TokenUser = Depends(get_current_user),
        settings: Settings = Depends(get_settings),
    ) -> TokenUser:
        """
        Check if current user has required roles.

        Args:
            current_user: Current authenticated user.
            settings: Application settings.

        Returns:
            Current user if authorized.

        Raises:
            AuthorizationError: If user doesn't have required roles.
        """
        if not required_roles:
            return current_user

        has_permission = (
            has_all_roles(current_user, list(required_roles), settings)
            if require_all
            else has_any_role(current_user, list(required_roles), settings)
        )

        if not has_permission:
            roles_str = ", ".join(required_roles)
            raise AuthorizationError(
                f"User does not have required role(s): {roles_str}"
            )

        return current_user

    return role_checker


def require_any_role(*required_roles: str):
    """
    Dependency factory to require any of the specified roles.

    Args:
        *required_roles: Role names (user must have at least one).

    Returns:
        Dependency function that checks roles.
    """
    return require_roles(*required_roles, require_all=False)


def require_all_roles(*required_roles: str):
    """
    Dependency factory to require all of the specified roles.

    Args:
        *required_roles: Role names (user must have all).

    Returns:
        Dependency function that checks roles.
    """
    return require_roles(*required_roles, require_all=True)

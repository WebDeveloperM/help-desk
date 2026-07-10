"""Authentication service - pure functions for token processing."""

from typing import Any

from app.auth.schemas import TokenUser
from app.config import Settings


def extract_user_from_token(
    token_payload: dict[str, Any], client_id: str
) -> TokenUser:
    """
    Extract user information from decoded JWT token payload.

    Args:
        token_payload: Decoded JWT token payload.
        client_id: Keycloak client ID for extracting client roles.

    Returns:
        TokenUser instance with extracted information.
    """
    # Display username: prefer name or email if preferred_username not in token
    preferred_username = (
        token_payload.get("preferred_username")
        or token_payload.get("name")
        or token_payload.get("email")
        or token_payload.get("sub")
        or ""
    )
    department_raw = token_payload.get("department")
    if department_raw is not None and not isinstance(department_raw, str):
        if isinstance(department_raw, list) and department_raw:
            department_raw = str(department_raw[0]).strip() or None
        else:
            department_raw = str(department_raw).strip() or None
    elif isinstance(department_raw, str):
        department_raw = department_raw.strip() or None

    return TokenUser(
        sub=token_payload.get("sub", ""),
        email=token_payload.get("email", ""),
        name=token_payload.get("name"),
        given_name=token_payload.get("given_name"),
        family_name=token_payload.get("family_name"),
        preferred_username=str(preferred_username).strip(),
        realm_access=token_payload.get("realm_access"),
        resource_access=token_payload.get("resource_access"),
        email_verified=token_payload.get("email_verified", False),
        exp=token_payload.get("exp", 0),
        iat=token_payload.get("iat", 0),
        department=department_raw,
    )


def extract_roles(token_user: TokenUser, settings: Settings) -> list[str]:
    """
    Extract all roles from token user.

    Backend-issued tokens carry roles under ``realm_access.roles``.

    Args:
        token_user: TokenUser instance.
        settings: Application settings.

    Returns:
        List of role names.
    """
    return token_user.get_realm_roles()


def has_role(token_user: TokenUser, required_role: str, settings: Settings) -> bool:
    """
    Check if user has a specific role.

    Args:
        token_user: TokenUser instance.
        required_role: Role name to check.
        settings: Application settings.

    Returns:
        True if user has the role, False otherwise.
    """
    roles = extract_roles(token_user, settings)
    return required_role in roles


def has_any_role(
    token_user: TokenUser, required_roles: list[str], settings: Settings
) -> bool:
    """
    Check if user has any of the required roles.

    Args:
        token_user: TokenUser instance.
        required_roles: List of role names to check.
        settings: Application settings.

    Returns:
        True if user has at least one of the roles, False otherwise.
    """
    if not required_roles:
        return True

    user_roles = extract_roles(token_user, settings)
    return any(role in user_roles for role in required_roles)


def has_all_roles(
    token_user: TokenUser, required_roles: list[str], settings: Settings
) -> bool:
    """
    Check if user has all of the required roles.

    Args:
        token_user: TokenUser instance.
        required_roles: List of role names to check.
        settings: Application settings.

    Returns:
        True if user has all of the roles, False otherwise.
    """
    if not required_roles:
        return True

    user_roles = extract_roles(token_user, settings)
    return all(role in user_roles for role in required_roles)

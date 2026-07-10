"""Local authentication: password hashing and JWT access tokens (HS256).

Replaces the Keycloak BFF flow. The backend now signs its own access tokens
with ``settings.jwt_secret`` and validates them on every request. Tokens carry
the same claims the Keycloak tokens used to carry (``sub``, ``email``,
``preferred_username``, ``realm_access.roles``, ``exp``, ``iat``) so the
downstream role-checking layer keeps working unchanged.
"""

from __future__ import annotations

import time
from typing import Any

import bcrypt
from jose import jwt

from app.auth.errors import TokenValidationError
from app.config import Settings


def hash_password(password: str) -> str:
    """Return a bcrypt hash for the given plaintext password."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def create_access_token(
    *,
    subject: str,
    username: str,
    email: str,
    full_name: str | None,
    roles: list[str],
    settings: Settings,
) -> tuple[str, int]:
    """Build a signed HS256 access token.

    Returns:
        Tuple of (encoded token, expires_in seconds).
    """
    issued_at = int(time.time())
    expires_in = settings.access_token_ttl_seconds
    payload: dict[str, Any] = {
        "sub": subject,
        "email": email,
        "preferred_username": username,
        "name": full_name,
        "realm_access": {"roles": roles},
        "iss": settings.jwt_issuer,
        "iat": issued_at,
        "exp": issued_at + expires_in,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Validate and decode a backend-issued access token.

    Raises:
        TokenValidationError: If the token is invalid, expired, or malformed.
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": False,
            },
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenValidationError("Token has expired") from exc
    except jwt.JWTClaimsError as exc:
        raise TokenValidationError(f"Token claims validation failed: {exc}") from exc
    except jwt.JWTError as exc:
        raise TokenValidationError(f"Token validation failed: {exc}") from exc

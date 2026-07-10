"""Security utilities for JWT token handling."""

from typing import Any

from jose import jwt
from jose.constants import ALGORITHMS


def decode_jwt_token(
    token: str, key: dict[str, Any], algorithms: list[str] | None = None
) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token string.
        key: The public key or JWKS key for verification.
        algorithms: List of allowed algorithms. Defaults to RS256.

    Returns:
        Decoded token payload.

    Raises:
        jwt.JWTError: If token is invalid, expired, or verification fails.
    """
    if algorithms is None:
        algorithms = [ALGORITHMS.RS256]

    return jwt.decode(
        token,
        key,
        algorithms=algorithms,
        options={
            "verify_signature": True,
            "verify_exp": True,
            "verify_iat": True,
            "verify_aud": False,
        },
    )

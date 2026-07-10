"""Tests for authentication functionality."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.auth.errors import AuthenticationError, AuthorizationError
from app.auth.schemas import TokenUser
from app.auth.services import (
    create_access_token,
    decode_access_token,
    extract_roles,
    extract_user_from_token,
    has_all_roles,
    has_any_role,
    has_role,
    hash_password,
    verify_password,
)
from app.config import Settings


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://test",
        jwt_secret="test-secret-key",
    )


def test_extract_user_from_token() -> None:
    """Test extracting user from token payload."""
    token_payload = {
        "sub": "user-123",
        "email": "test@example.com",
        "name": "Test User",
        "preferred_username": "testuser",
        "realm_access": {"roles": ["user", "admin"]},
        "email_verified": True,
        "exp": 1234567890,
        "iat": 1234567800,
    }

    user = extract_user_from_token(token_payload, "")

    assert user.sub == "user-123"
    assert user.email == "test@example.com"
    assert user.preferred_username == "testuser"
    assert "user" in user.get_realm_roles()
    assert "admin" in user.get_realm_roles()


def test_extract_roles() -> None:
    """Roles come from realm_access only."""
    settings = _settings()

    user = TokenUser(
        sub="user-123",
        email="test@example.com",
        preferred_username="testuser",
        realm_access={"roles": ["user", "admin"]},
        email_verified=True,
        exp=1234567890,
        iat=1234567800,
    )

    roles = extract_roles(user, settings)
    assert "user" in roles
    assert "admin" in roles


def test_has_role() -> None:
    """Test role checking."""
    settings = _settings()

    user = TokenUser(
        sub="user-123",
        email="test@example.com",
        preferred_username="testuser",
        realm_access={"roles": ["admin"]},
        email_verified=True,
        exp=1234567890,
        iat=1234567800,
    )

    assert has_role(user, "admin", settings) is True
    assert has_role(user, "user", settings) is False


def test_has_any_role() -> None:
    """Test any role checking."""
    settings = _settings()

    user = TokenUser(
        sub="user-123",
        email="test@example.com",
        preferred_username="testuser",
        realm_access={"roles": ["admin"]},
        email_verified=True,
        exp=1234567890,
        iat=1234567800,
    )

    assert has_any_role(user, ["admin", "user"], settings) is True
    assert has_any_role(user, ["user", "moderator"], settings) is False
    assert has_any_role(user, [], settings) is True


def test_has_all_roles() -> None:
    """Test all roles checking."""
    settings = _settings()

    user = TokenUser(
        sub="user-123",
        email="test@example.com",
        preferred_username="testuser",
        realm_access={"roles": ["admin", "user"]},
        email_verified=True,
        exp=1234567890,
        iat=1234567800,
    )

    assert has_all_roles(user, ["admin", "user"], settings) is True
    assert has_all_roles(user, ["admin", "moderator"], settings) is False
    assert has_all_roles(user, [], settings) is True


def test_password_hash_round_trip() -> None:
    """A hashed password verifies against the original and rejects others."""
    hashed = hash_password("s3cret-pass")
    assert hashed != "s3cret-pass"
    assert verify_password("s3cret-pass", hashed) is True
    assert verify_password("wrong", hashed) is False
    assert verify_password("anything", None) is False


def test_access_token_round_trip() -> None:
    """A token created by the backend decodes back to the same claims."""
    settings = _settings()
    token, expires_in = create_access_token(
        subject="user-123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        roles=["admin"],
        settings=settings,
    )
    assert expires_in == settings.access_token_ttl_seconds

    payload = decode_access_token(token, settings)
    assert payload["sub"] == "user-123"
    assert payload["preferred_username"] == "testuser"
    assert payload["realm_access"]["roles"] == ["admin"]

    user = extract_user_from_token(payload, "")
    assert "admin" in extract_roles(user, settings)


def test_decode_rejects_tampered_token() -> None:
    """A token signed with another secret fails validation."""
    settings = _settings()
    other = Settings(database_url="postgresql+asyncpg://test", jwt_secret="other-secret")
    token, _ = create_access_token(
        subject="u",
        username="u",
        email="u@example.com",
        full_name="U",
        roles=["user"],
        settings=other,
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(token, settings)


@pytest.mark.asyncio
async def test_auth_endpoint_missing_token(client: TestClient) -> None:
    """Test /auth/me endpoint without token returns 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_auth_endpoint_invalid_token(client: TestClient) -> None:
    """Test /auth/me endpoint with invalid token returns 401."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_authentication_error() -> None:
    """Test AuthenticationError exception."""
    error = AuthenticationError("Test error")
    assert error.status_code == status.HTTP_401_UNAUTHORIZED
    assert error.detail == "Test error"
    assert "WWW-Authenticate" in error.headers


def test_authorization_error() -> None:
    """Test AuthorizationError exception."""
    error = AuthorizationError("Test error")
    assert error.status_code == status.HTTP_403_FORBIDDEN
    assert error.detail == "Test error"

"""Authentication router (local username/password + backend-issued JWT)."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.auth.errors import AuthenticationError
from app.auth.schemas import LoginRequest, TokenResponse, TokenUser, UserInfo
from app.auth.services import (
    create_access_token,
    extract_roles,
    verify_password,
)
from app.config import Settings, get_settings
from app.user.dependencies import get_user_repository, get_user_service
from app.user.repositories import UserRepository
from app.user.services import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> TokenResponse:
    """
    Authenticate by username + password and return a signed access token.

    Raises:
        AuthenticationError: Unknown username, wrong password, or inactive user.
    """
    user = await repository.get_by_username(payload.username)
    invalid = AuthenticationError(
        detail="Invalid username or password",
        error_code="auth.invalid_credentials",
    )
    if not user or not user.is_active:
        raise invalid
    if not verify_password(payload.password, user.password_hash):
        raise invalid

    access_token, expires_in = create_access_token(
        subject=user.keycloak_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        roles=[user.role.value],
        settings=settings,
    )
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: Annotated[TokenUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserInfo:
    """
    Get current authenticated user information.

    Args:
        current_user: Current authenticated user from token.
        settings: Application settings.
        service: User service.

    Returns:
        User information with roles.
    """
    await service.ensure_user_exists(current_user)
    roles = extract_roles(current_user, settings)

    return UserInfo(
        sub=current_user.sub,
        email=current_user.email,
        name=current_user.name,
        preferred_username=current_user.preferred_username,
        roles=roles,
    )

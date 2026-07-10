"""bnpzID SSO router: login redirect, callback, and access-check callback."""

import logging
import secrets
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from app.auth.errors import AuthenticationError
from app.auth.services import create_access_token
from app.auth.services import bnpzid_service as bz
from app.config import Settings, get_settings
from app.user.dependencies import get_user_repository
from app.user.repositories import UserRepository
from app.user.schemas import UserCreate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["bnpzid"])

# Prevent caching of auth redirects.
_NO_CACHE = {
    "Cache-Control": "no-store, no-cache, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


class AccessCheckRequest(BaseModel):
    """Body bnpzID posts to the access-check callback."""

    client_id: str = ""
    client_secret: str = ""
    username: str = ""
    employee_slug: str = ""
    tabel_number: str = ""


def _require_bnpzid_enabled(settings: Settings) -> None:
    if not bz.is_bnpzid_configured(settings):
        raise AuthenticationError("bnpzID login is not enabled")


def _client_ip(request: Request) -> str:
    """Best-effort real client IP (behind our nginx, which sets X-Real-IP)."""
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


@router.get("/auth/bnpzid/login")
async def bnpzid_login(
    settings: Annotated[Settings, Depends(get_settings)],
    next: str = Query("/dashboard", description="Frontend path to land on after login"),
) -> RedirectResponse:
    """Start bnpzID login: set a signed state cookie and redirect to authorize."""
    # Browser navigation: on a config mismatch (button shown but backend off),
    # redirect to the login page with an error rather than dumping a 401 JSON.
    if not bz.is_bnpzid_configured(settings):
        return RedirectResponse(
            url="/login?error=bnpzid_disabled", status_code=302, headers=_NO_CACHE
        )

    state = secrets.token_urlsafe(24)
    next_path = bz.safe_next_path(next)
    cookie_value = bz.sign_state(settings, state=state, next_path=next_path)

    response = RedirectResponse(
        url=bz.build_authorize_url(settings, state),
        status_code=302,
        headers=_NO_CACHE,
    )
    response.set_cookie(
        key=bz.STATE_COOKIE_NAME,
        value=cookie_value,
        max_age=settings.bnpzid_state_ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.bnpzid_redirect_uri.startswith("https://"),
        path="/",
    )
    return response


async def _process_bnpzid_callback(
    request: Request,
    settings: Settings,
    repository: UserRepository,
    bnpzid_code: str,
    state: str,
) -> RedirectResponse:
    """Handle the redirect back from bnpzID: validate state, exchange code, issue JWT."""
    _require_bnpzid_enabled(settings)

    def _fail(error: str) -> RedirectResponse:
        resp = RedirectResponse(url=f"/login?error={error}", status_code=302, headers=_NO_CACHE)
        resp.delete_cookie(bz.STATE_COOKIE_NAME, path="/")
        return resp

    cookie_value = request.cookies.get(bz.STATE_COOKIE_NAME)
    if not cookie_value or not bnpzid_code or not state:
        return _fail("bnpzid_state")

    try:
        state_data = bz.read_state(settings, cookie_value)
    except AuthenticationError:
        return _fail("bnpzid_state")

    if not bz.states_match(state_data.get("state", ""), state):
        return _fail("bnpzid_state")

    # One-time use: reject a replayed code.
    if not bz.consume_code(bnpzid_code):
        return _fail("bnpzid_replay")

    try:
        claims = await bz.exchange_code(settings, bnpzid_code)
    except AuthenticationError as exc:
        logger.warning("bnpzID exchange failed: %s", exc.detail)
        return _fail("bnpzid_exchange")

    username = str(claims.get("username") or "").strip()
    if not username:
        return _fail("bnpzid_identity")

    user = await repository.get_by_username(username)
    if user is not None and not user.is_active:
        return _fail("bnpzid_disabled")

    if user is None:
        # Auto-provision (policy: create by username, no local password).
        full_name = (
            f"{claims.get('first_name', '')} {claims.get('last_name', '')}".strip()
            or username
        )
        user = await repository.create(
            UserCreate(
                username=username,
                password_hash=None,  # bnpzID-only account, no local password
                role=bz.map_role(settings, claims.get("role")),
                email=bz.synth_email(username),
                full_name=full_name,
                email_verified=True,
            )
        )
        logger.info("Provisioned bnpzID user '%s' (role=%s).", username, user.role.value)

    access_token, expires_in = create_access_token(
        subject=user.keycloak_id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        roles=[user.role.value],
        settings=settings,
    )

    next_path = bz.safe_next_path(state_data.get("next"))
    fragment = urlencode(
        {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
        }
    )
    resp = RedirectResponse(url=f"{next_path}#{fragment}", status_code=302, headers=_NO_CACHE)
    resp.delete_cookie(bz.STATE_COOKIE_NAME, path="/")
    return resp


@router.get("/auth/bnpzid/callback")
async def bnpzid_callback(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[UserRepository, Depends(get_user_repository)],
    bnpzid_code: str = Query(""),
    state: str = Query(""),
) -> RedirectResponse:
    """Native callback path (under /api/v1)."""
    return await _process_bnpzid_callback(request, settings, repository, bnpzid_code, state)


@router.post("/users/bnpzid/access-check/")
async def bnpzid_access_check(
    request: Request,
    payload: AccessCheckRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> Response:
    """Called BY bnpzID during authorize to decide access + FaceID requirement.

    Fail-closed: unknown client / bad secret / disallowed source IP -> allowed=false.
    """
    if not bz.is_bnpzid_configured(settings):
        return JSONResponse({"allowed": False}, status_code=status.HTTP_403_FORBIDDEN)

    # Source-IP allowlist (optional): only the bnpzID server should call this.
    allowed_ips = settings.bnpzid_source_ip_list
    if allowed_ips and _client_ip(request) not in allowed_ips:
        logger.warning("bnpzID access-check from disallowed IP %s", _client_ip(request))
        return JSONResponse({"allowed": False}, status_code=status.HTTP_403_FORBIDDEN)

    if not bz.verify_client_credentials(settings, payload.client_id, payload.client_secret):
        return JSONResponse({"allowed": False}, status_code=status.HTTP_403_FORBIDDEN)

    # Deny only if the user already exists in helpdesk and is deactivated.
    username = (payload.username or "").strip()
    if username:
        existing = await repository.get_by_username(username)
        if existing is not None and not existing.is_active:
            return JSONResponse({"allowed": False, "face_id_required": False})

    return JSONResponse(
        {"allowed": True, "face_id_required": bool(settings.bnpzid_always_require_face)}
    )


# Root-level router (NO /api/v1 prefix) for the callback path registered on
# bnpzID as `/auth/callback`. Mounted at the app root in main.py.
root_router = APIRouter(tags=["bnpzid"])


@root_router.get("/auth/callback")
async def bnpzid_callback_registered(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[UserRepository, Depends(get_user_repository)],
    bnpzid_code: str = Query(""),
    state: str = Query(""),
) -> RedirectResponse:
    """Registered callback path `/auth/callback` (matches bnpzID redirect URI)."""
    return await _process_bnpzid_callback(request, settings, repository, bnpzid_code, state)

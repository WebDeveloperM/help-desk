"""bnpzID SSO integration (external FaceID identity provider).

The helpdesk acts as a bnpzID *client*. Flow:
  1. /auth/bnpzid/login  -> redirect browser to bnpzID authorize (with signed state cookie)
  2. user authenticates on bnpzID (password + FaceID)
  3. bnpzID -> POST /users/bnpzid/access-check/  (we answer allowed + face_id_required)
  4. bnpzID -> redirect back to /auth/bnpzid/callback?bnpzid_code=..&state=..
  5. we exchange the code server-to-server for identity claims, map to a local user,
     and issue our own JWT.

This module holds the pure/service logic (URL building, signed state, code
single-use guard, code exchange, role/email mapping). DB/user provisioning and
HTTP request/response handling live in the router.
"""

from __future__ import annotations

import hmac
import re
import time
from typing import Any
from urllib.parse import urlencode

from jose import jwt

from app.auth.errors import AuthenticationError
from app.config import Settings
from app.core.enums import Role
from app.core.http import get_http_client

STATE_COOKIE_NAME = "bnpzid_state"
_STATE_ISSUER = "helpdesk-bnpzid-state"

# In-memory single-use guard for authorization codes. bnpzID codes are stateless
# signed tokens valid for their whole TTL (replayable), so we reject a code once
# it has been exchanged. NOTE: process-local — safe for single-worker uvicorn;
# multi-worker/replicas need a shared store (e.g. Redis).
_used_codes: dict[str, float] = {}
_USED_CODE_TTL_SECONDS = 300


def is_bnpzid_configured(settings: Settings) -> bool:
    """True only when bnpzID is enabled and fully configured."""
    return bool(
        settings.bnpzid_enabled
        and settings.bnpzid_base_url
        and settings.bnpzid_client_id
        and settings.bnpzid_client_secret
        and settings.bnpzid_redirect_uri
    )


def build_authorize_url(settings: Settings, state: str) -> str:
    """Build the bnpzID authorize redirect URL."""
    base = settings.bnpzid_base_url.rstrip("/")
    params = {
        "client_id": settings.bnpzid_client_id,
        "redirect_uri": settings.bnpzid_redirect_uri,
        "state": state,
    }
    return f"{base}/bnpzid/authorize/?{urlencode(params)}"


def sign_state(settings: Settings, *, state: str, next_path: str) -> str:
    """Sign {state, next} into a short-lived cookie value (HS256, our jwt_secret)."""
    now = int(time.time())
    payload = {
        "state": state,
        "next": next_path,
        "iss": _STATE_ISSUER,
        "iat": now,
        "exp": now + settings.bnpzid_state_ttl_seconds,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def read_state(settings: Settings, cookie_value: str) -> dict[str, Any]:
    """Decode+verify the state cookie. Raises AuthenticationError if invalid/expired."""
    try:
        return jwt.decode(
            cookie_value,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            issuer=_STATE_ISSUER,
            options={"verify_aud": False},
        )
    except jwt.JWTError as exc:
        raise AuthenticationError("bnpzID state is invalid or expired") from exc


def states_match(expected: str, received: str) -> bool:
    """Constant-time comparison of the state values."""
    return bool(expected) and bool(received) and hmac.compare_digest(expected, received)


def _prune_used_codes(now: float) -> None:
    expired = [c for c, ts in _used_codes.items() if now - ts > _USED_CODE_TTL_SECONDS]
    for c in expired:
        _used_codes.pop(c, None)


def consume_code(code: str) -> bool:
    """Mark a code as used. Returns False if it was already used (replay)."""
    now = time.time()
    _prune_used_codes(now)
    if code in _used_codes:
        return False
    _used_codes[code] = now
    return True


def verify_client_credentials(
    settings: Settings, client_id: str, client_secret: str
) -> bool:
    """Constant-time verification of the access-check callback credentials."""
    id_ok = hmac.compare_digest(client_id or "", settings.bnpzid_client_id)
    secret_ok = hmac.compare_digest(client_secret or "", settings.bnpzid_client_secret)
    return id_ok and secret_ok


async def exchange_code(settings: Settings, code: str) -> dict[str, Any]:
    """Exchange a bnpzid_code for identity claims (server-to-server).

    Returns the claims dict: {username, first_name, last_name, role,
    employee_slug, tabel_number}.

    Raises:
        AuthenticationError: If bnpzID rejects the exchange.
    """
    url = f"{settings.bnpzid_base_url.rstrip('/')}/api/v1/auth/bnpzid/exchange/"
    data = {
        "client_id": settings.bnpzid_client_id,
        "client_secret": settings.bnpzid_client_secret,
        "redirect_uri": settings.bnpzid_redirect_uri,
        "code": code,
    }
    async with get_http_client(timeout=15.0, verify=settings.bnpzid_ssl_verify) as client:
        response = await client.post(url, json=data)

    if response.status_code != 200:
        detail = ""
        try:
            detail = str(response.json().get("error") or "")[:200]
        except Exception:
            detail = response.text[:200]
        raise AuthenticationError(f"bnpzID code exchange failed: {detail}")

    return response.json()


def map_role(settings: Settings, bnpzid_role: str | None) -> Role:
    """Map a bnpzID role to a helpdesk Role, conservatively.

    Never elevate to admin from a bnpzID claim automatically: unknown/any role
    maps to the configured default (normally ``user``).
    """
    default = _coerce_role(settings.bnpzid_default_role, Role.USER)
    if not bnpzid_role:
        return default
    # Only honor an exact match to a known non-privileged helpdesk role.
    value = str(bnpzid_role).strip().lower()
    if value in {Role.USER.value, Role.EXECUTOR.value}:
        return Role(value)
    return default


def _coerce_role(value: str | None, fallback: Role) -> Role:
    try:
        return Role(str(value).strip().lower())
    except (ValueError, TypeError):
        return fallback


_EMAIL_LOCAL_SAFE = re.compile(r"[^A-Za-z0-9._%+-]")


def synth_email(username: str) -> str:
    """Synthesize a unique, valid email for a bnpzID user (no email claim exists)."""
    local = _EMAIL_LOCAL_SAFE.sub(".", (username or "user").strip()).strip(".") or "user"
    return f"{local}@bnpzid.example.com"


def safe_next_path(next_value: str | None, default: str = "/dashboard") -> str:
    """Return a safe same-origin relative path for the post-login redirect.

    Prevents open-redirect: only allows a single-slash-rooted relative path.
    """
    value = (next_value or "").strip()
    if not value.startswith("/") or value.startswith("//"):
        return default
    return value

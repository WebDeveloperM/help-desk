"""Authorization tests for the department router (GAU-234).

Covers two cases per endpoint:
- No Authorization header → 401 (or 403 from FastAPI's HTTPBearer default)
- Authenticated but missing required role → 403

Happy-path (200/201) is not asserted here since it requires a real DB connection
(the conftest seeds env vars but doesn't spin up Postgres).
"""

from typing import Callable, Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.auth.schemas import TokenUser
from app.config import Settings


def _token_user(roles: list[str]) -> TokenUser:
    return TokenUser(
        sub="user-123",
        email="t@example.com",
        preferred_username="t",
        realm_access={"roles": roles},
        email_verified=True,
        exp=9999999999,
        iat=1234567800,
    )


@pytest.fixture
def role_client(
    settings: Settings,
) -> Generator[tuple[TestClient, Callable[[list[str]], None]], None, None]:
    """Yield (client, set_roles) where `set_roles(["admin"])` overrides auth for this test."""
    from app.main import create_app

    app = create_app()

    def set_roles(roles: list[str]) -> None:
        app.dependency_overrides[get_current_user] = lambda: _token_user(roles)

    with TestClient(app) as test_client:
        yield test_client, set_roles
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Missing Authorization header → 401/403 from HTTPBearer
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "method,path,body",
    [
        ("post", "/api/v1/departments", {"code": "X", "name": "Y"}),
        ("get", "/api/v1/departments", None),
        ("get", f"/api/v1/departments/{uuid4()}", None),
        ("get", f"/api/v1/departments/{uuid4()}/users", None),
        ("put", f"/api/v1/departments/{uuid4()}", {"name": "Z"}),
        ("delete", f"/api/v1/departments/{uuid4()}", None),
    ],
)
def test_department_endpoints_reject_unauthenticated(
    client: TestClient, method: str, path: str, body: dict | None
) -> None:
    response = client.request(method, path, json=body)
    # FastAPI's HTTPBearer with auto_error=True raises HTTPException(403);
    # AuthenticationError raises 401. Either is "rejected" for the purpose of this audit.
    assert response.status_code in {401, 403}


# ---------------------------------------------------------------------------
# Authenticated but missing required role → 403
# ---------------------------------------------------------------------------

def test_create_department_requires_admin(
    role_client: tuple[TestClient, Callable[[list[str]], None]],
) -> None:
    client, set_roles = role_client
    set_roles(["user"])
    response = client.post(
        "/api/v1/departments",
        json={"code": "X", "name": "Y"},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 403


def test_update_department_requires_admin(
    role_client: tuple[TestClient, Callable[[list[str]], None]],
) -> None:
    client, set_roles = role_client
    set_roles(["user"])
    response = client.put(
        f"/api/v1/departments/{uuid4()}",
        json={"name": "Z"},
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 403


def test_delete_department_requires_admin(
    role_client: tuple[TestClient, Callable[[list[str]], None]],
) -> None:
    client, set_roles = role_client
    set_roles(["user"])
    response = client.delete(
        f"/api/v1/departments/{uuid4()}",
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 403



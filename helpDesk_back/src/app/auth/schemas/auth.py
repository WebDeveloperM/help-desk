"""Auth Pydantic schemas for authentication."""

from pydantic import BaseModel, Field


class TokenUser(BaseModel):
    """User information extracted from JWT token."""

    sub: str
    email: str
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    preferred_username: str
    realm_access: dict[str, list[str]] | None = None
    resource_access: dict[str, dict[str, list[str]]] | None = None
    email_verified: bool = False
    exp: int
    iat: int
    department: str | None = None

    def get_realm_roles(self) -> list[str]:
        """Extract realm roles from token."""
        if self.realm_access:
            return self.realm_access.get("roles", [])
        return []

    def get_client_roles(self, client_id: str) -> list[str]:
        """Extract client roles for a specific client."""
        if not self.resource_access:
            return []

        client_access = self.resource_access.get(client_id, {})
        return client_access.get("roles", [])

    def get_all_roles(self, client_id: str) -> list[str]:
        """Get all roles (realm + client) for a specific client."""
        realm_roles = self.get_realm_roles()
        client_roles = self.get_client_roles(client_id)
        return list(set(realm_roles + client_roles))


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    """Username + password login request."""

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=255)


class UserInfo(BaseModel):
    """User info response model."""

    sub: str
    email: str
    name: str | None = None
    preferred_username: str
    roles: list[str] = Field(default_factory=list)

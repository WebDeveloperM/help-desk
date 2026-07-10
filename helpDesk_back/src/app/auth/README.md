# Module: `auth`

**Authentication and session** integration with **Keycloak** (or OIDC-compatible IdP).

## Responsibilities

- **OAuth2 / OIDC** flows: login redirect, **PKCE**, callback, token exchange, refresh, logout URL
- **JWT** validation and parsing; building `TokenUser` for dependencies
- **`get_current_user`** and related `Depends` used by other routers

## HTTP surface

Router prefix: **`/auth`** (under global `api_prefix`).

## Dependencies

- **`config`**: Keycloak URLs, client id/secret, redirect URIs
- **`user`**: optional user sync / lookup after token issue

## See also

[Module overview](../../../docs/MODULES.md#auth) · [Keycloak setup](../../../docs/KEYCLOAK_SETUP.md)

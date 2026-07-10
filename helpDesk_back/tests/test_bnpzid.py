"""Unit tests for bnpzID SSO service logic (security-critical bits)."""

import pytest

from app.auth.errors import AuthenticationError
from app.auth.services import bnpzid_service as bz
from app.config import Settings
from app.core.enums import Role


def _settings(**overrides) -> Settings:
    base = dict(
        database_url="postgresql+asyncpg://test",
        jwt_secret="test-secret-key",
        bnpzid_enabled=True,
        bnpzid_base_url="https://192.168.101.6:5000",
        bnpzid_client_id="helpdesk",
        bnpzid_client_secret="s3cr3t-client",
        bnpzid_redirect_uri="http://192.168.1.50/api/v1/auth/bnpzid/callback",
    )
    base.update(overrides)
    return Settings(**base)


def test_source_ip_list_parses_env_bound_field() -> None:
    # Regression: the field name must equal the env var (pydantic-settings binds
    # by name), so BNPZID_ALLOWED_SOURCE_IPS reaches bnpzid_allowed_source_ips.
    assert _settings(bnpzid_allowed_source_ips="192.168.101.6, 10.0.0.1").bnpzid_source_ip_list == [
        "192.168.101.6",
        "10.0.0.1",
    ]
    assert _settings().bnpzid_source_ip_list == []


def test_is_configured_requires_all_fields() -> None:
    assert bz.is_bnpzid_configured(_settings()) is True
    assert bz.is_bnpzid_configured(_settings(bnpzid_enabled=False)) is False
    assert bz.is_bnpzid_configured(_settings(bnpzid_client_secret="")) is False
    assert bz.is_bnpzid_configured(_settings(bnpzid_redirect_uri="")) is False


def test_build_authorize_url_has_required_params() -> None:
    url = bz.build_authorize_url(_settings(), "abc123")
    assert url.startswith("https://192.168.101.6:5000/bnpzid/authorize/?")
    assert "client_id=helpdesk" in url
    assert "state=abc123" in url
    assert "redirect_uri=http" in url


def test_state_sign_verify_round_trip() -> None:
    s = _settings()
    cookie = bz.sign_state(s, state="xyz", next_path="/dashboard")
    data = bz.read_state(s, cookie)
    assert data["state"] == "xyz"
    assert data["next"] == "/dashboard"


def test_state_rejects_tampered_or_foreign_secret() -> None:
    cookie = bz.sign_state(_settings(), state="xyz", next_path="/x")
    other = _settings(jwt_secret="different-secret")
    with pytest.raises(AuthenticationError):
        bz.read_state(other, cookie)


def test_states_match_is_strict() -> None:
    assert bz.states_match("a-random-state", "a-random-state") is True
    assert bz.states_match("a", "b") is False
    assert bz.states_match("", "") is False


def test_consume_code_is_single_use() -> None:
    assert bz.consume_code("code-unique-1") is True
    assert bz.consume_code("code-unique-1") is False  # replay rejected


def test_verify_client_credentials() -> None:
    s = _settings()
    assert bz.verify_client_credentials(s, "helpdesk", "s3cr3t-client") is True
    assert bz.verify_client_credentials(s, "helpdesk", "wrong") is False
    assert bz.verify_client_credentials(s, "other", "s3cr3t-client") is False
    assert bz.verify_client_credentials(s, "", "") is False


def test_map_role_is_conservative() -> None:
    s = _settings()
    assert bz.map_role(s, "admin") == Role.USER  # never elevate from claim
    assert bz.map_role(s, "hr") == Role.USER
    assert bz.map_role(s, None) == Role.USER
    assert bz.map_role(s, "executor") == Role.EXECUTOR
    assert bz.map_role(s, "user") == Role.USER


def test_synth_email_is_valid_and_sanitized() -> None:
    assert bz.synth_email("maruf_shabonov_9112") == "maruf_shabonov_9112@bnpzid.example.com"
    # unsafe chars collapse to dots, no leading/trailing dot in local part
    assert bz.synth_email("bad name!") == "bad.name@bnpzid.example.com"


def test_safe_next_path_blocks_open_redirect() -> None:
    assert bz.safe_next_path("/tickets") == "/tickets"
    assert bz.safe_next_path("//evil.com") == "/dashboard"
    assert bz.safe_next_path("https://evil.com") == "/dashboard"
    assert bz.safe_next_path(None) == "/dashboard"
    assert bz.safe_next_path("") == "/dashboard"

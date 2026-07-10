from functools import lru_cache
import json
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "HelpDesk Backend"
    app_version: str = "0.1.0"
    app_description: str = "Backend Service for HelpDesk Development"
    app_contact: str = "devshilov@gmail.com"

    api_prefix: str = "/api/v1"
    debug: bool = False

    database_url: str = Field(..., env="DATABASE_URL")

    # RabbitMQ (optional; if not set, outbox publisher is disabled)
    rabbitmq_url: str | None = Field(
        default=None,
        env="RABBITMQ_URL",
        description="AMQP URL for RabbitMQ (e.g. amqp://guest:guest@localhost/).",
    )
    rabbitmq_exchange: str = Field(
        default="helpdesk",
        env="RABBITMQ_EXCHANGE",
        description="RabbitMQ exchange name for notification events.",
    )
    rabbitmq_queue: str = Field(
        default="notification.created",
        env="RABBITMQ_QUEUE",
        description="RabbitMQ queue name for notification.created events.",
    )
    outbox_batch_size: int = Field(
        default=50,
        env="OUTBOX_BATCH_SIZE",
        description="Max outbox rows to process per dispatcher run.",
    )
    outbox_interval_seconds: float = Field(
        default=5.0,
        env="OUTBOX_INTERVAL_SECONDS",
        description="Seconds between outbox dispatcher runs.",
    )
    outbox_max_attempts: int = Field(
        default=5,
        env="OUTBOX_MAX_ATTEMPTS",
        description="Max publish attempts before marking outbox row as failed.",
    )

    # MinIO object storage
    minio_endpoint: str | None = Field(
        default=None,
        env="MINIO_ENDPOINT",
        description="MinIO host:port without scheme, e.g. localhost:9000",
    )
    minio_access_key: str | None = Field(
        default=None,
        env="MINIO_ACCESS_KEY",
        description="MinIO access key.",
    )
    minio_secret_key: str | None = Field(
        default=None,
        env="MINIO_SECRET_KEY",
        description="MinIO secret key.",
    )
    minio_bucket_name: str = Field(
        default="assets",
        env="MINIO_BUCKET_NAME",
        description="Bucket for asset images.",
    )
    minio_secure: bool = Field(
        default=False,
        env="MINIO_SECURE",
        description="Use HTTPS for MinIO endpoint.",
    )
    minio_region: str | None = Field(
        default=None,
        env="MINIO_REGION",
        description="Optional MinIO region.",
    )
    minio_public_base_url: str | None = Field(
        default=None,
        env="MINIO_PUBLIC_BASE_URL",
        description="Optional public base URL for object links (e.g. https://cdn.example.com).",
    )

    # Database pool settings
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")

    # Local JWT auth (HS256, issued by this backend)
    jwt_secret: str = Field(
        ...,
        env="JWT_SECRET",
        description="Secret key for signing/verifying access tokens (HS256). Required.",
    )
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_issuer: str = Field(default="helpdesk", env="JWT_ISSUER")
    access_token_ttl_seconds: int = Field(
        default=43200,
        env="ACCESS_TOKEN_TTL_SECONDS",
        description="Access token lifetime in seconds (default 12h).",
    )

    # Bootstrap admin: auto-created on startup if it does not exist yet.
    bootstrap_admin_username: str | None = Field(
        default=None, env="BOOTSTRAP_ADMIN_USERNAME"
    )
    bootstrap_admin_password: str | None = Field(
        default=None, env="BOOTSTRAP_ADMIN_PASSWORD"
    )
    bootstrap_admin_email: str = Field(
        default="admin@example.com", env="BOOTSTRAP_ADMIN_EMAIL"
    )
    bootstrap_admin_full_name: str = Field(
        default="Administrator", env="BOOTSTRAP_ADMIN_FULL_NAME"
    )

    # Demo fixtures: seed sample users/tickets on startup. Keep OFF in production.
    seed_demo_data: bool = Field(
        default=False,
        env="SEED_DEMO_DATA",
        description="When true, idempotently seed demo users and tickets on startup.",
    )

    # ------------------------------
    # bnpzID SSO (FaceID) — optional external identity provider
    # ------------------------------
    bnpzid_enabled: bool = Field(default=False, env="BNPZID_ENABLED")
    bnpzid_base_url: str = Field(
        default="",
        env="BNPZID_BASE_URL",
        description="Public base URL of the bnpzID service, e.g. https://192.168.101.6:5000",
    )
    bnpzid_client_id: str = Field(default="", env="BNPZID_CLIENT_ID")
    bnpzid_client_secret: str = Field(default="", env="BNPZID_CLIENT_SECRET")
    bnpzid_redirect_uri: str = Field(
        default="",
        env="BNPZID_REDIRECT_URI",
        description="Exact callback URL registered on bnpzID (allowed_redirects). "
        "e.g. http://192.168.1.50/api/v1/auth/bnpzid/callback",
    )
    bnpzid_verify_ssl: bool = Field(
        default=False,
        env="BNPZID_VERIFY_SSL",
        description="Verify bnpzID TLS cert on server-to-server exchange. "
        "False for self-signed; set a CA path via BNPZID_CA_BUNDLE instead when possible.",
    )
    bnpzid_ca_bundle: str | None = Field(default=None, env="BNPZID_CA_BUNDLE")
    bnpzid_default_role: str = Field(
        default="user",
        env="BNPZID_DEFAULT_ROLE",
        description="Helpdesk role assigned to auto-provisioned bnpzID users.",
    )
    bnpzid_always_require_face: bool = Field(
        default=True,
        env="BNPZID_ALWAYS_REQUIRE_FACE",
        description="access-check returns face_id_required=true for every bnpzID login.",
    )
    # Field NAME must equal the env var (pydantic-settings v2 binds by name;
    # the deprecated Field(env=...) is ignored). Hence no `_raw` suffix here.
    bnpzid_allowed_source_ips: str | None = Field(
        default=None,
        description="Comma-separated IPs allowed to call the access-check callback "
        "(the bnpzID server), e.g. 192.168.101.6. Empty disables the IP check. "
        "Env var: BNPZID_ALLOWED_SOURCE_IPS.",
    )
    bnpzid_state_ttl_seconds: int = Field(default=600, env="BNPZID_STATE_TTL_SECONDS")

    @property
    def bnpzid_source_ip_list(self) -> List[str]:
        raw = self.bnpzid_allowed_source_ips
        if not raw:
            return []
        return [ip.strip() for ip in raw.split(",") if ip.strip()]

    @property
    def bnpzid_ssl_verify(self):
        """Value to pass to httpx `verify`: a CA path, or a bool."""
        if self.bnpzid_ca_bundle:
            return self.bnpzid_ca_bundle
        return self.bnpzid_verify_ssl

    @field_validator("jwt_secret", mode="before")
    @classmethod
    def require_non_empty_jwt_secret(cls, v: str) -> str:
        """Fail fast if JWT_SECRET is missing/blank — tokens cannot be signed without it."""
        value = (v or "").strip()
        if not value:
            raise ValueError("JWT_SECRET must be set to a non-empty value.")
        return value

    allowed_cors_origins_raw: str | None = Field(
        default=None,
        env="ALLOWED_CORS_ORIGINS",
        description="Comma-separated list or JSON list of allowed CORS origins",
    )

    @property
    def allowed_cors_origins(self) -> List[str]:
        """
        Return parsed CORS origins from env (comma-separated or JSON list).
        """
        value = self.allowed_cors_origins_raw
        if value is None or value == "":
            return ["http://localhost:5173"]
        # Try JSON list first
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            pass
        # Fallback to comma-separated string
        return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()

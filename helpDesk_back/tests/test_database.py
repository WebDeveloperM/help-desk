"""Tests for core database initialization."""

from unittest.mock import MagicMock, patch

from app.core import database
from app.core.database import init_database
from app.config import Settings


def test_init_database_uses_configured_pool_sizes(monkeypatch) -> None:
    """init_database must pass Settings.db_pool_size / db_max_overflow to the engine."""
    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database, "_session_factory", None)

    settings = Settings(
        database_url="postgresql+asyncpg://test:test@localhost/test",
        jwt_secret="test-secret-key",
        db_pool_size=42,
        db_max_overflow=7,
        debug=True,
    )

    with patch("app.core.database.create_async_engine") as create_engine:
        create_engine.return_value = MagicMock()
        init_database(settings)

    create_engine.assert_called_once()
    kwargs = create_engine.call_args.kwargs
    assert kwargs["pool_size"] == 42
    assert kwargs["max_overflow"] == 7

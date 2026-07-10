"""Pytest configuration and fixtures."""

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings


@pytest.fixture
def settings() -> Generator[Settings, None, None]:
    """Provide test settings."""
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
    os.environ.setdefault("JWT_SECRET", "test-secret-key")
    os.environ.setdefault("DEBUG", "true")

    from app.config import get_settings

    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest.fixture
def client(settings: Settings) -> Generator[TestClient, None, None]:
    """Provide test client."""
    from app.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

"""Asset dependencies."""

from app.asset.dependencies.asset_deps import (
    get_asset_repository,
    get_asset_service,
    get_asset_storage_service,
    get_asset_vectorizer,
)

__all__ = [
    "get_asset_repository",
    "get_asset_service",
    "get_asset_storage_service",
    "get_asset_vectorizer",
]

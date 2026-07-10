"""Asset dependencies for dependency injection."""

from typing import Annotated
from fastapi import Depends

from app.asset.repositories import AssetRepository, SQLAlchemyAssetRepository
from app.asset.services import AssetService, AssetServiceImpl
from app.asset.services.storage import AssetImageStorageService
from app.asset.services.vectorizer import AssetVectorizer
from app.config import Settings, get_settings
from app.core.database import DatabaseSession
from app.department.dependencies import get_department_repository
from app.department.repositories import DepartmentRepository
from app.user.dependencies import get_user_repository
from app.user.repositories import UserRepository


def get_asset_repository(session: DatabaseSession) -> AssetRepository:
    """Get asset repository instance."""
    return SQLAlchemyAssetRepository(session)


def get_asset_vectorizer() -> AssetVectorizer:
    """Get deterministic local vectorizer."""
    return AssetVectorizer(dimension=16)


def get_asset_storage_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AssetImageStorageService | None:
    """Get MinIO storage service when storage config is available."""
    if not settings.minio_endpoint:
        return None
    return AssetImageStorageService(settings)


def get_asset_service(
    repository: Annotated[AssetRepository, Depends(get_asset_repository)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    department_repository: Annotated[
        DepartmentRepository, Depends(get_department_repository)
    ],
    vectorizer: Annotated[AssetVectorizer, Depends(get_asset_vectorizer)],
    storage_service: Annotated[
        AssetImageStorageService | None, Depends(get_asset_storage_service)
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AssetService:
    """Get asset service instance."""
    return AssetServiceImpl(
        repository=repository,
        user_repository=user_repository,
        department_repository=department_repository,
        vectorizer=vectorizer,
        storage_service=storage_service,
        settings=settings,
    )

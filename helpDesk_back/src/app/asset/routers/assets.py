"""Asset router with CRUD and image management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.asset.dependencies import get_asset_service
from app.asset.schemas import (
    AssetCreate,
    AssetCursorPageResponse,
    AssetFilterParams,
    AssetImageDeleteRequest,
    AssetImageUploadResponse,
    AssetResponse,
    AssetSortField,
    SortOrder,
    AssetUpdate,
)
from app.asset.services import AssetService
from app.auth.dependencies import get_current_user
from app.auth.schemas import TokenUser
from app.core.enums import AssetLifecycleStatus
from app.user.dependencies import get_current_user_model
from app.user.models import User

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset_endpoint(
    asset_data: AssetCreate,
    current_user: Annotated[User, Depends(get_current_user_model)],
    token_user: Annotated[TokenUser, Depends(get_current_user)],
    service: Annotated[AssetService, Depends(get_asset_service)],
) -> AssetResponse:
    """Create a new asset."""
    return await service.create_asset(
        asset_data,
        current_user=current_user,
        token_user=token_user,
    )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset_endpoint(
    asset_id: UUID,
    current_user: Annotated[User, Depends(get_current_user_model)],
    token_user: Annotated[TokenUser, Depends(get_current_user)],
    service: Annotated[AssetService, Depends(get_asset_service)],
) -> AssetResponse:
    """Get asset by id."""
    return await service.get_asset(
        asset_id,
        current_user=current_user,
        token_user=token_user,
    )


@router.get("", response_model=AssetCursorPageResponse)
async def list_assets_endpoint(
    current_user: Annotated[User, Depends(get_current_user_model)],
    token_user: Annotated[TokenUser, Depends(get_current_user)],
    service: Annotated[AssetService, Depends(get_asset_service)],
    asset_type: Annotated[str | None, Query()] = None,
    status: Annotated[AssetLifecycleStatus | None, Query()] = None,
    department_id: Annotated[UUID | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    similarity_query: Annotated[str | None, Query()] = None,
    include_inactive: Annotated[bool, Query()] = False,
    sort_by: Annotated[AssetSortField, Query()] = "name",
    sort_order: Annotated[SortOrder, Query()] = "asc",
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query()] = None,
) -> AssetCursorPageResponse:
    """List assets with cursor pagination."""
    filters = AssetFilterParams(
        asset_type=asset_type,
        status=status,
        department_id=department_id,
        search=search,
        similarity_query=similarity_query,
        include_inactive=include_inactive,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        cursor=cursor,
    )
    return await service.list_assets(
        filters,
        current_user=current_user,
        token_user=token_user,
    )


@router.patch("/{asset_id}", response_model=AssetResponse)
async def update_asset_endpoint(
    asset_id: UUID,
    asset_data: AssetUpdate,
    current_user: Annotated[User, Depends(get_current_user_model)],
    token_user: Annotated[TokenUser, Depends(get_current_user)],
    service: Annotated[AssetService, Depends(get_asset_service)],
) -> AssetResponse:
    """Update asset."""
    return await service.update_asset(
        asset_id,
        asset_data,
        current_user=current_user,
        token_user=token_user,
    )


@router.delete("/{asset_id}", response_model=AssetResponse)
async def delete_asset_endpoint(
    asset_id: UUID,
    current_user: Annotated[User, Depends(get_current_user_model)],
    token_user: Annotated[TokenUser, Depends(get_current_user)],
    service: Annotated[AssetService, Depends(get_asset_service)],
) -> AssetResponse:
    """Soft-delete asset."""
    return await service.delete_asset(
        asset_id,
        current_user=current_user,
        token_user=token_user,
    )


@router.post(
    "/{asset_id}/images",
    response_model=AssetImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_asset_image_endpoint(
    asset_id: UUID,
    file: Annotated[UploadFile, File(...)],
    current_user: Annotated[User, Depends(get_current_user_model)],
    token_user: Annotated[TokenUser, Depends(get_current_user)],
    service: Annotated[AssetService, Depends(get_asset_service)],
) -> AssetImageUploadResponse:
    """Upload image for asset."""
    image_url = await service.upload_asset_image(
        asset_id,
        file,
        current_user=current_user,
        token_user=token_user,
    )
    return AssetImageUploadResponse(image_url=image_url)


@router.delete("/{asset_id}/images", response_model=AssetResponse)
async def delete_asset_image_endpoint(
    asset_id: UUID,
    payload: AssetImageDeleteRequest,
    current_user: Annotated[User, Depends(get_current_user_model)],
    token_user: Annotated[TokenUser, Depends(get_current_user)],
    service: Annotated[AssetService, Depends(get_asset_service)],
) -> AssetResponse:
    """Delete image from asset."""
    return await service.delete_asset_image(
        asset_id,
        payload.image_url,
        current_user=current_user,
        token_user=token_user,
    )

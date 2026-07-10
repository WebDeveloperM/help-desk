"""Asset service with business rules."""

from __future__ import annotations

import base64
import json
from uuid import UUID

from fastapi import UploadFile

from app.asset.exceptions import (
    AssetAlreadyExistsError,
    AssetDeleteForbiddenError,
    AssetNotFoundError,
    AssetPermissionDeniedError,
    AssetValidationError,
)
from app.asset.models import Asset
from app.asset.repositories import AssetRepository
from app.asset.schemas import (
    AssetCreate,
    AssetCursorPageResponse,
    AssetFilterParams,
    AssetResponse,
    AssetUpdate,
)
from app.asset.services.interfaces import AssetService
from app.asset.services.storage import AssetImageStorageService
from app.asset.services.vectorizer import AssetVectorizer
from app.auth.schemas import TokenUser
from app.auth.services import has_any_role
from app.config import Settings
from app.department.repositories import DepartmentRepository
from app.user.models import User
from app.user.repositories import UserRepository


class AssetServiceImpl(AssetService):
    """Asset business logic implementation."""

    def __init__(
        self,
        repository: AssetRepository,
        user_repository: UserRepository,
        department_repository: DepartmentRepository,
        vectorizer: AssetVectorizer,
        storage_service: AssetImageStorageService | None,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.user_repository = user_repository
        self.department_repository = department_repository
        self.vectorizer = vectorizer
        self.storage_service = storage_service
        self.settings = settings

    async def get_by_id(self, asset_id: UUID) -> Asset | None:
        """Return asset entity by ID."""
        return await self.repository.get_by_id(asset_id)

    def _is_admin(self, token_user: TokenUser) -> bool:
        """Return True when token has admin role."""
        return has_any_role(token_user, ["admin"], self.settings)

    def _is_department_head(self, token_user: TokenUser) -> bool:
        """Return True when token has department_head role."""
        return has_any_role(token_user, ["department_head"], self.settings)

    def _require_asset_role(self, token_user: TokenUser) -> None:
        """Ensure user has role allowed to work with assets."""
        if self._is_admin(token_user):
            return
        if self._is_department_head(token_user):
            return
        raise AssetPermissionDeniedError(
            detail="Только администратор или глава отдела может работать с активами"
        )

    async def _require_department_head_for_department(
        self,
        department_id: UUID,
        current_user: User,
    ) -> None:
        """Ensure current user is head of provided department."""
        if current_user.department_id != department_id:
            raise AssetPermissionDeniedError(
                detail="Глава отдела может управлять активами только своего отдела"
            )
        department = await self.department_repository.get_by_id(department_id)
        if department is None:
            raise AssetValidationError(detail="Указанный департамент не существует")
        if department.head_user_id != current_user.id:
            raise AssetPermissionDeniedError(
                detail="Только назначенный глава отдела может управлять активами департамента"
            )

    async def _ensure_asset_scope(
        self, asset: Asset, current_user: User, token_user: TokenUser
    ) -> None:
        """Ensure asset is visible for current principal."""
        if self._is_admin(token_user):
            return
        if current_user.department_id != asset.department_id:
            raise AssetPermissionDeniedError(
                detail="Доступ к активам других департаментов запрещен"
            )

    async def _validate_owner_department(
        self,
        assigned_user_id: UUID | None,
        department_id: UUID,
    ) -> None:
        """Ensure assigned owner belongs to asset department."""
        if assigned_user_id is None:
            return
        owner = await self.user_repository.get_by_id(assigned_user_id)
        if owner is None:
            raise AssetValidationError(detail="Указанный владелец актива не существует")
        if owner.department_id != department_id:
            raise AssetValidationError(
                detail="Владелец актива должен принадлежать тому же департаменту"
            )

    def _compose_embedding_text(self, data: dict) -> str:
        """Build a text payload for vectorization."""
        parts = [
            data.get("name"),
            data.get("asset_type"),
            data.get("inventory_number"),
            data.get("serial_number"),
            data.get("location"),
            data.get("notes"),
        ]
        return " ".join(part for part in parts if isinstance(part, str) and part.strip())

    def _encode_cursor(
        self,
        *,
        mode: str,
        value: str,
        asset_id: UUID,
        sort_by: str,
        sort_order: str,
    ) -> str:
        """Encode cursor payload."""
        payload = {
            "m": mode,
            "v": value,
            "id": str(asset_id),
            "s": sort_by,
            "o": sort_order,
        }
        raw = json.dumps(payload).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8")

    def _decode_cursor(self, cursor: str) -> dict[str, str]:
        """Decode cursor payload."""
        try:
            raw = base64.urlsafe_b64decode(cursor.encode("utf-8"))
            payload = json.loads(raw.decode("utf-8"))
            return payload
        except Exception as exc:
            raise AssetValidationError(detail="Некорректный cursor пагинации") from exc

    async def get_asset(
        self,
        asset_id: UUID,
        *,
        current_user: User,
        token_user: TokenUser,
    ) -> AssetResponse:
        """Return asset response by ID."""
        self._require_asset_role(token_user)
        asset = await self.repository.get_by_id(asset_id)
        if asset is None:
            raise AssetNotFoundError(asset_id=str(asset_id))
        await self._ensure_asset_scope(asset, current_user, token_user)
        return AssetResponse.model_validate(asset)

    async def create_asset(
        self,
        asset_data: AssetCreate,
        *,
        current_user: User,
        token_user: TokenUser,
    ) -> AssetResponse:
        """Create asset with permission and uniqueness checks."""
        self._require_asset_role(token_user)
        is_admin = self._is_admin(token_user)
        if not is_admin:
            await self._require_department_head_for_department(
                asset_data.department_id, current_user
            )

        existing = await self.repository.get_by_inventory_number(
            asset_data.inventory_number
        )
        if existing:
            raise AssetAlreadyExistsError(asset_data.inventory_number)
        await self._validate_owner_department(
            asset_data.assigned_user_id, asset_data.department_id
        )
        embedding_text = self._compose_embedding_text(asset_data.model_dump())
        embedding = self.vectorizer.encode(embedding_text)
        created = await self.repository.create(asset_data, embedding=embedding)
        return AssetResponse.model_validate(created)

    async def update_asset(
        self,
        asset_id: UUID,
        asset_data: AssetUpdate,
        *,
        current_user: User,
        token_user: TokenUser,
    ) -> AssetResponse:
        """Update asset with role and scope checks."""
        self._require_asset_role(token_user)
        asset = await self.repository.get_by_id(asset_id)
        if asset is None:
            raise AssetNotFoundError(asset_id=str(asset_id))

        is_admin = self._is_admin(token_user)
        target_department_id = asset_data.department_id or asset.department_id
        if not is_admin:
            await self._require_department_head_for_department(
                asset.department_id, current_user
            )
            if target_department_id != asset.department_id:
                raise AssetPermissionDeniedError(
                    detail="Глава отдела не может переносить активы в другой департамент"
                )

        if (
            asset_data.inventory_number
            and asset_data.inventory_number != asset.inventory_number
        ):
            existing = await self.repository.get_by_inventory_number(
                asset_data.inventory_number
            )
            if existing and existing.id != asset_id:
                raise AssetAlreadyExistsError(asset_data.inventory_number)

        await self._validate_owner_department(
            asset_data.assigned_user_id, target_department_id
        )

        merged_payload: dict[str, str | None] = {
            "name": asset.name,
            "asset_type": asset.asset_type,
            "inventory_number": asset.inventory_number,
            "serial_number": asset.serial_number,
            "location": asset.location,
            "notes": asset.notes,
        }
        merged_payload.update(asset_data.model_dump(exclude_unset=True))
        embedding_text = self._compose_embedding_text(merged_payload)
        embedding = self.vectorizer.encode(embedding_text)
        updated = await self.repository.update(asset_id, asset_data, embedding=embedding)
        if updated is None:
            raise AssetNotFoundError(asset_id=str(asset_id))
        return AssetResponse.model_validate(updated)

    async def delete_asset(
        self,
        asset_id: UUID,
        *,
        current_user: User,
        token_user: TokenUser,
    ) -> AssetResponse:
        """Soft-delete an asset."""
        self._require_asset_role(token_user)
        asset = await self.repository.get_by_id(asset_id)
        if asset is None:
            raise AssetNotFoundError(asset_id=str(asset_id))

        if not self._is_admin(token_user):
            await self._require_department_head_for_department(
                asset.department_id, current_user
            )
        if not asset.is_active:
            raise AssetDeleteForbiddenError(detail="Актив уже деактивирован")
        deleted = await self.repository.soft_delete(asset_id)
        if deleted is None:
            raise AssetNotFoundError(asset_id=str(asset_id))
        return AssetResponse.model_validate(deleted)

    async def list_assets(
        self,
        filters: AssetFilterParams,
        *,
        current_user: User,
        token_user: TokenUser,
    ) -> AssetCursorPageResponse:
        """Return cursor-based paginated assets."""
        self._require_asset_role(token_user)
        is_admin = self._is_admin(token_user)
        restrict_department_id = None if is_admin else current_user.department_id
        if not is_admin and restrict_department_id is None:
            raise AssetPermissionDeniedError(
                detail="Пользователь без департамента не может просматривать активы"
            )

        similarity_embedding = None
        if filters.similarity_query:
            similarity_embedding = self.vectorizer.encode(filters.similarity_query)

        cursor_value: str | None = None
        cursor_id: UUID | None = None
        if filters.cursor:
            payload = self._decode_cursor(filters.cursor)
            if payload.get("s") != filters.sort_by or payload.get("o") != filters.sort_order:
                raise AssetValidationError(
                    detail="Параметры сортировки не совпадают с переданным cursor"
                )
            cursor_value = payload.get("v")
            cursor_id_raw = payload.get("id")
            if not cursor_value or not cursor_id_raw:
                raise AssetValidationError(detail="Некорректный cursor пагинации")
            cursor_id = UUID(cursor_id_raw)

        items, next_value, next_id = await self.repository.list_with_cursor(
            filters,
            restrict_department_id=restrict_department_id,
            similarity_embedding=similarity_embedding,
            cursor_value=cursor_value,
            cursor_id=cursor_id,
        )
        has_more = next_value is not None and next_id is not None
        next_cursor = None
        if has_more:
            mode = "similarity" if filters.similarity_query else "default"
            next_cursor = self._encode_cursor(
                mode=mode,
                value=next_value,
                asset_id=next_id,
                sort_by=filters.sort_by,
                sort_order=filters.sort_order,
            )
        return AssetCursorPageResponse(
            items=[AssetResponse.model_validate(item) for item in items],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def upload_asset_image(
        self,
        asset_id: UUID,
        file: UploadFile,
        *,
        current_user: User,
        token_user: TokenUser,
    ) -> str:
        """Upload image and append URL to asset."""
        self._require_asset_role(token_user)
        if self.storage_service is None:
            raise AssetValidationError(detail="Хранилище MinIO не настроено")
        asset = await self.repository.get_by_id(asset_id)
        if asset is None:
            raise AssetNotFoundError(asset_id=str(asset_id))
        await self._ensure_asset_scope(asset, current_user, token_user)
        if not self._is_admin(token_user):
            await self._require_department_head_for_department(
                asset.department_id, current_user
            )
        image_url = await self.storage_service.upload_image(asset_id, file)
        updated = await self.repository.append_image_url(asset_id, image_url)
        if updated is None:
            raise AssetNotFoundError(asset_id=str(asset_id))
        return image_url

    async def delete_asset_image(
        self,
        asset_id: UUID,
        image_url: str,
        *,
        current_user: User,
        token_user: TokenUser,
    ) -> AssetResponse:
        """Delete image from object storage and asset URL list."""
        self._require_asset_role(token_user)
        if self.storage_service is None:
            raise AssetValidationError(detail="Хранилище MinIO не настроено")
        asset = await self.repository.get_by_id(asset_id)
        if asset is None:
            raise AssetNotFoundError(asset_id=str(asset_id))
        await self._ensure_asset_scope(asset, current_user, token_user)
        if not self._is_admin(token_user):
            await self._require_department_head_for_department(
                asset.department_id, current_user
            )
        self.storage_service.delete_image(image_url)
        updated = await self.repository.remove_image_url(asset_id, image_url)
        if updated is None:
            raise AssetNotFoundError(asset_id=str(asset_id))
        return AssetResponse.model_validate(updated)

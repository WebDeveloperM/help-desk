"""MinIO storage service for asset images."""

from __future__ import annotations

import io
from uuid import UUID, uuid4

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from app.asset.exceptions import AssetStorageError, AssetValidationError
from app.config import Settings


class AssetImageStorageService:
    """Handles asset image uploads/deletes in MinIO."""

    def __init__(self, settings: Settings) -> None:
        if not settings.minio_endpoint:
            raise AssetStorageError("Не настроен endpoint для MinIO")
        if not settings.minio_access_key or not settings.minio_secret_key:
            raise AssetStorageError("Не настроены учетные данные MinIO")

        self.settings = settings
        self.bucket = settings.minio_bucket_name
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
            region=settings.minio_region,
        )

    def _ensure_bucket(self) -> None:
        """Create bucket on-demand if it does not exist."""
        if self.client.bucket_exists(self.bucket):
            return
        self.client.make_bucket(self.bucket)

    def _build_object_url(self, object_name: str) -> str:
        """Build public URL for object."""
        if self.settings.minio_public_base_url:
            base = self.settings.minio_public_base_url.rstrip("/")
            return f"{base}/{self.bucket}/{object_name}"
        scheme = "https" if self.settings.minio_secure else "http"
        return f"{scheme}://{self.settings.minio_endpoint}/{self.bucket}/{object_name}"

    def _extract_object_name(self, image_url: str) -> str:
        """Extract object key from URL."""
        marker = f"/{self.bucket}/"
        if marker not in image_url:
            raise AssetValidationError(
                detail="Некорректный формат ссылки на изображение актива"
            )
        return image_url.split(marker, maxsplit=1)[1]

    async def upload_image(self, asset_id: UUID, file: UploadFile) -> str:
        """Upload image and return URL."""
        if not file.content_type or not file.content_type.startswith("image/"):
            raise AssetValidationError(detail="Разрешена загрузка только изображений")
        payload = await file.read()
        if not payload:
            raise AssetValidationError(detail="Файл изображения пуст")

        safe_name = (file.filename or "image").replace("/", "_").replace("\\", "_")
        object_name = f"assets/{asset_id}/{uuid4()}_{safe_name}"
        try:
            self._ensure_bucket()
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=object_name,
                data=io.BytesIO(payload),
                length=len(payload),
                content_type=file.content_type,
            )
        except S3Error as exc:
            raise AssetStorageError(
                detail=f"Не удалось загрузить изображение актива: {exc.code}"
            ) from exc
        return self._build_object_url(object_name)

    def delete_image(self, image_url: str) -> None:
        """Delete image by URL."""
        object_name = self._extract_object_name(image_url)
        try:
            self.client.remove_object(self.bucket, object_name)
        except S3Error as exc:
            raise AssetStorageError(
                detail=f"Не удалось удалить изображение актива: {exc.code}"
            ) from exc

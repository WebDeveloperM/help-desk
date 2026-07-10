"""Asset domain exceptions with HTTP mapping."""

from fastapi import HTTPException, status


class AssetNotFoundError(HTTPException):
    """Raised when asset is not found."""

    def __init__(self, asset_id: str | None = None, detail: str | None = None) -> None:
        message = detail or (
            f"Актив с идентификатором {asset_id} не найден" if asset_id else "Актив не найден"
        )
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)


class AssetAlreadyExistsError(HTTPException):
    """Raised when an asset already exists."""

    def __init__(self, inventory_number: str | None = None) -> None:
        message = (
            f"Актив с инвентарным номером '{inventory_number}' уже существует"
            if inventory_number
            else "Актив с таким инвентарным номером уже существует"
        )
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


class AssetAlreadyLinkedError(HTTPException):
    """Raised when attempting to create a duplicate ticket-asset relation."""

    def __init__(self, detail: str = "Актив уже привязан к указанной заявке") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class AssetDeleteForbiddenError(HTTPException):
    """Raised when asset cannot be deleted."""

    def __init__(
        self, detail: str = "Недостаточно прав для деактивации актива"
    ) -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class AssetPermissionDeniedError(HTTPException):
    """Raised when user has no permission for an asset action."""

    def __init__(
        self, detail: str = "Недостаточно прав для выполнения операции с активом"
    ) -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class AssetValidationError(HTTPException):
    """Raised when asset validation fails."""

    def __init__(self, detail: str = "Ошибка валидации данных актива") -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class AssetStorageError(HTTPException):
    """Raised when object storage operation fails."""

    def __init__(
        self, detail: str = "Не удалось выполнить операцию с хранилищем изображений"
    ) -> None:
        super().__init__(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail)

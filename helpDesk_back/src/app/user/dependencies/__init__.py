"""User dependencies package."""

from app.user.dependencies.auth import (
    get_current_user_model,
    get_user_by_id,
    get_user_repository,
    get_user_service,
    require_user_create_permission,
    require_user_delete_permission,
    require_user_list_permission,
    require_user_permission,
)

__all__ = [
    "get_current_user_model",
    "get_user_by_id",
    "get_user_repository",
    "get_user_service",
    "require_user_create_permission",
    "require_user_delete_permission",
    "require_user_list_permission",
    "require_user_permission",
]

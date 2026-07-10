"""User module package."""

# Import only what's commonly needed externally
# Dependencies are imported directly where needed to avoid circular imports

from app.user.models import User
from app.user.routers import router
from app.user.schemas import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserSyncRequest,
    UserUpdate,
)
from app.user.services import UserService, UserServiceImpl
from app.user.repositories import SQLAlchemyUserRepository, UserRepository
from app.user.exceptions import (
    UserAlreadyExistsError,
    UserInactiveError,
    UserNotFoundError,
    UserPermissionDeniedError,
    UserValidationError,
)

__all__ = [
    # Models
    "User",
    # Router
    "router",
    # Schemas
    "UserCreate",
    "UserListResponse",
    "UserResponse",
    "UserSyncRequest",
    "UserUpdate",
    # Services
    "UserService",
    "UserServiceImpl",
    # Repositories
    "UserRepository",
    "SQLAlchemyUserRepository",
    # Exceptions
    "UserAlreadyExistsError",
    "UserInactiveError",
    "UserNotFoundError",
    "UserPermissionDeniedError",
    "UserValidationError",
]

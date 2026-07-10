"""System repositories."""

from app.system.repositories.interfaces import SystemRepository
from app.system.repositories.system_repo import SQLAlchemySystemRepository

__all__ = ["SystemRepository", "SQLAlchemySystemRepository"]

"""Auth routers package."""

from app.auth.routers.auth import router
from app.auth.routers.bnpzid import root_router as bnpzid_root_router
from app.auth.routers.bnpzid import router as bnpzid_router

__all__ = ["router", "bnpzid_router", "bnpzid_root_router"]

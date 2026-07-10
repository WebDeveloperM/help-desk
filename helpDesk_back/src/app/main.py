"""Main FastAPI application."""

import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

from app.asset.routers import router as asset_router
from app.auth.routers import bnpzid_root_router, bnpzid_router
from app.auth.routers import router as auth_router
from app.config import get_settings
from app.core.database import close_database, init_database
from app.seed import seed_database
from app.core.exceptions import DomainError
from app.department.routers import router as department_router
from app.notification.outbox_publisher import run_outbox_dispatcher
from app.notification.routers import router as notification_router
from app.ticket.routers import router as ticket_router
from app.user.routers import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """
    settings = get_settings()
    init_database(settings)
    await seed_database(settings)
    outbox_task: asyncio.Task | None = None
    if settings.rabbitmq_url:
        outbox_task = asyncio.create_task(run_outbox_dispatcher(settings))
    try:
        yield
    finally:
        if outbox_task is not None:
            outbox_task.cancel()
            try:
                await outbox_task
            except asyncio.CancelledError:
                pass
        await close_database()


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI app instance.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=settings.app_description,
        contact={"email": settings.app_contact},
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(bnpzid_router, prefix=settings.api_prefix)
    # Registered bnpzID callback path `/auth/callback` (no api prefix).
    app.include_router(bnpzid_root_router)
    app.include_router(asset_router, prefix=settings.api_prefix)
    app.include_router(user_router, prefix=settings.api_prefix)
    app.include_router(ticket_router, prefix=settings.api_prefix)
    app.include_router(department_router, prefix=settings.api_prefix)
    app.include_router(notification_router, prefix=settings.api_prefix)

    @app.exception_handler(DomainError)
    async def domain_error_handler(request, exc: DomainError) -> JSONResponse:
        """Render DomainError with an `error_code` + `error_params` envelope.

        Keeps `detail` for back-compat / non-i18n consumers; the frontend reads
        `error_code` to look up a translated template.
        """
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error_code": exc.error_code,
                "error_params": exc.error_params,
            },
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request, exc: Exception) -> JSONResponse:
        """Log unhandled exceptions and return 500 so the real error is visible in logs."""
        from fastapi import HTTPException

        if isinstance(exc, HTTPException):
            raise exc
        logger.exception(
            "Unhandled exception: %s\n%s",
            exc,
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Check server logs for details."},
        )

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint."""
        return {"message": "HelpDesk Backend API", "version": settings.app_version}

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}
    
    
    @app.get("/test")
    async def test() -> dict[str, str]:
        return {"message": "Test endpoint"}

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

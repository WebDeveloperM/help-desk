"""Bootstrap admin: ensure an initial admin account exists on startup.

Login is closed (only an admin creates accounts), so the very first admin is
seeded from environment settings. Idempotent: does nothing if a user with the
configured username already exists.
"""

import logging

from sqlalchemy.exc import IntegrityError

from app.config import Settings
from app.core.database import get_session_factory
from app.core.enums import Role
from app.user.repositories import SQLAlchemyUserRepository
from app.user.schemas import UserCreate
from app.auth.services.token_service import hash_password

logger = logging.getLogger(__name__)


async def ensure_bootstrap_admin(settings: Settings) -> None:
    """Create the bootstrap admin from settings if it does not exist yet."""
    username = (settings.bootstrap_admin_username or "").strip()
    password = settings.bootstrap_admin_password or ""
    if not username or not password:
        logger.info(
            "Bootstrap admin not configured (BOOTSTRAP_ADMIN_USERNAME/PASSWORD); skipping."
        )
        return

    session_factory = get_session_factory()
    async with session_factory() as session:
        repository = SQLAlchemyUserRepository(session)

        if await repository.get_by_username(username):
            return
        if await repository.exists_by_email(settings.bootstrap_admin_email):
            logger.warning(
                "Bootstrap admin email %s already in use; skipping admin seed.",
                settings.bootstrap_admin_email,
            )
            return

        try:
            await repository.create(
                UserCreate(
                    username=username,
                    password_hash=hash_password(password),
                    role=Role.ADMIN,
                    email=settings.bootstrap_admin_email,
                    full_name=settings.bootstrap_admin_full_name,
                    email_verified=True,
                )
            )
            await session.commit()
            logger.info("Bootstrap admin '%s' created.", username)
        except IntegrityError:
            # Concurrency guard: with multi-worker uvicorn, several workers run
            # this on first boot. The check above is a TOCTOU race, so a losing
            # worker hits the unique constraint — treat it as an idempotent no-op
            # instead of crashing startup.
            await session.rollback()
            logger.info(
                "Bootstrap admin '%s' already created concurrently; skipping.",
                username,
            )

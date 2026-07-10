"""Idempotent database seeding for startup / deploy.

Entry point is :func:`seed_database`, called from the app lifespan and from the
``python -m app.seed`` CLI. It always ensures the bootstrap admin, then — when
demo seeding is enabled — inserts a small, realistic set of demo users, appoints
department heads, and creates demo tickets. Every step checks for existence
first, so running it repeatedly is safe.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.services.bootstrap import ensure_bootstrap_admin
from app.auth.services.token_service import hash_password
from app.config import Settings
from app.core.database import get_session_factory
from app.core.enums import TicketStatus
from app.department.models import Department
from app.seed.data import (
    DEMO_PASSWORD,
    DEMO_TICKETS,
    DEMO_USERS,
    DEPARTMENT_HEADS,
)
from app.ticket.models import Ticket, TicketCategory, ticket_executors_table
from app.user.models import User
from app.user.repositories import SQLAlchemyUserRepository
from app.user.schemas import UserCreate

logger = logging.getLogger(__name__)


def _register_all_models() -> None:
    """Import every ORM model so SQLAlchemy can resolve cross-model relationships.

    In the running app this happens implicitly via router imports; when seeding
    is invoked standalone (``python -m app.seed``) the models must be imported
    explicitly, mirroring ``alembic/env.py``. Without this, configuring the
    ``User`` mapper fails on the ``User -> Asset`` relationship.
    """
    from app.asset.models import Asset  # noqa: F401
    from app.department.models import Department  # noqa: F401
    from app.notification.models import Notification, NotificationOutbox  # noqa: F401
    from app.ticket.models import (  # noqa: F401
        Ticket,
        TicketCategory,
        TicketComment,
        TicketTemplate,
    )
    from app.user.models import User, UserRole  # noqa: F401


async def seed_database(settings: Settings, include_demo: bool | None = None) -> None:
    """Run all seeders.

    Always ensures the bootstrap admin. Demo data is seeded only when
    ``include_demo`` is True (or, when None, when ``settings.seed_demo_data`` is).

    Args:
        settings: Application settings.
        include_demo: Explicit override for demo seeding; None uses the setting.
    """
    _register_all_models()
    await ensure_bootstrap_admin(settings)

    should_demo = settings.seed_demo_data if include_demo is None else include_demo
    if not should_demo:
        return

    # Best-effort: demo fixtures must never block app startup. The single commit
    # below is atomic, so a mid-way failure rolls back cleanly (nothing partial
    # persists) and startup continues without demo data.
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            await _seed_demo_data(session)
            await session.commit()
        logger.info("Demo data seeding complete.")
    except Exception:
        logger.exception(
            "Demo data seeding failed; continuing without demo data."
        )


async def _seed_demo_data(session: AsyncSession) -> None:
    """Seed demo users, department heads and tickets within one transaction."""
    departments = await _load_by_code(session, Department)
    categories = await _load_by_code(session, TicketCategory)
    user_repo = SQLAlchemyUserRepository(session)

    username_to_id = await _seed_users(session, user_repo, departments)
    await _appoint_department_heads(departments, username_to_id)
    await _seed_tickets(session, categories, username_to_id)


async def _load_by_code(session: AsyncSession, model) -> dict[str, object]:
    """Return {code: row} for a model that has a unique ``code`` column."""
    result = await session.execute(select(model))
    return {row.code: row for row in result.scalars().all()}


async def _seed_users(
    session: AsyncSession,
    user_repo: SQLAlchemyUserRepository,
    departments: dict[str, Department],
) -> dict[str, UUID]:
    """Create demo users that don't exist yet; return {username: user_id}."""
    username_to_id: dict[str, UUID] = {}

    for spec in DEMO_USERS:
        username = spec["username"]

        existing = await user_repo.get_by_username(username)
        if existing:
            username_to_id[username] = existing.id
            continue

        if await user_repo.exists_by_email(spec["email"]):
            logger.warning(
                "Demo user email %s already in use; skipping user %s.",
                spec["email"],
                username,
            )
            continue

        department = departments.get(spec["department_code"])
        if department is None:
            logger.warning(
                "Department %s not found; creating demo user %s without a department.",
                spec["department_code"],
                username,
            )

        user = await user_repo.create(
            UserCreate(
                username=username,
                password_hash=hash_password(DEMO_PASSWORD),
                role=spec["role"],
                email=spec["email"],
                full_name=spec["full_name"],
                department_id=department.id if department else None,
                position=spec.get("position"),
                phone=spec.get("phone"),
                email_verified=True,
            )
        )
        username_to_id[username] = user.id
        logger.info("Seeded demo user %s (%s).", username, spec["role"].value)

    return username_to_id


async def _appoint_department_heads(
    departments: dict[str, Department],
    username_to_id: dict[str, UUID],
) -> None:
    """Set head_user_id for demo departments, never overriding an existing head."""
    for dept_code, username in DEPARTMENT_HEADS.items():
        department = departments.get(dept_code)
        user_id = username_to_id.get(username)
        if department is None or user_id is None:
            continue
        if department.head_user_id is None:
            department.head_user_id = user_id
            logger.info("Appointed %s as head of %s.", username, dept_code)


async def _seed_tickets(
    session: AsyncSession,
    categories: dict[str, TicketCategory],
    username_to_id: dict[str, UUID],
) -> None:
    """Create demo tickets keyed by seed_key in ticket_metadata (idempotent)."""
    existing_keys = await _existing_ticket_seed_keys(session)

    for spec in DEMO_TICKETS:
        seed_key = spec["seed_key"]
        if seed_key in existing_keys:
            continue

        creator_id = username_to_id.get(spec["creator_username"])
        category = categories.get(spec["category_code"])
        if creator_id is None or category is None:
            logger.warning(
                "Skipping ticket %s: missing creator (%s) or category (%s).",
                seed_key,
                spec["creator_username"],
                spec["category_code"],
            )
            continue

        creator = await session.get(User, creator_id)
        if creator is None or creator.department_id is None:
            logger.warning(
                "Skipping ticket %s: creator %s has no department.",
                seed_key,
                spec["creator_username"],
            )
            continue

        executor_ids = [
            username_to_id[u]
            for u in spec.get("executor_usernames", [])
            if u in username_to_id
        ]

        status = spec["status"]
        assigned_department_id = (
            creator.department_id if status != TicketStatus.DRAFT else None
        )

        ticket = Ticket(
            title=spec["title"],
            description=spec["description"],
            category_id=category.id,
            created_by_id=creator_id,
            creator_department_id=creator.department_id,
            assigned_department_id=assigned_department_id,
            status=status,
            priority=spec["priority"],
            is_urgent=spec.get("is_urgent", False),
            progress_percent=spec.get("progress_percent", 0),
            ticket_metadata={"seed": True, "seed_key": seed_key},
        )
        if status == TicketStatus.COMPLETED:
            now = datetime.now(timezone.utc)
            ticket.completed_at = now
            ticket.actual_completion_date = now
            ticket.completed_by_id = executor_ids[0] if executor_ids else creator_id

        session.add(ticket)
        # Flush so the BEFORE INSERT trigger assigns ticket_number and we get ticket.id.
        await session.flush()
        await session.refresh(ticket)

        if executor_ids:
            await session.execute(
                insert(ticket_executors_table),
                [
                    {"ticket_id": ticket.id, "user_id": uid}
                    for uid in executor_ids
                ],
            )
            await session.flush()

        logger.info("Seeded demo ticket %s (%s).", ticket.ticket_number, seed_key)


async def _existing_ticket_seed_keys(session: AsyncSession) -> set[str]:
    """Return the set of seed_key values already present on tickets."""
    result = await session.execute(
        select(Ticket.ticket_metadata["seed_key"].astext).where(
            Ticket.ticket_metadata.isnot(None)
        )
    )
    return {row for (row,) in result.all() if row}

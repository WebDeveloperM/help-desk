"""Run database seeding from the command line.

Usage (inside the backend container, after migrations have run):

    python -m app.seed

Always seeds the bootstrap admin. Demo fixtures are seeded only when
``SEED_DEMO_DATA=true`` — the CLI respects the same guard as startup so running
it against a production database never injects demo accounts by accident.
"""

import asyncio
import logging

from app.config import get_settings
from app.core.database import close_database, init_database
from app.seed.seeder import seed_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.seed")


async def _run() -> None:
    settings = get_settings()
    init_database(settings)
    try:
        # Respect SEED_DEMO_DATA (do not force demo data): the same behavior as
        # startup, so this is safe to run in any environment.
        await seed_database(settings)
    finally:
        await close_database()
    logger.info("Seeding finished.")


if __name__ == "__main__":
    asyncio.run(_run())

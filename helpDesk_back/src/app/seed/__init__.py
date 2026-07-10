"""Database seeding package (idempotent fixtures for startup / deploy)."""

from app.seed.seeder import seed_database

__all__ = ["seed_database"]

"""System setting model - key/value storage."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemSetting(Base):
    """Key-value system settings (e.g. SLA hours, ticket_number_prefix)."""

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        nullable=False,
    )
    value: Mapped[str | None] = mapped_column(Text(), nullable=True)

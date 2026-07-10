"""SLA domain schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.core.enums import TicketPriority


class SlaStatus(str, Enum):
    """SLA status for a ticket."""

    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    OVERDUE = "overdue"
    COMPLETED_ON_TIME = "completed_on_time"
    COMPLETED_LATE = "completed_late"


class SlaPriorityRule(BaseModel):
    """SLA target for a specific ticket priority."""

    priority: TicketPriority = Field(..., description="Ticket priority")
    target_hours: int = Field(..., gt=0, description="Allowed completion window in hours")


class SlaConfig(BaseModel):
    """Normalized SLA configuration loaded from system settings."""

    rules: list[SlaPriorityRule] = Field(
        default_factory=list,
        description="SLA rules by priority",
    )


class SlaInfo(BaseModel):
    """SLA information attached to ticket response."""

    status: SlaStatus = Field(..., description="Current SLA status")
    planned_completion_date: datetime | None = Field(
        None,
        description="Planned completion date by SLA",
    )


AT_RISK_FRACTION = 0.25

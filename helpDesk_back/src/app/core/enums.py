"""Database ENUM types for PostgreSQL."""

import enum


class Role(str, enum.Enum):
    """User roles in the system."""

    USER = "user"
    DEPARTMENT_HEAD = "department_head"
    EXECUTOR = "executor"
    ADMIN = "admin"


class TicketStatus(str, enum.Enum):
    """Ticket status values."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    REJECTED = "rejected"
    APPROVED = "approved"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    WAITING_INFO = "waiting_info"
    COMPLETED = "completed"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    """Ticket priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationType(str, enum.Enum):
    """Notification types."""

    TICKET_CREATED = "ticket_created"
    TICKET_APPROVED = "ticket_approved"
    TICKET_REJECTED = "ticket_rejected"
    TICKET_ASSIGNED = "ticket_assigned"
    TICKET_COMPLETED = "ticket_completed"
    COMMENT_ADDED = "comment_added"
    STATUS_CHANGED = "status_changed"


class AssetLifecycleStatus(str, enum.Enum):
    """Asset lifecycle status values."""

    ACTIVE = "active"
    IN_REPAIR = "in_repair"
    RETIRED = "retired"
    LOST = "lost"


class ActionType(str, enum.Enum):
    """Action types for ticket history."""

    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    ASSIGNED = "assigned"
    COMMENT_ADDED = "comment_added"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CLOSED = "closed"


class OutboxStatus(str, enum.Enum):
    """Notification outbox delivery status."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"

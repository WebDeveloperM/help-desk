"""Ticket domain exceptions with HTTP mapping."""

from fastapi import status

from app.core.exceptions import DomainError


class TicketNotFoundError(DomainError):
    """Raised when ticket is not found."""

    def __init__(
        self, ticket_id: str | None = None, detail: str | None = None
    ) -> None:
        message = detail or (
            f"Ticket with id {ticket_id} not found"
            if ticket_id
            else "Ticket not found"
        )
        params = {"ticket_id": ticket_id} if ticket_id else {}
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="ticket.not_found",
            detail=message,
            error_params=params,
        )


class TicketAlreadyExistsError(DomainError):
    """Raised when ticket already exists."""

    def __init__(self, ticket_number: str | None = None) -> None:
        message = (
            f"Ticket with number '{ticket_number}' already exists"
            if ticket_number
            else "Ticket with this number already exists"
        )
        params = {"ticket_number": ticket_number} if ticket_number else {}
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="ticket.already_exists",
            detail=message,
            error_params=params,
        )


class TicketPermissionDeniedError(DomainError):
    """Raised when user doesn't have permission to perform ticket operation."""

    def __init__(
        self, detail: str = "You don't have permission to perform this action"
    ) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="ticket.permission_denied",
            detail=detail,
        )


class TicketValidationError(DomainError):
    """Raised when ticket data validation fails."""

    def __init__(self, detail: str = "Ticket data validation failed") -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="ticket.validation_failed",
            detail=detail,
        )


class TicketStatusTransitionError(DomainError):
    """Raised when ticket status transition is invalid."""

    def __init__(
        self,
        current_status: str | None = None,
        target_status: str | None = None,
        detail: str | None = None,
    ) -> None:
        message = detail or (
            f"Invalid status transition from {current_status} to {target_status}"
            if current_status and target_status
            else "Invalid ticket status transition"
        )
        params: dict[str, str] = {}
        if current_status:
            params["current_status"] = current_status
        if target_status:
            params["target_status"] = target_status
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="ticket.invalid_status_transition",
            detail=message,
            error_params=params,
        )

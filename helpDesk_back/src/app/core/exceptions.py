"""Base domain exception with structured error codes for client-side translation."""

from __future__ import annotations

from typing import Any, Mapping

from fastapi import HTTPException


class DomainError(HTTPException):
    """
    HTTP exception that carries a stable machine-readable error code and
    parameter map alongside the human-readable detail.

    Frontend reads `error_code` to look up a localized message template
    and interpolates `error_params` into it. `detail` remains a plain
    English/legacy fallback for non-i18n consumers and server logs.
    """

    error_code: str
    error_params: dict[str, Any]

    def __init__(
        self,
        status_code: int,
        error_code: str,
        detail: str,
        error_params: Mapping[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code
        self.error_params = dict(error_params or {})

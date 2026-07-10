"""HTTP client utilities."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx


@asynccontextmanager
async def get_http_client(
    timeout: float = 10.0,
    verify: bool | str = True,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Create an async HTTP client with timeout.

    Args:
        timeout: Request timeout in seconds.
        verify: TLS verification — True/False, or a path to a CA bundle.
            Use False (or a CA path) for the self-signed bnpzID service.

    Yields:
        Configured httpx.AsyncClient instance.
    """
    async with httpx.AsyncClient(timeout=timeout, verify=verify) as client:
        yield client

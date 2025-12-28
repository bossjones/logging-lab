"""
Access logging middleware for FastAPI.

Logs HTTP requests with structured fields: method, path, status_code, duration, client_ip.
Replaces Uvicorn's default access logging with richer context including correlation IDs.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing_extensions import override

from logging_lab.logging_config import get_logger


class AccessLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs HTTP requests with structured data.

    Logs include: method, path, status_code, duration_ms, client_ip.
    Uses structlog for structured JSON output in production.
    """

    @override
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        log = get_logger("access")

        start_time = time.perf_counter()

        # Get client IP (considering X-Forwarded-For for proxies)
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log.exception(
                "Request failed with exception",
                method=request.method,
                path=request.url.path,
                client_ip=client_ip,
                duration_ms=round(duration_ms, 2),
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        log.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            client_ip=client_ip,
        )

        return response

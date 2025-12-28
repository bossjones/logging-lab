"""
Structlog configuration with OpenTelemetry trace context integration.

Configures structured logging with correlation IDs and trace context.
"""

from __future__ import annotations

import logging
from typing import Any

import structlog
from asgi_correlation_id import correlation_id
from opentelemetry import trace


def add_correlation_id(
    logger: logging.Logger,  # pyright: ignore[reportUnusedParameter]
    method_name: str,  # pyright: ignore[reportUnusedParameter]
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add request correlation ID to log entries."""
    if request_id := correlation_id.get():
        event_dict["request_id"] = request_id
    return event_dict


def add_open_telemetry_spans(
    logger: logging.Logger,  # pyright: ignore[reportUnusedParameter]
    method_name: str,  # pyright: ignore[reportUnusedParameter]
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Add OpenTelemetry span context to log entries.

    Enables correlation between logs and traces in observability platforms.
    """
    span = trace.get_current_span()
    if not span.is_recording():
        return event_dict

    ctx = span.get_span_context()
    parent = getattr(span, "parent", None)

    event_dict["trace_id"] = format(ctx.trace_id, "032x")
    event_dict["span_id"] = format(ctx.span_id, "016x")
    if parent:
        event_dict["parent_span_id"] = format(parent.span_id, "016x")

    return event_dict


def configure_logging(json_output: bool = False) -> None:
    """
    Configure structlog for the application.

    Args:
        json_output: If True, output JSON format (for production).
                     If False, use colored console output (for development).
    """
    shared_processors: list[structlog.types.Processor] = [  # pyright: ignore[reportAssignmentType]
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_correlation_id,
        add_open_telemetry_spans,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_output:
        shared_processors.extend(
            [
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ]
        )
    else:
        shared_processors.extend(
            [
                structlog.dev.set_exc_info,
                structlog.dev.ConsoleRenderer(colors=True),
            ]
        )

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a configured structlog logger instance."""
    return structlog.get_logger(name)

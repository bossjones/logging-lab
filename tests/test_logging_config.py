"""Tests for logging configuration and structlog processors."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import structlog

from logging_lab.logging_config import (
    add_correlation_id,
    add_open_telemetry_spans,
    configure_logging,
    get_logger,
)


class TestAddCorrelationId:
    """Tests for the add_correlation_id processor."""

    def test_adds_request_id_when_correlation_id_exists(self) -> None:
        """Request ID is added to event dict when correlation ID is set."""
        mock_logger = MagicMock(spec=logging.Logger)
        event_dict: dict[str, Any] = {"event": "test message"}

        with patch("logging_lab.logging_config.correlation_id") as mock_cid:
            mock_cid.get.return_value = "test-correlation-123"
            result = add_correlation_id(mock_logger, "info", event_dict)

        assert result["request_id"] == "test-correlation-123"
        assert result["event"] == "test message"

    def test_no_request_id_when_correlation_id_missing(self) -> None:
        """Event dict unchanged when no correlation ID is set."""
        mock_logger = MagicMock(spec=logging.Logger)
        event_dict: dict[str, Any] = {"event": "test message"}

        with patch("logging_lab.logging_config.correlation_id") as mock_cid:
            mock_cid.get.return_value = None
            result = add_correlation_id(mock_logger, "info", event_dict)

        assert "request_id" not in result
        assert result["event"] == "test message"

    def test_no_request_id_when_correlation_id_empty(self) -> None:
        """Event dict unchanged when correlation ID is empty string."""
        mock_logger = MagicMock(spec=logging.Logger)
        event_dict: dict[str, Any] = {"event": "test message"}

        with patch("logging_lab.logging_config.correlation_id") as mock_cid:
            mock_cid.get.return_value = ""
            result = add_correlation_id(mock_logger, "info", event_dict)

        assert "request_id" not in result


class TestAddOpenTelemetrySpans:
    """Tests for the add_open_telemetry_spans processor."""

    def test_returns_unchanged_when_span_not_recording(self) -> None:
        """Event dict returned unchanged when span is not recording."""
        mock_logger = MagicMock(spec=logging.Logger)
        event_dict: dict[str, Any] = {"event": "test message"}

        mock_span = MagicMock()
        mock_span.is_recording.return_value = False

        with patch("logging_lab.logging_config.trace.get_current_span", return_value=mock_span):
            result = add_open_telemetry_spans(mock_logger, "info", event_dict)

        assert "trace_id" not in result
        assert "span_id" not in result
        assert result["event"] == "test message"

    def test_adds_trace_and_span_id_when_recording(self) -> None:
        """Trace and span IDs are added when span is recording."""
        mock_logger = MagicMock(spec=logging.Logger)
        event_dict: dict[str, Any] = {"event": "test message"}

        mock_span_context = MagicMock()
        mock_span_context.trace_id = 0x1234567890ABCDEF1234567890ABCDEF
        mock_span_context.span_id = 0x1234567890ABCDEF

        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_span.get_span_context.return_value = mock_span_context
        mock_span.parent = None

        with patch("logging_lab.logging_config.trace.get_current_span", return_value=mock_span):
            result = add_open_telemetry_spans(mock_logger, "info", event_dict)

        assert result["trace_id"] == "1234567890abcdef1234567890abcdef"
        assert result["span_id"] == "1234567890abcdef"
        assert "parent_span_id" not in result

    def test_adds_parent_span_id_when_parent_exists(self) -> None:
        """Parent span ID is added when parent span exists."""
        mock_logger = MagicMock(spec=logging.Logger)
        event_dict: dict[str, Any] = {"event": "test message"}

        mock_span_context = MagicMock()
        mock_span_context.trace_id = 0xABCDEF1234567890ABCDEF1234567890
        mock_span_context.span_id = 0xABCDEF12345678

        mock_parent = MagicMock()
        mock_parent.span_id = 0x9876543210FEDCBA

        mock_span = MagicMock()
        mock_span.is_recording.return_value = True
        mock_span.get_span_context.return_value = mock_span_context
        mock_span.parent = mock_parent

        with patch("logging_lab.logging_config.trace.get_current_span", return_value=mock_span):
            result = add_open_telemetry_spans(mock_logger, "info", event_dict)

        assert result["trace_id"] == "abcdef1234567890abcdef1234567890"
        assert result["span_id"] == "00abcdef12345678"
        assert result["parent_span_id"] == "9876543210fedcba"


class TestConfigureLogging:
    """Tests for the configure_logging function."""

    def test_configure_logging_json_output(self) -> None:
        """JSON output mode configures JSONRenderer."""
        with patch.object(structlog, "configure") as mock_configure:
            configure_logging(json_output=True)

        mock_configure.assert_called_once()
        call_kwargs = mock_configure.call_args.kwargs
        processors = call_kwargs["processors"]

        processor_names = [p.__class__.__name__ for p in processors]
        assert "JSONRenderer" in processor_names

    def test_configure_logging_console_output(self) -> None:
        """Console output mode configures ConsoleRenderer."""
        with patch.object(structlog, "configure") as mock_configure:
            configure_logging(json_output=False)

        mock_configure.assert_called_once()
        call_kwargs = mock_configure.call_args.kwargs
        processors = call_kwargs["processors"]

        processor_names = [p.__class__.__name__ for p in processors]
        assert "ConsoleRenderer" in processor_names

    def test_configure_logging_includes_core_processors(self) -> None:
        """Core processors are included in both modes."""
        with patch.object(structlog, "configure") as mock_configure:
            configure_logging(json_output=False)

        call_kwargs = mock_configure.call_args.kwargs
        processors = call_kwargs["processors"]

        # Check that our custom processors are included
        processor_names = [getattr(p, "__name__", None) or p.__class__.__name__ for p in processors]
        assert "add_correlation_id" in processor_names
        assert "add_open_telemetry_spans" in processor_names


class TestGetLogger:
    """Tests for the get_logger function."""

    def test_get_logger_returns_bound_logger(self) -> None:
        """get_logger returns a structlog logger instance."""
        logger = get_logger("test_module")
        assert logger is not None

    def test_get_logger_without_name(self) -> None:
        """get_logger works without a name argument."""
        logger = get_logger()
        assert logger is not None

    def test_get_logger_with_name(self) -> None:
        """get_logger accepts a name argument."""
        logger = get_logger("my.custom.logger")
        assert logger is not None

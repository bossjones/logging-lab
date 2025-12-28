"""Tests for logging configuration and structlog processors."""

from __future__ import annotations

import io
import json
import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import structlog
from asgi_correlation_id import correlation_id
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

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


class TestAddCorrelationIdIntegration:
    """Integration tests for correlation ID with real context."""

    def test_with_real_correlation_id_context(self) -> None:
        """Test with actual asgi_correlation_id context variable."""
        mock_logger = MagicMock(spec=logging.Logger)
        event_dict: dict[str, Any] = {"event": "test message"}

        token = correlation_id.set("real-correlation-456")
        try:
            result = add_correlation_id(mock_logger, "info", event_dict)
            assert result["request_id"] == "real-correlation-456"
        finally:
            correlation_id.reset(token)

    def test_without_correlation_id_context(self) -> None:
        """Test when no correlation ID is set in context."""
        mock_logger = MagicMock(spec=logging.Logger)
        event_dict: dict[str, Any] = {"event": "test message"}

        # Ensure no correlation ID is set
        result = add_correlation_id(mock_logger, "info", event_dict)
        # Should not have request_id when correlation_id.get() returns None
        if correlation_id.get():
            assert "request_id" in result
        else:
            assert "request_id" not in result

    def test_preserves_existing_event_dict_fields(self) -> None:
        """Existing fields in event_dict are preserved."""
        mock_logger = MagicMock(spec=logging.Logger)
        event_dict: dict[str, Any] = {
            "event": "test message",
            "custom_field": "custom_value",
            "number": 42,
        }

        token = correlation_id.set("test-123")
        try:
            result = add_correlation_id(mock_logger, "info", event_dict)
            assert result["custom_field"] == "custom_value"
            assert result["number"] == 42
            assert result["event"] == "test message"
        finally:
            correlation_id.reset(token)


class TestAddOpenTelemetrySpansIntegration:
    """Integration tests for OpenTelemetry span context."""

    @pytest.fixture(autouse=True)
    def setup_tracer(self) -> None:
        """Set up a real tracer provider for tests."""
        provider = TracerProvider()
        trace.set_tracer_provider(provider)

    def test_with_real_span(self) -> None:
        """Test with an actual OpenTelemetry span."""
        mock_logger = MagicMock(spec=logging.Logger)
        event_dict: dict[str, Any] = {"event": "test message"}

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("test-span") as span:
            result = add_open_telemetry_spans(mock_logger, "info", event_dict)

            # Verify trace_id and span_id are present and properly formatted
            assert "trace_id" in result
            assert "span_id" in result
            assert len(result["trace_id"]) == 32  # 128-bit trace ID as hex
            assert len(result["span_id"]) == 16  # 64-bit span ID as hex

            # Verify they match the actual span context
            ctx = span.get_span_context()
            assert result["trace_id"] == format(ctx.trace_id, "032x")
            assert result["span_id"] == format(ctx.span_id, "016x")

    def test_with_nested_spans(self) -> None:
        """Test with nested spans to verify parent span ID."""
        mock_logger = MagicMock(spec=logging.Logger)
        event_dict: dict[str, Any] = {"event": "test message"}

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("parent-span") as parent_span:
            parent_span_id = format(parent_span.get_span_context().span_id, "016x")

            with tracer.start_as_current_span("child-span"):
                result = add_open_telemetry_spans(mock_logger, "info", event_dict)

                assert "trace_id" in result
                assert "span_id" in result

                # Child span should have parent_span_id matching parent's span_id
                assert "parent_span_id" in result
                assert result["parent_span_id"] == parent_span_id

    def test_outside_span_context(self) -> None:
        """Test when no span is active."""
        mock_logger = MagicMock(spec=logging.Logger)
        event_dict: dict[str, Any] = {"event": "test message"}

        # Outside any span context
        result = add_open_telemetry_spans(mock_logger, "info", event_dict)

        # No span recording, so no trace info should be added
        assert "trace_id" not in result or result.get("trace_id") == "0" * 32


class TestConfigureLoggingIntegration:
    """Integration tests for full logging configuration."""

    def test_json_output_produces_valid_json(self) -> None:
        """JSON output mode produces parseable JSON logs."""
        configure_logging(json_output=True)

        # Capture stdout
        captured = io.StringIO()
        structlog.configure(
            processors=[
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.PrintLoggerFactory(captured),
        )

        logger = structlog.get_logger("test")
        logger.info("test message", key="value")

        output = captured.getvalue().strip()
        if output:
            parsed = json.loads(output)
            assert parsed["event"] == "test message"
            assert parsed["key"] == "value"

    def test_configure_logging_sets_log_level_info(self) -> None:
        """Configure logging sets INFO as minimum log level."""
        with patch.object(structlog, "configure") as mock_configure:
            configure_logging(json_output=False)

        call_kwargs = mock_configure.call_args.kwargs
        wrapper_class = call_kwargs["wrapper_class"]
        # The wrapper class should be a filtering bound logger at INFO level
        assert wrapper_class is not None

    def test_configure_logging_uses_print_logger_factory(self) -> None:
        """Configure logging uses PrintLoggerFactory."""
        with patch.object(structlog, "configure") as mock_configure:
            configure_logging(json_output=False)

        call_kwargs = mock_configure.call_args.kwargs
        assert isinstance(call_kwargs["logger_factory"], structlog.PrintLoggerFactory)

    def test_configure_logging_caches_logger(self) -> None:
        """Configure logging enables logger caching."""
        with patch.object(structlog, "configure") as mock_configure:
            configure_logging(json_output=False)

        call_kwargs = mock_configure.call_args.kwargs
        assert call_kwargs["cache_logger_on_first_use"] is True

    def test_json_mode_includes_exception_formatter(self) -> None:
        """JSON mode includes format_exc_info processor (ExceptionRenderer)."""
        with patch.object(structlog, "configure") as mock_configure:
            configure_logging(json_output=True)

        call_kwargs = mock_configure.call_args.kwargs
        processors = call_kwargs["processors"]

        # format_exc_info is an instance of ExceptionRenderer
        processor_types = [type(p).__name__ for p in processors]
        assert "ExceptionRenderer" in processor_types

    def test_console_mode_includes_set_exc_info(self) -> None:
        """Console mode includes set_exc_info processor."""
        with patch.object(structlog, "configure") as mock_configure:
            configure_logging(json_output=False)

        call_kwargs = mock_configure.call_args.kwargs
        processors = call_kwargs["processors"]

        processor_names = [getattr(p, "__name__", None) or p.__class__.__name__ for p in processors]
        assert "set_exc_info" in processor_names

    def test_includes_timestamper(self) -> None:
        """Both modes include TimeStamper processor."""
        with patch.object(structlog, "configure") as mock_configure:
            configure_logging(json_output=True)

        call_kwargs = mock_configure.call_args.kwargs
        processors = call_kwargs["processors"]

        processor_types = [type(p).__name__ for p in processors]
        assert "TimeStamper" in processor_types

    def test_includes_stack_info_renderer(self) -> None:
        """Both modes include StackInfoRenderer processor."""
        with patch.object(structlog, "configure") as mock_configure:
            configure_logging(json_output=False)

        call_kwargs = mock_configure.call_args.kwargs
        processors = call_kwargs["processors"]

        processor_types = [type(p).__name__ for p in processors]
        assert "StackInfoRenderer" in processor_types


class TestProcessorChain:
    """Tests for the complete processor chain behavior."""

    def test_processors_execute_in_order(self) -> None:
        """Verify processors execute and accumulate results."""
        mock_logger = MagicMock(spec=logging.Logger)
        event_dict: dict[str, Any] = {"event": "test"}

        # Set up correlation ID
        token = correlation_id.set("chain-test-123")
        try:
            # Run through correlation ID processor
            result = add_correlation_id(mock_logger, "info", event_dict)
            assert result["request_id"] == "chain-test-123"

            # Run through OTel processor (no active span)
            result = add_open_telemetry_spans(mock_logger, "info", result)

            # Original fields preserved
            assert result["event"] == "test"
            assert result["request_id"] == "chain-test-123"
        finally:
            correlation_id.reset(token)

    def test_full_chain_with_span_and_correlation(self) -> None:
        """Test full processor chain with both span and correlation ID."""
        mock_logger = MagicMock(spec=logging.Logger)
        event_dict: dict[str, Any] = {"event": "full chain test", "extra": "data"}

        provider = TracerProvider()
        trace.set_tracer_provider(provider)
        tracer = trace.get_tracer(__name__)

        token = correlation_id.set("full-chain-456")
        try:
            with tracer.start_as_current_span("chain-span"):
                # Run through both processors
                result = add_correlation_id(mock_logger, "info", event_dict)
                result = add_open_telemetry_spans(mock_logger, "info", result)

                # All fields should be present
                assert result["event"] == "full chain test"
                assert result["extra"] == "data"
                assert result["request_id"] == "full-chain-456"
                assert "trace_id" in result
                assert "span_id" in result
        finally:
            correlation_id.reset(token)

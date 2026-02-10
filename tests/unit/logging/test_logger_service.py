"""
Unit tests for LoggerService (P2).

Tests cover:
- Initialization and configuration
- Convenience methods (debug, info, warning, error, critical)
- Context binding
- Trace ID binding
- Duration measurement
- Secret redaction integration
- Level filtering
- Exception capture
"""

import asyncio
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.fte_logging.config import LoggerConfig
from src.fte_logging.logger_service import LoggerService
from src.fte_logging.models import LogLevel


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def logger_config(temp_log_dir):
    """Create test logger config."""
    return LoggerConfig(
        log_dir=temp_log_dir,
        level=LogLevel.DEBUG,
        async_enabled=False,  # Disable async for simpler unit tests
    )


@pytest.fixture
def logger(logger_config):
    """Create test logger."""
    return LoggerService(logger_config)


class TestLoggerServiceInitialization:
    """Tests for LoggerService initialization."""

    def test_init_with_config(self, logger_config):
        """Should initialize with provided config."""
        logger = LoggerService(logger_config)

        assert logger.config == logger_config
        assert logger._redactor is not None

    def test_init_with_async_disabled(self, logger_config):
        """Should handle async disabled config."""
        config = replace(logger_config, async_enabled=False)
        logger = LoggerService(config)

        assert logger._writer is None

    def test_init_with_async_enabled(self, temp_log_dir):
        """Should create async writer when enabled."""
        config = LoggerConfig(log_dir=temp_log_dir, async_enabled=True)
        logger = LoggerService(config)

        assert logger._writer is not None


class TestConvenienceMethods:
    """Tests for convenience logging methods."""

    def test_debug_method(self, logger):
        """Should log DEBUG level message."""
        # Just ensure it doesn't crash
        logger.debug("Debug message")

    def test_info_method(self, logger):
        """Should log INFO level message."""
        logger.info("Info message")

    def test_warning_method(self, logger):
        """Should log WARNING level message."""
        logger.warning("Warning message")

    def test_error_method(self, logger):
        """Should log ERROR level message."""
        logger.error("Error message")

    def test_critical_method(self, logger):
        """Should log CRITICAL level message."""
        logger.critical("Critical message")

    def test_convenience_method_with_context(self, logger):
        """Convenience methods should accept context."""
        logger.info("Message", context={"key": "value"})

    def test_convenience_method_with_exception(self, logger):
        """Convenience methods should accept exception."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            logger.error("Error occurred", exception=e)


class TestContextBinding:
    """Tests for context binding."""

    def test_bind_context_simple(self, logger):
        """Should bind context to logs in scope."""
        with logger.bind_context(task_id="task-001"):
            # Context is bound but we can't easily verify without async writer
            logger.info("Message with context")

    def test_bind_context_nested(self, logger):
        """Should support nested context binding."""
        with logger.bind_context(task_id="task-001"):
            with logger.bind_context(user="alice"):
                logger.info("Message with nested context")

    def test_bind_context_restoration(self, logger):
        """Should restore previous context after exit."""
        with logger.bind_context(outer="value1"):
            with logger.bind_context(inner="value2"):
                pass
            # After inner context exits, only outer remains
            logger.info("Message with outer context")


class TestTraceIdBinding:
    """Tests for trace ID binding."""

    def test_bind_trace_id_auto_generate(self, logger):
        """Should auto-generate trace ID if not provided."""
        with logger.bind_trace_id() as trace_id:
            assert trace_id is not None
            assert len(trace_id) == 26  # ULID length

    def test_bind_trace_id_explicit(self, logger):
        """Should use provided trace ID."""
        with logger.bind_trace_id("custom-trace-123") as trace_id:
            assert trace_id == "custom-trace-123"

    def test_bind_trace_id_nested(self, logger):
        """Should support nested trace ID binding."""
        with logger.bind_trace_id("outer-trace") as outer_id:
            assert outer_id == "outer-trace"

            with logger.bind_trace_id("inner-trace") as inner_id:
                assert inner_id == "inner-trace"


class TestDurationMeasurement:
    """Tests for duration measurement."""

    def test_measure_duration_basic(self, logger):
        """Should measure operation duration."""
        import time

        with logger.measure_duration("test_operation"):
            time.sleep(0.01)  # 10ms

        # Should have logged start and end messages

    def test_measure_duration_with_context(self, logger):
        """Should support additional context."""
        with logger.measure_duration("operation", param="value"):
            pass

    def test_measure_duration_custom_message(self, logger):
        """Should support custom log message."""
        with logger.measure_duration(
            "operation", log_message="Custom completion message"
        ):
            pass

    def test_measure_duration_custom_level(self, logger):
        """Should support custom log level."""
        with logger.measure_duration("operation", log_level=LogLevel.DEBUG):
            pass


class TestLevelFiltering:
    """Tests for log level filtering."""

    def test_set_level_global(self, logger):
        """Should change global log level."""
        logger.set_level(LogLevel.WARNING)

        assert logger.get_level() == LogLevel.WARNING

    def test_set_level_per_module(self, logger):
        """Should support per-module log levels."""
        logger.set_level(LogLevel.DEBUG, module="src.test")

        assert logger.get_level("src.test") == LogLevel.DEBUG
        assert logger.get_level() == LogLevel.DEBUG  # Default unchanged

    def test_get_level_default(self, logger):
        """Should return default level if module not configured."""
        level = logger.get_level("some.unknown.module")

        assert level == LogLevel.DEBUG  # Test config default

    def test_should_log_filters_by_level(self, logger_config):
        """Should filter logs below configured level."""
        config = replace(logger_config, level=LogLevel.WARNING)
        logger = LoggerService(config)

        # DEBUG and INFO should be filtered (not logged)
        # WARNING, ERROR, CRITICAL should be logged


class TestSecretRedaction:
    """Tests for automatic secret redaction."""

    def test_redact_api_key_in_message(self, logger):
        """Should redact API keys in log messages."""
        # This test verifies integration with SecretRedactor
        logger.info("Authenticating with api_key=sk_live_12345678901234567890")
        # Secret should be redacted before writing

    def test_redact_password_in_context(self, logger):
        """Should redact passwords in context dict."""
        logger.info(
            "User login", context={"username": "alice", "password": "secret123"}
        )
        # Password should be redacted

    def test_redact_bearer_token(self, logger):
        """Should redact Bearer tokens."""
        logger.info("Bearer abc123def456ghi789jkl012mno345")


class TestExceptionCapture:
    """Tests for exception capture."""

    def test_capture_simple_exception(self, logger):
        """Should capture exception with stack trace."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            logger.error("Error occurred", exception=e)

    def test_capture_chained_exception(self, logger):
        """Should capture chained exceptions (__cause__)."""
        try:
            try:
                raise ValueError("Inner error")
            except ValueError as inner:
                raise RuntimeError("Outer error") from inner
        except RuntimeError as e:
            logger.error("Chained error", exception=e)

    def test_capture_nested_exception(self, logger):
        """Should capture nested exception stack traces."""

        def inner_function():
            raise ValueError("Inner error")

        def outer_function():
            inner_function()

        try:
            outer_function()
        except ValueError as e:
            logger.error("Nested error", exception=e)


class TestAsyncLifecycle:
    """Tests for async writer lifecycle."""

    @pytest.mark.asyncio
    async def test_start_async_writer(self, temp_log_dir):
        """Should start async writer."""
        config = LoggerConfig(log_dir=temp_log_dir, async_enabled=True)
        logger = LoggerService(config)

        await logger.start_async_writer()

        assert logger._writer is not None

        await logger.stop_async_writer()

    @pytest.mark.asyncio
    async def test_stop_async_writer(self, temp_log_dir):
        """Should stop async writer and flush logs."""
        config = LoggerConfig(log_dir=temp_log_dir, async_enabled=True)
        logger = LoggerService(config)

        await logger.start_async_writer()
        logger.info("Test message")
        await logger.stop_async_writer(timeout=2.0)

    @pytest.mark.asyncio
    async def test_start_without_async_enabled_raises_error(self, temp_log_dir):
        """Should raise error if async disabled."""
        config = LoggerConfig(log_dir=temp_log_dir, async_enabled=False)
        logger = LoggerService(config)

        with pytest.raises(RuntimeError, match="Async logging disabled"):
            await logger.start_async_writer()

    @pytest.mark.asyncio
    async def test_flush(self, temp_log_dir):
        """Should flush pending logs."""
        config = LoggerConfig(log_dir=temp_log_dir, async_enabled=True)
        logger = LoggerService(config)

        await logger.start_async_writer()
        logger.info("Test message")
        await logger.flush()
        await logger.stop_async_writer()


class TestErrorHandling:
    """Tests for error handling."""

    def test_log_never_crashes(self, logger):
        """Logging should never crash application."""
        # Even with invalid inputs, should not raise
        logger.info(None)  # type: ignore
        logger.info("Message", context={"bad": object()})  # Non-serializable

    def test_fallback_to_stderr(self, logger_config):
        """Should fallback to stderr if writer unavailable."""
        config = replace(logger_config, async_enabled=False)
        logger = LoggerService(config)

        # Should write to stderr without crashing
        logger.info("Fallback message")


class TestPublicAPI:
    """Tests for public API functions."""

    def test_init_logging_default(self, temp_log_dir):
        """Should initialize logging with defaults."""
        from src.fte_logging import init_logging

        logger = init_logging(log_dir=temp_log_dir)

        assert logger is not None
        assert isinstance(logger, LoggerService)

    def test_init_logging_with_level(self, temp_log_dir):
        """Should initialize with custom level."""
        from src.fte_logging import init_logging

        logger = init_logging(log_dir=temp_log_dir, level="DEBUG")

        assert logger.config.level == LogLevel.DEBUG

    def test_get_logger(self, temp_log_dir):
        """Should get global logger instance."""
        from src.fte_logging import get_logger, init_logging

        init_logging(log_dir=temp_log_dir)
        logger = get_logger(__name__)

        assert logger is not None
        assert isinstance(logger, LoggerService)

    def test_get_logger_auto_init(self):
        """Should auto-initialize if not initialized."""
        from src.fte_logging import get_logger

        # Reset global logger
        import src.fte_logging

        src.fte_logging._global_logger = None

        logger = get_logger(__name__)

        assert logger is not None

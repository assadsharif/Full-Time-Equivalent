"""
Unit tests for logging models (P2).

Tests cover:
- LogLevel enum ordering
- LogEntry immutability and structure
- ExceptionInfo with chained exceptions
- StackFrame data structure
- MetricEntry structure
- MetricType enum values
"""

from datetime import datetime, timezone

import pytest

from src.logging.models import (
    ExceptionInfo,
    LogEntry,
    LogLevel,
    MetricEntry,
    MetricType,
    StackFrame,
)


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_log_level_ordering(self):
        """Log levels should be numerically ordered by severity."""
        assert LogLevel.DEBUG < LogLevel.INFO
        assert LogLevel.INFO < LogLevel.WARNING
        assert LogLevel.WARNING < LogLevel.ERROR
        assert LogLevel.ERROR < LogLevel.CRITICAL

    def test_log_level_values(self):
        """Log levels should have correct numeric values."""
        assert LogLevel.DEBUG == 10
        assert LogLevel.INFO == 20
        assert LogLevel.WARNING == 30
        assert LogLevel.ERROR == 40
        assert LogLevel.CRITICAL == 50

    def test_log_level_names(self):
        """Log levels should have correct string names."""
        assert LogLevel.DEBUG.name == "DEBUG"
        assert LogLevel.INFO.name == "INFO"
        assert LogLevel.WARNING.name == "WARNING"
        assert LogLevel.ERROR.name == "ERROR"
        assert LogLevel.CRITICAL.name == "CRITICAL"


class TestStackFrame:
    """Tests for StackFrame dataclass."""

    def test_stack_frame_creation(self):
        """StackFrame should be created with required fields."""
        frame = StackFrame(
            file="src/logging/models.py",
            line=42,
            function="test_function",
            code="result = test_function()",
        )

        assert frame.file == "src/logging/models.py"
        assert frame.line == 42
        assert frame.function == "test_function"
        assert frame.code == "result = test_function()"

    def test_stack_frame_optional_code(self):
        """StackFrame should allow optional code field."""
        frame = StackFrame(
            file="src/logging/models.py",
            line=42,
            function="test_function",
        )

        assert frame.file == "src/logging/models.py"
        assert frame.line == 42
        assert frame.function == "test_function"
        assert frame.code is None

    def test_stack_frame_immutable(self):
        """StackFrame should be immutable (frozen dataclass)."""
        frame = StackFrame(file="test.py", line=1, function="test")

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            frame.line = 2


class TestExceptionInfo:
    """Tests for ExceptionInfo dataclass."""

    def test_exception_info_creation(self):
        """ExceptionInfo should be created with required fields."""
        stack = [
            StackFrame(file="test.py", line=10, function="outer"),
            StackFrame(file="test.py", line=5, function="inner"),
        ]

        exc = ExceptionInfo(
            type="ValueError",
            message="Invalid value",
            stack_trace=stack,
        )

        assert exc.type == "ValueError"
        assert exc.message == "Invalid value"
        assert len(exc.stack_trace) == 2
        assert exc.cause is None

    def test_exception_info_with_cause(self):
        """ExceptionInfo should support chained exceptions."""
        cause = ExceptionInfo(
            type="OSError",
            message="File not found",
            stack_trace=[],
        )

        exc = ExceptionInfo(
            type="FileOperationError",
            message="Failed to process file",
            stack_trace=[],
            cause=cause,
        )

        assert exc.cause is not None
        assert exc.cause.type == "OSError"
        assert exc.cause.message == "File not found"

    def test_exception_info_immutable(self):
        """ExceptionInfo should be immutable (frozen dataclass)."""
        exc = ExceptionInfo(type="Error", message="test", stack_trace=[])

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            exc.type = "NewError"


class TestLogEntry:
    """Tests for LogEntry dataclass."""

    def test_log_entry_minimal(self):
        """LogEntry should be created with minimal required fields."""
        now = datetime.now(timezone.utc)
        entry = LogEntry(
            trace_id="01HQ8Z9X0ABCDEFGHIJKLMNOPQ",
            timestamp=now,
            level=LogLevel.INFO,
            module="src.logging.test",
            message="Test message",
        )

        assert entry.trace_id == "01HQ8Z9X0ABCDEFGHIJKLMNOPQ"
        assert entry.timestamp == now
        assert entry.level == LogLevel.INFO
        assert entry.module == "src.logging.test"
        assert entry.message == "Test message"
        assert entry.function is None
        assert entry.line_number is None
        assert entry.context is None
        assert entry.exception is None
        assert entry.duration_ms is None
        assert entry.tags == []

    def test_log_entry_full(self):
        """LogEntry should support all optional fields."""
        now = datetime.now(timezone.utc)
        exc = ExceptionInfo(type="Error", message="test", stack_trace=[])

        entry = LogEntry(
            trace_id="01HQ8Z9X0ABCDEFGHIJKLMNOPQ",
            timestamp=now,
            level=LogLevel.ERROR,
            module="src.logging.test",
            message="Test error",
            function="test_function",
            line_number=42,
            context={"key": "value"},
            exception=exc,
            duration_ms=123.45,
            tags=["error", "test"],
        )

        assert entry.function == "test_function"
        assert entry.line_number == 42
        assert entry.context == {"key": "value"}
        assert entry.exception is not None
        assert entry.duration_ms == 123.45
        assert entry.tags == ["error", "test"]

    def test_log_entry_immutable(self):
        """LogEntry should be immutable (frozen dataclass)."""
        now = datetime.now(timezone.utc)
        entry = LogEntry(
            trace_id="test",
            timestamp=now,
            level=LogLevel.INFO,
            module="test",
            message="test",
        )

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            entry.message = "new message"


class TestMetricType:
    """Tests for MetricType enum."""

    def test_metric_type_values(self):
        """MetricType should have correct enum values."""
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.DURATION.value == "duration"
        assert MetricType.HISTOGRAM.value == "histogram"

    def test_metric_type_names(self):
        """MetricType should have correct names."""
        assert MetricType.COUNTER.name == "COUNTER"
        assert MetricType.GAUGE.name == "GAUGE"
        assert MetricType.DURATION.name == "DURATION"
        assert MetricType.HISTOGRAM.name == "HISTOGRAM"


class TestMetricEntry:
    """Tests for MetricEntry dataclass."""

    def test_metric_entry_creation(self):
        """MetricEntry should be created with all required fields."""
        now = datetime.now(timezone.utc)
        metric = MetricEntry(
            trace_id="01HQ8Z9X0ABCDEFGHIJKLMNOPQ",
            timestamp=now,
            metric_name="operation.duration",
            metric_type=MetricType.DURATION,
            value=123.45,
            unit="milliseconds",
            tags={"operation": "test", "result": "success"},
        )

        assert metric.trace_id == "01HQ8Z9X0ABCDEFGHIJKLMNOPQ"
        assert metric.timestamp == now
        assert metric.metric_name == "operation.duration"
        assert metric.metric_type == MetricType.DURATION
        assert metric.value == 123.45
        assert metric.unit == "milliseconds"
        assert metric.tags == {"operation": "test", "result": "success"}

    def test_metric_entry_no_tags(self):
        """MetricEntry should allow empty tags."""
        now = datetime.now(timezone.utc)
        metric = MetricEntry(
            trace_id="test",
            timestamp=now,
            metric_name="counter.total",
            metric_type=MetricType.COUNTER,
            value=42.0,
            unit="count",
        )

        assert metric.tags == {}

    def test_metric_entry_immutable(self):
        """MetricEntry should be immutable (frozen dataclass)."""
        now = datetime.now(timezone.utc)
        metric = MetricEntry(
            trace_id="test",
            timestamp=now,
            metric_name="test",
            metric_type=MetricType.COUNTER,
            value=1.0,
            unit="count",
        )

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            metric.value = 2.0

"""
Integration test for exception logging (P2).

Tests exception capture and logging:
- Simple exceptions with stack traces
- Chained exceptions (__cause__)
- Nested exception stack traces
- Exception context preservation
- Full exception details in logs

Constitutional compliance: Section 9 (errors never hidden, full context captured).
"""

import asyncio
import json
from pathlib import Path

import pytest

from src.logging import get_logger, init_logging


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


class TestSimpleExceptions:
    """Tests for simple exception logging."""

    @pytest.mark.asyncio
    async def test_log_simple_exception(self, temp_log_dir):
        """Should log exception with full details."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        try:
            raise ValueError("Test error message")
        except ValueError as e:
            logger.error("Error occurred", exception=e)

        await logger.flush()
        await logger.stop_async_writer()

        # Verify exception logged
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert entry["level"] == "ERROR"
        assert "exception" in entry
        assert entry["exception"]["type"] == "ValueError"
        assert entry["exception"]["message"] == "Test error message"
        assert "stack_trace" in entry["exception"]

    @pytest.mark.asyncio
    async def test_exception_stack_trace(self, temp_log_dir):
        """Should capture full stack trace."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        def level3():
            raise RuntimeError("Deep error")

        def level2():
            level3()

        def level1():
            level2()

        try:
            level1()
        except RuntimeError as e:
            logger.error("Nested error", exception=e)

        await logger.flush()
        await logger.stop_async_writer()

        # Verify stack trace has multiple frames
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        stack_trace = entry["exception"]["stack_trace"]
        assert len(stack_trace) >= 3  # At least 3 levels

        # Verify frame structure
        for frame in stack_trace:
            assert "file" in frame
            assert "line" in frame
            assert "function" in frame

    @pytest.mark.asyncio
    async def test_exception_with_context(self, temp_log_dir):
        """Should log exception with additional context."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        try:
            value = 1 / 0  # ZeroDivisionError
        except ZeroDivisionError as e:
            logger.error(
                "Division error",
                exception=e,
                context={"numerator": 1, "denominator": 0}
            )

        await logger.flush()
        await logger.stop_async_writer()

        # Verify exception and context
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert entry["exception"]["type"] == "ZeroDivisionError"
        assert entry["context"]["numerator"] == 1
        assert entry["context"]["denominator"] == 0


class TestChainedExceptions:
    """Tests for chained exception logging."""

    @pytest.mark.asyncio
    async def test_chained_exception_cause(self, temp_log_dir):
        """Should capture chained exceptions (__cause__)."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        try:
            try:
                raise ValueError("Original error")
            except ValueError as original:
                raise RuntimeError("Wrapper error") from original
        except RuntimeError as e:
            logger.error("Chained error occurred", exception=e)

        await logger.flush()
        await logger.stop_async_writer()

        # Verify chained exception
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert entry["exception"]["type"] == "RuntimeError"
        assert entry["exception"]["message"] == "Wrapper error"

        # Check cause
        assert "cause" in entry["exception"]
        cause = entry["exception"]["cause"]
        assert cause["type"] == "ValueError"
        assert cause["message"] == "Original error"

    @pytest.mark.asyncio
    async def test_deep_exception_chain(self, temp_log_dir):
        """Should capture deep exception chains."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        try:
            try:
                try:
                    raise ValueError("Level 1")
                except ValueError as e1:
                    raise TypeError("Level 2") from e1
            except TypeError as e2:
                raise RuntimeError("Level 3") from e2
        except RuntimeError as e:
            logger.error("Deep chain error", exception=e)

        await logger.flush()
        await logger.stop_async_writer()

        # Verify full chain
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        # Level 3 (outermost)
        assert entry["exception"]["type"] == "RuntimeError"

        # Level 2
        assert entry["exception"]["cause"]["type"] == "TypeError"

        # Level 1 (innermost)
        assert entry["exception"]["cause"]["cause"]["type"] == "ValueError"


class TestExceptionContext:
    """Tests for exception context preservation."""

    @pytest.mark.asyncio
    async def test_exception_with_trace_id(self, temp_log_dir):
        """Should preserve trace ID with exception."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        with logger.bind_trace_id("error-trace") as trace_id:
            try:
                raise ValueError("Error with trace")
            except ValueError as e:
                logger.error("Error", exception=e)

        await logger.flush()
        await logger.stop_async_writer()

        # Verify trace ID in error log
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert entry["trace_id"] == trace_id
        assert entry["exception"]["type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_exception_with_bound_context(self, temp_log_dir):
        """Should include bound context with exception."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        with logger.bind_context(task_id="task-001", operation="process"):
            try:
                raise RuntimeError("Processing failed")
            except RuntimeError as e:
                logger.error("Task failed", exception=e)

        await logger.flush()
        await logger.stop_async_writer()

        # Verify context preserved
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert entry["context"]["task_id"] == "task-001"
        assert entry["context"]["operation"] == "process"
        assert entry["exception"]["type"] == "RuntimeError"


class TestExceptionLoggingPatterns:
    """Tests for common exception logging patterns."""

    @pytest.mark.asyncio
    async def test_try_except_logging_pattern(self, temp_log_dir):
        """Test typical try-except logging pattern."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        def risky_operation():
            """Simulated operation that might fail."""
            raise OSError("File not found")

        try:
            result = risky_operation()
        except Exception as e:
            logger.error(
                "Operation failed",
                exception=e,
                context={"operation": "risky_operation"}
            )

        await logger.flush()
        await logger.stop_async_writer()

        # Verify error logged
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert entry["exception"]["type"] == "OSError"
        assert entry["context"]["operation"] == "risky_operation"

    @pytest.mark.asyncio
    async def test_exception_reraise_with_logging(self, temp_log_dir):
        """Test logging exception before re-raising."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        def inner_function():
            raise ValueError("Inner error")

        def outer_function():
            try:
                inner_function()
            except ValueError as e:
                # Log and re-raise
                logger.error("Caught error, re-raising", exception=e)
                raise

        try:
            outer_function()
        except ValueError:
            pass  # Expected

        await logger.flush()
        await logger.stop_async_writer()

        # Verify error logged
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert entry["exception"]["type"] == "ValueError"

    @pytest.mark.asyncio
    async def test_multiple_exceptions_different_traces(self, temp_log_dir):
        """Should log multiple exceptions with different trace IDs."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        # First error with trace A
        with logger.bind_trace_id("trace-A"):
            try:
                raise ValueError("Error A")
            except ValueError as e:
                logger.error("First error", exception=e)

        # Second error with trace B
        with logger.bind_trace_id("trace-B"):
            try:
                raise TypeError("Error B")
            except TypeError as e:
                logger.error("Second error", exception=e)

        await logger.flush()
        await logger.stop_async_writer()

        # Verify both errors logged with different traces
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        entry1 = json.loads(lines[0])
        entry2 = json.loads(lines[1])

        assert entry1["trace_id"] == "trace-A"
        assert entry1["exception"]["type"] == "ValueError"

        assert entry2["trace_id"] == "trace-B"
        assert entry2["exception"]["type"] == "TypeError"


class TestExceptionDetails:
    """Tests for exception detail capture."""

    @pytest.mark.asyncio
    async def test_exception_message_preserved(self, temp_log_dir):
        """Should preserve full exception message."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        error_message = "This is a detailed error message with important context"

        try:
            raise RuntimeError(error_message)
        except RuntimeError as e:
            logger.error("Error", exception=e)

        await logger.flush()
        await logger.stop_async_writer()

        # Verify message preserved
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert entry["exception"]["message"] == error_message

    @pytest.mark.asyncio
    async def test_exception_type_captured(self, temp_log_dir):
        """Should capture exception class name."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        # Test various exception types
        exceptions = [
            ValueError("value error"),
            TypeError("type error"),
            RuntimeError("runtime error"),
            OSError("os error"),
            KeyError("key error"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except Exception as e:
                logger.error(f"Error: {type(e).__name__}", exception=e)

        await logger.flush()
        await logger.stop_async_writer()

        # Verify all exception types captured
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        exception_types = [
            json.loads(line)["exception"]["type"] for line in lines
        ]

        assert "ValueError" in exception_types
        assert "TypeError" in exception_types
        assert "RuntimeError" in exception_types
        assert "OSError" in exception_types
        assert "KeyError" in exception_types

    @pytest.mark.asyncio
    async def test_source_code_in_stack_frame(self, temp_log_dir):
        """Should capture source code line in stack frames."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        try:
            x = 1 / 0  # This line should appear in stack trace
        except ZeroDivisionError as e:
            logger.error("Division error", exception=e)

        await logger.flush()
        await logger.stop_async_writer()

        # Verify source code captured
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        stack_frames = entry["exception"]["stack_trace"]
        # At least one frame should have source code
        has_code = any("code" in frame for frame in stack_frames)
        assert has_code

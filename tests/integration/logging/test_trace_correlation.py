"""
Integration test for trace ID propagation and correlation (P2).

Tests trace ID functionality:
- Auto-generation of trace IDs
- Trace ID propagation across log calls
- Trace ID binding to operation scope
- Multiple trace IDs (nested operations)
- Trace ID in all log fields

Constitutional compliance: Section 8 (auditability via trace correlation).
"""

import asyncio
import json
from pathlib import Path

import pytest

from src.logging import get_logger, init_logging, new_trace_id
from logging.trace import get_trace_id


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


class TestTraceIdGeneration:
    """Tests for trace ID generation."""

    def test_new_trace_id_format(self):
        """Trace IDs should be valid ULIDs."""
        trace_id = new_trace_id()

        assert len(trace_id) == 26
        assert trace_id.isalnum()  # ULID is alphanumeric

    def test_new_trace_id_uniqueness(self):
        """Trace IDs should be unique."""
        ids = [new_trace_id() for _ in range(100)]

        assert len(set(ids)) == 100  # All unique


class TestTraceIdPropagation:
    """Tests for trace ID propagation across log calls."""

    @pytest.mark.asyncio
    async def test_auto_trace_id_generation(self, temp_log_dir):
        """Should auto-generate trace ID if not provided."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        # Log without explicit trace ID
        logger.info("Message 1")
        logger.info("Message 2")
        logger.info("Message 3")

        await logger.flush()
        await logger.stop_async_writer()

        # Verify each log has a trace ID
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        for line in lines:
            entry = json.loads(line)
            assert "trace_id" in entry
            assert len(entry["trace_id"]) == 26

    @pytest.mark.asyncio
    async def test_explicit_trace_id_binding(self, temp_log_dir):
        """Should use bound trace ID for all logs in scope."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        # Bind trace ID for operation
        with logger.bind_trace_id() as trace_id:
            logger.info("Operation started")
            logger.info("Processing")
            logger.info("Operation complete")

        await logger.flush()
        await logger.stop_async_writer()

        # Verify all logs share same trace ID
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        trace_ids = [json.loads(line)["trace_id"] for line in lines]

        assert len(set(trace_ids)) == 1  # All same trace ID
        assert trace_ids[0] == trace_id

    @pytest.mark.asyncio
    async def test_custom_trace_id(self, temp_log_dir):
        """Should accept custom trace ID."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        custom_trace = "custom-trace-id-12345"

        with logger.bind_trace_id(custom_trace):
            logger.info("Message with custom trace")

        await logger.flush()
        await logger.stop_async_writer()

        # Verify custom trace ID used
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert entry["trace_id"] == custom_trace

    @pytest.mark.asyncio
    async def test_nested_trace_ids(self, temp_log_dir):
        """Should support nested trace ID scopes."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        with logger.bind_trace_id("outer-trace"):
            logger.info("Outer operation started")

            with logger.bind_trace_id("inner-trace"):
                logger.info("Inner operation")

            logger.info("Outer operation complete")

        await logger.flush()
        await logger.stop_async_writer()

        # Verify trace IDs
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        entries = [json.loads(line) for line in lines]

        assert entries[0]["trace_id"] == "outer-trace"
        assert entries[1]["trace_id"] == "inner-trace"
        assert entries[2]["trace_id"] == "outer-trace"  # Restored

    @pytest.mark.asyncio
    async def test_trace_id_propagation_through_functions(self, temp_log_dir):
        """Should propagate trace ID through function calls."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        def inner_function():
            """Inner function that logs."""
            logger.info("Inner function log")

        def outer_function():
            """Outer function that calls inner."""
            logger.info("Outer function log")
            inner_function()

        # Bind trace ID at top level
        with logger.bind_trace_id("propagation-test"):
            outer_function()

        await logger.flush()
        await logger.stop_async_writer()

        # Verify both logs have same trace ID
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        trace_ids = [json.loads(line)["trace_id"] for line in lines]

        assert all(tid == "propagation-test" for tid in trace_ids)

    @pytest.mark.asyncio
    async def test_get_current_trace_id(self, temp_log_dir):
        """Should be able to get current trace ID."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        with logger.bind_trace_id("test-trace") as bound_trace:
            current_trace = get_trace_id()
            assert current_trace == "test-trace"
            assert current_trace == bound_trace

        await logger.stop_async_writer()

    @pytest.mark.asyncio
    async def test_trace_id_restoration_on_exception(self, temp_log_dir):
        """Should restore previous trace ID even on exception."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        with logger.bind_trace_id("outer-trace"):
            logger.info("Outer operation")

            try:
                with logger.bind_trace_id("inner-trace"):
                    logger.info("Inner operation")
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # Should restore outer trace
            logger.info("After exception")

        await logger.flush()
        await logger.stop_async_writer()

        # Verify trace IDs
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        entries = [json.loads(line) for line in lines]

        assert entries[0]["trace_id"] == "outer-trace"
        assert entries[1]["trace_id"] == "inner-trace"
        assert entries[2]["trace_id"] == "outer-trace"  # Restored


class TestTraceIdQueryability:
    """Tests for trace ID queryability (finding related logs)."""

    @pytest.mark.asyncio
    async def test_filter_logs_by_trace_id(self, temp_log_dir):
        """Should be able to filter logs by trace ID."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        # Log multiple operations with different trace IDs
        with logger.bind_trace_id("trace-A"):
            logger.info("Operation A - step 1")
            logger.info("Operation A - step 2")

        with logger.bind_trace_id("trace-B"):
            logger.info("Operation B - step 1")
            logger.info("Operation B - step 2")

        await logger.flush()
        await logger.stop_async_writer()

        # Read and filter logs
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        # Filter by trace-A
        trace_a_logs = [
            json.loads(line)
            for line in lines
            if json.loads(line)["trace_id"] == "trace-A"
        ]

        assert len(trace_a_logs) == 2
        assert "Operation A - step 1" in trace_a_logs[0]["message"]
        assert "Operation A - step 2" in trace_a_logs[1]["message"]

    @pytest.mark.asyncio
    async def test_trace_correlation_with_context(self, temp_log_dir):
        """Should correlate logs via trace ID and context."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        # Simulate task processing with trace ID
        with logger.bind_trace_id() as trace_id:
            with logger.bind_context(task_id="task-001"):
                logger.info("Task processing started")
                logger.info("Processing file 1")
                logger.info("Processing file 2")
                logger.info("Task processing complete")

        await logger.flush()
        await logger.stop_async_writer()

        # Verify all logs can be correlated
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        for line in lines:
            entry = json.loads(line)
            # All should have same trace ID and task ID
            assert entry["trace_id"] == trace_id
            assert entry["context"]["task_id"] == "task-001"

    @pytest.mark.asyncio
    async def test_concurrent_operations_different_traces(self, temp_log_dir):
        """Should maintain separate trace IDs for concurrent operations."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        async def operation_1():
            with logger.bind_trace_id("op1-trace"):
                logger.info("Operation 1 - step A")
                await asyncio.sleep(0.01)
                logger.info("Operation 1 - step B")

        async def operation_2():
            with logger.bind_trace_id("op2-trace"):
                logger.info("Operation 2 - step A")
                await asyncio.sleep(0.01)
                logger.info("Operation 2 - step B")

        # Run concurrently
        await asyncio.gather(operation_1(), operation_2())

        await logger.flush()
        await logger.stop_async_writer()

        # Verify trace IDs correctly isolated
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        op1_logs = [
            json.loads(line)
            for line in lines
            if json.loads(line)["trace_id"] == "op1-trace"
        ]
        op2_logs = [
            json.loads(line)
            for line in lines
            if json.loads(line)["trace_id"] == "op2-trace"
        ]

        assert len(op1_logs) == 2
        assert len(op2_logs) == 2

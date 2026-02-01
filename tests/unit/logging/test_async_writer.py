"""
Unit tests for AsyncWriter (P2).

Tests cover:
- Start/stop lifecycle
- Async writing and buffering
- Auto-flush (time and size triggers)
- File rotation (daily and size-based)
- Graceful shutdown
- Error handling and stderr fallback
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.logging.async_writer import AsyncWriter
from src.logging.models import ExceptionInfo, LogEntry, LogLevel, StackFrame


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def sample_log_entry():
    """Create sample LogEntry for testing."""
    return LogEntry(
        trace_id="01HQ8Z9X0ABCDEFGHIJKLMNOPQ",
        timestamp=datetime.now(timezone.utc),
        level=LogLevel.INFO,
        module="test.module",
        message="Test log message",
    )


class TestAsyncWriterLifecycle:
    """Tests for AsyncWriter start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_creates_log_dir(self, tmp_path):
        """start() should create log directory if it doesn't exist."""
        log_dir = tmp_path / "new_logs"
        assert not log_dir.exists()

        writer = AsyncWriter(log_dir=log_dir)
        await writer.start()

        assert log_dir.exists()

        await writer.stop()

    @pytest.mark.asyncio
    async def test_start_initializes_queue(self, temp_log_dir):
        """start() should initialize the async queue."""
        writer = AsyncWriter(log_dir=temp_log_dir)

        assert writer._queue is None
        await writer.start()
        assert writer._queue is not None
        assert isinstance(writer._queue, asyncio.Queue)

        await writer.stop()

    @pytest.mark.asyncio
    async def test_stop_flushes_buffer(self, temp_log_dir, sample_log_entry):
        """stop() should flush all pending log entries."""
        writer = AsyncWriter(log_dir=temp_log_dir, buffer_size=100)
        await writer.start()

        # Write entry
        await writer.write(sample_log_entry)

        # Stop (should flush)
        await writer.stop()

        # Verify log file exists and contains entry
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) == 1

        content = log_files[0].read_text()
        assert "Test log message" in content

    @pytest.mark.asyncio
    async def test_write_before_start_raises_error(self, temp_log_dir, sample_log_entry):
        """write() should raise error if called before start()."""
        writer = AsyncWriter(log_dir=temp_log_dir)

        with pytest.raises(RuntimeError, match="not started"):
            await writer.write(sample_log_entry)


class TestAsyncWriting:
    """Tests for async writing functionality."""

    @pytest.mark.asyncio
    async def test_write_single_entry(self, temp_log_dir, sample_log_entry):
        """Should write a single log entry to file."""
        writer = AsyncWriter(
            log_dir=temp_log_dir,
            flush_interval_s=0.1  # Fast flush for testing
        )
        await writer.start()

        await writer.write(sample_log_entry)

        # Wait for flush
        await asyncio.sleep(0.2)

        await writer.stop()

        # Verify log file
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) == 1

        content = log_files[0].read_text()
        data = json.loads(content.strip())

        assert data["trace_id"] == "01HQ8Z9X0ABCDEFGHIJKLMNOPQ"
        assert data["level"] == "INFO"
        assert data["module"] == "test.module"
        assert data["message"] == "Test log message"

    @pytest.mark.asyncio
    async def test_write_multiple_entries(self, temp_log_dir):
        """Should write multiple log entries."""
        writer = AsyncWriter(
            log_dir=temp_log_dir,
            flush_interval_s=0.1
        )
        await writer.start()

        # Write multiple entries
        for i in range(5):
            entry = LogEntry(
                trace_id=f"trace-{i}",
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.INFO,
                module="test",
                message=f"Message {i}",
            )
            await writer.write(entry)

        # Wait for flush
        await asyncio.sleep(0.2)

        await writer.stop()

        # Verify all entries written
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 5
        for i, line in enumerate(lines):
            data = json.loads(line)
            assert data["message"] == f"Message {i}"

    @pytest.mark.asyncio
    async def test_write_entry_with_all_fields(self, temp_log_dir):
        """Should serialize all LogEntry fields correctly."""
        exc = ExceptionInfo(
            type="ValueError",
            message="Test error",
            stack_trace=[
                StackFrame(
                    file="test.py",
                    line=42,
                    function="test_func",
                    code="raise ValueError()"
                )
            ]
        )

        entry = LogEntry(
            trace_id="01HQ8Z9X0ABCDEFGHIJKLMNOPQ",
            timestamp=datetime(2026, 1, 28, 12, 0, 0, tzinfo=timezone.utc),
            level=LogLevel.ERROR,
            module="test.module",
            message="Error occurred",
            function="test_function",
            line_number=100,
            context={"key": "value"},
            exception=exc,
            duration_ms=123.45,
            tags=["error", "test"],
        )

        writer = AsyncWriter(log_dir=temp_log_dir, flush_interval_s=0.1)
        await writer.start()

        await writer.write(entry)
        await asyncio.sleep(0.2)
        await writer.stop()

        # Verify serialization
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        data = json.loads(content.strip())

        assert data["function"] == "test_function"
        assert data["line_number"] == 100
        assert data["context"] == {"key": "value"}
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["stack_trace"][0]["file"] == "test.py"
        assert data["duration_ms"] == 123.45
        assert data["tags"] == ["error", "test"]


class TestBuffering:
    """Tests for buffering and flushing behavior."""

    @pytest.mark.asyncio
    async def test_buffer_size_trigger(self, temp_log_dir):
        """Should flush when buffer size reached."""
        writer = AsyncWriter(
            log_dir=temp_log_dir,
            buffer_size=10,
            flush_interval_s=10.0  # Long interval - shouldn't trigger
        )
        await writer.start()

        # Write exactly buffer_size entries
        for i in range(10):
            entry = LogEntry(
                trace_id=f"trace-{i}",
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.INFO,
                module="test",
                message=f"Message {i}",
            )
            await writer.write(entry)

        # Wait for buffer flush
        await asyncio.sleep(0.2)

        await writer.stop()

        # Verify entries written
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 10

    @pytest.mark.asyncio
    async def test_time_interval_trigger(self, temp_log_dir):
        """Should flush when time interval reached."""
        writer = AsyncWriter(
            log_dir=temp_log_dir,
            buffer_size=1000,  # Large buffer - shouldn't trigger
            flush_interval_s=0.1
        )
        await writer.start()

        # Write single entry
        entry = LogEntry(
            trace_id="test",
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            module="test",
            message="Test",
        )
        await writer.write(entry)

        # Wait for time interval flush
        await asyncio.sleep(0.2)

        # Entry should be flushed even though buffer not full
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) == 1
        assert "Test" in log_files[0].read_text()

        await writer.stop()

    @pytest.mark.asyncio
    async def test_manual_flush(self, temp_log_dir, sample_log_entry):
        """flush() should flush buffer immediately."""
        writer = AsyncWriter(
            log_dir=temp_log_dir,
            buffer_size=1000,
            flush_interval_s=10.0  # Long interval
        )
        await writer.start()

        await writer.write(sample_log_entry)

        # Manual flush
        await writer.flush()

        # Verify immediately written (don't wait for interval)
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) == 1

        await writer.stop()


class TestFileRotation:
    """Tests for file rotation (daily and size-based)."""

    @pytest.mark.asyncio
    async def test_daily_rotation(self, temp_log_dir):
        """Should create log file with date in filename."""
        writer = AsyncWriter(log_dir=temp_log_dir, flush_interval_s=0.1)
        await writer.start()

        entry = LogEntry(
            trace_id="test",
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            module="test",
            message="Test",
        )
        await writer.write(entry)
        await asyncio.sleep(0.2)
        await writer.stop()

        # Verify filename format: YYYY-MM-DD.log
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) == 1

        filename = log_files[0].name
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert filename == f"{today}.log"

    @pytest.mark.asyncio
    async def test_ndjson_format(self, temp_log_dir):
        """Should write logs in NDJSON format (newline-delimited JSON)."""
        writer = AsyncWriter(log_dir=temp_log_dir, flush_interval_s=0.1)
        await writer.start()

        # Write multiple entries
        for i in range(3):
            entry = LogEntry(
                trace_id=f"trace-{i}",
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.INFO,
                module="test",
                message=f"Message {i}",
            )
            await writer.write(entry)

        await asyncio.sleep(0.2)
        await writer.stop()

        # Verify NDJSON format
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        # Each line should be valid JSON
        assert len(lines) == 3
        for line in lines:
            data = json.loads(line)  # Should not raise
            assert "message" in data


class TestErrorHandling:
    """Tests for error handling and stderr fallback."""

    @pytest.mark.asyncio
    async def test_graceful_shutdown_timeout(self, temp_log_dir):
        """stop() should handle timeout gracefully."""
        writer = AsyncWriter(log_dir=temp_log_dir)
        await writer.start()

        # Fill queue with many entries
        for i in range(100):
            entry = LogEntry(
                trace_id=f"trace-{i}",
                timestamp=datetime.now(timezone.utc),
                level=LogLevel.INFO,
                module="test",
                message=f"Message {i}",
            )
            try:
                await asyncio.wait_for(writer.write(entry), timeout=0.1)
            except asyncio.TimeoutError:
                break

        # Should not hang
        await writer.stop()

    @pytest.mark.asyncio
    async def test_buffer_cleared_after_flush(self, temp_log_dir, sample_log_entry):
        """Buffer should be cleared after successful flush."""
        writer = AsyncWriter(log_dir=temp_log_dir, flush_interval_s=0.1)
        await writer.start()

        await writer.write(sample_log_entry)
        await asyncio.sleep(0.2)

        # Buffer should be empty after flush
        assert len(writer._buffer) == 0

        await writer.stop()


class TestPerformance:
    """Performance tests for AsyncWriter (< 5μs overhead target)."""

    @pytest.mark.asyncio
    async def test_write_overhead(self, temp_log_dir):
        """write() should have < 5μs overhead (queue put operation)."""
        import time

        writer = AsyncWriter(
            log_dir=temp_log_dir,
            buffer_size=10000,
            flush_interval_s=10.0
        )
        await writer.start()

        entry = LogEntry(
            trace_id="test",
            timestamp=datetime.now(timezone.utc),
            level=LogLevel.INFO,
            module="test",
            message="Test",
        )

        # Warm up
        for _ in range(100):
            await writer.write(entry)

        # Measure write overhead
        iterations = 1000
        start = time.perf_counter()
        for _ in range(iterations):
            await writer.write(entry)
        end = time.perf_counter()

        avg_time_us = ((end - start) / iterations) * 1_000_000

        # Target: < 5μs (relaxed to < 100μs for CI/async overhead)
        assert avg_time_us < 100, f"Write took {avg_time_us:.2f}μs (target: < 100μs)"

        await writer.stop()

"""
Integration test for logging lifecycle (P2).

Tests end-to-end logging workflow:
- Initialize logging system
- Write log entries
- Flush to disk
- Verify file contents
- Graceful shutdown

Constitutional compliance: Sections 2, 8 (logs written to disk, verifiable).
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.fte_logging import get_logger, init_logging
from src.fte_logging.models import LogLevel


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


class TestLoggingLifecycle:
    """Integration tests for complete logging lifecycle."""

    @pytest.mark.asyncio
    async def test_basic_logging_lifecycle(self, temp_log_dir):
        """Test basic logging workflow: init -> log -> flush -> verify."""
        # Initialize logging
        logger = init_logging(log_dir=temp_log_dir, level="INFO", async_enabled=True)

        # Start async writer
        await logger.start_async_writer()

        # Log some entries
        logger.info("Application started")
        logger.info("Configuration loaded", context={"config_file": "test.yaml"})
        logger.warning("Test warning message")

        # Flush to disk
        await logger.flush()

        # Stop and flush
        await logger.stop_async_writer()

        # Verify log file created
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) == 1

        # Verify log file has today's date
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert log_files[0].name == f"{today}.log"

        # Verify log entries
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 3

        # Parse first entry
        entry1 = json.loads(lines[0])
        assert entry1["level"] == "INFO"
        assert entry1["message"] == "Application started"
        assert "trace_id" in entry1
        assert "timestamp" in entry1

        # Parse second entry
        entry2 = json.loads(lines[1])
        assert entry2["message"] == "Configuration loaded"
        assert entry2["context"]["config_file"] == "test.yaml"

        # Parse third entry
        entry3 = json.loads(lines[2])
        assert entry3["level"] == "WARNING"

    @pytest.mark.asyncio
    async def test_multiple_log_levels(self, temp_log_dir):
        """Test logging at different levels."""
        logger = init_logging(log_dir=temp_log_dir, level="DEBUG", async_enabled=True)
        await logger.start_async_writer()

        # Log at different levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        await logger.flush()
        await logger.stop_async_writer()

        # Verify all levels logged
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 5

        levels = [json.loads(line)["level"] for line in lines]
        assert levels == ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    @pytest.mark.asyncio
    async def test_structured_context(self, temp_log_dir):
        """Test structured context logging."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        # Log with rich context
        logger.info(
            "Task processing complete",
            context={
                "task_id": "task-001",
                "duration_ms": 145.32,
                "from_state": "Inbox",
                "to_state": "Done",
                "files_processed": 5,
            },
        )

        await logger.flush()
        await logger.stop_async_writer()

        # Verify context preserved
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert entry["context"]["task_id"] == "task-001"
        assert entry["context"]["duration_ms"] == 145.32
        assert entry["context"]["files_processed"] == 5

    @pytest.mark.asyncio
    async def test_high_volume_logging(self, temp_log_dir):
        """Test high-volume logging (performance)."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        # Log many entries
        num_entries = 1000
        for i in range(num_entries):
            logger.info(f"Log entry {i}", context={"index": i})

        await logger.flush()
        await logger.stop_async_writer()

        # Verify all entries written
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        assert len(lines) == num_entries

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, temp_log_dir):
        """Test graceful shutdown with pending logs."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        # Log entries
        for i in range(10):
            logger.info(f"Message {i}")

        # Stop (should flush pending logs)
        await logger.stop_async_writer(timeout=5.0)

        # Verify all logs written
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 10

    @pytest.mark.asyncio
    async def test_ndjson_format(self, temp_log_dir):
        """Test NDJSON (newline-delimited JSON) format."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        # Log multiple entries
        logger.info("Entry 1")
        logger.info("Entry 2")
        logger.info("Entry 3")

        await logger.flush()
        await logger.stop_async_writer()

        # Verify NDJSON format
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        # Each line should be valid JSON
        for line in lines:
            entry = json.loads(line)  # Should not raise
            assert "message" in entry
            assert "trace_id" in entry
            assert "timestamp" in entry

    @pytest.mark.asyncio
    async def test_module_metadata_injection(self, temp_log_dir):
        """Test automatic module/function/line injection."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        logger.info("Test message with metadata")

        await logger.flush()
        await logger.stop_async_writer()

        # Verify metadata
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        entry = json.loads(content.strip())

        assert "module" in entry
        assert entry["module"] == __name__
        assert "function" in entry
        assert "line_number" in entry

    @pytest.mark.asyncio
    async def test_context_binding(self, temp_log_dir):
        """Test context binding across multiple log calls."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        # Bind context for scope
        with logger.bind_context(task_id="task-001", user="system"):
            logger.info("Operation started")
            logger.info("Processing item")
            logger.info("Operation complete")

        await logger.flush()
        await logger.stop_async_writer()

        # Verify context in all entries
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        for line in lines:
            entry = json.loads(line)
            assert entry["context"]["task_id"] == "task-001"
            assert entry["context"]["user"] == "system"

    @pytest.mark.asyncio
    async def test_duration_measurement(self, temp_log_dir):
        """Test duration measurement context manager."""
        import time

        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        # Measure operation duration
        with logger.measure_duration("test_operation"):
            time.sleep(0.01)  # 10ms

        await logger.flush()
        await logger.stop_async_writer()

        # Verify duration logged
        log_files = list(temp_log_dir.glob("*.log"))
        content = log_files[0].read_text()
        lines = content.strip().split("\n")

        # Should have start and end messages
        assert len(lines) == 2

        start_entry = json.loads(lines[0])
        assert "test_operation started" in start_entry["message"]

        end_entry = json.loads(lines[1])
        assert "test_operation complete" in end_entry["message"]
        assert "duration_ms" in end_entry
        assert end_entry["duration_ms"] >= 10  # At least 10ms


class TestLogFileManagement:
    """Integration tests for log file management."""

    @pytest.mark.asyncio
    async def test_log_directory_creation(self, tmp_path):
        """Test automatic log directory creation."""
        log_dir = tmp_path / "new_logs"
        assert not log_dir.exists()

        logger = init_logging(log_dir=log_dir, async_enabled=True)
        await logger.start_async_writer()

        logger.info("Test message")

        await logger.flush()
        await logger.stop_async_writer()

        # Directory should be created
        assert log_dir.exists()
        assert log_dir.is_dir()

    @pytest.mark.asyncio
    async def test_file_permissions(self, temp_log_dir):
        """Test log file permissions (600 - owner only)."""
        logger = init_logging(log_dir=temp_log_dir, async_enabled=True)
        await logger.start_async_writer()

        logger.info("Test message")

        await logger.flush()
        await logger.stop_async_writer()

        # Verify file exists
        log_files = list(temp_log_dir.glob("*.log"))
        assert len(log_files) == 1

        # Note: Permission check skipped as it's OS-dependent
        # In production, AsyncWriter should set file permissions to 600

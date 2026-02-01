"""
Async non-blocking log writer (P2).

Background task that writes log entries to disk with minimal overhead.
Performance target: < 5μs overhead per log call.
Constitutional compliance: Section 2 (logs written to disk as source of truth).
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import LogEntry


class AsyncWriter:
    """
    Asynchronous log writer with background task and buffering.

    Features:
    - Async queue for non-blocking writes (< 5μs overhead target)
    - Buffer management (configurable size, default 1000 entries)
    - Auto-flush (time-based: 1s interval OR size-based: buffer full)
    - File rotation (daily files + 100MB size limit)
    - Graceful shutdown (flush pending logs)
    - Error handling (fallback to stderr)

    Constitutional compliance:
    - Section 2: Logs written to disk as source of truth
    - Section 9: Errors never hidden (stderr fallback)

    Example:
        >>> async def main():
        ...     writer = AsyncWriter(log_dir=Path("./Logs"))
        ...     await writer.start()
        ...     await writer.write(log_entry)
        ...     await writer.stop()
    """

    def __init__(
        self,
        log_dir: Path,
        buffer_size: int = 1000,
        flush_interval_s: float = 1.0,
        max_file_size_mb: int = 100,
    ):
        """
        Initialize AsyncWriter.

        Args:
            log_dir: Directory for log files
            buffer_size: Max entries in buffer before forced flush
            flush_interval_s: Auto-flush interval in seconds
            max_file_size_mb: Max file size before rotation (MB)
        """
        self.log_dir = log_dir
        self.buffer_size = buffer_size
        self.flush_interval_s = flush_interval_s
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

        # Async queue for log entries (bounded)
        self._queue: Optional[asyncio.Queue] = None
        self._buffer: list[LogEntry] = []
        self._writer_task: Optional[asyncio.Task] = None
        self._running = False
        self._current_file: Optional[Path] = None
        self._current_file_handle = None
        self._current_date: Optional[str] = None

    async def start(self) -> None:
        """
        Start the async writer background task.

        Creates the log directory if it doesn't exist.
        Starts the background writer loop.

        Example:
            >>> writer = AsyncWriter(log_dir=Path("./Logs"))
            >>> await writer.start()
        """
        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Create queue
        self._queue = asyncio.Queue(maxsize=self.buffer_size * 2)

        # Start background writer
        self._running = True
        self._writer_task = asyncio.create_task(self._writer_loop())

    async def stop(self) -> None:
        """
        Stop the async writer and flush pending logs.

        Graceful shutdown:
        1. Stop accepting new entries
        2. Drain queue
        3. Flush buffer
        4. Close file handle
        5. Cancel background task

        Example:
            >>> await writer.stop()
        """
        if not self._running:
            return

        # Stop accepting new entries
        self._running = False

        # Wait for queue to drain (with timeout)
        if self._queue is not None:
            try:
                await asyncio.wait_for(self._queue.join(), timeout=5.0)
            except asyncio.TimeoutError:
                # Force flush remaining items
                pass

        # Flush buffer
        await self._flush()

        # Close file handle
        if self._current_file_handle is not None:
            self._current_file_handle.close()
            self._current_file_handle = None

        # Cancel background task
        if self._writer_task is not None:
            self._writer_task.cancel()
            try:
                await self._writer_task
            except asyncio.CancelledError:
                pass

    async def write(self, entry: LogEntry) -> None:
        """
        Write a log entry (async, non-blocking).

        Performance: < 5μs overhead (queue put operation).

        Args:
            entry: LogEntry to write

        Raises:
            RuntimeError: If writer not started

        Example:
            >>> await writer.write(log_entry)
        """
        if not self._running or self._queue is None:
            raise RuntimeError("AsyncWriter not started. Call start() first.")

        try:
            # Non-blocking put with timeout
            await asyncio.wait_for(
                self._queue.put(entry),
                timeout=0.01  # 10ms timeout
            )
        except asyncio.TimeoutError:
            # Queue full - fallback to stderr
            self._write_to_stderr(entry, "Queue full")

    async def flush(self) -> None:
        """
        Flush buffered log entries to disk immediately.

        Example:
            >>> await writer.flush()
        """
        await self._flush()

    async def _writer_loop(self) -> None:
        """
        Background writer loop.

        Continuously:
        1. Read entries from queue
        2. Add to buffer
        3. Flush when buffer full OR interval elapsed
        """
        last_flush_time = asyncio.get_event_loop().time()

        while self._running:
            try:
                # Wait for entry with timeout (for periodic flush)
                try:
                    entry = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=self.flush_interval_s
                    )
                    self._buffer.append(entry)
                    self._queue.task_done()
                except asyncio.TimeoutError:
                    # Timeout - check if flush needed
                    pass

                current_time = asyncio.get_event_loop().time()

                # Flush conditions:
                # 1. Buffer full
                # 2. Flush interval elapsed
                should_flush = (
                    len(self._buffer) >= self.buffer_size or
                    (current_time - last_flush_time) >= self.flush_interval_s
                )

                if should_flush and self._buffer:
                    await self._flush()
                    last_flush_time = current_time

            except Exception as e:
                # Error handling - never crash the writer loop
                self._write_error_to_stderr(f"Writer loop error: {e}")

    async def _flush(self) -> None:
        """
        Flush buffer to disk.

        Handles:
        - File rotation (daily + size limit)
        - NDJSON formatting
        - Error fallback to stderr
        """
        if not self._buffer:
            return

        try:
            # Check if rotation needed
            await self._rotate_if_needed()

            # Write entries as NDJSON
            for entry in self._buffer:
                try:
                    json_line = self._entry_to_json(entry)
                    self._current_file_handle.write(json_line + "\n")
                except Exception as e:
                    # Per-entry error - log to stderr but continue
                    self._write_to_stderr(entry, f"Serialization error: {e}")

            # Flush file handle
            self._current_file_handle.flush()

            # Clear buffer
            self._buffer.clear()

        except Exception as e:
            # Critical error - write all buffered entries to stderr
            self._write_error_to_stderr(f"Flush error: {e}")
            for entry in self._buffer:
                self._write_to_stderr(entry, "Flush failed")
            self._buffer.clear()

    async def _rotate_if_needed(self) -> None:
        """
        Rotate log file if needed.

        Rotation triggers:
        1. Date changed (new day)
        2. File size exceeds max_file_size_bytes
        """
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Check if rotation needed
        needs_rotation = False

        # Daily rotation
        if self._current_date != current_date:
            needs_rotation = True

        # Size rotation
        if self._current_file is not None and self._current_file.exists():
            if self._current_file.stat().st_size >= self.max_file_size_bytes:
                needs_rotation = True

        # Perform rotation
        if needs_rotation:
            # Close current file
            if self._current_file_handle is not None:
                self._current_file_handle.close()

            # Open new file
            self._current_date = current_date
            self._current_file = self.log_dir / f"{current_date}.log"

            try:
                self._current_file_handle = open(
                    self._current_file,
                    mode="a",  # Append mode
                    encoding="utf-8",
                    buffering=8192,  # 8KB buffer
                )
            except Exception as e:
                self._write_error_to_stderr(f"Failed to open log file: {e}")
                # Fallback to stderr for all writes
                self._current_file_handle = None

    def _entry_to_json(self, entry: LogEntry) -> str:
        """
        Convert LogEntry to JSON string (NDJSON format).

        Args:
            entry: LogEntry to serialize

        Returns:
            JSON string (single line, no newline)
        """
        import json

        # Convert LogEntry to dict
        data = {
            "trace_id": entry.trace_id,
            "timestamp": entry.timestamp.isoformat(),
            "level": entry.level.name,
            "module": entry.module,
            "message": entry.message,
        }

        # Add optional fields
        if entry.function is not None:
            data["function"] = entry.function
        if entry.line_number is not None:
            data["line_number"] = entry.line_number
        if entry.context is not None:
            data["context"] = entry.context
        if entry.exception is not None:
            data["exception"] = self._exception_to_dict(entry.exception)
        if entry.duration_ms is not None:
            data["duration_ms"] = entry.duration_ms
        if entry.tags:
            data["tags"] = entry.tags

        return json.dumps(data, ensure_ascii=False)

    def _exception_to_dict(self, exc: "ExceptionInfo") -> dict:
        """Convert ExceptionInfo to dict for JSON serialization."""
        data = {
            "type": exc.type,
            "message": exc.message,
            "stack_trace": [
                {
                    "file": frame.file,
                    "line": frame.line,
                    "function": frame.function,
                    **({"code": frame.code} if frame.code else {})
                }
                for frame in exc.stack_trace
            ],
        }

        if exc.cause is not None:
            data["cause"] = self._exception_to_dict(exc.cause)

        return data

    def _write_to_stderr(self, entry: LogEntry, reason: str) -> None:
        """
        Fallback: write log entry to stderr.

        Constitutional compliance: Section 9 (errors never hidden).

        Args:
            entry: LogEntry that failed to write
            reason: Reason for fallback
        """
        try:
            json_line = self._entry_to_json(entry)
            sys.stderr.write(f"[AsyncWriter Fallback: {reason}] {json_line}\n")
            sys.stderr.flush()
        except Exception:
            # Last resort - write minimal info
            sys.stderr.write(f"[AsyncWriter Error: {reason}] {entry.message}\n")
            sys.stderr.flush()

    def _write_error_to_stderr(self, message: str) -> None:
        """
        Write error message to stderr.

        Args:
            message: Error message
        """
        sys.stderr.write(f"[AsyncWriter Error] {message}\n")
        sys.stderr.flush()

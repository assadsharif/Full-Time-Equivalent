"""
Logger service for structured, async logging (P2).

Provides high-level logging API with context binding, trace correlation,
and automatic secret redaction.

Constitutional compliance: Sections 2, 3, 8, 9 (disk-based, private, structured, errors never hidden).
"""

import asyncio
import inspect
import sys
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .async_writer import AsyncWriter
from .models import ExceptionInfo, LogEntry, LogLevel, StackFrame
from .redaction import SecretRedactor
from .trace import bind_trace_id as _bind_trace_id, get_trace_id, new_trace_id


# Context variable for bound context
_context_var: ContextVar[Dict[str, Any]] = ContextVar("log_context", default={})


class LoggerService:
    """
    Core logging service with structured, async logging.

    Features:
    - Structured logging with trace IDs
    - Async non-blocking writes (< 5μs overhead)
    - Automatic secret redaction
    - Context binding (contextvars)
    - Module/function/line injection
    - Exception capture with stack traces
    - Performance measurement

    Constitutional compliance:
    - Section 2: Logs written to disk
    - Section 3: Secrets auto-redacted
    - Section 8: Structured, append-only logs
    - Section 9: Errors never hidden

    Example:
        >>> from src.logging.config import from_file
        >>> config = from_file("config/logging.yaml")
        >>> logger = LoggerService(config)
        >>> logger.info("Application started")
    """

    def __init__(
        self,
        config: "LoggerConfig",
        *,
        start_async: bool = False
    ):
        """
        Initialize logging service.

        Args:
            config: Logging configuration
            start_async: Whether to start async writer (requires async context)

        Note:
            If start_async=True, call this from async context.
            Otherwise, call start_async_writer() manually later.
        """
        self.config = config
        self._redactor = SecretRedactor(
            patterns=config.secret_patterns,
            redaction_text=config.redaction_text
        )

        # Initialize async writer (but don't start yet)
        self._writer: Optional[AsyncWriter] = None
        if config.async_enabled:
            self._writer = AsyncWriter(
                log_dir=config.log_dir,
                buffer_size=config.buffer_size,
                flush_interval_s=config.flush_interval_s,
                max_file_size_mb=config.max_file_size_mb,
            )

            if start_async:
                # Start writer in current event loop
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._writer.start())
                except RuntimeError:
                    # No event loop running - user must call start_async_writer()
                    pass

    async def start_async_writer(self) -> None:
        """
        Start background async log writer task.

        Must be called from async context.

        Raises:
            RuntimeError: If async disabled or writer already running
        """
        if self._writer is None:
            raise RuntimeError("Async logging disabled in config")

        await self._writer.start()

    async def stop_async_writer(self, timeout: float = 5.0) -> None:
        """
        Stop async writer and flush pending logs.

        Args:
            timeout: Max seconds to wait for flush

        Raises:
            TimeoutError: If flush doesn't complete within timeout
        """
        if self._writer is None:
            return

        try:
            await asyncio.wait_for(self._writer.stop(), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Failed to flush logs within {timeout}s")

    async def flush(self) -> None:
        """Flush pending logs to disk immediately."""
        if self._writer is not None:
            await self._writer.flush()

    def log(
        self,
        level: LogLevel,
        message: str,
        *,
        trace_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[BaseException] = None,
        duration_ms: Optional[float] = None,
        tags: Optional[List[str]] = None
    ) -> None:
        """
        Log a message with structured context.

        Args:
            level: Log severity level
            message: Human-readable log message
            trace_id: Optional trace ID (auto-generated if None)
            context: Optional structured context dict
            exception: Optional exception to log
            duration_ms: Optional operation duration
            tags: Optional tags for categorization

        Performance: < 5μs overhead (non-blocking)

        Example:
            >>> logger.log(
            ...     LogLevel.INFO,
            ...     "Task transitioned",
            ...     context={"task_id": "task-001"}
            ... )
        """
        try:
            # Check if level should be logged
            if not self._should_log(level):
                return

            # Get or generate trace ID
            if trace_id is None:
                trace_id = get_trace_id() or new_trace_id()

            # Merge bound context with provided context
            merged_context = self._merge_context(context)

            # Redact secrets from message and context
            redacted_message = self._redactor.redact(message)
            redacted_context = None
            if merged_context:
                redacted_context = self._redactor.redact_dict(merged_context)

            # Capture caller information (module, function, line)
            frame = inspect.currentframe()
            if frame and frame.f_back:
                caller_frame = frame.f_back
                module = caller_frame.f_globals.get("__name__", "unknown")
                function = caller_frame.f_code.co_name
                line_number = caller_frame.f_lineno
            else:
                module = "unknown"
                function = None
                line_number = None

            # Capture exception info
            exception_info = None
            if exception is not None:
                exception_info = self._capture_exception(exception)

            # Create log entry
            entry = LogEntry(
                trace_id=trace_id,
                timestamp=datetime.now(timezone.utc),
                level=level,
                module=module,
                message=redacted_message,
                function=function,
                line_number=line_number,
                context=redacted_context,
                exception=exception_info,
                duration_ms=duration_ms,
                tags=tags or [],
            )

            # Write to async writer or fallback to stderr
            if self._writer is not None:
                # Schedule write in event loop
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self._writer.write(entry))
                except RuntimeError:
                    # No event loop - fallback to stderr
                    self._write_to_stderr(entry)
            else:
                # Sync mode - write to stderr
                self._write_to_stderr(entry)

        except Exception as e:
            # Never crash on logging error
            sys.stderr.write(f"[LoggerService Error] {e}: {message}\n")
            sys.stderr.flush()

    def debug(self, message: str, **kwargs) -> None:
        """Log DEBUG level message."""
        self.log(LogLevel.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log INFO level message."""
        self.log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log WARNING level message."""
        self.log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log ERROR level message."""
        self.log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log CRITICAL level message."""
        self.log(LogLevel.CRITICAL, message, **kwargs)

    @contextmanager
    def bind_context(self, **context: Any) -> Iterator[None]:
        """
        Bind context to all logs in this scope.

        Args:
            **context: Key-value pairs to bind

        Example:
            >>> with logger.bind_context(task_id="task-001"):
            ...     logger.info("Operation started")
            ...     logger.info("Operation complete")
        """
        # Get current context
        current_context = _context_var.get().copy()

        # Merge new context
        current_context.update(context)

        # Set new context
        token = _context_var.set(current_context)

        try:
            yield
        finally:
            # Restore previous context
            _context_var.reset(token)

    @contextmanager
    def bind_trace_id(self, trace_id: Optional[str] = None) -> Iterator[str]:
        """
        Bind trace ID to all logs in this scope.

        Args:
            trace_id: Optional trace ID (auto-generated if None)

        Yields:
            trace_id: The bound trace ID

        Example:
            >>> with logger.bind_trace_id() as trace_id:
            ...     logger.info("Operation started")
            ...     do_work(trace_id)
        """
        with _bind_trace_id(trace_id) as bound_id:
            yield bound_id

    @contextmanager
    def measure_duration(
        self,
        operation_name: str,
        *,
        log_level: LogLevel = LogLevel.INFO,
        log_message: Optional[str] = None,
        **context: Any
    ) -> Iterator[None]:
        """
        Measure and log operation duration.

        Args:
            operation_name: Name of operation
            log_level: Log level for messages
            log_message: Optional custom log message
            **context: Additional context to bind

        Example:
            >>> with logger.measure_duration("file_operation", path="/tmp/file"):
            ...     atomic_move(src, dst)
        """
        start_time = time.perf_counter()

        # Log start
        self.log(
            log_level,
            f"{operation_name} started",
            context=context
        )

        try:
            yield
        finally:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log end with duration
            message = log_message or f"{operation_name} complete"
            self.log(
                log_level,
                message,
                context=context,
                duration_ms=duration_ms
            )

    def set_level(self, level: LogLevel, module: Optional[str] = None) -> None:
        """
        Change log level at runtime.

        Args:
            level: New log level
            module: Optional module name (global if None)
        """
        if module is None:
            self.config.level = level
        else:
            self.config.module_levels[module] = level

    def get_level(self, module: Optional[str] = None) -> LogLevel:
        """
        Get current log level.

        Args:
            module: Optional module name (global if None)

        Returns:
            Current log level
        """
        if module is None:
            return self.config.level
        return self.config.module_levels.get(module, self.config.level)

    def _should_log(self, level: LogLevel) -> bool:
        """Check if log level should be logged."""
        # Get caller module for level check
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            caller_frame = frame.f_back.f_back
            module = caller_frame.f_globals.get("__name__", "")
        else:
            module = ""

        # Check module-specific level
        for mod_prefix, mod_level in self.config.module_levels.items():
            if module.startswith(mod_prefix):
                return level >= mod_level

        # Check global level
        return level >= self.config.level

    def _merge_context(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge bound context with provided context."""
        bound_context = _context_var.get()

        if context is None:
            return bound_context.copy()

        merged = bound_context.copy()
        merged.update(context)
        return merged

    def _capture_exception(self, exception: BaseException) -> ExceptionInfo:
        """
        Capture exception with full stack trace.

        Args:
            exception: Exception to capture

        Returns:
            ExceptionInfo with stack trace
        """
        import traceback

        # Get exception type and message
        exc_type = type(exception).__name__
        exc_message = str(exception)

        # Extract stack trace
        tb = exception.__traceback__
        stack_frames = []

        if tb is not None:
            for frame_summary in traceback.extract_tb(tb):
                stack_frames.append(
                    StackFrame(
                        file=frame_summary.filename,
                        line=frame_summary.lineno,
                        function=frame_summary.name,
                        code=frame_summary.line
                    )
                )

        # Capture chained exception (__cause__)
        cause = None
        if exception.__cause__ is not None:
            cause = self._capture_exception(exception.__cause__)

        return ExceptionInfo(
            type=exc_type,
            message=exc_message,
            stack_trace=stack_frames,
            cause=cause
        )

    def _write_to_stderr(self, entry: LogEntry) -> None:
        """
        Fallback: write log entry to stderr.

        Args:
            entry: LogEntry to write
        """
        import json

        try:
            data = {
                "trace_id": entry.trace_id,
                "timestamp": entry.timestamp.isoformat(),
                "level": entry.level.name,
                "module": entry.module,
                "message": entry.message,
            }

            if entry.context:
                data["context"] = entry.context

            sys.stderr.write(json.dumps(data) + "\n")
            sys.stderr.flush()
        except Exception:
            # Last resort
            sys.stderr.write(f"[{entry.level.name}] {entry.message}\n")
            sys.stderr.flush()

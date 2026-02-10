# API Contract: LoggerService

**Module**: `src.fte_logging.logger_service`
**Purpose**: Core logging service for structured, async logging with context and correlation
**Status**: Planning

---

## Overview

`LoggerService` provides the primary interface for application logging. It wraps structlog with custom processors, async queue management, and constitutional compliance enforcement.

---

## Class: LoggerService

### Constructor

```python
def __init__(
    self,
    config: LoggerConfig,
    *,
    start_async_writer: bool = True
) -> None:
    """
    Initialize logging service.

    Args:
        config: Logging configuration (log_dir, levels, format, etc.)
        start_async_writer: Whether to start background async writer immediately

    Raises:
        ValueError: If config is invalid (e.g., log_dir doesn't exist and can't be created)
        RuntimeError: If async writer fails to start

    Side Effects:
        - Creates log_dir if it doesn't exist
        - Starts background asyncio task for log writing
        - Registers shutdown handler

    Constitutional Compliance:
        - Section 3: All logs written to local filesystem (log_dir)
        - Section 8: Append-only log files created
    """
```

---

## Core Logging Methods

### log()

```python
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
        trace_id: Optional trace ID for correlation (auto-generated if None)
        context: Optional structured context dict
        exception: Optional exception to log (auto-captures stack trace)
        duration_ms: Optional operation duration in milliseconds
        tags: Optional tags for categorization

    Returns:
        None

    Raises:
        Never raises. Logging failures logged to stderr, never crash application.

    Side Effects:
        - Adds entry to async queue (non-blocking, < 5μs)
        - Auto-redacts secrets in message and context
        - Injects module/function/line metadata

    Performance:
        - Overhead: < 1μs for queue insertion
        - Non-blocking: Never waits for disk I/O
        - Backpressure: Drops DEBUG logs if queue full

    Example:
        >>> logger.log(
        ...     LogLevel.INFO,
        ...     "Task transitioned successfully",
        ...     context={"task_id": "task-001", "from_state": "Inbox"},
        ...     duration_ms=145.32
        ... )

    Constitutional Compliance:
        - Section 8: All required fields included (timestamp, action, result)
        - Section 3: Secrets auto-redacted before queueing
    """
```

### debug(), info(), warning(), error(), critical()

```python
def debug(self, message: str, **kwargs) -> None:
    """Convenience method for DEBUG level logging."""

def info(self, message: str, **kwargs) -> None:
    """Convenience method for INFO level logging."""

def warning(self, message: str, **kwargs) -> None:
    """Convenience method for WARNING level logging."""

def error(self, message: str, **kwargs) -> None:
    """Convenience method for ERROR level logging."""

def critical(self, message: str, **kwargs) -> None:
    """Convenience method for CRITICAL level logging."""
```

**Parameters**: Same as `log()` except `level` is implicit
**Example**:
```python
logger.info("Task created", context={"task_id": "task-001"})
logger.error("File operation failed", exception=e, context={"path": "/tmp/file.txt"})
```

---

## Context Management

### bind_context()

```python
@contextmanager
def bind_context(self, **context: Any) -> Iterator[None]:
    """
    Temporarily bind context to all logs in this scope.

    Args:
        **context: Key-value pairs to bind

    Yields:
        None

    Example:
        >>> with logger.bind_context(task_id="task-001", user="system"):
        ...     logger.info("Starting operation")  # Automatically includes task_id, user
        ...     do_work()
        ...     logger.info("Operation complete")  # Also includes task_id, user

    Thread Safety:
        Uses contextvars for thread-safe context isolation

    Constitutional Compliance:
        - Section 8: Context preserved across log entries for auditability
    """
```

### bind_trace_id()

```python
@contextmanager
def bind_trace_id(self, trace_id: Optional[str] = None) -> Iterator[str]:
    """
    Bind trace ID to all logs in this scope.

    Args:
        trace_id: Optional trace ID (auto-generated ULID if None)

    Yields:
        trace_id: The bound trace ID (useful for propagation)

    Example:
        >>> with logger.bind_trace_id() as trace_id:
        ...     logger.info("Operation started")
        ...     result = do_work(trace_id)  # Pass to child operations
        ...     logger.info("Operation complete")

    Constitutional Compliance:
        - Section 8: Trace ID enables complete operation audit trail
    """
```

---

## Lifecycle Management

### start_async_writer()

```python
async def start_async_writer(self) -> None:
    """
    Start background async log writer task.

    Raises:
        RuntimeError: If writer already running or event loop not available

    Side Effects:
        - Creates asyncio task for background writing
        - Registers signal handlers for graceful shutdown

    Constitutional Compliance:
        - Section 9: Errors logged, never hidden
    """
```

### stop_async_writer()

```python
async def stop_async_writer(self, timeout: float = 5.0) -> None:
    """
    Stop background async log writer and flush pending logs.

    Args:
        timeout: Max seconds to wait for flush (default 5.0)

    Raises:
        TimeoutError: If flush doesn't complete within timeout

    Side Effects:
        - Waits for queue to drain
        - Writes all pending logs to disk
        - Closes log files
        - Cancels background task

    Constitutional Compliance:
        - Section 8: All logs flushed to disk before shutdown
        - Section 13: Completion verified via disk inspection
    """
```

### flush()

```python
async def flush(self) -> None:
    """
    Flush pending logs to disk immediately.

    Waits for all queued log entries to be written.

    Raises:
        Never raises. Errors logged to stderr.

    Timeout:
        Max 5 seconds. After timeout, logs warning and returns.

    Example:
        >>> await logger.flush()  # Ensure logs written before critical operation
    """
```

---

## Configuration Methods

### set_level()

```python
def set_level(self, level: LogLevel, module: Optional[str] = None) -> None:
    """
    Change log level at runtime.

    Args:
        level: New log level
        module: Optional module name (global if None)

    Example:
        >>> logger.set_level(LogLevel.DEBUG, module="src.control_plane")
        >>> logger.set_level(LogLevel.WARNING)  # Global level

    Thread Safety:
        Thread-safe. Uses atomic config updates.
    """
```

### get_level()

```python
def get_level(self, module: Optional[str] = None) -> LogLevel:
    """
    Get current log level.

    Args:
        module: Optional module name (global if None)

    Returns:
        Current log level for specified module or global

    Example:
        >>> logger.get_level("src.control_plane")
        LogLevel.DEBUG
    """
```

---

## Metrics Methods

### log_metric()

```python
def log_metric(
    self,
    metric_name: str,
    value: float,
    *,
    metric_type: MetricType = MetricType.GAUGE,
    unit: str = "units",
    trace_id: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Log a metric entry.

    Args:
        metric_name: Metric identifier (e.g., "file_operation.duration")
        value: Numeric value
        metric_type: Type of metric (COUNTER, GAUGE, DURATION, HISTOGRAM)
        unit: Unit of measurement (e.g., "milliseconds", "bytes")
        trace_id: Optional trace ID for correlation
        tags: Optional tags for metric dimensions

    Side Effects:
        - Writes metric entry to separate metrics log file
        - Format: Logs/metrics/YYYY-MM-DD.metrics.log

    Example:
        >>> logger.log_metric(
        ...     "state_transition.duration",
        ...     145.32,
        ...     metric_type=MetricType.DURATION,
        ...     unit="milliseconds",
        ...     tags={"from_state": "Inbox", "to_state": "Needs_Action"}
        ... )

    Constitutional Compliance:
        - Section 8: Metrics logged for auditability
    """
```

### measure_duration()

```python
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
        operation_name: Name of operation (used in metric name)
        log_level: Log level for start/end messages
        log_message: Optional custom log message (default: "Operation complete")
        **context: Additional context to bind

    Yields:
        None

    Side Effects:
        - Logs start message
        - Logs end message with duration
        - Writes metric entry

    Example:
        >>> with logger.measure_duration("file_operation", path="/tmp/file.txt"):
        ...     atomic_move(src, dst)
        # Logs: "Operation complete" with duration_ms context

    Constitutional Compliance:
        - Section 8: Performance data logged for audit
    """
```

---

## Internal Methods (Not for Public Use)

### _redact_secrets()

```python
def _redact_secrets(self, text: str) -> str:
    """
    Redact secrets from text using configured patterns.

    Args:
        text: Text to scan

    Returns:
        Text with secrets replaced by redaction_text

    Performance:
        - < 1μs per entry for typical log messages
        - Uses compiled regex patterns (cached)

    Constitutional Compliance:
        - Section 3: Secrets never written to disk
    """
```

### _async_writer_loop()

```python
async def _async_writer_loop(self) -> None:
    """
    Background task that writes queued logs to disk.

    Runs continuously until stop_async_writer() called.

    Behavior:
        - Polls queue every 100ms
        - Flushes when buffer_size reached OR flush_interval_s elapsed
        - Handles file rotation (daily + size-based)

    Error Handling:
        - Logs errors to stderr
        - Never crashes (continues processing queue)
        - Graceful degradation if disk full

    Constitutional Compliance:
        - Section 8: Append-only writes
        - Section 9: Errors never hidden
    """
```

---

## Usage Examples

### Basic Logging

```python
from src.fte_logging import LoggerService, LoggerConfig, LogLevel

# Initialize logger
config = LoggerConfig.from_file("config/logging.yaml")
logger = LoggerService(config)

# Simple logging
logger.info("Application started")
logger.debug("Configuration loaded", context={"config_file": "logging.yaml"})

# Error logging with exception
try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed", exception=e, context={"operation": "risky"})
```

### Context Binding

```python
# Bind context for operation scope
with logger.bind_trace_id() as trace_id:
    with logger.bind_context(task_id="task-001", user="system"):
        logger.info("Starting task processing")
        process_task()
        logger.info("Task processing complete")
# All logs above include trace_id, task_id, user context
```

### Performance Measurement

```python
# Measure operation duration
with logger.measure_duration("state_transition", from_state="Inbox", to_state="Needs_Action"):
    state_machine.transition(task, WorkflowState.NEEDS_ACTION, reason="...", actor="system")
# Automatically logs duration metric + end message
```

### Shutdown Handling

```python
import asyncio

async def main():
    logger = LoggerService(config)

    try:
        await run_application()
    finally:
        # Ensure all logs flushed before exit
        await logger.stop_async_writer(timeout=5.0)

asyncio.run(main())
```

---

## Thread Safety

- ✅ **Thread-safe**: All public methods are thread-safe
- ✅ **Async-safe**: Compatible with asyncio applications
- ✅ **Context isolation**: Uses `contextvars` for proper context propagation

---

## Performance Guarantees

| Operation | Max Overhead | Notes |
|-----------|--------------|-------|
| `log()` call | < 5μs | Queue insertion only |
| Context binding | < 1μs | Uses contextvars |
| Secret redaction | < 1μs per entry | Compiled regex patterns |
| Async writer | < 1% CPU | Background task |
| Flush operation | < 100ms | For typical buffer (1000 entries) |

---

## Constitutional Compliance Summary

| Section | Requirement | Compliance |
|---------|-------------|------------|
| Section 2 | File system is source of truth | ✅ All logs written to disk |
| Section 3 | Local-first, secrets protected | ✅ Local files, auto-redaction |
| Section 8 | Append-only, structured logs | ✅ NDJSON format, append mode |
| Section 9 | Errors never hidden | ✅ Failures logged to stderr |
| Section 13 | State verifiable via disk | ✅ Log files inspectable |

---

## Error Handling

### Logging Failures
- **Queue Full**: Drop DEBUG logs, then INFO, etc. Log warning to stderr.
- **Disk Full**: Log CRITICAL to stderr, continue queueing (hope for space).
- **Permission Error**: Log CRITICAL to stderr, fallback to `/tmp/fte-logs/`.
- **Async Writer Crash**: Restart writer, log ERROR. Never crash application.

### Fallback Behavior
1. Primary: Write to configured `log_dir`
2. Fallback 1: Write to stderr (JSON format preserved)
3. Fallback 2: Write to `/tmp/fte-emergency.log`
4. Last Resort: Print to stdout (human-readable format)

---

## Testing Strategy

### Unit Tests
- Secret redaction with various patterns
- Context binding and propagation
- Log level filtering
- Async queue backpressure

### Integration Tests
- Async writer lifecycle (start, stop, crash recovery)
- File rotation (daily + size-based)
- Multi-threaded logging
- Graceful shutdown with pending logs

### Performance Tests
- Throughput: 100k logs/sec minimum
- Latency: < 5μs per log call (99th percentile)
- Memory: Bounded queue size, no leaks

---

## Next Steps

1. Implement `LoggerService` class in `src/logging/logger_service.py`
2. Implement async writer in `src/logging/async_writer.py`
3. Implement secret redaction in `src/logging/redaction.py`
4. Create unit tests in `tests/unit/logging/test_logger_service.py`
5. Create integration tests in `tests/integration/test_logging_lifecycle.py`

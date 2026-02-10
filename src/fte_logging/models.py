"""
Data models for logging infrastructure (P2).

All models are passive dataclasses with no I/O or side effects.
Constitutional compliance: Section 8 (structured, append-only logging).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum, Enum
from pathlib import Path
from typing import Optional


class LogLevel(IntEnum):
    """Standard log severity levels (numerically ordered by severity)."""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class MetricType(Enum):
    """Types of metrics that can be logged."""

    COUNTER = "counter"  # Incrementing count (e.g., requests_total)
    GAUGE = "gauge"  # Point-in-time value (e.g., queue_size)
    DURATION = "duration"  # Time measurement (e.g., operation_duration_ms)
    HISTOGRAM = "histogram"  # Distribution of values (e.g., response_time_buckets)


@dataclass(frozen=True)
class StackFrame:
    """
    Represents a single frame in an exception stack trace.

    Constitutional compliance: Section 9 (capture full error context).
    """

    file: str  # Source file path (relative)
    line: int  # Line number
    function: str  # Function name
    code: Optional[str] = None  # Source code line


@dataclass(frozen=True)
class ExceptionInfo:
    """
    Captures exception details for error logging.

    Supports chained exceptions (__cause__) for full error context.
    Constitutional compliance: Section 9 (errors never hidden).
    """

    type: str  # Exception class name
    message: str  # Exception message
    stack_trace: list[StackFrame]  # Full stack trace
    cause: Optional["ExceptionInfo"] = None  # Chained exception (__cause__)


@dataclass(frozen=True)
class LogEntry:
    """
    Represents a single structured log entry.

    Immutable once created (append-only logging).
    Constitutional compliance: Sections 2, 3, 8, 9.

    Validation rules (enforced at creation):
    - trace_id: valid ULID format (26 characters, Base32)
    - timestamp: UTC timezone
    - level: one of LogLevel enum values
    - module: Python module naming conventions
    - message: secrets auto-redacted before creation
    - context: dict keys must be snake_case strings
    - duration_ms: non-negative if present
    """

    trace_id: str  # ULID for correlation
    timestamp: datetime  # When log was created (UTC)
    level: LogLevel  # Log severity level
    module: str  # Python module name
    message: str  # Human-readable log message (redacted)
    function: Optional[str] = None  # Function name where log originated
    line_number: Optional[int] = None  # Source code line number
    context: Optional[dict] = None  # Structured context data
    exception: Optional[ExceptionInfo] = None  # Exception details if error
    duration_ms: Optional[float] = None  # Operation duration in milliseconds
    tags: list[str] = field(default_factory=list)  # Tags for categorization


@dataclass(frozen=True)
class MetricEntry:
    """
    Structured performance and operational metrics.

    Shares trace_id with LogEntry for correlation.
    Constitutional compliance: Section 8 (structured logging).
    """

    trace_id: str  # Correlation ID (ULID)
    timestamp: datetime  # When metric was recorded (UTC)
    metric_name: str  # Metric identifier (e.g., "file_operation.duration")
    metric_type: MetricType  # Type of metric
    value: float  # Numeric value
    unit: str  # Unit of measurement (e.g., "milliseconds")
    tags: dict[str, str] = field(default_factory=dict)  # Metric dimensions


@dataclass(frozen=True)
class LoggerConfig:
    """
    Configuration for logging system behavior.

    Loaded from config/logging.yaml or environment variables.
    Constitutional compliance: Section 3 (local-first, privacy).
    """

    log_dir: Path = Path("./Logs")  # Directory for log files
    level: LogLevel = LogLevel.INFO  # Global minimum log level
    module_levels: dict[str, LogLevel] = field(
        default_factory=dict
    )  # Per-module overrides
    format: str = "json"  # Output format (json, console, hybrid)
    async_enabled: bool = True  # Use async logging queue
    buffer_size: int = 1000  # Max entries in async queue
    flush_interval_s: float = 1.0  # Auto-flush interval in seconds
    retention_days: int = 30  # Log retention period
    compression_enabled: bool = True  # Compress logs older than 7 days
    max_file_size_mb: int = 100  # Max size before rotation
    secret_patterns: list[str] = field(
        default_factory=list
    )  # Regex patterns for secrets
    redaction_text: str = "***REDACTED***"  # Replacement for secrets


@dataclass
class LogQuery:
    """
    Query parameters for log retrieval and filtering.

    Used with QueryService to filter and search logs.
    Constitutional compliance: Section 2 (queries read from disk).
    """

    start_time: Optional[datetime] = None  # Filter logs after this time
    end_time: Optional[datetime] = None  # Filter logs before this time
    levels: Optional[list[LogLevel]] = None  # Filter by log levels
    modules: Optional[list[str]] = None  # Filter by modules
    trace_id: Optional[str] = None  # Filter by trace ID
    search_text: Optional[str] = None  # Full-text search in message
    tags: Optional[list[str]] = None  # Filter by tags (AND logic)
    limit: int = 1000  # Max results to return
    offset: int = 0  # Skip first N results
    order_by: str = "timestamp"  # Sort field
    order_dir: str = "desc"  # Sort direction (asc/desc)

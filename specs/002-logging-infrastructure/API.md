# Logging Infrastructure - API Documentation

**Version**: 0.1.0
**Status**: Implemented (US1, US2)
**Constitutional Compliance**: Sections 2, 3, 8, 9

---

## Quick Start

```python
import asyncio
from src.logging import init_logging, get_logger

async def main():
    # Initialize logging system
    logger = init_logging(log_dir="./Logs", level="INFO")
    await logger.start_async_writer()

    # Get logger for your module
    logger = get_logger(__name__)

    # Basic logging
    logger.info("Application started")
    logger.debug("Debug information", context={"user": "alice"})

    # Error logging with exception
    try:
        risky_operation()
    except Exception as e:
        logger.error("Operation failed", exception=e)

    # Trace correlation
    with logger.bind_trace_id() as trace_id:
        logger.info("Starting operation", context={"step": 1})
        do_work()
        logger.info("Operation complete", context={"step": 2})

    # Duration measurement
    with logger.measure_duration("database_query"):
        result = db.query("SELECT * FROM users")

    # Graceful shutdown
    await logger.stop_async_writer()

asyncio.run(main())
```

---

## Core Functions

### `init_logging()`

Initialize the global logging system.

```python
def init_logging(
    config_path: Optional[str | Path] = None,
    *,
    log_dir: Optional[str | Path] = None,
    level: Optional[str | LogLevel] = None,
    async_enabled: bool = True,
) -> LoggerService
```

**Parameters:**
- `config_path` (str | Path, optional): Path to `logging.yaml` configuration file
- `log_dir` (str | Path, optional): Log directory override (default: `./Logs`)
- `level` (str | LogLevel, optional): Log level override (default: `INFO`)
- `async_enabled` (bool): Enable async logging (default: `True`)

**Returns:**
- `LoggerService`: Global logger instance

**Example:**
```python
# With config file
logger = init_logging(config_path="config/logging.yaml")

# With overrides
logger = init_logging(log_dir="./logs", level="DEBUG")

# With environment variables
logger = init_logging()  # Uses LOGGING_* env vars
```

---

### `get_logger()`

Get the global logger instance.

```python
def get_logger(name: Optional[str] = None) -> LoggerService
```

**Parameters:**
- `name` (str, optional): Logger name (typically `__name__`)

**Returns:**
- `LoggerService`: Global logger instance

**Example:**
```python
logger = get_logger(__name__)
logger.info("Module initialized")
```

---

## LoggerService Class

The main logging interface.

### Logging Methods

#### `log()`

Log a message with structured context.

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
) -> None
```

**Parameters:**
- `level` (LogLevel): Log severity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `message` (str): Human-readable log message
- `trace_id` (str, optional): Trace ID for correlation (auto-generated if None)
- `context` (dict, optional): Structured context data
- `exception` (Exception, optional): Exception to log with stack trace
- `duration_ms` (float, optional): Operation duration in milliseconds
- `tags` (list[str], optional): Tags for categorization

**Example:**
```python
logger.log(
    LogLevel.INFO,
    "Task completed",
    context={"task_id": "task-001", "result": "success"},
    duration_ms=145.32,
    tags=["task", "completion"]
)
```

#### Convenience Methods

```python
logger.debug("Debug message", context={"detail": "value"})
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message", exception=e)
logger.critical("Critical error", exception=e)
```

### Context Management

#### `bind_context()`

Bind context to all logs in scope.

```python
@contextmanager
def bind_context(self, **context: Any) -> Iterator[None]
```

**Example:**
```python
with logger.bind_context(task_id="task-001", user="alice"):
    logger.info("Starting task")  # Includes task_id and user
    process_task()
    logger.info("Task complete")  # Also includes task_id and user
```

#### `bind_trace_id()`

Bind trace ID to all logs in scope.

```python
@contextmanager
def bind_trace_id(self, trace_id: Optional[str] = None) -> Iterator[str]
```

**Example:**
```python
with logger.bind_trace_id() as trace_id:
    logger.info("Operation started")
    do_work(trace_id)  # Pass to child operations
    logger.info("Operation complete")
# All logs share same trace_id
```

#### `measure_duration()`

Measure and log operation duration.

```python
@contextmanager
def measure_duration(
    self,
    operation_name: str,
    *,
    log_level: LogLevel = LogLevel.INFO,
    log_message: Optional[str] = None,
    **context: Any
) -> Iterator[None]
```

**Example:**
```python
with logger.measure_duration("database_query", table="users"):
    result = db.query("SELECT * FROM users")
# Logs start and end messages with duration_ms
```

### Lifecycle Management

#### `start_async_writer()`

Start background async log writer.

```python
async def start_async_writer(self) -> None
```

**Example:**
```python
await logger.start_async_writer()
```

#### `stop_async_writer()`

Stop async writer and flush pending logs.

```python
async def stop_async_writer(self, timeout: float = 5.0) -> None
```

**Example:**
```python
await logger.stop_async_writer(timeout=10.0)
```

#### `flush()`

Flush pending logs immediately.

```python
async def flush(self) -> None
```

**Example:**
```python
await logger.flush()
```

### Configuration

#### `set_level()`

Change log level at runtime.

```python
def set_level(self, level: LogLevel, module: Optional[str] = None) -> None
```

**Example:**
```python
# Global level
logger.set_level(LogLevel.DEBUG)

# Per-module level
logger.set_level(LogLevel.DEBUG, module="src.control_plane")
```

#### `get_level()`

Get current log level.

```python
def get_level(self, module: Optional[str] = None) -> LogLevel
```

---

## Trace ID Functions

### `new_trace_id()`

Generate a new ULID-based trace ID.

```python
def new_trace_id() -> str
```

**Returns:**
- `str`: 26-character ULID (sortable, timestamp-embedded)

**Example:**
```python
trace_id = new_trace_id()
# '01HQ8Z9X0ABCDEFGHIJKLMNOPQ'
```

### `get_trace_id()`

Get the current trace ID from context.

```python
def get_trace_id() -> Optional[str]
```

**Returns:**
- `str | None`: Current trace ID or None

**Example:**
```python
current_trace = get_trace_id()
if current_trace:
    print(f"Trace: {current_trace}")
```

### `bind_trace_id()`

Bind trace ID to execution context.

```python
@contextmanager
def bind_trace_id(trace_id: Optional[str] = None) -> Iterator[str]
```

---

## QueryService Class

High-performance log querying with DuckDB.

### Initialization

```python
from pathlib import Path
from src.logging.query_service import QueryService

service = QueryService(log_dir=Path("./Logs"))
```

### Query Methods

#### `query()`

Query logs with structured filters.

```python
def query(
    self,
    query_params: LogQuery,
    *,
    format: str = "dict"
) -> Union[List[LogEntry], str]
```

**Parameters:**
- `query_params` (LogQuery): Query filters
- `format` (str): Output format ("dict", "json", "csv", "table")

**Example:**
```python
from datetime import datetime, timedelta
from src.logging.models import LogQuery, LogLevel

params = LogQuery(
    start_time=datetime.now() - timedelta(hours=1),
    levels=[LogLevel.ERROR, LogLevel.CRITICAL],
    limit=100
)
results = service.query(params, format="json")
```

#### `filter_by_trace()`

Get all logs for a trace ID.

```python
def filter_by_trace(
    self,
    trace_id: str,
    *,
    order_by: str = "timestamp"
) -> List[LogEntry]
```

**Example:**
```python
logs = service.filter_by_trace("01HQ8Z9X0ABCDEFGHIJKLMNOPQ")
for log in logs:
    print(f"{log.timestamp}: {log.message}")
```

#### `filter_by_time_range()`

Get logs in time range.

```python
def filter_by_time_range(
    self,
    start_time: datetime,
    end_time: datetime,
    *,
    level: Optional[LogLevel] = None,
    module: Optional[str] = None
) -> List[LogEntry]
```

**Example:**
```python
from datetime import datetime, timedelta

start = datetime.now() - timedelta(hours=24)
end = datetime.now()
logs = service.filter_by_time_range(start, end, level=LogLevel.ERROR)
```

#### `search_text()`

Full-text search in log messages.

```python
def search_text(
    self,
    search_term: str,
    *,
    case_sensitive: bool = False,
    limit: int = 100
) -> List[LogEntry]
```

**Example:**
```python
logs = service.search_text("disk full", limit=50)
```

#### `query_sql()`

Execute raw SQL query.

```python
def query_sql(
    self,
    sql: str,
    *,
    params: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]
```

**Example:**
```python
sql = "SELECT level, COUNT(*) as count FROM logs GROUP BY level"
results = service.query_sql(sql)
```

---

## CLI Commands

### `fte logs tail`

View recent log entries.

```bash
# Last 10 entries (default)
fte logs tail

# Last 50 entries
fte logs tail --lines 50

# JSON format
fte logs tail -n 100 --format json

# Custom log directory
fte logs tail --log-dir /var/log/fte
```

### `fte logs query`

Query logs with filters.

```bash
# Filter by level
fte logs query --level ERROR --level CRITICAL

# Filter by module
fte logs query --module src.control_plane

# Time range (ISO format)
fte logs query --start "2026-01-28 00:00:00" --end "2026-01-28 23:59:59"

# Time range (relative)
fte logs query --start 1h --end now

# Trace ID
fte logs query --trace-id 01HQ8Z9X0ABCDEFGHIJKLMNOPQ

# Combined filters
fte logs query --level ERROR --start 24h --limit 50 --format json
```

### `fte logs search`

Full-text search.

```bash
# Case-insensitive search
fte logs search "disk full"

# Case-sensitive search
fte logs search "Error" --case-sensitive

# Search in last hour
fte logs search "timeout" --last 1h

# JSON output
fte logs search "failed" --format json --limit 100
```

---

## Configuration

### YAML Configuration

**File:** `config/logging.yaml`

```yaml
# Log directory
log_dir: ./Logs

# Global log level
level: INFO

# Per-module log levels
module_levels:
  src.control_plane: DEBUG
  src.mcp_servers: WARNING

# Output format
format: json

# Async logging
async_enabled: true
async_writer:
  buffer_size: 1000
  flush_interval_seconds: 1.0

# Secret redaction
secret_redaction:
  enabled: true
  patterns:
    - "(?i)(api[_-]?key|apikey)[\"']?\\s*[:=]\\s*[\"']?([a-zA-Z0-9_\\-]{20,})"
    - "(?i)(password|passwd|pwd)[\"']?\\s*[:=]\\s*[\"']?([^\\s\"']{6,})"
  redaction_text: "***REDACTED***"

# Log retention
retention:
  max_log_age_days: 30
  max_archive_size_mb: 100
  compression: gzip
```

### Environment Variables

```bash
# Log directory
export LOGGING_LOG_DIR=/var/log/fte

# Log level
export LOGGING_LEVEL=DEBUG

# Per-module levels
export LOGGING_MODULE_LEVELS="src.control_plane=DEBUG,src.mcp_servers=WARNING"

# Async settings
export LOGGING_ASYNC_ENABLED=true
export LOGGING_BUFFER_SIZE=2000
export LOGGING_FLUSH_INTERVAL_S=0.5

# Secret patterns
export LOGGING_SECRET_PATTERNS="api_key=\\w+|Bearer \\w+"
export LOGGING_REDACTION_TEXT="[HIDDEN]"
```

---

## Models

### LogLevel

Log severity levels (enum).

```python
from src.logging.models import LogLevel

LogLevel.DEBUG      # 10
LogLevel.INFO       # 20
LogLevel.WARNING    # 30
LogLevel.ERROR      # 40
LogLevel.CRITICAL   # 50
```

### LogEntry

Immutable log entry (dataclass).

```python
@dataclass(frozen=True)
class LogEntry:
    trace_id: str
    timestamp: datetime
    level: LogLevel
    module: str
    message: str
    function: Optional[str] = None
    line_number: Optional[int] = None
    context: Optional[dict] = None
    exception: Optional[ExceptionInfo] = None
    duration_ms: Optional[float] = None
    tags: list[str] = field(default_factory=list)
```

### LogQuery

Query parameters (dataclass).

```python
@dataclass
class LogQuery:
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    levels: Optional[list[LogLevel]] = None
    modules: Optional[list[str]] = None
    trace_id: Optional[str] = None
    search_text: Optional[str] = None
    tags: Optional[list[str]] = None
    limit: int = 1000
    offset: int = 0
    order_by: str = "timestamp"
    order_dir: str = "desc"
```

---

## Performance Guarantees

| Operation | Target | Notes |
|-----------|--------|-------|
| Log call overhead | < 5μs | Queue insertion only |
| Context binding | < 1μs | Uses contextvars |
| Secret redaction | < 1μs/entry | Compiled regex |
| Simple query | < 500ms | 1GB logs |
| Complex query | < 3s | With filters |
| 1GB log query | < 10s | Constitutional requirement |
| Flush operation | < 100ms | 1000 entries |

---

## Constitutional Compliance

| Section | Requirement | Implementation |
|---------|-------------|----------------|
| Section 2 | File system as source of truth | All logs written to disk |
| Section 3 | Local-first, privacy | Local files, auto-redaction |
| Section 8 | Structured, append-only | NDJSON format, append mode |
| Section 9 | Errors never hidden | Exception capture, stderr fallback |
| Section 13 | State verifiable | Log files inspectable |

---

## Error Handling

### Logging Failures

- **Queue Full**: Drop DEBUG logs, then INFO (graceful degradation)
- **Disk Full**: Log to stderr, continue queueing
- **Permission Error**: Log to stderr, attempt `/tmp/fte-logs/`
- **Writer Crash**: Restart writer, log ERROR

### Fallback Hierarchy

1. **Primary**: Write to `log_dir`
2. **Fallback 1**: Write to stderr (JSON format)
3. **Fallback 2**: Write to `/tmp/fte-emergency.log`
4. **Last Resort**: Print to stdout

---

## Thread Safety

- ✅ All public methods are thread-safe
- ✅ Compatible with asyncio applications
- ✅ Context isolation via `contextvars`
- ✅ No global mutable state

---

## See Also

- [Implementation Plan](plan.md)
- [Task Breakdown](tasks.md)
- [API Contracts](contracts/)
- [Data Model](data-model.md)

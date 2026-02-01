# Quick Start: Logging Infrastructure

**Feature**: 002-logging-infrastructure
**Audience**: Developers implementing or using the logging system
**Time to read**: 10 minutes

> **💡 New to the logging system?** Check out the [usage examples](examples/) directory for complete, runnable code demonstrating all features. See [API.md](API.md) for comprehensive API reference.

---

## What This Feature Does

Adds comprehensive logging infrastructure to the Digital FTE with:
- **Structured logging** at DEBUG/INFO/WARNING/ERROR/CRITICAL levels
- **Trace correlation** across operations with ULID trace IDs
- **Async logging** (non-blocking, < 5μs overhead)
- **Automatic secret redaction** (API keys, tokens, passwords)
- **High-performance queries** (DuckDB SQL, < 3s for 1GB logs)
- **Metrics logging** (durations, counts, gauges)
- **Constitutional compliance** (local-first, append-only, auditable)

**Key Constraint**: This feature is ADDITIVE ONLY. The frozen MVP control plane code (`src/control_plane/logger.py`) is NOT modified.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Code                         │
│                                                              │
│  from src.logging import get_logger                         │
│  logger = get_logger(__name__)                              │
│  logger.info("Message", context={...})                      │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              LoggerService (structlog)                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Processors: Context → Redaction → JSON → Queue      │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼ (async queue, non-blocking)
┌─────────────────────────────────────────────────────────────┐
│              AsyncWriter (background task)                   │
│                                                              │
│  Buffers logs → Flushes to disk (1s or 1000 entries)       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                   Log Files (NDJSON)                        │
│                                                              │
│  Logs/2026-01-28.log  (application logs)                   │
│  Logs/metrics/2026-01-28.metrics.log  (metrics)            │
│  Logs/archive/2026-01-21.log.gz  (compressed archives)     │
└─────────────────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│              QueryService (DuckDB)                          │
│                                                              │
│  SQL queries → Virtual tables → Results (< 3s)             │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start: Using the Logger

### 1. Initialize Logger (Application Startup)

```python
from src.logging import init_logging, get_logger
from pathlib import Path

# Initialize logging system (do this once at startup)
init_logging(
    log_dir=Path("./Logs"),
    level="INFO",
    module_levels={
        "src.control_plane": "DEBUG",
        "src.mcp_servers": "WARNING"
    }
)

# Get module-specific logger
logger = get_logger(__name__)
```

### 2. Basic Logging

```python
# Simple messages
logger.debug("Detailed diagnostic info")
logger.info("Normal operation completed")
logger.warning("Something unexpected but not critical")
logger.error("Operation failed but system continues")
logger.critical("System stability at risk")

# With context (structured data)
logger.info(
    "Task created",
    context={
        "task_id": "task-001",
        "priority": "P1",
        "created_by": "system"
    }
)

# With exception
try:
    risky_operation()
except Exception as e:
    logger.error(
        "Operation failed",
        exception=e,
        context={"operation": "risky_operation"}
    )
```

### 3. Trace Correlation

```python
from src.logging import get_logger, new_trace_id

logger = get_logger(__name__)

def process_task(task_id: str) -> None:
    # Generate trace ID for this operation
    trace_id = new_trace_id()  # ULID: 01HQ8Z9X0ABCDEFGHIJKLMNOPQ

    # Bind trace ID to all logs in this scope
    with logger.bind_trace_id(trace_id):
        logger.info("Starting task processing", context={"task_id": task_id})

        # All logs here automatically include trace_id
        do_step_1()
        do_step_2()

        logger.info("Task processing complete")
```

### 4. Context Binding

```python
def handle_request(user_id: str, request_data: dict) -> None:
    # Bind context for entire request scope
    with logger.bind_context(user_id=user_id, request_type="api"):
        logger.info("Request received")

        # Process request (all logs include user_id, request_type)
        result = process_request(request_data)

        logger.info("Request completed", context={"result": result})
```

### 5. Performance Measurement

```python
from src.logging import get_logger

logger = get_logger(__name__)

def expensive_operation() -> None:
    # Automatically log duration
    with logger.measure_duration("file_operation", path="/tmp/file.txt"):
        # Do work...
        atomic_move(src, dst)

    # Logs: "Operation complete" with duration_ms context
    # Also writes metric entry: file_operation.duration = 145.32ms
```

---

## Quick Start: Querying Logs

### 1. Initialize Query Service

```python
from src.logging import QueryService, LogQuery, LogLevel
from pathlib import Path
from datetime import datetime, timedelta

# Initialize
query_service = QueryService(log_dir=Path("./Logs"))
```

### 2. Simple Queries

```python
# Get recent errors
params = LogQuery(
    start_time=datetime.now() - timedelta(hours=1),
    levels=[LogLevel.ERROR, LogLevel.CRITICAL],
    limit=100
)
errors = query_service.query(params)

for error in errors:
    print(f"{error.timestamp} [{error.module}] {error.message}")
```

### 3. Trace Analysis

```python
# Reconstruct operation trace
trace = query_service.trace_operation("01HQ8Z9X0ABCDEFGHIJKLMNOPQ")

print(f"Operation took {trace.duration_ms}ms")
print(f"Success: {trace.success}")

for log in trace.logs:
    print(f"  {log.timestamp} [{log.level}] {log.message}")
```

### 4. SQL Queries (Advanced)

```python
# Custom SQL query
results = query_service.query_sql("""
    SELECT
        module,
        COUNT(*) as error_count
    FROM logs
    WHERE
        level >= 40  -- ERROR or CRITICAL
        AND timestamp >= ?
    GROUP BY module
    ORDER BY error_count DESC
    LIMIT 10
""", params={"1": "2026-01-28T00:00:00Z"})

print("Top modules by error count:")
for row in results:
    print(f"  {row['module']}: {row['error_count']}")
```

### 5. Export Results

```python
# Export errors to JSON
params = LogQuery(
    start_time=datetime.now() - timedelta(days=1),
    levels=[LogLevel.ERROR, LogLevel.CRITICAL]
)

count = query_service.export_to_json(
    params,
    Path("errors_last_24h.json"),
    pretty=True
)

print(f"Exported {count} errors to errors_last_24h.json")
```

---

## CLI Usage

> **📋 Complete CLI examples:** See [examples/05_cli_usage.sh](examples/05_cli_usage.sh) for comprehensive CLI usage examples.

The logging infrastructure provides three CLI commands: `tail`, `query`, and `search`.

### View Recent Logs

```bash
# Show last 100 logs
python -m src.cli.logs tail --lines 100

# Show last 10 logs in table format (default)
python -m src.cli.logs tail -n 10 --format table

# Output as JSON
python -m src.cli.logs tail -n 50 --format json

# Output as CSV
python -m src.cli.logs tail -n 100 --format csv
```

### Query Logs with Filters

```bash
# Query by log level
python -m src.cli.logs query --level ERROR --level CRITICAL --limit 20

# Query by time range (ISO format)
python -m src.cli.logs query \
  --start "2026-01-28 00:00:00" \
  --end "2026-01-28 23:59:59" \
  --level ERROR \
  --limit 50

# Query by relative time (last hour)
python -m src.cli.logs query --start 1h --limit 20

# Query by relative time (last 24 hours)
python -m src.cli.logs query --start 24h --level WARNING --limit 50

# Query by trace ID
python -m src.cli.logs query --trace-id "01HQ8Z9X0ABCDEFGHIJKLMNOPQ"

# Query by module
python -m src.cli.logs query --module src.logging --limit 20

# Complex query with multiple filters
python -m src.cli.logs query \
  --level ERROR \
  --level CRITICAL \
  --start 24h \
  --limit 10 \
  --format json
```

### Full-Text Search

```bash
# Search for text in logs
python -m src.cli.logs search "disk full" --limit 20

# Case-sensitive search
python -m src.cli.logs search "Error" --case-sensitive --limit 10

# Search in last hour
python -m src.cli.logs search "task" --last 1h --limit 20

# Search with relative time
python -m src.cli.logs search "authentication" --last 24h --limit 50
```

### Output Formats

All CLI commands support multiple output formats:

```bash
# Table format (default, human-readable)
python -m src.cli.logs tail -n 10 --format table

# JSON format (machine-readable, for piping)
python -m src.cli.logs query --level ERROR --format json

# CSV format (for spreadsheets)
python -m src.cli.logs query --level ERROR --format csv > errors.csv
```

---

## Configuration

### config/logging.yaml

```yaml
# Core settings
log_dir: ./Logs
level: INFO  # Global minimum level

# Per-module levels
module_levels:
  src.control_plane: DEBUG
  src.mcp_servers: WARNING
  src.logging: WARNING

# Output format
format: json  # json | console | hybrid

# Async settings
async_enabled: true
buffer_size: 1000  # Max entries in queue
flush_interval_s: 1.0  # Auto-flush interval

# Retention settings
retention_days: 30
compression_enabled: true
max_file_size_mb: 100

# Secret redaction
secret_patterns:
  - 'api_key=[\w-]+'
  - 'Bearer [\w-]+'
  - 'password=[\w-]+'
  - 'token=[\w-]+'
redaction_text: "***REDACTED***"
```

### Environment Variables (Alternative)

```bash
# Override config via environment (prefix: LOGGING_)
export LOGGING_LOG_DIR="./Logs"
export LOGGING_LEVEL="DEBUG"
export LOGGING_FORMAT="json"
export LOGGING_ASYNC_ENABLED="true"
export LOGGING_BUFFER_SIZE="1000"
export LOGGING_FLUSH_INTERVAL_S="1.0"

# Per-module levels (comma-separated)
export LOGGING_MODULE_LEVELS="src.control_plane=DEBUG,src.mcp_servers=WARNING"

# Secret redaction patterns (pipe-separated)
export LOGGING_SECRET_PATTERNS="api_key=[\w-]+|Bearer [\w-]+|password=[\w-]+"
export LOGGING_REDACTION_TEXT="***REDACTED***"
```

---

## Integration with Existing Code

### Don't Modify: Frozen Control Plane

The existing `AuditLogger` in `src/control_plane/logger.py` is FROZEN and continues to work as-is:

```python
# This code remains unchanged
from src.control_plane.logger import AuditLogger

audit_logger = AuditLogger(log_dir=Path("./Logs"))
audit_logger.log_transition(transition)  # Still works
```

### Do Use: New Logging for Application Code

New application code uses the new logging infrastructure:

```python
# New code uses src.logging
from src.logging import get_logger

logger = get_logger(__name__)
logger.info("New feature logged here")
```

### Coexistence

Both logging systems write to the same `Logs/` directory:
- **Control plane logs**: `Logs/YYYY-MM-DD.log` (from AuditLogger)
- **Application logs**: `Logs/YYYY-MM-DD.log` (from LoggerService)

They use the same NDJSON format, so queries work across both log sources.

---

## Common Patterns

### Pattern 1: Request-Scoped Logging

```python
async def handle_api_request(request_id: str, user_id: str) -> Response:
    with logger.bind_trace_id() as trace_id:
        with logger.bind_context(request_id=request_id, user_id=user_id):
            logger.info("API request received")

            try:
                result = await process_request()
                logger.info("API request succeeded")
                return Response(status=200, data=result)
            except Exception as e:
                logger.error("API request failed", exception=e)
                return Response(status=500, error=str(e))
```

### Pattern 2: Background Task Logging

```python
async def background_task() -> None:
    logger = get_logger("background_worker")

    while True:
        with logger.bind_trace_id():
            logger.info("Background task cycle started")

            try:
                await process_queue()
                logger.info("Background task cycle completed")
            except Exception as e:
                logger.error("Background task failed", exception=e)

            await asyncio.sleep(60)
```

### Pattern 3: Conditional Debug Logging

```python
def complex_algorithm(data: List[int]) -> int:
    logger = get_logger(__name__)

    # Only logged if module level is DEBUG
    logger.debug("Algorithm input", context={"size": len(data)})

    for i, value in enumerate(data):
        # Expensive debug logging (lazy evaluation)
        logger.debug(
            "Processing item",
            context=lambda: {"index": i, "value": value, "partial_result": compute_partial()}
        )

    result = sum(data)
    logger.debug("Algorithm output", context={"result": result})
    return result
```

---

## Testing

### Integration Tests with QueryService

```python
import pytest
from pathlib import Path
from src.logging import init_logging, get_logger
from src.logging.query_service import QueryService
from src.logging.models import LogQuery, LogLevel

@pytest.fixture
async def logger_service(tmp_path):
    """Fixture that provides an initialized logger."""
    logger = init_logging(log_dir=tmp_path, level="DEBUG", async_enabled=True)
    await logger.start_async_writer()
    yield logger
    await logger.stop_async_writer()

@pytest.fixture
def query_service(tmp_path):
    """Fixture that provides a QueryService."""
    return QueryService(log_dir=tmp_path)

async def test_error_logging(logger_service, query_service):
    """Test that error logs can be queried."""
    logger = get_logger("test")

    # Generate logs
    logger.info("Test started")
    logger.error("Test error", context={"error_code": 123})

    # Flush logs to disk
    await logger_service.flush()

    # Query logs
    params = LogQuery(levels=[LogLevel.ERROR])
    errors = query_service.query(params, format="dict")

    assert len(errors) >= 1
    error_log = next(e for e in errors if e.message == "Test error")
    assert error_log.context["error_code"] == 123

async def test_trace_correlation(logger_service, query_service):
    """Test that trace IDs correlate logs."""
    logger = get_logger("test")

    with logger.bind_trace_id() as trace_id:
        logger.info("Step 1")
        logger.info("Step 2")
        logger.info("Step 3")

    # Flush logs to disk
    await logger_service.flush()

    # Query by trace ID
    trace_logs = query_service.filter_by_trace(trace_id)

    assert len(trace_logs) == 3
    assert all(log.trace_id == trace_id for log in trace_logs)
```

---

## Performance Tuning

### Async Logging (Default)

```python
# Async logging is default (< 5μs overhead)
init_logging(log_dir=Path("./Logs"), async_enabled=True)
```

### Sync Logging (Simpler, Slightly Slower)

```python
# Disable async for debugging (logs written immediately)
init_logging(log_dir=Path("./Logs"), async_enabled=False)
```

### Buffer Tuning

```python
# Larger buffer = higher throughput, more memory
init_logging(
    log_dir=Path("./Logs"),
    buffer_size=5000,  # Default: 1000
    flush_interval_s=2.0  # Default: 1.0
)
```

### Query Optimization

```python
# Use columnar selection (faster)
results = query_service.query_sql("""
    SELECT timestamp, level, message  -- Only needed columns
    FROM logs
    WHERE timestamp >= ?
""")

# Avoid SELECT * on large datasets
```

---

## Troubleshooting

### Problem: Logs Not Appearing

**Check**:
1. Log level configured correctly? (`logger.set_level(LogLevel.DEBUG)`)
2. Async writer started? (`await logger.start_async_writer()`)
3. Logs flushed? (`await logger.flush()`)

**Solution**:
```python
# Force immediate write for debugging
init_logging(log_dir=Path("./Logs"), async_enabled=False)
```

### Problem: High Memory Usage

**Check**:
- Is async queue filling up faster than flushing?

**Solution**:
```python
# Reduce buffer size or decrease flush interval
init_logging(
    log_dir=Path("./Logs"),
    buffer_size=500,  # Default: 1000
    flush_interval_s=0.5  # Default: 1.0
)
```

### Problem: Slow Queries

**Check**:
- Are you using `SELECT *` on large datasets?
- Are you querying compressed archives without time filters?

**Solution**:
```python
# Use specific columns and time filters
params = LogQuery(
    start_time=start,  # Always specify time range
    end_time=end,
    levels=[LogLevel.ERROR]  # Filter early
)
```

---

## Next Steps

1. **Try Examples**: Run the [usage examples](examples/) to see the logging system in action
2. **Read API Reference**: See [API.md](API.md) for complete API documentation
3. **Read Full Spec**: [spec.md](spec.md) for requirements and user stories
4. **Review API Contracts**: [contracts/](contracts/) for detailed API contracts
5. **Check Data Model**: [data-model.md](data-model.md) for entity definitions
6. **Review Research**: [research.md](research.md) for design decisions
7. **See Implementation Plan**: [plan.md](plan.md) for architecture details

---

## Key Takeaways

✅ **Simple API**: `logger.info("message", context={...})`
✅ **Non-blocking**: < 5μs overhead per log call
✅ **Correlation**: Trace IDs link related operations
✅ **Query-able**: SQL queries with DuckDB (< 3s for 1GB)
✅ **Secure**: Automatic secret redaction
✅ **Constitutional**: Local-first, append-only, auditable
✅ **Additive**: Doesn't modify frozen control plane code

Happy logging! 🪵

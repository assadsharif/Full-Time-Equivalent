# API Contract: QueryService

**Module**: `src.logging.query_service`
**Purpose**: Query, filter, and analyze log files using DuckDB SQL interface
**Status**: Planning

---

## Overview

`QueryService` provides high-performance log querying capabilities using DuckDB's SQL engine. Supports filtering by time, level, module, trace ID, and full-text search without importing log files into a database.

---

## Class: QueryService

### Constructor

```python
def __init__(
    self,
    log_dir: Path,
    *,
    include_archives: bool = True
) -> None:
    """
    Initialize query service.

    Args:
        log_dir: Directory containing log files
        include_archives: Whether to include compressed archives in queries

    Raises:
        ValueError: If log_dir doesn't exist
        ImportError: If DuckDB not installed

    Side Effects:
        - Creates in-memory DuckDB connection
        - Registers virtual table for log files

    Performance:
        - No data import (reads files on demand)
        - Memory usage: ~10MB base + result set
    """
```

---

## Query Methods

### query()

```python
def query(
    self,
    query_params: LogQuery,
    *,
    format: str = "json"
) -> Union[List[LogEntry], str]:
    """
    Query logs with structured filters.

    Args:
        query_params: LogQuery object with filters (time, level, module, etc.)
        format: Output format ("json", "csv", "table", "dict")

    Returns:
        List of LogEntry objects (format="dict") or formatted string

    Raises:
        ValueError: If query parameters invalid
        QueryError: If SQL query fails

    Performance:
        - Typical: 100-500ms for 1GB logs
        - Complex queries: < 3s (well under 10s requirement)
        - Memory: Streams results, doesn't load full dataset

    Example:
        >>> params = LogQuery(
        ...     start_time=datetime(2026, 1, 28, 0, 0, 0),
        ...     end_time=datetime(2026, 1, 28, 23, 59, 59),
        ...     levels=[LogLevel.ERROR, LogLevel.CRITICAL],
        ...     limit=100
        ... )
        >>> results = query_service.query(params)
        >>> print(f"Found {len(results)} errors")

    Constitutional Compliance:
        - Section 2: Queries read from disk (source of truth)
    """
```

### query_sql()

```python
def query_sql(
    self,
    sql: str,
    *,
    params: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Execute raw SQL query against log files.

    Args:
        sql: SQL query string (DuckDB dialect)
        params: Optional query parameters for prepared statement

    Returns:
        List of result rows as dictionaries

    Raises:
        QueryError: If SQL syntax error or execution fails

    Security:
        - Uses prepared statements to prevent SQL injection
        - Read-only access (no INSERT, UPDATE, DELETE)

    Example:
        >>> sql = '''
        ...     SELECT level, COUNT(*) as count
        ...     FROM logs
        ...     WHERE timestamp >= ?
        ...     GROUP BY level
        ...     ORDER BY count DESC
        ... '''
        >>> results = query_service.query_sql(sql, params={"1": "2026-01-28T00:00:00Z"})

    Advanced Use Cases:
        - Custom aggregations
        - Complex JOINs (logs + metrics)
        - Window functions for trending
    """
```

---

## Filtering Methods

### filter_by_trace()

```python
def filter_by_trace(
    self,
    trace_id: str,
    *,
    order_by: str = "timestamp"
) -> List[LogEntry]:
    """
    Get all logs for a specific trace ID.

    Args:
        trace_id: Trace ID to filter by
        order_by: Sort field (default: "timestamp")

    Returns:
        List of LogEntry objects in chronological order

    Performance:
        - Fast: Indexed trace_id lookups
        - Typical: < 100ms for traces with 100s of entries

    Example:
        >>> logs = query_service.filter_by_trace("01HQ8Z9X0ABCDEFGHIJKLMNOPQ")
        >>> for log in logs:
        ...     print(f"{log.timestamp} [{log.level}] {log.message}")

    Use Case:
        - Debugging: Trace single operation through system
        - Auditing: Reconstruct complete action history
    """
```

### filter_by_time_range()

```python
def filter_by_time_range(
    self,
    start_time: datetime,
    end_time: datetime,
    *,
    level: Optional[LogLevel] = None,
    module: Optional[str] = None
) -> List[LogEntry]:
    """
    Get logs in time range with optional filters.

    Args:
        start_time: Start of time range (inclusive)
        end_time: End of time range (inclusive)
        level: Optional minimum log level filter
        module: Optional module filter

    Returns:
        List of LogEntry objects

    Example:
        >>> start = datetime.now() - timedelta(hours=1)
        >>> end = datetime.now()
        >>> errors = query_service.filter_by_time_range(
        ...     start, end,
        ...     level=LogLevel.ERROR,
        ...     module="src.control_plane"
        ... )
    """
```

### search_text()

```python
def search_text(
    self,
    search_query: str,
    *,
    case_sensitive: bool = False,
    regex: bool = False,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> List[LogEntry]:
    """
    Full-text search in log messages.

    Args:
        search_query: Text to search for
        case_sensitive: Whether search is case-sensitive (default: False)
        regex: Whether search_query is regex pattern (default: False)
        start_time: Optional time range start
        end_time: Optional time range end

    Returns:
        List of LogEntry objects matching search

    Performance:
        - Plain text: Fast (100-500ms for 1GB)
        - Regex: Slower (1-3s for complex patterns)

    Example:
        >>> # Find all "disk full" errors
        >>> results = query_service.search_text("disk full", regex=False)
        >>>
        >>> # Find API key patterns (debugging)
        >>> results = query_service.search_text(r"api_key=\w+", regex=True)

    Constitutional Compliance:
        - Section 8: Full audit trail searchable
    """
```

---

## Aggregation Methods

### count_by_level()

```python
def count_by_level(
    self,
    start_time: datetime,
    end_time: datetime,
    *,
    module: Optional[str] = None
) -> Dict[LogLevel, int]:
    """
    Count logs by level in time range.

    Args:
        start_time: Start of time range
        end_time: End of time range
        module: Optional module filter

    Returns:
        Dictionary mapping LogLevel to count

    Example:
        >>> counts = query_service.count_by_level(start, end)
        >>> print(counts)
        {
            LogLevel.DEBUG: 5234,
            LogLevel.INFO: 12890,
            LogLevel.WARNING: 42,
            LogLevel.ERROR: 7,
            LogLevel.CRITICAL: 0
        }

    Use Case:
        - System health dashboard
        - Alert on high error rates
    """
```

### count_by_module()

```python
def count_by_module(
    self,
    start_time: datetime,
    end_time: datetime,
    *,
    level: Optional[LogLevel] = None
) -> Dict[str, int]:
    """
    Count logs by module in time range.

    Args:
        start_time: Start of time range
        end_time: End of time range
        level: Optional level filter

    Returns:
        Dictionary mapping module name to count

    Example:
        >>> counts = query_service.count_by_module(start, end, level=LogLevel.ERROR)
        >>> top_modules = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
        >>> for module, count in top_modules:
        ...     print(f"{module}: {count} errors")

    Use Case:
        - Identify problematic modules
        - Targeted debugging
    """
```

### aggregate_metrics()

```python
def aggregate_metrics(
    self,
    metric_name: str,
    start_time: datetime,
    end_time: datetime,
    *,
    aggregation: str = "avg",
    tags: Optional[Dict[str, str]] = None,
    bucket_size: Optional[timedelta] = None
) -> Union[float, List[Tuple[datetime, float]]]:
    """
    Aggregate metric values over time.

    Args:
        metric_name: Metric to aggregate
        start_time: Start of time range
        end_time: End of time range
        aggregation: Aggregation function (avg, sum, min, max, count, p50, p95, p99)
        tags: Optional tag filters
        bucket_size: Optional time bucket for time series (None = single value)

    Returns:
        Single aggregated value OR list of (timestamp, value) tuples if bucketed

    Example:
        >>> # Average state transition duration
        >>> avg_duration = query_service.aggregate_metrics(
        ...     "state_transition.duration",
        ...     start, end,
        ...     aggregation="avg"
        ... )
        >>> print(f"Average duration: {avg_duration}ms")
        >>>
        >>> # Hourly p95 latency trend
        >>> timeseries = query_service.aggregate_metrics(
        ...     "state_transition.duration",
        ...     start, end,
        ...     aggregation="p95",
        ...     bucket_size=timedelta(hours=1)
        ... )
        >>> for timestamp, p95 in timeseries:
        ...     print(f"{timestamp}: {p95}ms")

    Use Case:
        - Performance dashboards
        - SLO monitoring
        - Capacity planning
    """
```

---

## Analysis Methods

### analyze_errors()

```python
def analyze_errors(
    self,
    start_time: datetime,
    end_time: datetime
) -> Dict[str, Any]:
    """
    Analyze error patterns in time range.

    Args:
        start_time: Start of time range
        end_time: End of time range

    Returns:
        Dictionary with error analysis:
        {
            "total_errors": int,
            "error_rate": float,  # errors per minute
            "by_type": Dict[str, int],  # exception type -> count
            "by_module": Dict[str, int],  # module -> count
            "top_errors": List[Tuple[str, int]],  # (message, count) sorted
            "new_errors": List[str]  # errors not seen in previous period
        }

    Example:
        >>> analysis = query_service.analyze_errors(start, end)
        >>> print(f"Total errors: {analysis['total_errors']}")
        >>> print(f"Error rate: {analysis['error_rate']:.2f}/min")
        >>> print("Top errors:")
        >>> for message, count in analysis['top_errors'][:5]:
        ...     print(f"  {count}x: {message}")

    Use Case:
        - Error triage
        - Incident response
        - Regression detection
    """
```

### trace_operation()

```python
def trace_operation(
    self,
    trace_id: str,
    *,
    include_metrics: bool = True
) -> OperationTrace:
    """
    Reconstruct complete operation trace.

    Args:
        trace_id: Trace ID to reconstruct
        include_metrics: Whether to include metric entries

    Returns:
        OperationTrace object with:
        - logs: List[LogEntry] in chronological order
        - metrics: Optional[List[MetricEntry]]
        - duration_ms: Total operation duration
        - success: Whether operation succeeded (no errors)
        - timeline: List of key events

    Example:
        >>> trace = query_service.trace_operation("01HQ8Z9X0ABCDEFGHIJKLMNOPQ")
        >>> print(f"Operation: {trace.duration_ms}ms, Success: {trace.success}")
        >>> for event in trace.timeline:
        ...     print(f"{event.timestamp} - {event.description}")

    Use Case:
        - Debugging failed operations
        - Performance analysis
        - Compliance audits
    """
```

---

## Export Methods

### export_to_json()

```python
def export_to_json(
    self,
    query_params: LogQuery,
    output_file: Path,
    *,
    pretty: bool = False
) -> int:
    """
    Export query results to JSON file.

    Args:
        query_params: LogQuery filters
        output_file: Path to output file
        pretty: Whether to pretty-print JSON (default: False)

    Returns:
        Number of entries exported

    Side Effects:
        - Writes JSON to output_file (overwrites if exists)

    Example:
        >>> count = query_service.export_to_json(
        ...     LogQuery(levels=[LogLevel.ERROR]),
        ...     Path("errors.json"),
        ...     pretty=True
        ... )
        >>> print(f"Exported {count} errors to errors.json")
    """
```

### export_to_csv()

```python
def export_to_csv(
    self,
    query_params: LogQuery,
    output_file: Path,
    *,
    columns: Optional[List[str]] = None
) -> int:
    """
    Export query results to CSV file.

    Args:
        query_params: LogQuery filters
        output_file: Path to output file
        columns: Optional list of columns to export (default: all)

    Returns:
        Number of entries exported

    Example:
        >>> count = query_service.export_to_csv(
        ...     LogQuery(start_time=start, end_time=end),
        ...     Path("logs.csv"),
        ...     columns=["timestamp", "level", "module", "message"]
        ... )
    """
```

---

## Archive Management

### list_archives()

```python
def list_archives(self) -> List[LogArchive]:
    """
    List all archived log files.

    Returns:
        List of LogArchive objects sorted by archive_date (newest first)

    Example:
        >>> archives = query_service.list_archives()
        >>> for archive in archives:
        ...     ratio = archive.compression_ratio
        ...     print(f"{archive.original_file}: {ratio:.1f}x compression")
    """
```

### query_archive()

```python
def query_archive(
    self,
    archive_id: str,
    query_params: LogQuery
) -> List[LogEntry]:
    """
    Query a specific archived log file.

    Args:
        archive_id: Archive ID from list_archives()
        query_params: LogQuery filters

    Returns:
        List of LogEntry objects from archive

    Performance:
        - Decompression: < 500ms for typical archive
        - Query: Same as uncompressed logs

    Example:
        >>> # Find errors from 2 weeks ago
        >>> archives = query_service.list_archives()
        >>> old_archive = archives[-14]  # 14 days ago
        >>> errors = query_service.query_archive(
        ...     old_archive.archive_id,
        ...     LogQuery(levels=[LogLevel.ERROR])
        ... )
    """
```

---

## Performance Methods

### get_query_stats()

```python
def get_query_stats(self) -> Dict[str, Any]:
    """
    Get query performance statistics.

    Returns:
        Dictionary with stats:
        {
            "total_queries": int,
            "avg_query_time_ms": float,
            "p95_query_time_ms": float,
            "cache_hit_rate": float,
            "total_bytes_scanned": int
        }

    Example:
        >>> stats = query_service.get_query_stats()
        >>> print(f"Avg query time: {stats['avg_query_time_ms']}ms")
        >>> print(f"Cache hit rate: {stats['cache_hit_rate']:.1%}")
    """
```

### optimize_query()

```python
def optimize_query(self, sql: str) -> str:
    """
    Optimize SQL query for better performance.

    Args:
        sql: Original SQL query

    Returns:
        Optimized SQL query

    Example:
        >>> original = "SELECT * FROM logs WHERE message LIKE '%error%'"
        >>> optimized = query_service.optimize_query(original)
        >>> print(optimized)
        # "SELECT * FROM logs WHERE level >= 40"  # More efficient
    """
```

---

## Usage Examples

### Basic Querying

```python
from src.logging import QueryService, LogQuery, LogLevel
from datetime import datetime, timedelta

# Initialize
query_service = QueryService(log_dir=Path("./Logs"))

# Query recent errors
params = LogQuery(
    start_time=datetime.now() - timedelta(hours=1),
    levels=[LogLevel.ERROR, LogLevel.CRITICAL],
    limit=100
)
errors = query_service.query(params)

for error in errors:
    print(f"{error.timestamp} [{error.module}] {error.message}")
```

### Trace Analysis

```python
# Find all operations that failed
failed_traces = query_service.query_sql("""
    SELECT DISTINCT trace_id
    FROM logs
    WHERE level >= 40  -- ERROR or CRITICAL
    AND timestamp >= ?
""", params={"1": "2026-01-28T00:00:00Z"})

# Analyze each failed operation
for trace_id in [row["trace_id"] for row in failed_traces]:
    trace = query_service.trace_operation(trace_id)
    print(f"Failed operation: {trace.duration_ms}ms")
    for log in trace.logs:
        if log.level >= LogLevel.ERROR:
            print(f"  Error: {log.message}")
```

### Performance Dashboard

```python
# Get hourly metrics for last 24 hours
start = datetime.now() - timedelta(hours=24)
end = datetime.now()

# Average state transition duration
avg_duration = query_service.aggregate_metrics(
    "state_transition.duration",
    start, end,
    aggregation="avg"
)

# P95 latency trend (hourly buckets)
p95_trend = query_service.aggregate_metrics(
    "state_transition.duration",
    start, end,
    aggregation="p95",
    bucket_size=timedelta(hours=1)
)

# Error rate
error_counts = query_service.count_by_level(start, end)
total_logs = sum(error_counts.values())
error_rate = (error_counts.get(LogLevel.ERROR, 0) / total_logs) * 100

print(f"Avg duration: {avg_duration:.2f}ms")
print(f"Error rate: {error_rate:.2f}%")
print("P95 latency trend:")
for timestamp, p95 in p95_trend:
    print(f"  {timestamp}: {p95:.2f}ms")
```

---

## Constitutional Compliance Summary

| Section | Requirement | Compliance |
|---------|-------------|------------|
| Section 2 | File system is source of truth | ✅ Queries read from disk files |
| Section 8 | Complete audit trail | ✅ Full history queryable |
| Section 13 | State verifiable via disk | ✅ No hidden query state |

---

## Performance Guarantees

| Operation | Target | Notes |
|-----------|--------|-------|
| Simple filter query (1GB) | < 500ms | Single file, time range + level |
| Complex aggregation (1GB) | < 3s | GROUP BY + multiple filters |
| Trace reconstruction | < 100ms | Single trace ID lookup |
| Full-text search (1GB) | < 2s | Plain text search |
| Regex search (1GB) | < 5s | Complex patterns |
| Archive decompression | < 500ms | gzip decompression |

---

## Next Steps

1. Implement `QueryService` class in `src/logging/query_service.py`
2. Implement DuckDB integration in `src/logging/duckdb_adapter.py`
3. Create unit tests in `tests/unit/logging/test_query_service.py`
4. Create performance benchmarks in `tests/performance/test_query_performance.py`
5. Implement CLI wrapper in `src/cli/logs.py`

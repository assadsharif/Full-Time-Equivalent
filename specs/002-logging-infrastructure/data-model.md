# Data Model: Logging Infrastructure

**Feature**: 002-logging-infrastructure
**Date**: 2026-01-28
**Status**: Planning

---

## Overview

This document defines the data structures, entities, and relationships for the Logging Infrastructure feature. All models are additive and do not modify the frozen control plane code.

---

## Core Entities

### 1. LogEntry

**Purpose**: Represents a single structured log entry in the system

**Fields**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `trace_id` | str (ULID) | Yes | Unique trace ID for correlation | `01HQ8Z9X0ABCDEFGHIJKLMNOPQ` |
| `timestamp` | datetime (ISO8601) | Yes | When the log was created | `2026-01-28T15:30:45.123456Z` |
| `level` | LogLevel enum | Yes | Log severity level | `INFO` |
| `module` | str | Yes | Python module name | `src.control_plane.state_machine` |
| `function` | str | No | Function name where log originated | `transition` |
| `line_number` | int | No | Source code line number | `142` |
| `message` | str | Yes | Human-readable log message | `Task transitioned successfully` |
| `context` | dict | No | Structured context data | `{"task_id": "task-001", "from_state": "Inbox"}` |
| `exception` | ExceptionInfo | No | Exception details if error | See ExceptionInfo below |
| `duration_ms` | float | No | Operation duration in milliseconds | `145.32` |
| `tags` | list[str] | No | Tags for categorization | `["performance", "critical_path"]` |

**Validation Rules**:
- `trace_id` must be valid ULID format (26 characters, Base32)
- `timestamp` must be UTC timezone
- `level` must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `module` must match Python module naming conventions
- `message` must not contain secrets (auto-redacted)
- `context` dict keys must be snake_case strings
- `duration_ms` must be non-negative if present

**State Transitions**: None (immutable once created)

**Example JSON**:
```json
{
  "trace_id": "01HQ8Z9X0ABCDEFGHIJKLMNOPQ",
  "timestamp": "2026-01-28T15:30:45.123456Z",
  "level": "INFO",
  "module": "src.control_plane.state_machine",
  "function": "transition",
  "line_number": 142,
  "message": "Task transitioned successfully",
  "context": {
    "task_id": "task-001",
    "from_state": "Inbox",
    "to_state": "Needs_Action",
    "actor": "system"
  },
  "duration_ms": 145.32,
  "tags": ["state_transition"]
}
```

---

### 2. ExceptionInfo

**Purpose**: Captures exception details for error logging

**Fields**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `type` | str | Yes | Exception class name | `FileOperationError` |
| `message` | str | Yes | Exception message | `Failed to move file: disk full` |
| `stack_trace` | list[StackFrame] | Yes | Full stack trace | See StackFrame below |
| `cause` | ExceptionInfo | No | Chained exception (__cause__) | Recursive structure |

**Example JSON**:
```json
{
  "type": "FileOperationError",
  "message": "Failed to move file: disk full",
  "stack_trace": [
    {
      "file": "src/control_plane/state_machine.py",
      "line": 170,
      "function": "transition",
      "code": "atomic_move(source_path, destination_path)"
    }
  ],
  "cause": {
    "type": "OSError",
    "message": "[Errno 28] No space left on device",
    "stack_trace": []
  }
}
```

---

### 3. StackFrame

**Purpose**: Represents a single frame in an exception stack trace

**Fields**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `file` | str | Yes | Source file path (relative) | `src/control_plane/state_machine.py` |
| `line` | int | Yes | Line number | `170` |
| `function` | str | Yes | Function name | `transition` |
| `code` | str | No | Source code line | `atomic_move(source_path, destination_path)` |

---

### 4. LogLevel (Enum)

**Purpose**: Standard log severity levels

**Values**:
- `DEBUG = 10`: Detailed diagnostic information
- `INFO = 20`: Informational messages (default)
- `WARNING = 30`: Warning messages (non-critical issues)
- `ERROR = 40`: Error messages (operation failed)
- `CRITICAL = 50`: Critical errors (system stability at risk)

**Ordering**: Numerically ordered by severity (DEBUG < INFO < WARNING < ERROR < CRITICAL)

---

### 5. LoggerConfig

**Purpose**: Configuration for logging system behavior

**Fields**:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `log_dir` | Path | Yes | `./Logs` | Directory for log files |
| `level` | LogLevel | Yes | `INFO` | Global minimum log level |
| `module_levels` | dict[str, LogLevel] | No | `{}` | Per-module log levels |
| `format` | str | Yes | `json` | Output format (json, console, hybrid) |
| `async_enabled` | bool | Yes | `True` | Use async logging queue |
| `buffer_size` | int | Yes | `1000` | Max entries in async queue |
| `flush_interval_s` | float | Yes | `1.0` | Auto-flush interval in seconds |
| `retention_days` | int | Yes | `30` | Log retention period |
| `compression_enabled` | bool | Yes | `True` | Compress logs older than 7 days |
| `max_file_size_mb` | int | Yes | `100` | Max size before rotation |
| `secret_patterns` | list[str] | No | `[]` | Regex patterns for secret detection |
| `redaction_text` | str | Yes | `***REDACTED***` | Replacement for secrets |

**Example YAML** (config/logging.yaml):
```yaml
log_dir: ./Logs
level: INFO
module_levels:
  src.control_plane: DEBUG
  src.mcp_servers: WARNING
format: json
async_enabled: true
buffer_size: 1000
flush_interval_s: 1.0
retention_days: 30
compression_enabled: true
max_file_size_mb: 100
secret_patterns:
  - 'api_key=\w+'
  - 'Bearer \w+'
redaction_text: "***REDACTED***"
```

---

### 6. MetricEntry

**Purpose**: Structured performance and operational metrics

**Fields**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `trace_id` | str (ULID) | Yes | Correlation ID | `01HQ8Z9X0ABCDEFGHIJKLMNOPQ` |
| `timestamp` | datetime | Yes | When metric was recorded | `2026-01-28T15:30:45Z` |
| `metric_name` | str | Yes | Metric identifier | `file_operation.duration` |
| `metric_type` | MetricType enum | Yes | Type of metric | `DURATION` |
| `value` | float | Yes | Numeric value | `145.32` |
| `unit` | str | Yes | Unit of measurement | `milliseconds` |
| `tags` | dict[str, str] | No | Metric dimensions | `{"operation": "rename", "result": "success"}` |

**MetricType Enum**:
- `COUNTER`: Incrementing count (e.g., requests_total)
- `GAUGE`: Point-in-time value (e.g., queue_size)
- `DURATION`: Time measurement (e.g., operation_duration_ms)
- `HISTOGRAM`: Distribution of values (e.g., response_time_buckets)

**Example JSON**:
```json
{
  "trace_id": "01HQ8Z9X0ABCDEFGHIJKLMNOPQ",
  "timestamp": "2026-01-28T15:30:45Z",
  "metric_name": "state_transition.duration",
  "metric_type": "DURATION",
  "value": 145.32,
  "unit": "milliseconds",
  "tags": {
    "from_state": "Inbox",
    "to_state": "Needs_Action",
    "result": "success"
  }
}
```

---

### 7. LogQuery

**Purpose**: Query parameters for log retrieval and filtering

**Fields**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `start_time` | datetime | No | Filter logs after this time | `2026-01-28T00:00:00Z` |
| `end_time` | datetime | No | Filter logs before this time | `2026-01-28T23:59:59Z` |
| `levels` | list[LogLevel] | No | Filter by log levels | `[ERROR, CRITICAL]` |
| `modules` | list[str] | No | Filter by modules | `["src.control_plane"]` |
| `trace_id` | str | No | Filter by trace ID | `01HQ8Z9X0ABCDEFGHIJKLMNOPQ` |
| `search_text` | str | No | Full-text search in message | `"disk full"` |
| `tags` | list[str] | No | Filter by tags (AND logic) | `["performance"]` |
| `limit` | int | No | Max results to return | `1000` |
| `offset` | int | No | Skip first N results | `0` |
| `order_by` | str | No | Sort field | `timestamp` |
| `order_dir` | str | No | Sort direction | `desc` |

**Example JSON**:
```json
{
  "start_time": "2026-01-28T00:00:00Z",
  "end_time": "2026-01-28T23:59:59Z",
  "levels": ["ERROR", "CRITICAL"],
  "modules": ["src.control_plane"],
  "limit": 100,
  "order_by": "timestamp",
  "order_dir": "desc"
}
```

---

### 8. LogArchive

**Purpose**: Metadata for archived log files

**Fields**:

| Field | Type | Required | Description | Example |
|-------|------|----------|-------------|---------|
| `archive_id` | str (ULID) | Yes | Unique archive identifier | `01HQ8Z9X0ABCDEFGHIJKLMNOPQ` |
| `original_file` | str | Yes | Original log file name | `2026-01-27.log` |
| `archive_file` | str | Yes | Compressed archive name | `2026-01-27.log.gz` |
| `archive_date` | datetime | Yes | When archived | `2026-02-03T00:00:00Z` |
| `original_size_bytes` | int | Yes | Original file size | `52428800` |
| `compressed_size_bytes` | int | Yes | Compressed size | `5242880` |
| `compression_ratio` | float | Yes | Compression ratio | `10.0` |
| `entry_count` | int | Yes | Number of log entries | `12500` |
| `checksum` | str | Yes | SHA256 checksum | `a3b2c1...` |

---

## Relationships

### LogEntry Relationships

```
LogEntry (many) → LogLevel (one)
  - Each log entry has exactly one severity level

LogEntry (many) → ExceptionInfo (optional one)
  - Error logs may contain exception details

LogEntry (many) → MetricEntry (many)
  - Logs and metrics share trace_id for correlation

LogEntry (many) → LogArchive (many)
  - Log entries belong to daily files, which get archived
```

### Configuration Relationships

```
LoggerConfig (one) → LogLevel (one)
  - Global default log level

LoggerConfig (one) → module_levels (many)
  - Per-module log level overrides
```

---

## File Storage Schema

### Daily Log Files

**Path Pattern**: `<log_dir>/YYYY-MM-DD.log`
**Format**: Newline-delimited JSON (NDJSON)
**Encoding**: UTF-8
**Permissions**: 600 (owner read/write only)

**Example**: `Logs/2026-01-28.log`
```
{"trace_id":"01HQ8Z9X0A...","timestamp":"2026-01-28T15:30:45.123Z","level":"INFO",...}
{"trace_id":"01HQ8Z9X0B...","timestamp":"2026-01-28T15:30:46.234Z","level":"ERROR",...}
```

### Metric Log Files

**Path Pattern**: `<log_dir>/metrics/YYYY-MM-DD.metrics.log`
**Format**: NDJSON (same as application logs)
**Separation**: Metrics in separate directory for efficient querying

### Archived Log Files

**Path Pattern**: `<log_dir>/archive/YYYY-MM-DD.log.gz`
**Compression**: gzip (standard compression)
**Trigger**: Logs older than 7 days automatically compressed

### Archive Index

**Path Pattern**: `<log_dir>/archive/index.json`
**Format**: JSON array of LogArchive objects
**Purpose**: Fast lookup of archived log metadata

---

## Validation Rules (Cross-Entity)

### Rule 1: Trace ID Propagation
- All LogEntry and MetricEntry objects in the same operation MUST share the same `trace_id`
- Trace ID MUST be generated once at operation start and passed through context

### Rule 2: Timestamp Ordering
- Within a single trace ID, `timestamp` values MUST be monotonically increasing
- Allows reconstruction of operation timeline

### Rule 3: Secret Redaction
- Before writing LogEntry to disk, `message` and `context` MUST be scanned
- Any matches to `secret_patterns` MUST be replaced with `redaction_text`
- Redaction is irreversible (secrets never written to disk)

### Rule 4: Archive Integrity
- Archived files MUST have valid `checksum` in index
- Checksum MUST be verified before reading archived data
- Corrupted archives flagged with ERROR log

### Rule 5: Retention Policy
- LogArchive files older than `retention_days` MAY be deleted
- Deletion MUST be logged with INFO level: `"Deleted archive: {filename}"`
- Logs newer than `retention_days` MUST NEVER be deleted

---

## Performance Considerations

### Indexing Strategy
- **DuckDB Virtual Tables**: Query log files directly without import
- **NDJSON Format**: Line-by-line parsing, no full-file load
- **Columnar Reads**: DuckDB reads only needed columns

### Memory Management
- **Async Queue**: Bounded at `buffer_size` entries
- **Backpressure**: When queue full, drop DEBUG logs first, then INFO, etc.
- **Flush Strategy**: Time-based (1s) OR size-based (1000 entries)

### Disk Space Management
- **Compression**: Reduces disk usage by ~90% for text logs
- **Retention**: Automatically delete old archives
- **Rotation**: Split large files at 100MB boundary

---

## Constitutional Compliance

### Section 2 (Source of Truth)
- ✅ All logs written to disk (no hidden state)
- ✅ File system is authoritative for log history

### Section 3 (Local-First & Privacy)
- ✅ All logs remain local (no cloud sync)
- ✅ Secrets automatically redacted before write
- ✅ File permissions enforce owner-only access (600)

### Section 8 (Auditability & Logging)
- ✅ All logs include required fields (timestamp, action, result)
- ✅ Append-only log files (never modify existing entries)
- ✅ Structured format for machine parsing

### Section 9 (Error Handling & Safety)
- ✅ Logging failures never crash application (fallback to stderr)
- ✅ Exception details captured with full stack traces
- ✅ Explicit error levels (ERROR, CRITICAL)

---

## Next Steps

1. **API Contracts**: Define function signatures for LoggerService, QueryService
2. **Implementation Plan**: Sequence modules (config → logger → query → CLI)
3. **Test Strategy**: Unit tests for each entity, integration tests for workflows
4. **Migration Path**: No breaking changes (additive only, control plane frozen)

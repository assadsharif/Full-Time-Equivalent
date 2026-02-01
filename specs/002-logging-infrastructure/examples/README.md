# Logging Infrastructure - Usage Examples

This directory contains practical examples demonstrating the logging infrastructure features.

---

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run examples:**
   ```bash
   # Basic logging
   python examples/01_basic_logging.py

   # Trace correlation
   python examples/02_trace_correlation.py

   # Context binding
   python examples/03_context_binding.py

   # Querying logs
   python examples/04_querying_logs.py

   # CLI usage
   bash examples/05_cli_usage.sh
   ```

---

## Examples

### 01 - Basic Logging

**File:** `01_basic_logging.py`

**Demonstrates:**
- Initializing the logging system
- Logging at different levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Structured context
- Tags
- Exception logging
- Graceful shutdown

**Run:**
```bash
python examples/01_basic_logging.py
```

**Output:** Creates log files in `./Logs/`

---

### 02 - Trace Correlation

**File:** `02_trace_correlation.py`

**Demonstrates:**
- Auto-generated trace IDs
- Custom trace IDs
- Trace propagation across function calls
- Concurrent operations with different traces
- Nested trace contexts

**Run:**
```bash
python examples/02_trace_correlation.py
```

**Key Concept:** All logs in a `bind_trace_id()` context share the same trace ID, enabling you to track a single operation through the system.

**Query by trace ID:**
```bash
python -m src.cli.logs query --trace-id <trace_id>
```

---

### 03 - Context Binding

**File:** `03_context_binding.py`

**Demonstrates:**
- Binding context to operation scope
- Context propagation through function calls
- Nested context
- Duration measurement with context
- Combined trace ID and context

**Run:**
```bash
python examples/03_context_binding.py
```

**Key Concept:** Context bound with `bind_context()` is automatically included in all logs within that scope.

---

### 04 - Querying Logs

**File:** `04_querying_logs.py`

**Demonstrates:**
- Querying logs with filters
- Filtering by log level
- Filtering by trace ID
- Filtering by time range
- Full-text search
- Raw SQL queries
- Aggregations
- Different output formats (dict, JSON, CSV, table)

**Run:**
```bash
python examples/04_querying_logs.py
```

**Prerequisites:** Run examples 01-03 first to generate log data.

---

### 05 - CLI Usage

**File:** `05_cli_usage.sh`

**Demonstrates:**
- `fte logs tail` - View recent logs
- `fte logs query` - Query with filters
- `fte logs search` - Full-text search
- Output formats
- Time range queries (ISO and relative)
- Combining filters

**Run:**
```bash
bash examples/05_cli_usage.sh
```

**Prerequisites:** Run examples 01-03 first to generate log data.

---

## Common Patterns

### Pattern 1: Operation with Trace and Context

```python
with logger.bind_trace_id() as trace_id:
    with logger.bind_context(operation="user_login", user="alice"):
        logger.info("Login attempt started")
        result = authenticate_user()
        logger.info("Login successful", context={"result": result})
```

### Pattern 2: Error Handling with Context

```python
try:
    result = risky_operation()
except Exception as e:
    logger.error(
        "Operation failed",
        exception=e,
        context={"input": data, "attempt": retry_count}
    )
```

### Pattern 3: Performance Measurement

```python
with logger.measure_duration("database_query", table="users"):
    result = db.query("SELECT * FROM users WHERE active = true")
```

### Pattern 4: Find All Logs for an Operation

```python
# After running the operation
from src.logging.query_service import QueryService

service = QueryService(log_dir="./Logs")
logs = service.filter_by_trace(trace_id)
for log in logs:
    print(f"{log.timestamp}: {log.message}")
```

---

## Performance Tips

1. **Use async logging:**
   ```python
   logger = init_logging(async_enabled=True)
   await logger.start_async_writer()
   ```

2. **Set appropriate log levels:**
   ```python
   # Production
   logger = init_logging(level="INFO")

   # Development
   logger = init_logging(level="DEBUG")
   ```

3. **Use context binding to avoid repetition:**
   ```python
   # Instead of:
   logger.info("Step 1", context={"user": "alice"})
   logger.info("Step 2", context={"user": "alice"})

   # Use:
   with logger.bind_context(user="alice"):
       logger.info("Step 1")
       logger.info("Step 2")
   ```

4. **Query efficiently:**
   ```python
   # Use filters to reduce result set
   params = LogQuery(
       start_time=recent,
       levels=[LogLevel.ERROR],
       limit=100
   )
   ```

---

## Troubleshooting

### Logs not appearing

1. Check if async writer is started:
   ```python
   await logger.start_async_writer()
   ```

2. Flush logs manually:
   ```python
   await logger.flush()
   ```

3. Check log directory exists:
   ```python
   import os
   print(os.path.exists("./Logs"))
   ```

### Query returns no results

1. Check if log files exist:
   ```bash
   ls -la Logs/
   ```

2. Check time range:
   ```python
   # Use wider time range
   start = datetime.now() - timedelta(days=7)
   ```

3. Check log level filter:
   ```python
   # Query all levels
   params = LogQuery(levels=None, limit=100)
   ```

### Performance issues

1. Use query limits:
   ```python
   params = LogQuery(limit=100)  # Don't query millions of logs
   ```

2. Filter by time range:
   ```python
   params = LogQuery(
       start_time=recent,
       end_time=now,
       limit=1000
   )
   ```

3. Use raw SQL for complex aggregations:
   ```python
   sql = "SELECT level, COUNT(*) FROM logs GROUP BY level"
   results = service.query_sql(sql)
   ```

---

## Next Steps

- Read [API Documentation](../API.md) for complete reference
- See [Implementation Plan](../plan.md) for architecture details
- Check [Task Breakdown](../tasks.md) for implementation status

---

## Constitutional Compliance

All examples follow constitutional principles:

- **Section 2**: Logs written to disk (source of truth)
- **Section 3**: Secrets automatically redacted
- **Section 8**: Structured, append-only logging
- **Section 9**: Errors captured with full context

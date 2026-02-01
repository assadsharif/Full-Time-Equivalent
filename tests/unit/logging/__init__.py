"""
Unit tests for logging infrastructure (P2).

Tests in this directory cover:
- LoggerService (structured logging, context binding, trace IDs)
- QueryService (DuckDB queries, filtering, aggregations)
- AsyncWriter (background task, buffering, flushing)
- SecretRedactor (regex-based redaction)
- Models (LogEntry, LoggerConfig, MetricEntry)
- Trace (ULID generation, context management)
"""

"""
Integration tests for logging infrastructure (P2).

Tests in this directory cover:
- End-to-end logging lifecycle (write → query)
- Trace correlation across multiple log entries
- Exception logging with stack traces
- Secret redaction in production scenarios
- Log rotation and archival
- Query performance under load
- Concurrent logging from multiple threads/tasks
"""

"""
Performance tests for logging infrastructure (P2).

Tests in this directory validate:
- AsyncWriter overhead (< 5μs target per log call)
- Query performance (< 10s for 1GB log file)
- Secret redaction performance (< 1μs overhead)
- Concurrent logging throughput (> 100k logs/sec)
- Memory usage under sustained load
- DuckDB query optimization

Note: Performance tests are marked with @pytest.mark.performance
and are excluded from default test runs.
"""

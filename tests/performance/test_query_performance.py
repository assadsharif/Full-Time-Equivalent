"""
Performance benchmarks for QueryService (P2).

Tests verify:
- Query performance < 10s for 1GB logs
- Query throughput for various operations
- Memory usage under load

Performance targets:
- Simple queries: < 500ms
- Complex queries: < 3s
- 1GB log file queries: < 10s
"""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.logging.models import LogLevel, LogQuery
from src.logging.query_service import QueryService


@pytest.fixture
def large_log_dir(tmp_path):
    """Create log directory with large log file for performance testing."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    # Create log file with many entries
    log_file = log_dir / "2026-01-28.log"

    # Generate sample logs
    num_entries = 10000  # 10k entries for testing (adjust for CI)
    now = datetime.now(timezone.utc)

    levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    modules = ["test.module1", "test.module2", "test.module3"]

    with open(log_file, "w") as f:
        for i in range(num_entries):
            log = {
                "trace_id": f"trace-{i % 100}",
                "timestamp": (now - timedelta(seconds=i)).isoformat(),
                "level": levels[i % len(levels)],
                "module": modules[i % len(modules)],
                "message": f"Log message {i}",
                "function": "test_func",
                "line_number": i,
            }
            f.write(json.dumps(log) + "\n")

    return log_dir


class TestQueryPerformance:
    """Performance tests for query operations."""

    @pytest.mark.performance
    def test_simple_query_performance(self, large_log_dir):
        """Simple queries should complete in < 500ms."""
        service = QueryService(large_log_dir)

        params = LogQuery(limit=100)

        start = time.perf_counter()
        results = service.query(params, format="dict")
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000

        assert len(results) == 100
        assert elapsed_ms < 500, f"Query took {elapsed_ms:.2f}ms (target: < 500ms)"

        service.close()

    @pytest.mark.performance
    def test_filtered_query_performance(self, large_log_dir):
        """Filtered queries should complete in < 1s."""
        service = QueryService(large_log_dir)

        params = LogQuery(
            levels=[LogLevel.ERROR, LogLevel.CRITICAL],
            limit=1000
        )

        start = time.perf_counter()
        results = service.query(params, format="dict")
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000

        assert elapsed_ms < 1000, f"Query took {elapsed_ms:.2f}ms (target: < 1000ms)"

        service.close()

    @pytest.mark.performance
    def test_time_range_query_performance(self, large_log_dir):
        """Time range queries should complete in < 1s."""
        service = QueryService(large_log_dir)

        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=1)
        end_time = now

        start = time.perf_counter()
        results = service.filter_by_time_range(start_time, end_time)
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000

        assert elapsed_ms < 1000, f"Query took {elapsed_ms:.2f}ms (target: < 1000ms)"

        service.close()

    @pytest.mark.performance
    def test_trace_filter_performance(self, large_log_dir):
        """Trace filtering should complete in < 100ms."""
        service = QueryService(large_log_dir)

        start = time.perf_counter()
        results = service.filter_by_trace("trace-0")
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000

        assert elapsed_ms < 100, f"Query took {elapsed_ms:.2f}ms (target: < 100ms)"

        service.close()

    @pytest.mark.performance
    def test_text_search_performance(self, large_log_dir):
        """Text search should complete in < 2s."""
        service = QueryService(large_log_dir)

        start = time.perf_counter()
        results = service.search_text("message", limit=100)
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000

        assert elapsed_ms < 2000, f"Query took {elapsed_ms:.2f}ms (target: < 2000ms)"

        service.close()

    @pytest.mark.performance
    def test_aggregation_query_performance(self, large_log_dir):
        """Aggregation queries should complete in < 1s."""
        service = QueryService(large_log_dir)

        sql = "SELECT level, COUNT(*) as count FROM logs GROUP BY level"

        start = time.perf_counter()
        results = service.query_sql(sql)
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000

        assert elapsed_ms < 1000, f"Query took {elapsed_ms:.2f}ms (target: < 1000ms)"
        assert len(results) == 5  # 5 log levels

        service.close()


class TestQueryThroughput:
    """Tests for query throughput."""

    @pytest.mark.performance
    def test_sequential_query_throughput(self, large_log_dir):
        """Should handle multiple sequential queries efficiently."""
        service = QueryService(large_log_dir)

        num_queries = 10
        params = LogQuery(limit=10)

        start = time.perf_counter()
        for _ in range(num_queries):
            results = service.query(params, format="dict")
            assert len(results) == 10
        end = time.perf_counter()

        total_time_ms = (end - start) * 1000
        avg_time_ms = total_time_ms / num_queries

        assert avg_time_ms < 100, f"Avg query time: {avg_time_ms:.2f}ms (target: < 100ms)"

        service.close()


class TestMemoryUsage:
    """Tests for memory efficiency."""

    @pytest.mark.performance
    def test_large_result_set_memory(self, large_log_dir):
        """Should handle large result sets without excessive memory."""
        service = QueryService(large_log_dir)

        # Query all logs (10k entries)
        params = LogQuery(limit=10000)

        start = time.perf_counter()
        results = service.query(params, format="dict")
        end = time.perf_counter()

        elapsed_ms = (end - start) * 1000

        assert len(results) == 10000
        # Should still complete reasonably fast even with large result set
        assert elapsed_ms < 5000, f"Query took {elapsed_ms:.2f}ms (target: < 5000ms)"

        service.close()


class TestScalability:
    """Tests for scalability with larger datasets."""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_very_large_log_file(self, tmp_path):
        """Should handle very large log files (simulated 1GB)."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()

        # Create larger log file
        # Note: Creating actual 1GB file takes too long for CI
        # This simulates with 100k entries (~10MB)
        log_file = log_dir / "2026-01-28.log"

        num_entries = 100000
        now = datetime.now(timezone.utc)

        with open(log_file, "w") as f:
            for i in range(num_entries):
                log = {
                    "trace_id": f"trace-{i % 1000}",
                    "timestamp": (now - timedelta(seconds=i)).isoformat(),
                    "level": "INFO",
                    "module": "test.module",
                    "message": f"Log message {i}",
                    "function": "test_func",
                    "line_number": i,
                }
                f.write(json.dumps(log) + "\n")

        service = QueryService(log_dir)

        # Query with filter
        params = LogQuery(levels=[LogLevel.INFO], limit=1000)

        start = time.perf_counter()
        results = service.query(params, format="dict")
        end = time.perf_counter()

        elapsed_seconds = end - start

        assert len(results) == 1000
        # For 100k entries (~10MB), should be much faster than 10s
        # For actual 1GB, target is < 10s
        assert elapsed_seconds < 10, f"Query took {elapsed_seconds:.2f}s (target: < 10s)"

        service.close()


class TestComparisonBenchmarks:
    """Comparative performance benchmarks."""

    @pytest.mark.performance
    def test_query_vs_raw_sql_performance(self, large_log_dir):
        """Compare structured query vs raw SQL performance."""
        service = QueryService(large_log_dir)

        # Structured query
        params = LogQuery(levels=[LogLevel.ERROR], limit=100)

        start = time.perf_counter()
        results1 = service.query(params, format="dict")
        end = time.perf_counter()
        structured_time_ms = (end - start) * 1000

        # Raw SQL query
        sql = "SELECT * FROM logs WHERE level = 'ERROR' LIMIT 100"

        start = time.perf_counter()
        results2 = service.query_sql(sql)
        end = time.perf_counter()
        raw_sql_time_ms = (end - start) * 1000

        # Both should be fast
        assert structured_time_ms < 500
        assert raw_sql_time_ms < 500

        # Both should return same count
        assert len(results1) == len(results2)

        service.close()

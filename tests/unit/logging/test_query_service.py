"""
Unit tests for QueryService (P2).

Tests cover:
- Query with filters
- Raw SQL queries
- Trace ID filtering
- Time range filtering
- Text search
- Output formats
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.logging.models import LogEntry, LogLevel, LogQuery
from src.logging.query_service import QueryService


@pytest.fixture
def temp_log_dir_with_data(tmp_path):
    """Create temporary log directory with sample log files."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    # Create sample log file with NDJSON
    log_file = log_dir / "2026-01-28.log"

    now = datetime.now(timezone.utc)

    logs = [
        {
            "trace_id": "trace-001",
            "timestamp": (now - timedelta(hours=2)).isoformat(),
            "level": "INFO",
            "module": "test.module",
            "message": "Application started",
            "function": "main",
            "line_number": 10,
            "context": {},
            "exception": None,
            "duration_ms": None,
            "tags": [],
        },
        {
            "trace_id": "trace-001",
            "timestamp": (now - timedelta(hours=1, minutes=30)).isoformat(),
            "level": "DEBUG",
            "module": "test.module",
            "message": "Debug message",
            "function": "debug_func",
            "line_number": 20,
            "context": {"debug": True},
            "exception": None,
            "duration_ms": None,
            "tags": [],
        },
        {
            "trace_id": "trace-002",
            "timestamp": (now - timedelta(hours=1)).isoformat(),
            "level": "ERROR",
            "module": "test.error",
            "message": "Disk full error occurred",
            "function": "write_file",
            "line_number": 30,
            "context": {"disk": "/dev/sda1"},
            "exception": {"type": "IOError", "message": "No space left"},
            "duration_ms": 150.5,
            "tags": ["disk", "error"],
        },
        {
            "trace_id": "trace-002",
            "timestamp": (now - timedelta(minutes=30)).isoformat(),
            "level": "WARNING",
            "module": "test.warning",
            "message": "Warning message",
            "function": "warn_func",
            "line_number": 40,
            "context": {},
            "exception": None,
            "duration_ms": None,
            "tags": ["warning"],
        },
        {
            "trace_id": "trace-003",
            "timestamp": (now - timedelta(minutes=10)).isoformat(),
            "level": "CRITICAL",
            "module": "test.critical",
            "message": "Critical error",
            "function": "critical_func",
            "line_number": 50,
            "context": {"severity": "high"},
            "exception": {"type": "CriticalError", "message": "System failure"},
            "duration_ms": 500.0,
            "tags": ["critical", "system"],
        },
    ]

    with open(log_file, "w") as f:
        for log in logs:
            f.write(json.dumps(log) + "\n")

    return log_dir


class TestQueryServiceInitialization:
    """Tests for QueryService initialization."""

    def test_init_with_valid_dir(self, temp_log_dir_with_data):
        """Should initialize with valid log directory."""
        service = QueryService(temp_log_dir_with_data)

        assert service.log_dir == temp_log_dir_with_data
        assert service._adapter is not None

        service.close()

    def test_init_with_invalid_dir(self, tmp_path):
        """Should raise error if log directory doesn't exist."""
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(ValueError, match="does not exist"):
            QueryService(nonexistent)


class TestQueryWithFilters:
    """Tests for query() method with filters."""

    def test_query_all_logs(self, temp_log_dir_with_data):
        """Should query all logs without filters."""
        service = QueryService(temp_log_dir_with_data)

        params = LogQuery(limit=100)
        results = service.query(params, format="dict")

        assert len(results) == 5
        assert all(isinstance(entry, LogEntry) for entry in results)

        service.close()

    def test_query_filter_by_level(self, temp_log_dir_with_data):
        """Should filter by log level."""
        service = QueryService(temp_log_dir_with_data)

        params = LogQuery(levels=[LogLevel.ERROR, LogLevel.CRITICAL])
        results = service.query(params, format="dict")

        assert len(results) == 2
        assert all(entry.level in [LogLevel.ERROR, LogLevel.CRITICAL] for entry in results)

        service.close()

    def test_query_filter_by_module(self, temp_log_dir_with_data):
        """Should filter by module prefix."""
        service = QueryService(temp_log_dir_with_data)

        params = LogQuery(modules=["test.error"])
        results = service.query(params, format="dict")

        assert len(results) == 1
        assert results[0].module == "test.error"

        service.close()

    def test_query_with_limit(self, temp_log_dir_with_data):
        """Should respect limit parameter."""
        service = QueryService(temp_log_dir_with_data)

        params = LogQuery(limit=2)
        results = service.query(params, format="dict")

        assert len(results) == 2

        service.close()

    def test_query_with_offset(self, temp_log_dir_with_data):
        """Should respect offset parameter."""
        service = QueryService(temp_log_dir_with_data)

        # Get all
        all_results = service.query(LogQuery(limit=100), format="dict")

        # Get with offset
        params = LogQuery(limit=100, offset=2)
        offset_results = service.query(params, format="dict")

        assert len(offset_results) == 3  # 5 total - 2 offset
        assert offset_results[0].message == all_results[2].message

        service.close()


class TestFilterByTrace:
    """Tests for filter_by_trace() method."""

    def test_filter_by_trace_id(self, temp_log_dir_with_data):
        """Should filter by trace ID."""
        service = QueryService(temp_log_dir_with_data)

        results = service.filter_by_trace("trace-001")

        assert len(results) == 2
        assert all(entry.trace_id == "trace-001" for entry in results)

        service.close()

    def test_filter_by_trace_chronological_order(self, temp_log_dir_with_data):
        """Should return results in chronological order."""
        service = QueryService(temp_log_dir_with_data)

        results = service.filter_by_trace("trace-001")

        # Should be in ascending timestamp order
        assert results[0].timestamp < results[1].timestamp

        service.close()

    def test_filter_by_nonexistent_trace(self, temp_log_dir_with_data):
        """Should return empty list for nonexistent trace."""
        service = QueryService(temp_log_dir_with_data)

        results = service.filter_by_trace("nonexistent-trace")

        assert len(results) == 0

        service.close()


class TestFilterByTimeRange:
    """Tests for filter_by_time_range() method."""

    def test_filter_by_time_range(self, temp_log_dir_with_data):
        """Should filter by time range."""
        service = QueryService(temp_log_dir_with_data)

        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=2)
        end = now - timedelta(minutes=30)

        results = service.filter_by_time_range(start, end)

        # Should exclude logs outside range
        assert len(results) >= 1

        service.close()

    def test_filter_by_time_range_with_level(self, temp_log_dir_with_data):
        """Should filter by time range and level."""
        service = QueryService(temp_log_dir_with_data)

        now = datetime.now(timezone.utc)
        start = now - timedelta(hours=3)
        end = now

        results = service.filter_by_time_range(
            start, end,
            level=LogLevel.ERROR
        )

        # Should only include ERROR logs in time range
        assert all(entry.level >= LogLevel.ERROR for entry in results)

        service.close()


class TestSearchText:
    """Tests for search_text() method."""

    def test_search_text_case_insensitive(self, temp_log_dir_with_data):
        """Should perform case-insensitive text search."""
        service = QueryService(temp_log_dir_with_data)

        results = service.search_text("DISK FULL")

        assert len(results) == 1
        assert "Disk full" in results[0].message

        service.close()

    def test_search_text_case_sensitive(self, temp_log_dir_with_data):
        """Should perform case-sensitive text search if requested."""
        service = QueryService(temp_log_dir_with_data)

        results = service.search_text("Disk full", case_sensitive=True)

        assert len(results) == 1

        service.close()

    def test_search_text_no_matches(self, temp_log_dir_with_data):
        """Should return empty list if no matches."""
        service = QueryService(temp_log_dir_with_data)

        results = service.search_text("nonexistent text")

        assert len(results) == 0

        service.close()

    def test_search_text_with_limit(self, temp_log_dir_with_data):
        """Should respect limit in search."""
        service = QueryService(temp_log_dir_with_data)

        results = service.search_text("message", limit=2)

        assert len(results) <= 2

        service.close()


class TestRawSQLQuery:
    """Tests for query_sql() method."""

    def test_query_sql_basic(self, temp_log_dir_with_data):
        """Should execute raw SQL query."""
        service = QueryService(temp_log_dir_with_data)

        sql = "SELECT COUNT(*) as count FROM logs"
        results = service.query_sql(sql)

        assert len(results) == 1
        assert results[0]["count"] == 5

        service.close()

    def test_query_sql_aggregation(self, temp_log_dir_with_data):
        """Should support aggregation queries."""
        service = QueryService(temp_log_dir_with_data)

        sql = "SELECT level, COUNT(*) as count FROM logs GROUP BY level ORDER BY count DESC"
        results = service.query_sql(sql)

        assert len(results) >= 1
        assert all("level" in row and "count" in row for row in results)

        service.close()

    def test_query_sql_filter(self, temp_log_dir_with_data):
        """Should support filtered queries."""
        service = QueryService(temp_log_dir_with_data)

        sql = "SELECT * FROM logs WHERE level = 'ERROR'"
        results = service.query_sql(sql)

        assert len(results) == 1
        assert results[0]["level"] == "ERROR"

        service.close()


class TestOutputFormats:
    """Tests for different output formats."""

    def test_format_dict(self, temp_log_dir_with_data):
        """Should return LogEntry objects for dict format."""
        service = QueryService(temp_log_dir_with_data)

        params = LogQuery(limit=2)
        results = service.query(params, format="dict")

        assert isinstance(results, list)
        assert all(isinstance(entry, LogEntry) for entry in results)

        service.close()

    def test_format_json(self, temp_log_dir_with_data):
        """Should return JSON string for json format."""
        service = QueryService(temp_log_dir_with_data)

        params = LogQuery(limit=2)
        results = service.query(params, format="json")

        assert isinstance(results, str)
        # Should be valid JSON
        parsed = json.loads(results)
        assert isinstance(parsed, list)

        service.close()

    def test_format_csv(self, temp_log_dir_with_data):
        """Should return CSV string for csv format."""
        service = QueryService(temp_log_dir_with_data)

        params = LogQuery(limit=2)
        results = service.query(params, format="csv")

        assert isinstance(results, str)
        assert "trace_id" in results  # Header
        assert "," in results  # CSV delimiter

        service.close()

    def test_format_table(self, temp_log_dir_with_data):
        """Should return ASCII table for table format."""
        service = QueryService(temp_log_dir_with_data)

        params = LogQuery(limit=2)
        results = service.query(params, format="table")

        assert isinstance(results, str)
        assert "|" in results  # Table separator
        assert "-" in results  # Header separator

        service.close()


class TestContextManager:
    """Tests for context manager protocol."""

    def test_context_manager(self, temp_log_dir_with_data):
        """Should support context manager protocol."""
        with QueryService(temp_log_dir_with_data) as service:
            params = LogQuery(limit=1)
            results = service.query(params, format="dict")
            assert len(results) == 1

        # Connection should be closed after exit

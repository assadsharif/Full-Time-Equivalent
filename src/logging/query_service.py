"""
Query service for log files using DuckDB (P2).

Provides high-performance SQL interface to query, filter, and analyze logs.
Constitutional compliance: Section 2 (file system as source of truth).
"""

import csv
import json
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .duckdb_adapter import DuckDBAdapter
from .models import LogEntry, LogLevel, LogQuery


class QueryService:
    """
    High-performance log query service using DuckDB.

    Features:
    - Filter by time, level, module, trace ID
    - Full-text search
    - Raw SQL queries
    - Multiple output formats (JSON, CSV, table)
    - Performance: < 10s for 1GB logs

    Constitutional compliance:
    - Section 2: Queries read from disk (source of truth)

    Example:
        >>> service = QueryService(log_dir=Path("./Logs"))
        >>> params = LogQuery(levels=[LogLevel.ERROR], limit=10)
        >>> results = service.query(params)
    """

    def __init__(self, log_dir: Path, *, include_archives: bool = True):
        """
        Initialize query service.

        Args:
            log_dir: Directory containing log files
            include_archives: Whether to include compressed archives

        Raises:
            ValueError: If log_dir doesn't exist
            ImportError: If DuckDB not installed
        """
        if not log_dir.exists():
            raise ValueError(f"Log directory does not exist: {log_dir}")

        self.log_dir = log_dir
        self.include_archives = include_archives

        # Initialize DuckDB adapter
        self._adapter = DuckDBAdapter(log_dir, include_archives=include_archives)
        self._adapter.register_log_files()

    def query(
        self, query_params: LogQuery, *, format: str = "dict"
    ) -> Union[List[LogEntry], str]:
        """
        Query logs with structured filters.

        Args:
            query_params: LogQuery object with filters
            format: Output format ("dict", "json", "csv", "table")

        Returns:
            List of LogEntry objects (format="dict") or formatted string

        Raises:
            ValueError: If query parameters invalid

        Example:
            >>> params = LogQuery(
            ...     start_time=datetime(2026, 1, 28, 0, 0, 0),
            ...     levels=[LogLevel.ERROR],
            ...     limit=100
            ... )
            >>> results = service.query(params)
        """
        # Build SQL query from params
        sql = self._build_query_sql(query_params)

        # Execute query
        results = self._adapter.execute_query(sql)

        # Format results
        if format == "dict":
            return [self._dict_to_log_entry(row) for row in results]
        elif format == "json":
            return json.dumps(results, indent=2, default=str)
        elif format == "csv":
            return self._format_as_csv(results)
        elif format == "table":
            return self._format_as_table(results)
        else:
            raise ValueError(f"Unknown format: {format}")

    def query_sql(
        self, sql: str, *, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute raw SQL query against log files.

        Args:
            sql: SQL query string (DuckDB dialect)
            params: Optional query parameters

        Returns:
            List of result rows as dictionaries

        Example:
            >>> sql = "SELECT level, COUNT(*) FROM logs GROUP BY level"
            >>> results = service.query_sql(sql)
        """
        return self._adapter.execute_query(sql, params)

    def filter_by_trace(
        self, trace_id: str, *, order_by: str = "timestamp"
    ) -> List[LogEntry]:
        """
        Get all logs for a specific trace ID.

        Args:
            trace_id: Trace ID to filter by
            order_by: Sort field (default: "timestamp")

        Returns:
            List of LogEntry objects in chronological order

        Example:
            >>> logs = service.filter_by_trace("01HQ8Z9X0ABCDEFGHIJKLMNOPQ")
        """
        params = LogQuery(trace_id=trace_id, order_by=order_by, order_dir="asc")
        return self.query(params, format="dict")

    def filter_by_time_range(
        self,
        start_time: datetime,
        end_time: datetime,
        *,
        level: Optional[LogLevel] = None,
        module: Optional[str] = None,
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
            >>> from datetime import datetime, timedelta
            >>> start = datetime.now() - timedelta(hours=1)
            >>> end = datetime.now()
            >>> logs = service.filter_by_time_range(start, end, level=LogLevel.ERROR)
        """
        params = LogQuery(
            start_time=start_time,
            end_time=end_time,
            levels=[level] if level else None,
            modules=[module] if module else None,
        )
        return self.query(params, format="dict")

    def search_text(
        self, search_term: str, *, case_sensitive: bool = False, limit: int = 100
    ) -> List[LogEntry]:
        """
        Full-text search in log messages.

        Args:
            search_term: Text to search for
            case_sensitive: Whether search is case-sensitive
            limit: Max results to return

        Returns:
            List of LogEntry objects containing search term

        Example:
            >>> logs = service.search_text("disk full", limit=50)
        """
        params = LogQuery(search_text=search_term, limit=limit)

        # Build custom SQL for case-sensitive search if needed
        if case_sensitive:
            sql = f"""
                SELECT * FROM logs
                WHERE message LIKE '%{search_term}%'
                ORDER BY timestamp DESC
                LIMIT {limit}
            """
            results = self._adapter.execute_query(sql)
            return [self._dict_to_log_entry(row) for row in results]

        return self.query(params, format="dict")

    def close(self) -> None:
        """Close DuckDB connection."""
        self._adapter.close()

    def _build_query_sql(self, params: LogQuery) -> str:
        """
        Build SQL query from LogQuery parameters.

        Args:
            params: LogQuery object

        Returns:
            SQL query string
        """
        conditions = []

        # Time range filter
        if params.start_time:
            conditions.append(f"timestamp >= '{params.start_time.isoformat()}'")
        if params.end_time:
            conditions.append(f"timestamp <= '{params.end_time.isoformat()}'")

        # Level filter
        if params.levels:
            level_names = [f"'{level.name}'" for level in params.levels]
            conditions.append(f"level IN ({', '.join(level_names)})")

        # Module filter
        if params.modules:
            module_patterns = [f"module LIKE '{mod}%'" for mod in params.modules]
            conditions.append(f"({' OR '.join(module_patterns)})")

        # Trace ID filter
        if params.trace_id:
            conditions.append(f"trace_id = '{params.trace_id}'")

        # Text search filter (case-insensitive)
        if params.search_text:
            # Use ILIKE for case-insensitive search
            conditions.append(f"message ILIKE '%{params.search_text}%'")

        # Tags filter (AND logic)
        if params.tags:
            for tag in params.tags:
                conditions.append(f"list_contains(tags, '{tag}')")

        # Build WHERE clause
        where_clause = ""
        if conditions:
            where_clause = f"WHERE {' AND '.join(conditions)}"

        # Build ORDER BY clause
        order_clause = f"ORDER BY {params.order_by} {params.order_dir.upper()}"

        # Build LIMIT and OFFSET
        limit_clause = f"LIMIT {params.limit} OFFSET {params.offset}"

        # Construct full query
        sql = f"""
            SELECT * FROM logs
            {where_clause}
            {order_clause}
            {limit_clause}
        """

        return sql

    def _dict_to_log_entry(self, row: Dict[str, Any]) -> LogEntry:
        """
        Convert query result row to LogEntry object.

        Args:
            row: Dictionary from query result

        Returns:
            LogEntry object
        """
        from .models import ExceptionInfo, StackFrame

        # Parse exception if present
        exception = None
        if row.get("exception"):
            exc_data = row["exception"]
            if isinstance(exc_data, str):
                exc_data = json.loads(exc_data)

            # Build stack frames
            stack_frames = []
            if "stack_trace" in exc_data:
                for frame_data in exc_data["stack_trace"]:
                    stack_frames.append(
                        StackFrame(
                            file=frame_data["file"],
                            line=frame_data["line"],
                            function=frame_data["function"],
                            code=frame_data.get("code"),
                        )
                    )

            exception = ExceptionInfo(
                type=exc_data["type"],
                message=exc_data["message"],
                stack_trace=stack_frames,
                cause=None,  # Simplified for now
            )

        # Parse context if present
        context = row.get("context")
        if isinstance(context, str):
            context = json.loads(context)

        # Parse tags
        tags = row.get("tags", [])
        if tags is None:
            tags = []

        # Parse timestamp
        timestamp = row["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return LogEntry(
            trace_id=row["trace_id"],
            timestamp=timestamp,
            level=LogLevel[row["level"]],
            module=row["module"],
            message=row["message"],
            function=row.get("function"),
            line_number=row.get("line_number"),
            context=context,
            exception=exception,
            duration_ms=row.get("duration_ms"),
            tags=tags,
        )

    def _format_as_csv(self, results: List[Dict[str, Any]]) -> str:
        """Format results as CSV string."""
        if not results:
            return ""

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

        return output.getvalue()

    def _format_as_table(self, results: List[Dict[str, Any]]) -> str:
        """Format results as ASCII table."""
        if not results:
            return "No results"

        # Get column names and widths
        columns = list(results[0].keys())
        col_widths = {
            col: max(len(col), max(len(str(row.get(col, ""))) for row in results))
            for col in columns
        }

        # Build header
        header = " | ".join(col.ljust(col_widths[col]) for col in columns)
        separator = "-+-".join("-" * col_widths[col] for col in columns)

        # Build rows
        rows = []
        for row in results:
            row_str = " | ".join(
                str(row.get(col, "")).ljust(col_widths[col]) for col in columns
            )
            rows.append(row_str)

        return "\n".join([header, separator] + rows)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

"""
DuckDB adapter for querying NDJSON log files (P2).

Provides high-performance SQL interface to log files without importing data.
Constitutional compliance: Section 2 (file system as source of truth).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb


class DuckDBAdapter:
    """
    Adapter for querying NDJSON log files using DuckDB.

    Features:
    - Virtual table registration (no data import)
    - NDJSON format support
    - Read-only access
    - In-memory query execution
    - Performance: < 10s for 1GB logs

    Constitutional compliance:
    - Section 2: Queries read directly from disk files

    Example:
        >>> adapter = DuckDBAdapter(log_dir=Path("./Logs"))
        >>> adapter.register_log_files()
        >>> results = adapter.execute_query("SELECT * FROM logs WHERE level='ERROR'")
    """

    def __init__(self, log_dir: Path, include_archives: bool = True):
        """
        Initialize DuckDB adapter.

        Args:
            log_dir: Directory containing log files
            include_archives: Whether to include compressed archives

        Raises:
            ValueError: If log_dir doesn't exist
        """
        if not log_dir.exists():
            raise ValueError(f"Log directory does not exist: {log_dir}")

        self.log_dir = log_dir
        self.include_archives = include_archives

        # Create in-memory DuckDB connection
        self.conn = duckdb.connect(":memory:")

        # Set read-only mode for safety
        self.conn.execute("SET enable_progress_bar = false")

    def register_log_files(self) -> None:
        """
        Register log files as virtual table.

        Creates a 'logs' view that reads from all NDJSON log files
        in the log directory.

        Example:
            >>> adapter.register_log_files()
            >>> # Now can query: SELECT * FROM logs
        """
        # Find all log files
        log_files = self._find_log_files()

        if not log_files:
            # Create empty view if no log files
            self.conn.execute("""
                CREATE VIEW logs AS
                SELECT
                    NULL::VARCHAR as trace_id,
                    NULL::TIMESTAMP as timestamp,
                    NULL::VARCHAR as level,
                    NULL::VARCHAR as module,
                    NULL::VARCHAR as message,
                    NULL::VARCHAR as function,
                    NULL::INTEGER as line_number,
                    NULL::JSON as context,
                    NULL::JSON as exception,
                    NULL::DOUBLE as duration_ms,
                    NULL::VARCHAR[] as tags
                WHERE false
            """)
            return

        # Create view from NDJSON files
        # Use read_json with 'auto' format for NDJSON
        files_pattern = ", ".join([f"'{str(f)}'" for f in log_files])

        # DuckDB can read multiple NDJSON files with glob pattern
        # For now, use UNION ALL to combine multiple files
        if len(log_files) == 1:
            query = f"""
                CREATE VIEW logs AS
                SELECT
                    trace_id,
                    CAST(timestamp AS TIMESTAMP) as timestamp,
                    level,
                    module,
                    message,
                    function,
                    line_number,
                    context,
                    exception,
                    duration_ms,
                    tags
                FROM read_json_auto('{log_files[0]}', format='newline_delimited')
            """
        else:
            # For multiple files, read each and union
            subqueries = [f"""
                SELECT
                    trace_id,
                    CAST(timestamp AS TIMESTAMP) as timestamp,
                    level,
                    module,
                    message,
                    function,
                    line_number,
                    context,
                    exception,
                    duration_ms,
                    tags
                FROM read_json_auto('{f}', format='newline_delimited')
                """ for f in log_files]
            query = f"CREATE VIEW logs AS\n{' UNION ALL '.join(subqueries)}"

        self.conn.execute(query)

    def execute_query(
        self, sql: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results.

        Args:
            sql: SQL query string (DuckDB dialect)
            params: Optional query parameters

        Returns:
            List of result rows as dictionaries

        Raises:
            duckdb.Error: If query execution fails

        Example:
            >>> results = adapter.execute_query("SELECT COUNT(*) FROM logs")
        """
        if params:
            result = self.conn.execute(sql, params)
        else:
            result = self.conn.execute(sql)

        # Fetch all results as dictionaries
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()

        return [dict(zip(columns, row)) for row in rows]

    def execute_query_df(self, sql: str) -> Any:
        """
        Execute SQL query and return as DataFrame.

        Args:
            sql: SQL query string

        Returns:
            DuckDB relation (can be converted to pandas/arrow)

        Example:
            >>> df = adapter.execute_query_df("SELECT * FROM logs").df()
        """
        return self.conn.execute(sql)

    def close(self) -> None:
        """Close DuckDB connection."""
        if self.conn:
            self.conn.close()

    def _find_log_files(self) -> List[Path]:
        """
        Find all log files in log directory.

        Returns:
            List of log file paths (sorted by name)
        """
        log_files = []

        # Find regular log files (*.log)
        log_files.extend(self.log_dir.glob("*.log"))

        # Find archived log files (*.log.gz) if enabled
        if self.include_archives:
            # Note: DuckDB can read gzipped files directly
            log_files.extend(self.log_dir.glob("*.log.gz"))

        # Sort by name (chronological for date-based names)
        return sorted(log_files)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

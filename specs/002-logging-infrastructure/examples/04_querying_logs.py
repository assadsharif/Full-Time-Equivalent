"""
Example 4: Querying Logs

Demonstrates:
- Querying logs with filters
- Filtering by trace ID
- Filtering by time range
- Full-text search
- Raw SQL queries
- Different output formats
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.logging.models import LogLevel, LogQuery
from src.logging.query_service import QueryService


def main():
    # Initialize query service
    service = QueryService(log_dir=Path("./Logs"))

    # Example 1: Query all recent logs
    print("Example 1: Query recent logs")
    params = LogQuery(limit=10)
    results = service.query(params, format="dict")
    print(f"Found {len(results)} recent logs")
    for entry in results[:3]:  # Show first 3
        print(f"  [{entry.level.name}] {entry.message}")

    # Example 2: Filter by log level
    print("\nExample 2: Filter by log level (ERROR, CRITICAL)")
    params = LogQuery(
        levels=[LogLevel.ERROR, LogLevel.CRITICAL],
        limit=50
    )
    results = service.query(params, format="dict")
    print(f"Found {len(results)} errors")

    # Example 3: Filter by trace ID
    print("\nExample 3: Filter by trace ID")
    # Get a trace ID from recent logs
    recent = service.query(LogQuery(limit=1), format="dict")
    if recent:
        trace_id = recent[0].trace_id
        trace_logs = service.filter_by_trace(trace_id)
        print(f"Found {len(trace_logs)} logs for trace {trace_id}")
        for entry in trace_logs:
            print(f"  {entry.timestamp}: {entry.message}")

    # Example 4: Filter by time range
    print("\nExample 4: Filter by time range (last hour)")
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=1)
    results = service.filter_by_time_range(
        start_time, end_time,
        level=LogLevel.INFO
    )
    print(f"Found {len(results)} INFO logs in last hour")

    # Example 5: Full-text search
    print("\nExample 5: Full-text search")
    results = service.search_text("started", limit=10)
    print(f"Found {len(results)} logs containing 'started'")
    for entry in results[:3]:
        print(f"  {entry.message}")

    # Example 6: Complex query
    print("\nExample 6: Complex query")
    params = LogQuery(
        start_time=datetime.now(timezone.utc) - timedelta(hours=24),
        levels=[LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL],
        modules=["src.logging"],
        limit=20,
        order_by="timestamp",
        order_dir="desc"
    )
    results = service.query(params, format="dict")
    print(f"Found {len(results)} warnings/errors in last 24h from src.logging")

    # Example 7: Raw SQL query
    print("\nExample 7: Raw SQL query (count by level)")
    sql = """
        SELECT level, COUNT(*) as count
        FROM logs
        GROUP BY level
        ORDER BY count DESC
    """
    results = service.query_sql(sql)
    print("Log count by level:")
    for row in results:
        print(f"  {row['level']}: {row['count']}")

    # Example 8: Aggregation query
    print("\nExample 8: Aggregation (top modules by error count)")
    sql = """
        SELECT module, COUNT(*) as error_count
        FROM logs
        WHERE level IN ('ERROR', 'CRITICAL')
        GROUP BY module
        ORDER BY error_count DESC
        LIMIT 5
    """
    results = service.query_sql(sql)
    print("Top modules by error count:")
    for row in results:
        print(f"  {row['module']}: {row['error_count']}")

    # Example 9: Different output formats
    print("\nExample 9: Output formats")

    # JSON format
    params = LogQuery(limit=2)
    json_output = service.query(params, format="json")
    print(f"JSON format (first 200 chars): {json_output[:200]}...")

    # CSV format
    csv_output = service.query(params, format="csv")
    print(f"CSV format (first 200 chars): {csv_output[:200]}...")

    # Table format
    table_output = service.query(params, format="table")
    print(f"Table format:\n{table_output[:300]}...")

    # Close service
    service.close()
    print("\nQuery service closed.")


if __name__ == "__main__":
    main()

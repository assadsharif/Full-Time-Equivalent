#!/bin/bash
# Example 5: CLI Usage
#
# Demonstrates CLI commands for querying and viewing logs.
# Run this after generating some logs with the previous examples.

set -e

echo "=== Logging Infrastructure CLI Examples ==="
echo

# Example 1: Tail recent logs
echo "Example 1: View last 10 log entries"
python -m src.cli.logs tail --lines 10 --format table
echo

# Example 2: Tail more entries
echo "Example 2: View last 50 entries in JSON format"
python -m src.cli.logs tail -n 50 --format json | head -n 20
echo "... (showing first 20 lines)"
echo

# Example 3: Query by log level
echo "Example 3: Query ERROR and CRITICAL logs"
python -m src.cli.logs query --level ERROR --level CRITICAL --limit 10
echo

# Example 4: Query by module
echo "Example 4: Query logs from specific module"
python -m src.cli.logs query --module src.logging --limit 10
echo

# Example 5: Query with time range (ISO format)
echo "Example 5: Query logs with time range"
python -m src.cli.logs query \
    --start "2026-01-28 00:00:00" \
    --end "2026-01-28 23:59:59" \
    --level INFO \
    --limit 10
echo

# Example 6: Query with relative time
echo "Example 6: Query logs from last hour"
python -m src.cli.logs query --start 1h --limit 20
echo

# Example 7: Query with relative time (last day)
echo "Example 7: Query logs from last 24 hours"
python -m src.cli.logs query --start 24h --level ERROR --limit 10
echo

# Example 8: Query by trace ID
echo "Example 8: Query logs by trace ID (example)"
# First get a trace ID from recent logs
TRACE_ID=$(python -m src.cli.logs tail -n 1 --format json | python -c "import sys, json; print(json.loads(sys.stdin.read())[0]['trace_id'])" 2>/dev/null || echo "trace-example")
if [ "$TRACE_ID" != "trace-example" ]; then
    python -m src.cli.logs query --trace-id "$TRACE_ID"
else
    echo "No logs found, skipping trace ID query"
fi
echo

# Example 9: Full-text search
echo "Example 9: Search for 'started' in logs"
python -m src.cli.logs search "started" --limit 10
echo

# Example 10: Case-sensitive search
echo "Example 10: Case-sensitive search"
python -m src.cli.logs search "Error" --case-sensitive --limit 5
echo

# Example 11: Search in last hour
echo "Example 11: Search in last hour"
python -m src.cli.logs search "task" --last 1h --limit 10
echo

# Example 12: Combined filters with JSON output
echo "Example 12: Complex query with JSON output"
python -m src.cli.logs query \
    --level ERROR \
    --level CRITICAL \
    --start 24h \
    --limit 5 \
    --format json | python -m json.tool
echo

# Example 13: CSV output
echo "Example 13: Export to CSV"
python -m src.cli.logs query --limit 100 --format csv > /tmp/logs_export.csv
echo "Exported 100 logs to /tmp/logs_export.csv"
head -n 5 /tmp/logs_export.csv
echo

echo "=== CLI Examples Complete ==="
echo
echo "For more options, run:"
echo "  python -m src.cli.logs --help"
echo "  python -m src.cli.logs tail --help"
echo "  python -m src.cli.logs query --help"
echo "  python -m src.cli.logs search --help"

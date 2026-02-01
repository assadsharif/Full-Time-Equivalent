"""
CLI commands for querying and viewing logs (P2).

Commands:
- fte logs tail: View recent log entries
- fte logs query: Query logs with filters
- fte logs search: Full-text search in logs

Constitutional compliance: Section 2 (queries read from disk).
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

try:
    import click
except ImportError:
    print("Error: click library not installed. Install with: pip install click>=8.0.0", file=sys.stderr)
    sys.exit(1)

from ..logging.models import LogLevel, LogQuery
from ..logging.query_service import QueryService


@click.group(name="logs")
def logs_cli():
    """
    Log management and query commands.

    Query, filter, and analyze application logs.
    """
    pass


@logs_cli.command(name="tail")
@click.option(
    "--lines", "-n",
    type=int,
    default=10,
    help="Number of lines to display (default: 10)"
)
@click.option(
    "--follow", "-f",
    is_flag=True,
    help="Follow log file (not implemented yet)"
)
@click.option(
    "--log-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="./Logs",
    help="Log directory (default: ./Logs)"
)
@click.option(
    "--format",
    type=click.Choice(["json", "table", "csv"], case_sensitive=False),
    default="table",
    help="Output format (default: table)"
)
def tail_command(lines: int, follow: bool, log_dir: Path, format: str):
    """
    View recent log entries (like 'tail' command).

    Examples:
        fte logs tail --lines 50
        fte logs tail -n 100 --format json
        fte logs tail --follow  # (not implemented yet)
    """
    if follow:
        click.echo("Error: --follow not implemented yet", err=True)
        sys.exit(1)

    try:
        with QueryService(log_dir) as service:
            # Query most recent logs
            params = LogQuery(
                limit=lines,
                order_by="timestamp",
                order_dir="desc"
            )

            results = service.query(params, format=format)

            if isinstance(results, str):
                click.echo(results)
            else:
                # If results are LogEntry objects, format them
                for entry in results:
                    click.echo(f"[{entry.timestamp}] [{entry.level.name}] {entry.module}: {entry.message}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@logs_cli.command(name="query")
@click.option(
    "--level", "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    multiple=True,
    help="Filter by log level (can specify multiple)"
)
@click.option(
    "--module", "-m",
    multiple=True,
    help="Filter by module (can specify multiple)"
)
@click.option(
    "--trace-id", "-t",
    help="Filter by trace ID"
)
@click.option(
    "--start",
    type=str,
    help="Start time (ISO format: 2026-01-28T00:00:00 or relative: 1h, 1d)"
)
@click.option(
    "--end",
    type=str,
    help="End time (ISO format or relative)"
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="Max results to return (default: 100)"
)
@click.option(
    "--log-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="./Logs",
    help="Log directory (default: ./Logs)"
)
@click.option(
    "--format",
    type=click.Choice(["json", "table", "csv"], case_sensitive=False),
    default="table",
    help="Output format (default: table)"
)
def query_command(
    level: tuple,
    module: tuple,
    trace_id: Optional[str],
    start: Optional[str],
    end: Optional[str],
    limit: int,
    log_dir: Path,
    format: str
):
    """
    Query logs with filters.

    Examples:
        fte logs query --level ERROR --level CRITICAL
        fte logs query --module src.control_plane --start "2026-01-28 00:00:00"
        fte logs query --trace-id 01HQ8Z9X0ABCDEFGHIJKLMNOPQ
        fte logs query --start 1h --format json
    """
    try:
        # Parse levels
        levels = [LogLevel[l.upper()] for l in level] if level else None

        # Parse time range
        start_time = _parse_time(start) if start else None
        end_time = _parse_time(end) if end else None

        # Build query
        params = LogQuery(
            start_time=start_time,
            end_time=end_time,
            levels=levels,
            modules=list(module) if module else None,
            trace_id=trace_id,
            limit=limit
        )

        with QueryService(log_dir) as service:
            results = service.query(params, format=format)

            if isinstance(results, str):
                click.echo(results)
            else:
                # Format LogEntry objects
                for entry in results:
                    click.echo(f"[{entry.timestamp}] [{entry.level.name}] {entry.module}: {entry.message}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@logs_cli.command(name="search")
@click.argument("search_term")
@click.option(
    "--case-sensitive", "-c",
    is_flag=True,
    help="Case-sensitive search"
)
@click.option(
    "--last",
    type=str,
    help="Search in last N time (e.g., 1h, 1d, 1w)"
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="Max results to return (default: 100)"
)
@click.option(
    "--log-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default="./Logs",
    help="Log directory (default: ./Logs)"
)
@click.option(
    "--format",
    type=click.Choice(["json", "table", "csv"], case_sensitive=False),
    default="table",
    help="Output format (default: table)"
)
def search_command(
    search_term: str,
    case_sensitive: bool,
    last: Optional[str],
    limit: int,
    log_dir: Path,
    format: str
):
    """
    Full-text search in log messages.

    Examples:
        fte logs search "disk full"
        fte logs search "Error" --case-sensitive
        fte logs search "timeout" --last 1h
        fte logs search "failed" --format json
    """
    try:
        with QueryService(log_dir) as service:
            # If time range specified, use query() with search_text
            if last:
                end_time = datetime.now(timezone.utc)
                start_time = end_time - _parse_relative_time(last)

                params = LogQuery(
                    start_time=start_time,
                    end_time=end_time,
                    search_text=search_term,
                    limit=limit
                )

                results = service.query(params, format=format)
            else:
                # Use search_text() method
                if format == "dict":
                    results = service.search_text(
                        search_term,
                        case_sensitive=case_sensitive,
                        limit=limit
                    )
                else:
                    # For other formats, use query with search_text
                    params = LogQuery(
                        search_text=search_term,
                        limit=limit
                    )
                    results = service.query(params, format=format)

            if isinstance(results, str):
                click.echo(results)
            else:
                # Format LogEntry objects
                for entry in results:
                    # Highlight search term in message
                    message = entry.message
                    if not case_sensitive:
                        # Simple highlight (could be improved)
                        import re
                        pattern = re.compile(re.escape(search_term), re.IGNORECASE)
                        message = pattern.sub(f"**{search_term}**", message)

                    click.echo(f"[{entry.timestamp}] [{entry.level.name}] {entry.module}: {message}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _parse_time(time_str: str) -> datetime:
    """
    Parse time string (ISO format or relative).

    Args:
        time_str: Time string (e.g., "2026-01-28T00:00:00", "1h", "2d")

    Returns:
        datetime object

    Raises:
        ValueError: If time format invalid
    """
    # Try relative time first (e.g., "1h", "2d")
    if time_str[-1] in ['h', 'd', 'w', 'm']:
        delta = _parse_relative_time(time_str)
        return datetime.now(timezone.utc) - delta

    # Try ISO format
    try:
        # Try with timezone
        return datetime.fromisoformat(time_str)
    except ValueError:
        # Try without timezone (assume UTC)
        try:
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            # Try date only
            try:
                dt = datetime.strptime(time_str, "%Y-%m-%d")
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                raise ValueError(f"Invalid time format: {time_str}")


def _parse_relative_time(relative_str: str) -> timedelta:
    """
    Parse relative time string (e.g., "1h", "2d", "1w").

    Args:
        relative_str: Relative time string

    Returns:
        timedelta object

    Raises:
        ValueError: If format invalid
    """
    try:
        value = int(relative_str[:-1])
        unit = relative_str[-1]

        if unit == 'm':
            return timedelta(minutes=value)
        elif unit == 'h':
            return timedelta(hours=value)
        elif unit == 'd':
            return timedelta(days=value)
        elif unit == 'w':
            return timedelta(weeks=value)
        else:
            raise ValueError(f"Unknown time unit: {unit}")
    except (ValueError, IndexError):
        raise ValueError(f"Invalid relative time format: {relative_str}")


if __name__ == "__main__":
    logs_cli()

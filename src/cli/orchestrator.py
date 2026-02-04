"""
Orchestrator Commands

Commands for viewing orchestrator performance metrics.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from cli.utils import (
    display_error,
    display_info,
    resolve_vault_path,
    validate_vault_or_error,
)

console = Console()


def _parse_since(since_str: str) -> datetime:
    """Parse a duration string like '24h', '7d' into a cutoff datetime.

    Supported units: h (hours), d (days).
    """
    if not since_str:
        raise click.BadParameter("Empty --since value")
    unit = since_str[-1].lower()
    unit_map = {"h": "hours", "d": "days"}
    if unit not in unit_map:
        raise click.BadParameter(f"Unknown unit '{unit}' — use 'h' (hours) or 'd' (days)")
    try:
        amount = int(since_str[:-1])
    except ValueError:
        raise click.BadParameter(f"Invalid number in --since: {since_str}")
    if amount <= 0:
        raise click.BadParameter("--since value must be positive")
    return datetime.now(timezone.utc) - timedelta(**{unit_map[unit]: amount})


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group(name="orchestrator")
def orchestrator_group():
    """Orchestrator commands"""
    pass


# ---------------------------------------------------------------------------
# fte orchestrator metrics
# ---------------------------------------------------------------------------


@orchestrator_group.command(name="metrics")
@click.option(
    "--since",
    type=str,
    default="24h",
    help="Time window for metrics (e.g. 1h, 7d, 30d). Default: 24h",
    show_default=True,
)
@click.option(
    "--vault-path",
    type=click.Path(path_type=Path),
    help="Path to vault (overrides config)",
)
@click.pass_context
def metrics_command(ctx: click.Context, since: str, vault_path: Optional[Path]):
    """
    Display orchestrator performance metrics.

    Shows throughput, average latency, and error rate for the selected
    time window.

    \b
    Examples:
        fte orchestrator metrics
        fte orchestrator metrics --since 7d
        fte orchestrator metrics --since 1h
    """
    try:
        if vault_path is None:
            vault_path = resolve_vault_path()
        validate_vault_or_error(vault_path)

        since_dt = _parse_since(since)

        # Import locally to avoid circular imports at module load time
        from orchestrator.metrics import MetricsCollector

        metrics_path = vault_path.parent / ".fte" / "orchestrator_metrics.log"
        collector = MetricsCollector(log_path=metrics_path)

        if not metrics_path.exists():
            display_info("No metrics data found. The orchestrator has not recorded any events yet.")
            return

        # Load and aggregate
        events = collector._load_events(since_dt)
        started = sum(1 for e in events if e["event"] == "task_started")
        completed = sum(1 for e in events if e["event"] == "task_completed")
        failed = sum(1 for e in events if e["event"] == "task_failed")

        throughput = collector.calculate_throughput(since_dt)
        avg_latency = collector.calculate_avg_latency(since_dt)
        error_rate = collector.calculate_error_rate(since_dt)

        # Display
        console.print(f"\n[bold]Orchestrator Metrics[/bold] (since {since})")
        console.print(f"  Window: {since_dt.strftime('%Y-%m-%d %H:%M UTC')} → now\n")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Value")

        table.add_row("Tasks Started", str(started))
        table.add_row("Tasks Completed", f"[green]{completed}[/green]")
        table.add_row("Tasks Failed", f"[red]{failed}[/red]" if failed else "0")
        table.add_row("Throughput", f"{throughput} tasks/hr")
        table.add_row("Avg Latency", f"{avg_latency} s")
        table.add_row(
            "Error Rate",
            f"[red]{error_rate * 100:.1f}%[/red]" if error_rate > 0 else "0.0%",
        )

        console.print(table)

    except click.BadParameter as exc:
        console.print(f"[red]Error:[/red] {exc}")
        ctx.exit(1)
    except Exception as exc:
        display_error(exc, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


# ---------------------------------------------------------------------------
# fte orchestrator health
# ---------------------------------------------------------------------------


@orchestrator_group.command(name="health")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output health status as JSON",
)
@click.option(
    "--vault-path",
    type=click.Path(path_type=Path),
    help="Path to vault (overrides config)",
)
@click.pass_context
def health_command(ctx: click.Context, output_json: bool, vault_path: Optional[Path]):
    """
    Check orchestrator health status.

    Runs diagnostic checks for scheduler liveness, task backlog,
    error rate, and completion staleness. Outputs a summary status
    (healthy / degraded / unhealthy).

    \b
    Examples:
        fte orchestrator health
        fte orchestrator health --json
    """
    try:
        if vault_path is None:
            vault_path = resolve_vault_path()
        validate_vault_or_error(vault_path)

        # Import locally to avoid circular imports at module load time
        from orchestrator.health_check import HealthCheck

        health = HealthCheck(vault_path=vault_path)
        result = health.get_health_status()

        if output_json:
            import json
            console.print(json.dumps(result, indent=2))
        else:
            # Rich text output
            status = result["status"]
            status_color = {
                "healthy": "green",
                "degraded": "yellow",
                "unhealthy": "red",
            }.get(status, "white")

            console.print(f"\n[bold]Orchestrator Health Status[/bold]: [{status_color}]{status.upper()}[/{status_color}]")
            console.print(f"  Checked at: {result['timestamp']}\n")

            table = Table(show_header=True, header_style="bold cyan")
            table.add_column("Check", style="bold")
            table.add_column("Status")
            table.add_column("Message")

            for check_name, check_data in result["checks"].items():
                check_label = check_name.replace("_", " ").title()
                ok = check_data["ok"]
                msg = check_data["message"]
                status_icon = "[green]✓ PASS[/green]" if ok else "[red]✗ FAIL[/red]"
                table.add_row(check_label, status_icon, msg)

            console.print(table)

    except Exception as exc:
        display_error(exc, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)

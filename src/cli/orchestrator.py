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
        raise click.BadParameter(
            f"Unknown unit '{unit}' — use 'h' (hours) or 'd' (days)"
        )
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
# fte orchestrator run
# ---------------------------------------------------------------------------


@orchestrator_group.command(name="run")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Dry-run mode: discover and score tasks but don't invoke Claude",
)
@click.option(
    "--once",
    is_flag=True,
    help="Run a single sweep and exit (useful for testing)",
)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to orchestrator config YAML (default: config/orchestrator.yaml)",
)
@click.pass_context
def run_command(ctx, dry_run: bool, once: bool, config: Optional[Path]):
    """
    Start the orchestrator (Ralph Wiggum Loop).

    Continuously discovers tasks in Needs_Action, scores priorities, enforces
    HITL approvals, invokes Claude Code, and drives tasks to Done/Rejected.

    \b
    Examples:
      fte orchestrator run               # Continuous operation
      fte orchestrator run --once        # Single sweep
      fte orchestrator run --dry-run     # Test without execution
      fte orchestrator run --config custom.yaml
    """
    vault_path = ctx.obj.get("vault_path") if ctx.obj else None
    if not vault_path:
        vault_path = resolve_vault_path(None)

    # Validate vault
    if not validate_vault_or_error(vault_path):
        return

    # Load config
    try:
        from orchestrator.models import OrchestratorConfig

        if config:
            orch_config = OrchestratorConfig.from_yaml(
                config, vault_path_override=vault_path
            )
        else:
            # Try default config location
            default_config = Path("config/orchestrator.yaml")
            if default_config.exists():
                orch_config = OrchestratorConfig.from_yaml(
                    default_config, vault_path_override=vault_path
                )
            else:
                # Use defaults
                orch_config = OrchestratorConfig(vault_path=vault_path)

        # Create and start orchestrator
        from orchestrator.scheduler import Orchestrator

        orchestrator = Orchestrator(config=orch_config, dry_run=dry_run)

        if dry_run:
            display_info("Orchestrator starting in DRY-RUN mode (no execution)")
        if once:
            display_info("Orchestrator running single sweep")

        if once:
            # Run single sweep
            exits = orchestrator.run_once()
            if exits:
                console.print(f"\n[green]✓[/green] Processed {len(exits)} task(s)")
                for exit in exits:
                    status_icon = "✓" if exit.success else "✗"
                    status_color = "green" if exit.success else "red"
                    console.print(
                        f"  [{status_color}]{status_icon}[/{status_color}] {exit.task_name}"
                    )
            else:
                console.print("[yellow]No tasks to process[/yellow]")
            return

        # Start continuous loop
        orchestrator.run()

    except KeyboardInterrupt:
        display_info("\nOrchestrator stopped by user (Ctrl+C)")
    except Exception as e:
        display_error(f"Orchestrator error: {e}")
        raise


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
            display_info(
                "No metrics data found. The orchestrator has not recorded any events yet."
            )
            return

        # Load and aggregate
        events = collector._load_events(since_dt)
        started = sum(1 for e in events if e["event"] == "task_started")
        completed = sum(1 for e in events if e["event"] == "task_completed")
        failed = sum(1 for e in events if e["event"] == "task_failed")

        throughput = collector.calculate_throughput(since_dt)
        avg_latency = collector.calculate_avg_latency(since_dt)
        error_rate = collector.calculate_error_rate(since_dt)

        # Resource usage (if available)
        avg_cpu = collector.calculate_avg_cpu_percent(since_dt)
        avg_memory = collector.calculate_avg_memory_mb(since_dt)
        peak_memory = collector.get_peak_memory_mb(since_dt)

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

        # Resource metrics (if captured)
        if avg_cpu > 0 or avg_memory > 0:
            table.add_row("", "")  # Separator
            table.add_row("Avg CPU Usage", f"{avg_cpu:.1f}%")
            table.add_row("Avg Memory", f"{avg_memory:.1f} MB")
            table.add_row("Peak Memory", f"{peak_memory:.1f} MB")

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

            console.print(
                f"\n[bold]Orchestrator Health Status[/bold]: [{status_color}]{status.upper()}[/{status_color}]"
            )
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


# ---------------------------------------------------------------------------
# fte orchestrator dashboard
# ---------------------------------------------------------------------------


@orchestrator_group.command(name="dashboard")
@click.option(
    "--watch",
    is_flag=True,
    help="Live refresh mode (update every 5 seconds)",
)
@click.option(
    "--vault-path",
    type=click.Path(path_type=Path),
    help="Path to vault (overrides config)",
)
@click.pass_context
def dashboard_command(ctx: click.Context, watch: bool, vault_path: Optional[Path]):
    """
    Display orchestrator dashboard.

    Shows real-time orchestrator status, pending task queue with priorities,
    active tasks, and recent completions.

    \b
    Examples:
        fte orchestrator dashboard
        fte orchestrator dashboard --watch
    """
    try:
        if vault_path is None:
            vault_path = resolve_vault_path()
        validate_vault_or_error(vault_path)

        # Import locally to avoid circular imports at module load time
        from orchestrator.dashboard import OrchestratorDashboard

        dashboard = OrchestratorDashboard(vault_path=vault_path)

        def render_dashboard():
            """Render a single dashboard frame."""
            import time as time_module

            status = dashboard.get_status()
            queue = dashboard.get_queue()
            active = dashboard.get_active_tasks()
            recent = dashboard.get_recent_completions(limit=10)

            # Status section
            state = status["state"]
            state_color = {
                "running": "green",
                "stopped": "yellow",
                "error": "red",
            }.get(state, "white")

            console.print(f"\n[bold]Orchestrator Dashboard[/bold]")
            console.print(f"  Status: [{state_color}]{state.upper()}[/{state_color}]")
            console.print(f"  {status['message']}")
            if status["last_iteration"] is not None:
                console.print(f"  Last iteration: {status['last_iteration']}")
            console.print()

            # Queue section
            console.print(
                f"[bold cyan]Pending Tasks[/bold cyan] ({len(queue)} in queue)"
            )
            if queue:
                queue_table = Table(show_header=True, header_style="bold")
                queue_table.add_column("Priority", style="bold")
                queue_table.add_column("Task")
                for task in queue[:10]:  # Show top 10
                    pri = task["priority"]
                    pri_str = (
                        f"[yellow]{pri:.1f}[/yellow]" if pri > 3.0 else f"{pri:.1f}"
                    )
                    queue_table.add_row(pri_str, task["name"])
                if len(queue) > 10:
                    queue_table.add_row("...", f"({len(queue) - 10} more)")
                console.print(queue_table)
            else:
                console.print("  [dim]No pending tasks[/dim]")
            console.print()

            # Active tasks section
            console.print(
                f"[bold magenta]Active Tasks[/bold magenta] ({len(active)} executing)"
            )
            if active:
                active_table = Table(show_header=True, header_style="bold")
                active_table.add_column("Task")
                active_table.add_column("State")
                active_table.add_column("Attempts")
                for task in active:
                    console.print(
                        f"  [cyan]{task['name']}[/cyan] — {task['state']} (attempt {task['attempts']})"
                    )
            else:
                console.print("  [dim]No active tasks[/dim]")
            console.print()

            # Recent completions section
            console.print(
                f"[bold green]Recent Completions[/bold green] (last {len(recent)})"
            )
            if recent:
                comp_table = Table(show_header=True, header_style="bold")
                comp_table.add_column("Task")
                comp_table.add_column("Status")
                comp_table.add_column("Duration")
                for comp in recent:
                    status_icon = (
                        "[green]✓[/green]" if comp["success"] else "[red]✗[/red]"
                    )
                    duration = f"{comp['duration_s']:.1f}s"
                    comp_table.add_row(comp["task"], status_icon, duration)
                console.print(comp_table)
            else:
                console.print("  [dim]No recent completions[/dim]")

            if watch:
                console.print(f"\n[dim]Refreshing every 5s... (Ctrl+C to exit)[/dim]")

        if watch:
            # Live refresh mode
            try:
                while True:
                    console.clear()
                    render_dashboard()
                    import time as time_module

                    time_module.sleep(5)
            except KeyboardInterrupt:
                console.print("\n[yellow]Dashboard stopped[/yellow]")
        else:
            # Single render
            render_dashboard()

    except Exception as exc:
        display_error(exc, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


# ---------------------------------------------------------------------------
# fte orchestrator queue
# ---------------------------------------------------------------------------


@orchestrator_group.command(name="queue")
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed task information (file paths)",
)
@click.option(
    "--watch",
    is_flag=True,
    help="Live refresh mode (update every 5 seconds)",
)
@click.option(
    "--vault-path",
    type=click.Path(path_type=Path),
    help="Path to vault (overrides config)",
)
@click.pass_context
def queue_command(
    ctx: click.Context, verbose: bool, watch: bool, vault_path: Optional[Path]
):
    """
    Display orchestrator task queue.

    Shows pending tasks from Needs_Action folder sorted by priority score,
    with wait times since each task was added.

    \b
    Examples:
        fte orchestrator queue
        fte orchestrator queue --verbose
        fte orchestrator queue --watch
    """
    try:
        if vault_path is None:
            vault_path = resolve_vault_path()
        validate_vault_or_error(vault_path)

        # Import locally to avoid circular imports at module load time
        from orchestrator.queue_visualizer import QueueVisualizer

        visualizer = QueueVisualizer(vault_path=vault_path)

        def render_queue():
            """Render a single queue frame."""
            queue = visualizer.render_queue_table(verbose=verbose)

            console.print(
                f"\n[bold]Orchestrator Task Queue[/bold] ({len(queue)} pending)"
            )
            console.print()

            if queue:
                table = Table(show_header=True, header_style="bold cyan")
                table.add_column("Priority", style="bold", justify="right")
                table.add_column("Task")
                table.add_column("Wait Time", justify="right")
                if verbose:
                    table.add_column("Path", style="dim")

                for task in queue:
                    pri = task["priority"]
                    # Highlight high-priority tasks
                    pri_str = (
                        f"[yellow]{pri:.1f}[/yellow]" if pri > 3.0 else f"{pri:.1f}"
                    )
                    wait = task["wait_time_display"]
                    # Highlight stale tasks (> 1 hour)
                    wait_str = (
                        f"[red]{wait}[/red]"
                        if task["wait_time_seconds"] > 3600
                        else wait
                    )

                    row = [pri_str, task["name"], wait_str]
                    if verbose:
                        row.append(task["path"])
                    table.add_row(*row)

                console.print(table)
            else:
                console.print("  [dim]Queue is empty[/dim]")

            if watch:
                console.print(f"\n[dim]Refreshing every 5s... (Ctrl+C to exit)[/dim]")

        if watch:
            # Live refresh mode
            try:
                while True:
                    console.clear()
                    render_queue()
                    import time as time_module

                    time_module.sleep(5)
            except KeyboardInterrupt:
                console.print("\n[yellow]Queue monitor stopped[/yellow]")
        else:
            # Single render
            render_queue()

    except Exception as exc:
        display_error(exc, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)

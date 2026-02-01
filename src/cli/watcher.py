"""
Watcher Lifecycle Management Commands

Commands for managing watcher daemons including start, stop, status, and logs.
Watchers monitor various sources (Gmail, WhatsApp, Filesystem) for new tasks.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import click
from rich.console import Console
from rich.table import Table

from cli.checkpoint import get_checkpoint_manager
from cli.config import get_config
from cli.errors import (
    CLIError,
    PM2NotFoundError,
    WatcherNotFoundError,
    WatcherValidationError,
)
from cli.utils import (
    display_error,
    display_info,
    display_success,
    display_warning,
)

console = Console()

# Valid watcher names
VALID_WATCHERS = ["gmail", "whatsapp", "filesystem"]


def check_pm2_installed() -> bool:
    """Check if PM2 is installed and available."""
    try:
        result = subprocess.run(
            ["pm2", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def validate_watcher_name(name: str) -> None:
    """
    Validate watcher name against allowed watchers.

    Args:
        name: Watcher name to validate

    Raises:
        WatcherValidationError: If watcher name is invalid
    """
    if name not in VALID_WATCHERS:
        raise WatcherValidationError(
            f"Invalid watcher name: {name}. Valid watchers: {', '.join(VALID_WATCHERS)}"
        )


def get_pm2_list() -> List[Dict]:
    """
    Get list of PM2 processes.

    Returns:
        List of PM2 process dictionaries

    Raises:
        PM2NotFoundError: If PM2 is not installed
        CLIError: If PM2 command fails
    """
    if not check_pm2_installed():
        raise PM2NotFoundError(
            "PM2 is not installed. Install with: npm install -g pm2"
        )

    try:
        result = subprocess.run(
            ["pm2", "jlist"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            raise CLIError(f"PM2 command failed: {result.stderr}")

        # Parse JSON output
        processes = json.loads(result.stdout)
        return processes if isinstance(processes, list) else []

    except json.JSONDecodeError as e:
        raise CLIError(f"Failed to parse PM2 output: {e}")
    except subprocess.TimeoutExpired:
        raise CLIError("PM2 command timed out")
    except Exception as e:
        raise CLIError(f"Failed to get PM2 process list: {e}")


def get_watcher_process(name: str) -> Optional[Dict]:
    """
    Get PM2 process for specific watcher.

    Args:
        name: Watcher name

    Returns:
        PM2 process dict or None if not found
    """
    processes = get_pm2_list()

    # Look for process with matching name
    for proc in processes:
        proc_name = proc.get("name", "")
        if proc_name == f"fte-watcher-{name}" or proc_name == name:
            return proc

    return None


def start_watcher_pm2(name: str) -> None:
    """
    Start watcher using PM2.

    Args:
        name: Watcher name (gmail, whatsapp, filesystem)

    Raises:
        WatcherValidationError: If watcher name is invalid
        PM2NotFoundError: If PM2 is not installed
        CLIError: If PM2 start command fails
    """
    validate_watcher_name(name)

    if not check_pm2_installed():
        raise PM2NotFoundError(
            "PM2 is not installed. Install with: npm install -g pm2"
        )

    # Check if already running
    existing = get_watcher_process(name)
    if existing and existing.get("pm2_env", {}).get("status") == "online":
        display_warning(f"Watcher '{name}' is already running")
        return

    # Path to watcher script
    script_path = Path.cwd() / "scripts" / f"run_{name}_watcher.py"

    if not script_path.exists():
        raise WatcherNotFoundError(
            f"Watcher script not found: {script_path}"
        )

    # Start with PM2
    try:
        result = subprocess.run(
            [
                "pm2", "start",
                str(script_path),
                "--name", f"fte-watcher-{name}",
                "--interpreter", "python3",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0:
            raise CLIError(f"Failed to start watcher: {result.stderr}")

        # Update checkpoint
        checkpoint_manager = get_checkpoint_manager()
        checkpoint_manager.update_watcher(name, "running")

    except subprocess.TimeoutExpired:
        raise CLIError(f"PM2 start command timed out for watcher '{name}'")
    except Exception as e:
        raise CLIError(f"Failed to start watcher: {e}")


def stop_watcher_pm2(name: str) -> None:
    """
    Stop watcher using PM2.

    Args:
        name: Watcher name

    Raises:
        WatcherValidationError: If watcher name is invalid
        PM2NotFoundError: If PM2 is not installed
        WatcherNotFoundError: If watcher is not running
        CLIError: If PM2 stop command fails
    """
    validate_watcher_name(name)

    if not check_pm2_installed():
        raise PM2NotFoundError(
            "PM2 is not installed. Install with: npm install -g pm2"
        )

    # Check if running
    existing = get_watcher_process(name)
    if not existing:
        raise WatcherNotFoundError(
            f"Watcher '{name}' is not running"
        )

    # Stop with PM2
    try:
        result = subprocess.run(
            ["pm2", "stop", f"fte-watcher-{name}"],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0:
            raise CLIError(f"Failed to stop watcher: {result.stderr}")

        # Delete from PM2
        subprocess.run(
            ["pm2", "delete", f"fte-watcher-{name}"],
            capture_output=True,
            timeout=10,
        )

        # Update checkpoint
        checkpoint_manager = get_checkpoint_manager()
        checkpoint_manager.update_watcher(name, "stopped")

    except subprocess.TimeoutExpired:
        raise CLIError(f"PM2 stop command timed out for watcher '{name}'")
    except Exception as e:
        raise CLIError(f"Failed to stop watcher: {e}")


def format_uptime(uptime_ms: int) -> str:
    """
    Format uptime from milliseconds to human-readable string.

    Args:
        uptime_ms: Uptime in milliseconds

    Returns:
        Formatted uptime string (e.g., "2h 30m")
    """
    if uptime_ms <= 0:
        return "0s"

    seconds = uptime_ms // 1000

    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 and not parts:  # Only show seconds if nothing else
        parts.append(f"{secs}s")

    return " ".join(parts) if parts else "0s"


def display_watcher_status(processes: List[Dict]) -> None:
    """
    Display watcher status in Rich table.

    Args:
        processes: List of PM2 process dictionaries
    """
    # Create table
    table = Table(
        title="Watcher Status",
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("Name", style="bold")
    table.add_column("Status")
    table.add_column("PID")
    table.add_column("Uptime")
    table.add_column("Restarts")
    table.add_column("CPU", justify="right")
    table.add_column("Memory", justify="right")

    if not processes:
        console.print("[yellow]No watchers are currently running[/yellow]")
        return

    # Filter for watcher processes
    watcher_processes = []
    for proc in processes:
        name = proc.get("name", "")
        if name.startswith("fte-watcher-") or name in VALID_WATCHERS:
            watcher_processes.append(proc)

    if not watcher_processes:
        console.print("[yellow]No watchers are currently running[/yellow]")
        return

    # Add rows
    for proc in watcher_processes:
        name = proc.get("name", "unknown")
        # Strip prefix if present
        if name.startswith("fte-watcher-"):
            name = name[len("fte-watcher-"):]

        pm2_env = proc.get("pm2_env", {})
        monit = proc.get("monit", {})

        status = pm2_env.get("status", "unknown")
        pid = str(proc.get("pid", "-"))

        # Calculate uptime
        uptime_ms = pm2_env.get("pm_uptime", 0)
        uptime = format_uptime(uptime_ms)

        restarts = str(pm2_env.get("restart_time", 0))

        # CPU and memory
        cpu = f"{monit.get('cpu', 0)}%"
        memory_bytes = monit.get('memory', 0)
        memory_mb = memory_bytes / (1024 * 1024) if memory_bytes else 0
        memory = f"{memory_mb:.1f}MB"

        # Color code status
        if status == "online":
            status_colored = "[green]online[/green]"
        elif status == "stopped":
            status_colored = "[yellow]stopped[/yellow]"
        else:
            status_colored = f"[red]{status}[/red]"

        table.add_row(
            name,
            status_colored,
            pid,
            uptime,
            restarts,
            cpu,
            memory,
        )

    console.print(table)


def get_watcher_logs(name: str, tail: int = 50, follow: bool = False) -> None:
    """
    Display watcher logs using PM2.

    Args:
        name: Watcher name
        tail: Number of lines to display
        follow: Whether to follow logs in real-time

    Raises:
        WatcherValidationError: If watcher name is invalid
        PM2NotFoundError: If PM2 is not installed
        WatcherNotFoundError: If watcher is not found
        CLIError: If PM2 logs command fails
    """
    validate_watcher_name(name)

    if not check_pm2_installed():
        raise PM2NotFoundError(
            "PM2 is not installed. Install with: npm install -g pm2"
        )

    # Check if watcher exists
    existing = get_watcher_process(name)
    if not existing:
        raise WatcherNotFoundError(
            f"Watcher '{name}' is not running. Start it with: fte watcher start {name}"
        )

    # Build PM2 logs command
    cmd = ["pm2", "logs", f"fte-watcher-{name}", "--lines", str(tail)]

    if not follow:
        cmd.append("--nostream")

    try:
        if follow:
            # For follow mode, stream directly to terminal
            display_info(f"Following logs for '{name}' watcher (Ctrl+C to exit)...\n")
            subprocess.run(cmd)
        else:
            # For non-follow, capture and display
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                raise CLIError(f"Failed to get logs: {result.stderr}")

            # Display logs
            console.print(result.stdout)

    except subprocess.TimeoutExpired:
        raise CLIError(f"PM2 logs command timed out for watcher '{name}'")
    except KeyboardInterrupt:
        display_info("\nStopped following logs")
    except Exception as e:
        raise CLIError(f"Failed to get logs: {e}")


# CLI Commands

@click.group(name="watcher")
def watcher_group():
    """Watcher lifecycle management commands"""
    pass


@watcher_group.command(name="start")
@click.argument("name")
@click.pass_context
def watcher_start_command(ctx: click.Context, name: str):
    """
    Start watcher daemon.

    Launches a watcher daemon using PM2 process manager. The watcher will
    monitor the specified source for new tasks.

    Valid watchers: gmail, whatsapp, filesystem

    Examples:
        fte watcher start gmail
        fte watcher start filesystem
    """
    try:
        display_info(f"Starting '{name}' watcher...")

        start_watcher_pm2(name)

        display_success(f"\n✓ Watcher '{name}' started successfully")
        display_info(f"View status: fte watcher status")
        display_info(f"View logs: fte watcher logs {name}")

    except (WatcherValidationError, PM2NotFoundError, WatcherNotFoundError, CLIError) as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@watcher_group.command(name="stop")
@click.argument("name")
@click.pass_context
def watcher_stop_command(ctx: click.Context, name: str):
    """
    Stop watcher daemon.

    Gracefully stops a running watcher daemon and removes it from PM2.

    Examples:
        fte watcher stop gmail
        fte watcher stop filesystem
    """
    try:
        display_info(f"Stopping '{name}' watcher...")

        stop_watcher_pm2(name)

        display_success(f"\n✓ Watcher '{name}' stopped successfully")

    except (WatcherValidationError, PM2NotFoundError, WatcherNotFoundError, CLIError) as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@watcher_group.command(name="status")
@click.pass_context
def watcher_status_command(ctx: click.Context):
    """
    Show watcher status.

    Displays status of all watchers including state (running/stopped),
    PID, uptime, restart count, and resource usage.

    Examples:
        fte watcher status
    """
    try:
        display_info("Retrieving watcher status...")

        processes = get_pm2_list()

        console.print()  # Blank line
        display_watcher_status(processes)

    except (PM2NotFoundError, CLIError) as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@watcher_group.command(name="logs")
@click.argument("name")
@click.option(
    "--tail",
    "-n",
    default=50,
    type=int,
    help="Number of lines to display (default: 50)",
)
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Follow log output in real-time",
)
@click.pass_context
def watcher_logs_command(ctx: click.Context, name: str, tail: int, follow: bool):
    """
    Display watcher logs.

    Shows log output from a running watcher. Use --follow to stream
    logs in real-time.

    Examples:
        fte watcher logs gmail --tail 100
        fte watcher logs filesystem --follow
    """
    try:
        get_watcher_logs(name, tail=tail, follow=follow)

    except (WatcherValidationError, PM2NotFoundError, WatcherNotFoundError, CLIError) as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)

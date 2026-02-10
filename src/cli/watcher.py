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

from .checkpoint import get_checkpoint_manager
from .config import get_config
from .errors import (
    CLIError,
    PM2NotFoundError,
    WatcherNotFoundError,
    WatcherValidationError,
)
from .utils import (
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
        raise PM2NotFoundError("PM2 is not installed. Install with: npm install -g pm2")

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
        raise PM2NotFoundError("PM2 is not installed. Install with: npm install -g pm2")

    # Check if already running
    existing = get_watcher_process(name)
    if existing and existing.get("pm2_env", {}).get("status") == "online":
        display_warning(f"Watcher '{name}' is already running")
        return

    # Path to watcher script
    script_path = Path.cwd() / "scripts" / "run_watcher.py"

    if not script_path.exists():
        raise WatcherNotFoundError(f"Watcher script not found: {script_path}")

    # Get configuration
    config = get_config()
    vault_path = config.vault.default_path

    # Start with PM2
    try:
        result = subprocess.run(
            [
                "pm2",
                "start",
                str(script_path),
                "--name",
                f"fte-watcher-{name}",
                "--interpreter",
                "python3",
                "--",  # Arguments after this go to the script
                name,  # Watcher type (gmail, filesystem, whatsapp)
                "--vault-path",
                vault_path,
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
        raise PM2NotFoundError("PM2 is not installed. Install with: npm install -g pm2")

    # Check if running
    existing = get_watcher_process(name)
    if not existing:
        raise WatcherNotFoundError(f"Watcher '{name}' is not running")

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
            name = name[len("fte-watcher-") :]

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
        memory_bytes = monit.get("memory", 0)
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
        raise PM2NotFoundError("PM2 is not installed. Install with: npm install -g pm2")

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

    except (
        WatcherValidationError,
        PM2NotFoundError,
        WatcherNotFoundError,
        CLIError,
    ) as e:
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

    except (
        WatcherValidationError,
        PM2NotFoundError,
        WatcherNotFoundError,
        CLIError,
    ) as e:
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

    except (
        WatcherValidationError,
        PM2NotFoundError,
        WatcherNotFoundError,
        CLIError,
    ) as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@watcher_group.command(name="run")
@click.argument("name")
@click.option(
    "--vault-path",
    "-v",
    type=click.Path(exists=False),
    default=None,
    help="Path to vault (default: from config)",
)
@click.option(
    "--watch-path",
    "-w",
    type=click.Path(exists=False),
    default=None,
    help="Path to watch (filesystem watcher only)",
)
@click.pass_context
def watcher_run_command(
    ctx: click.Context,
    name: str,
    vault_path: Optional[str],
    watch_path: Optional[str],
):
    """
    Run watcher directly (without PM2).

    Runs a watcher in the foreground for testing and debugging.
    Press Ctrl+C to stop.

    Examples:
        fte watcher run filesystem --watch-path ./Input_Documents
        fte watcher run gmail
    """
    try:
        validate_watcher_name(name)

        # Get configuration
        config = get_config()
        vault = Path(vault_path) if vault_path else Path(config.vault.default_path)

        display_info(f"Starting '{name}' watcher in foreground mode...")
        display_info(f"Vault path: {vault}")
        display_info("Press Ctrl+C to stop\n")

        if name == "filesystem":
            from src.watchers.filesystem_watcher import FileSystemWatcher

            watch = Path(watch_path) if watch_path else Path("./Input_Documents")
            display_info(f"Watch path: {watch}")

            watcher = FileSystemWatcher(vault_path=vault, watch_path=watch)
            watcher.run()

        elif name == "gmail":
            from src.watchers.gmail_watcher import GmailWatcher

            credentials = Path("~/.credentials/gmail_credentials.json")
            display_info(f"Credentials: {credentials}")

            watcher = GmailWatcher(vault_path=vault, credentials_file=credentials)
            watcher.run()

        elif name == "whatsapp":
            from src.watchers.whatsapp_watcher import WhatsAppWatcher

            import os

            port = int(os.environ.get("WHATSAPP_PORT", "5000"))
            verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")

            if not verify_token:
                display_error("No verify token configured")
                display_info("Set WHATSAPP_VERIFY_TOKEN environment variable")
                ctx.exit(1)

            display_info(f"Webhook port: {port}")
            display_info(f"Verify token: {'*' * len(verify_token)}")

            watcher = WhatsAppWatcher(
                vault_path=vault,
                verify_token=verify_token,
                port=port,
            )
            watcher.run()

    except KeyboardInterrupt:
        display_info("\nWatcher stopped")
    except ImportError as e:
        display_error(f"Missing dependencies: {e}")
        display_info("Install with: pip install .[watchers]")
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@watcher_group.command(name="test")
@click.argument("name")
@click.pass_context
def watcher_test_command(ctx: click.Context, name: str):
    """
    Test watcher connectivity and configuration.

    Verifies that the watcher can connect to its data source and
    the vault is accessible.

    Examples:
        fte watcher test gmail
        fte watcher test filesystem
    """
    try:
        validate_watcher_name(name)

        config = get_config()
        vault_path = Path(config.vault.default_path)

        display_info(f"Testing '{name}' watcher...\n")

        # Check vault
        display_info("Checking vault...")
        if vault_path.exists():
            display_success(f"  ✓ Vault exists: {vault_path}")
        else:
            display_warning(f"  ! Vault not found: {vault_path}")

        inbox_path = vault_path / "Inbox"
        if inbox_path.exists():
            display_success(f"  ✓ Inbox folder exists")
        else:
            display_warning(f"  ! Inbox folder not found, will be created")

        if name == "filesystem":
            from src.watchers.filesystem_watcher import FileSystemWatcher

            watch_path = Path("./Input_Documents")
            display_info(f"\nChecking filesystem watcher...")

            if watch_path.exists():
                display_success(f"  ✓ Watch path exists: {watch_path}")
            else:
                display_warning(f"  ! Watch path not found: {watch_path}")

            # Check watchdog
            try:
                from watchdog.observers import Observer

                display_success("  ✓ watchdog library installed")
            except ImportError:
                display_error("  ✗ watchdog library not installed")
                display_info("    Install with: pip install watchdog")

            display_success(f"\n✓ Filesystem watcher ready")

        elif name == "gmail":
            display_info(f"\nChecking Gmail watcher...")

            # Check Google API libraries
            try:
                from google.oauth2.credentials import Credentials

                display_success("  ✓ Google API libraries installed")
            except ImportError:
                display_error("  ✗ Google API libraries not installed")
                display_info("    Install with: pip install .[gmail]")
                ctx.exit(1)

            # Check credentials file
            credentials_path = Path(
                "~/.credentials/gmail_credentials.json"
            ).expanduser()

            if credentials_path.exists():
                display_success(f"  ✓ Credentials file exists: {credentials_path}")
            else:
                display_warning(f"  ! Credentials file not found: {credentials_path}")
                display_info("    Download from Google Cloud Console")

            # Check token
            token_path = credentials_path.parent / "gmail_token.json"
            if token_path.exists():
                display_success(f"  ✓ OAuth token exists (may need refresh)")
            else:
                display_info(
                    f"  i OAuth token not found, will prompt for authorization"
                )

            display_success(f"\n✓ Gmail watcher configuration checked")

        elif name == "whatsapp":
            display_info(f"\nChecking WhatsApp watcher...")

            # Check Flask
            try:
                from flask import Flask

                display_success("  ✓ Flask library installed")
            except ImportError:
                display_error("  ✗ Flask library not installed")
                display_info("    Install with: pip install flask")

            # Check verify token
            import os

            verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
            if verify_token:
                display_success(f"  ✓ Verify token configured")
            else:
                display_warning("  ! Verify token not configured")
                display_info("    Set WHATSAPP_VERIFY_TOKEN environment variable")

            # Check app secret
            app_secret = os.environ.get("WHATSAPP_APP_SECRET", "")
            if app_secret:
                display_success(f"  ✓ App secret configured")
            else:
                display_warning(
                    "  ! App secret not configured (signature verification disabled)"
                )
                display_info("    Set WHATSAPP_APP_SECRET environment variable")

            # Check access token (for media download)
            access_token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
            if access_token:
                display_success(f"  ✓ Access token configured (media download enabled)")
            else:
                display_info(
                    "  i Access token not configured (media download disabled)"
                )
                display_info("    Set WHATSAPP_ACCESS_TOKEN environment variable")

            port = int(os.environ.get("WHATSAPP_PORT", "5000"))
            display_info(f"  i Webhook port: {port}")

            display_success(f"\n✓ WhatsApp watcher configuration checked")

    except ImportError as e:
        display_error(f"Missing dependencies: {e}")
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)

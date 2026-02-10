"""
FTE Status Command

Displays comprehensive system status including vault health,
watcher states, MCP server health, and pending approvals.
"""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .checkpoint import get_checkpoint_manager
from .config import get_config
from .errors import VaultNotFoundError
from .utils import (
    display_error,
    display_info,
    display_panel,
    is_valid_vault,
    resolve_vault_path,
)

console = Console()


def check_vault_status(vault_path: Optional[Path] = None) -> Dict[str, any]:
    """
    Check vault status and folder structure.

    Args:
        vault_path: Optional vault path to check

    Returns:
        Dict with vault status information
    """
    try:
        if vault_path is None:
            vault_path = resolve_vault_path()

        status = {
            "path": str(vault_path),
            "exists": vault_path.exists(),
            "valid": False,
            "folders": {},
            "task_counts": {},
        }

        if not vault_path.exists():
            status["error"] = "Vault directory not found"
            return status

        # Check if valid vault
        status["valid"] = is_valid_vault(vault_path)

        if not status["valid"]:
            status["error"] = "Invalid vault (missing required folders)"
            return status

        # Check folder structure
        required_folders = [
            "Inbox",
            "Needs_Action",
            "In_Progress",
            "Done",
            "Approvals",
            "Briefings",
            "Attachments",
        ]

        for folder in required_folders:
            folder_path = vault_path / folder
            exists = folder_path.exists()
            status["folders"][folder] = exists

            # Count tasks (markdown files) in each folder
            if exists:
                task_files = list(folder_path.glob("*.md"))
                status["task_counts"][folder] = len(task_files)
            else:
                status["task_counts"][folder] = 0

        return status

    except Exception as e:
        return {
            "path": str(vault_path) if vault_path else "unknown",
            "exists": False,
            "valid": False,
            "error": str(e),
        }


def check_watcher_status() -> Dict[str, Dict[str, any]]:
    """
    Check status of all watchers using checkpoint data.

    Returns:
        Dict with watcher status information
    """
    checkpoint_manager = get_checkpoint_manager()
    checkpoint = checkpoint_manager.get()

    watchers = {}
    for watcher_name, watcher_data in checkpoint.watchers.items():
        watchers[watcher_name] = {
            "status": watcher_data.status,
            "pid": watcher_data.pid,
            "uptime": watcher_data.uptime,
            "last_start": watcher_data.last_start,
            "last_stop": watcher_data.last_stop,
        }

    # Try to get real-time PM2 status if available
    try:
        result = subprocess.run(
            ["pm2", "jlist"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            pm2_processes = json.loads(result.stdout)
            for process in pm2_processes:
                process_name = process.get("name", "")
                if "watcher" in process_name.lower():
                    # Extract watcher name (e.g., "gmail-watcher" -> "gmail")
                    watcher_name = process_name.replace("-watcher", "").replace(
                        "_watcher", ""
                    )
                    if watcher_name in watchers:
                        watchers[watcher_name]["status"] = process.get(
                            "pm2_env", {}
                        ).get("status", "unknown")
                        watchers[watcher_name]["pid"] = process.get("pid")
                        watchers[watcher_name]["pm2_available"] = True

    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        # PM2 not available or error - use checkpoint data only
        pass

    return watchers


def check_mcp_status() -> Dict[str, Dict[str, any]]:
    """
    Check MCP server health status.

    Returns:
        Dict with MCP server status information
    """
    checkpoint_manager = get_checkpoint_manager()
    checkpoint = checkpoint_manager.get()

    mcp_status = {
        "registry_loaded": checkpoint.mcp_servers.registry_loaded,
        "last_health_check": checkpoint.mcp_servers.last_health_check,
        "servers": [],
    }

    # Load MCP server registry if available
    config = get_config()
    project_root = Path(__file__).parent.parent.parent
    registry_path = project_root / config.mcp.registry_file

    if registry_path.exists():
        try:
            import yaml

            with open(registry_path, "r") as f:
                registry_data = yaml.safe_load(f)

            if registry_data and "servers" in registry_data:
                for server in registry_data["servers"]:
                    server_info = {
                        "name": server.get("name", "unknown"),
                        "url": server.get("url", "unknown"),
                        "status": "unknown",
                        "available": False,
                    }
                    mcp_status["servers"].append(server_info)
                    mcp_status["registry_loaded"] = True

        except Exception:
            pass

    return mcp_status


def check_approval_status(vault_path: Optional[Path] = None) -> Dict[str, any]:
    """
    Check pending approvals status.

    Args:
        vault_path: Optional vault path

    Returns:
        Dict with approval status information
    """
    try:
        if vault_path is None:
            vault_path = resolve_vault_path()

        approvals_path = vault_path / "Approvals"

        if not approvals_path.exists():
            return {"count": 0, "approvals": []}

        # Count pending approval files
        approval_files = list(approvals_path.glob("*.md"))
        pending_approvals = []

        for approval_file in approval_files:
            try:
                # Quick parse to check if pending
                content = approval_file.read_text()
                if "approval_status: pending" in content:
                    pending_approvals.append(approval_file.name)
            except Exception:
                continue

        return {
            "count": len(pending_approvals),
            "approvals": pending_approvals,
        }

    except Exception:
        return {"count": 0, "approvals": [], "error": "Unable to check approvals"}


def display_status_overview(
    vault_status: Dict,
    watcher_status: Dict,
    mcp_status: Dict,
    approval_status: Dict,
) -> None:
    """
    Display comprehensive status overview with Rich formatting.

    Args:
        vault_status: Vault status information
        watcher_status: Watcher status information
        mcp_status: MCP status information
        approval_status: Approval status information
    """
    # Vault Status Panel
    vault_content = []

    if vault_status.get("valid"):
        vault_content.append(f"[green]✓[/green] Path: {vault_status['path']}")
        vault_content.append(f"[green]✓[/green] Status: Valid")

        # Task counts
        task_counts = vault_status.get("task_counts", {})
        vault_content.append("\n[bold]Task Counts:[/bold]")
        for folder, count in task_counts.items():
            vault_content.append(f"  {folder}: {count}")
    else:
        vault_content.append(
            f"[red]✗[/red] Path: {vault_status.get('path', 'unknown')}"
        )
        vault_content.append(
            f"[red]✗[/red] Status: {vault_status.get('error', 'Invalid')}"
        )
        vault_content.append("\n[yellow]→[/yellow] Run 'fte vault init' to initialize")

    console.print(
        Panel(
            "\n".join(vault_content),
            title="[bold blue]Vault Status[/bold blue]",
            border_style="blue",
        )
    )

    # Watcher Status Table
    watcher_table = Table(
        title="Watcher Status", show_header=True, header_style="bold cyan"
    )
    watcher_table.add_column("Watcher", style="cyan")
    watcher_table.add_column("Status", style="white")
    watcher_table.add_column("PID", style="white")
    watcher_table.add_column("Last Start", style="white")

    for watcher_name, watcher_info in watcher_status.items():
        status = watcher_info["status"]
        pid = str(watcher_info["pid"]) if watcher_info["pid"] else "-"
        last_start = watcher_info["last_start"] or "-"

        # Color code status
        if status == "running":
            status_display = f"[green]●[/green] {status}"
        elif status == "stopped":
            status_display = f"[red]●[/red] {status}"
        else:
            status_display = f"[yellow]●[/yellow] {status}"

        watcher_table.add_row(
            watcher_name.capitalize(),
            status_display,
            pid,
            last_start[:19] if last_start != "-" else "-",
        )

    console.print(watcher_table)

    # MCP Server Status Table
    mcp_table = Table(
        title="MCP Server Status", show_header=True, header_style="bold magenta"
    )
    mcp_table.add_column("Server", style="magenta")
    mcp_table.add_column("URL", style="white")
    mcp_table.add_column("Status", style="white")

    if mcp_status["servers"]:
        for server in mcp_status["servers"]:
            status = server["status"]
            if status == "healthy":
                status_display = f"[green]✓[/green] {status}"
            else:
                status_display = f"[yellow]?[/yellow] {status}"

            mcp_table.add_row(server["name"], server["url"], status_display)
    else:
        mcp_table.add_row("[dim]No servers configured[/dim]", "-", "-")

    console.print(mcp_table)

    # Approval Status Panel
    approval_content = []
    approval_count = approval_status.get("count", 0)

    if approval_count > 0:
        approval_content.append(
            f"[yellow]⚠[/yellow] Pending Approvals: [bold]{approval_count}[/bold]"
        )
        approval_content.append(
            "\n[yellow]→[/yellow] Run 'fte approval pending' to view"
        )
    else:
        approval_content.append(f"[green]✓[/green] No pending approvals")

    console.print(
        Panel(
            "\n".join(approval_content),
            title="[bold yellow]Approvals[/bold yellow]",
            border_style="yellow",
        )
    )


@click.command(name="status")
@click.option(
    "--vault-path",
    type=click.Path(path_type=Path),
    help="Path to AI Employee vault (overrides config)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output status as JSON",
)
@click.pass_context
def status_command(ctx: click.Context, vault_path: Optional[Path], output_json: bool):
    """
    Show comprehensive system status.

    Displays vault health, watcher states, MCP server status,
    and pending approvals in a formatted overview.

    \b
    Examples:
      fte status                      # Show full status
      fte status --json               # JSON output
      fte status --vault-path ~/vault # Check specific vault
    """
    try:
        # Gather status information in parallel for better performance
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all checks concurrently
            future_vault = executor.submit(check_vault_status, vault_path)
            future_watcher = executor.submit(check_watcher_status)
            future_mcp = executor.submit(check_mcp_status)
            future_approval = executor.submit(check_approval_status, vault_path)

            # Gather results
            vault_status = future_vault.result()
            watcher_status = future_watcher.result()
            mcp_status = future_mcp.result()
            approval_status = future_approval.result()

        # Output format
        if output_json:
            import json

            status_data = {
                "vault": vault_status,
                "watchers": watcher_status,
                "mcp": mcp_status,
                "approvals": approval_status,
            }
            console.print_json(json.dumps(status_data, indent=2))
        else:
            display_status_overview(
                vault_status, watcher_status, mcp_status, approval_status
            )

        # Exit with error if vault is invalid
        if not vault_status.get("valid"):
            ctx.exit(1)

    except VaultNotFoundError as e:
        display_error(e, verbose=ctx.obj.get("verbose", False))
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False))
        ctx.exit(1)

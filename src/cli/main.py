"""
Main CLI Entry Point

Unified CLI tool for Digital FTE management.
Provides commands for vault, watcher, MCP, approval, and briefing operations.
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich import print as rprint
from rich.console import Console

from cli.checkpoint import get_checkpoint_manager
from cli.config import get_config
from cli.errors import CLIError, handle_cli_error
from cli.logging_setup import (
    disable_colors,
    setup_logging,
    setup_quiet_mode,
    setup_verbose_mode,
)


console = Console()


# Version from pyproject.toml
__version__ = "0.1.0"


@click.group()
@click.version_option(version=__version__, prog_name="fte")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging (DEBUG level)",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Enable quiet mode (ERROR level only)",
)
@click.option(
    "--no-color",
    is_flag=True,
    help="Disable colored output (for CI/CD environments)",
)
@click.option(
    "--vault-path",
    type=click.Path(exists=False, path_type=Path),
    help="Path to AI Employee vault (overrides config)",
)
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: bool,
    quiet: bool,
    no_color: bool,
    vault_path: Optional[Path]
):
    """
    FTE - Digital Full-Time Employee CLI

    Unified command-line interface for managing the Digital FTE system.

    \b
    Commands:
      - vault      Vault management (init, status, approve, reject)
      - watcher    Watcher lifecycle (start, stop, status, logs)
      - mcp        MCP server management (list, add, test, tools)
      - approval   Approval workflow (pending, review)
      - briefing   CEO briefing (generate, view)
      - status     System status overview

    \b
    Examples:
      fte --version                    # Show version
      fte status                       # Show system status
      fte vault init                   # Initialize vault
      fte watcher start gmail          # Start Gmail watcher
      fte mcp list                     # List MCP servers
      fte approval pending             # List pending approvals

    \b
    For more information on a specific command:
      fte <command> --help
    """
    # Initialize logging
    try:
        setup_logging()

        if no_color:
            disable_colors()

        if verbose:
            setup_verbose_mode()
        elif quiet:
            setup_quiet_mode()

        # Store global options in context
        ctx.ensure_object(dict)
        ctx.obj["verbose"] = verbose
        ctx.obj["quiet"] = quiet
        ctx.obj["no_color"] = no_color
        ctx.obj["vault_path"] = vault_path

        # Track command usage
        checkpoint_manager = get_checkpoint_manager()
        command_name = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "fte"
        checkpoint_manager.update_usage(command_name)

    except Exception as e:
        console.print(f"[red]Initialization error:[/red] {e}")
        sys.exit(1)


# Import init command from cli.init module
from cli.init import init_command
cli.add_command(init_command)


# Import status command from cli.status module
from cli.status import status_command
cli.add_command(status_command)


# Import vault command group from cli.vault module
from cli.vault import vault_group
cli.add_command(vault_group)

# Import watcher command group from cli.watcher module
from cli.watcher import watcher_group
cli.add_command(watcher_group)

# Import mcp command group from cli.mcp module
from cli.mcp import mcp_group
cli.add_command(mcp_group)

# Import approval command group from cli.approval module
from cli.approval import approval_group
cli.add_command(approval_group)

# Import briefing command group from cli.briefing module
from cli.briefing import briefing_group
cli.add_command(briefing_group)

# Import tdd command group from cli.tdd module
from cli.tdd import tdd_group
cli.add_command(tdd_group)

# Import security command group from cli.security module
from cli.security import security_group
cli.add_command(security_group)

# Import orchestrator command group from cli.orchestrator module
from cli.orchestrator import orchestrator_group
cli.add_command(orchestrator_group)

# Import skill command group from cli.skill module
from cli.skill import skill_group
cli.add_command(skill_group)


def main():
    """Main entry point for CLI"""
    try:
        cli(obj={})
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

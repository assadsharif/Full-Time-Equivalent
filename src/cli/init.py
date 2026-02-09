"""
FTE Init Command

Initializes FTE configuration including vault path setup,
configuration file creation, and checkpoint initialization.
"""

from pathlib import Path
from typing import Optional

import click
from rich.prompt import Prompt

from cli.checkpoint import get_checkpoint_manager
from cli.config import get_config
from cli.errors import ConfigError
from cli.utils import (
    display_error,
    display_info,
    display_success,
    display_warning,
    expand_path,
    is_valid_vault,
)


def init_configuration(vault_path: Optional[str] = None, force: bool = False) -> None:
    """
    Initialize FTE CLI configuration.

    Args:
        vault_path: Optional explicit vault path
        force: Force re-initialization even if config exists
    """
    display_info("Initializing FTE CLI configuration...")

    # Step 1: Check if configuration exists
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "config" / "cli.yaml"
    checkpoint_path = project_root / ".fte" / "cli.checkpoint.json"

    if config_path.exists() and not force:
        display_success(f"Configuration already exists: {config_path}")
    else:
        if force:
            display_info("Force flag set - recreating configuration")
        else:
            display_info("Configuration file not found. Using defaults.")

    # Step 2: Prompt for vault path if not provided
    if vault_path is None:
        config = get_config()
        default_path = config.vault.default_path

        display_info(f"\nVault Configuration:")
        display_info(f"Default vault path: {default_path}")

        use_default = Prompt.ask(
            "Use default vault path?", choices=["y", "n"], default="y"
        )

        if use_default.lower() == "n":
            vault_path = Prompt.ask("Enter vault path", default=default_path)
        else:
            vault_path = default_path

    # Step 3: Validate vault path
    vault_path_resolved = expand_path(vault_path)

    display_info(f"\nValidating vault path: {vault_path_resolved}")

    if not vault_path_resolved.exists():
        display_warning(f"Vault directory does not exist: {vault_path_resolved}")
        create_vault = Prompt.ask(
            "Would you like to create it?", choices=["y", "n"], default="n"
        )

        if create_vault.lower() == "y":
            display_info("To create vault structure, run: fte vault init")
        else:
            display_info("Vault path saved, but not validated.")
    elif not is_valid_vault(vault_path_resolved):
        display_warning(
            f"Directory exists but is not a valid vault (missing required folders)."
        )
        display_info("To initialize vault structure, run: fte vault init")
    else:
        display_success(f"Valid vault found at: {vault_path_resolved}")

    # Step 4: Initialize checkpoint
    if checkpoint_path.exists() and not force:
        display_success(f"Checkpoint file exists: {checkpoint_path}")
    else:
        display_info(f"Creating checkpoint file: {checkpoint_path}")
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        checkpoint_manager = get_checkpoint_manager()
        checkpoint_manager.update_vault(
            path=str(vault_path_resolved),
            initialized=is_valid_vault(vault_path_resolved),
        )

        display_success("Checkpoint file created")

    # Step 5: Display configuration summary
    display_info("\n" + "=" * 60)
    display_success("FTE CLI initialized successfully!")
    display_info("=" * 60)

    display_info("\nConfiguration:")
    display_info(f"  Config file: {config_path}")
    display_info(f"  Checkpoint: {checkpoint_path}")
    display_info(f"  Vault path: {vault_path_resolved}")

    display_info("\nNext steps:")
    if not is_valid_vault(vault_path_resolved):
        display_info("  1. Run 'fte vault init' to create vault structure")
        display_info("  2. Run 'fte status' to check system status")
    else:
        display_info("  1. Run 'fte status' to check system status")
        display_info("  2. Configure watchers with 'fte watcher start <name>'")


@click.command(name="init")
@click.option(
    "--vault-path",
    type=str,
    help="Path to AI Employee vault",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-initialization even if config exists",
)
@click.pass_context
def init_command(ctx: click.Context, vault_path: Optional[str], force: bool):
    """
    Initialize FTE configuration.

    Creates default configuration files and sets up vault path.

    \b
    Examples:
      fte init                           # Interactive setup
      fte init --vault-path ~/MyVault   # Specify vault path
      fte init --force                   # Force re-initialization
    """
    try:
        init_configuration(vault_path=vault_path, force=force)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False))
        raise click.Abort()

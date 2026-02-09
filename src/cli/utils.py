"""
CLI Utilities

Utility functions for CLI operations including path resolution,
vault detection, and error formatting.
"""

import os
from pathlib import Path
from typing import Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from cli.config import get_config

console = Console()


def resolve_vault_path(vault_path: Optional[str] = None) -> Path:
    """
    Resolve vault path from CLI argument, config, or auto-detection.

    Args:
        vault_path: Optional explicit vault path

    Returns:
        Resolved Path to vault

    Priority:
    1. Explicit --vault-path argument
    2. FTE_VAULT_PATH environment variable
    3. Config default_path
    4. Auto-detection (search for AI_Employee_Vault in common locations)
    """
    # Priority 1: Explicit argument
    if vault_path:
        return Path(vault_path).expanduser().resolve()

    # Priority 2: Environment variable
    env_path = os.getenv("FTE_VAULT_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()

    # Priority 3: Config default
    config = get_config()
    config_path = Path(config.vault.default_path).expanduser().resolve()

    if config_path.exists():
        return config_path

    # Priority 4: Auto-detection
    if config.vault.auto_detect:
        detected = auto_detect_vault()
        if detected:
            return detected

    # Fallback to config default (even if doesn't exist)
    return config_path


def auto_detect_vault() -> Optional[Path]:
    """
    Auto-detect vault location by searching common paths.

    Returns:
        Path to vault if found, None otherwise

    Search order:
    1. ~/AI_Employee_Vault
    2. ~/Documents/AI_Employee_Vault
    3. ~/Obsidian/AI_Employee_Vault
    4. Current directory/AI_Employee_Vault
    """
    search_paths = [
        Path.home() / "AI_Employee_Vault",
        Path.home() / "Documents" / "AI_Employee_Vault",
        Path.home() / "Obsidian" / "AI_Employee_Vault",
        Path.cwd() / "AI_Employee_Vault",
    ]

    for path in search_paths:
        if is_valid_vault(path):
            return path

    return None


def is_valid_vault(path: Path) -> bool:
    """
    Check if path is a valid AI Employee vault.

    Args:
        path: Path to check

    Returns:
        True if valid vault, False otherwise

    A valid vault must have:
    - Directory exists
    - Contains core folders: Inbox, Needs_Action, Done
    """
    if not path.exists() or not path.is_dir():
        return False

    # Check for core folders
    required_folders = ["Inbox", "Needs_Action", "Done"]
    for folder in required_folders:
        if not (path / folder).exists():
            return False

    return True


def validate_vault_or_error(vault_path: Path) -> None:
    """
    Validate vault path and raise error if invalid.

    Args:
        vault_path: Path to validate

    Raises:
        VaultNotFoundError: Vault doesn't exist or is invalid
    """
    from cli.errors import VaultNotFoundError

    if not is_valid_vault(vault_path):
        raise VaultNotFoundError(
            f"Vault not found or invalid: {vault_path}\n"
            f"Run 'fte vault init' to create a new vault."
        )


def format_error(error: Exception, verbose: bool = False) -> str:
    """
    Format error message for CLI display.

    Args:
        error: Exception to format
        verbose: Include traceback in output

    Returns:
        Formatted error string
    """
    error_type = type(error).__name__
    error_msg = str(error)

    if verbose:
        import traceback

        tb = traceback.format_exc()
        return f"[red bold]{error_type}:[/red bold] {error_msg}\n\n{tb}"
    else:
        return f"[red bold]Error:[/red bold] {error_msg}"


def display_error(error: Exception, verbose: bool = False) -> None:
    """
    Display formatted error to console.

    Args:
        error: Exception to display
        verbose: Include traceback in output
    """
    console.print(format_error(error, verbose))


def display_success(message: str) -> None:
    """
    Display success message to console.

    Args:
        message: Success message to display
    """
    console.print(f"[green]✓[/green] {message}")


def display_warning(message: str) -> None:
    """
    Display warning message to console.

    Args:
        message: Warning message to display
    """
    console.print(f"[yellow]⚠[/yellow] {message}")


def display_info(message: str) -> None:
    """
    Display info message to console.

    Args:
        message: Info message to display
    """
    console.print(f"[blue]ℹ[/blue] {message}")


def display_panel(
    content: str, title: Optional[str] = None, border_style: str = "blue"
) -> None:
    """
    Display content in a Rich panel.

    Args:
        content: Content to display
        title: Optional panel title
        border_style: Border color (blue, green, red, yellow)
    """
    console.print(Panel(content, title=title, border_style=border_style))


def confirm_action(prompt: str, default: bool = False) -> bool:
    """
    Prompt user for yes/no confirmation.

    Args:
        prompt: Confirmation prompt
        default: Default value if user just presses Enter

    Returns:
        True if user confirms, False otherwise
    """
    from rich.prompt import Confirm

    return Confirm.ask(prompt, default=default)


def get_project_root() -> Path:
    """
    Get project root directory.

    Returns:
        Path to project root
    """
    # Project root is 3 levels up from this file (src/cli/utils.py)
    return Path(__file__).parent.parent.parent


def get_checkpoint_path() -> Path:
    """
    Get path to CLI checkpoint file.

    Returns:
        Path to .fte/cli.checkpoint.json
    """
    return get_project_root() / ".fte" / "cli.checkpoint.json"


def expand_path(path: str) -> Path:
    """
    Expand user home and resolve path.

    Args:
        path: Path string (may contain ~)

    Returns:
        Resolved Path object
    """
    return Path(path).expanduser().resolve()


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def truncate_string(text: str, max_length: int = 80, suffix: str = "...") -> str:
    """
    Truncate string to max length with suffix.

    Args:
        text: String to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix

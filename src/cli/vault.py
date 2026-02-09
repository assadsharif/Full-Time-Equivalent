"""
Vault Management Commands

Commands for managing the AI Employee vault including initialization,
status checking, and approval workflow management.
"""

import hashlib
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

import click
import yaml
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from cli.checkpoint import get_checkpoint_manager
from cli.config import get_config
from cli.errors import (
    ApprovalIntegrityError,
    ApprovalInvalidNonceError,
    ApprovalNotFoundError,
    VaultNotFoundError,
)
from cli.utils import (
    display_error,
    display_info,
    display_success,
    display_warning,
    expand_path,
    is_valid_vault,
    resolve_vault_path,
)

console = Console()


def get_templates_dir() -> Path:
    """
    Resolve the .vault_templates directory relative to the repo root.

    Walks up from this file's location (src/cli/) to find the repo root
    containing .vault_templates/.

    Returns:
        Absolute path to .vault_templates/

    Raises:
        FileNotFoundError: If .vault_templates/ cannot be located
    """
    candidate = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = candidate.parent
        if (candidate / ".vault_templates").is_dir():
            return candidate / ".vault_templates"
    raise FileNotFoundError(
        ".vault_templates/ not found. Ensure the repo root contains this directory."
    )


def create_vault_structure(vault_path: Path) -> None:
    """
    Create vault folder structure from .vault_templates/.

    Copies the canonical folder layout, Obsidian config, .gitignore,
    and Templates/ from the repo's .vault_templates/ directory, then
    generates Dashboard.md and Company_Handbook.md with live timestamps.

    Args:
        vault_path: Path to vault root
    """
    templates_dir = get_templates_dir()
    vault_path.mkdir(parents=True, exist_ok=True)

    # Copy core folders (each contains a .gitkeep)
    folders_src = templates_dir / "folders"
    for folder in folders_src.iterdir():
        if folder.is_dir():
            dest = vault_path / folder.name
            dest.mkdir(exist_ok=True)
            # Copy .gitkeep if present
            gitkeep = folder / ".gitkeep"
            if gitkeep.exists():
                shutil.copy2(gitkeep, dest / ".gitkeep")
            display_success(f"Created folder: {folder.name}")

    # Copy .obsidian/ config
    obsidian_src = templates_dir / ".obsidian"
    if obsidian_src.is_dir():
        obsidian_dest = vault_path / ".obsidian"
        shutil.copytree(obsidian_src, obsidian_dest, dirs_exist_ok=True)
        display_success("Created: .obsidian/ config")

    # Copy .gitignore
    gitignore_src = templates_dir / ".gitignore"
    if gitignore_src.exists():
        shutil.copy2(gitignore_src, vault_path / ".gitignore")
        display_success("Created: .gitignore")

    # Copy Templates/ (task_template.md, approval_template.md)
    templates_content_src = templates_dir / "Templates"
    if templates_content_src.is_dir():
        templates_dest = vault_path / "Templates"
        templates_dest.mkdir(exist_ok=True)
        for tmpl in templates_content_src.iterdir():
            if tmpl.is_file() and tmpl.name != ".gitkeep":
                shutil.copy2(tmpl, templates_dest / tmpl.name)
        display_success("Created: Templates/")

    # Generate Dashboard.md with live date
    dashboard_template = (templates_dir / "Dashboard.md").read_text()
    dashboard_content = dashboard_template.format(
        date=datetime.now().strftime("%Y-%m-%d"),
        inbox_count=0,
        needs_action_count=0,
        in_progress_count=0,
        done_count=0,
        approvals_count=0,
    )
    (vault_path / "Dashboard.md").write_text(dashboard_content)
    display_success("Created: Dashboard.md")

    # Generate Company_Handbook.md with live date
    handbook_template = (templates_dir / "Company_Handbook.md").read_text()
    handbook_content = handbook_template.format(
        date=datetime.now().strftime("%Y-%m-%d")
    )
    (vault_path / "Company_Handbook.md").write_text(handbook_content)
    display_success("Created: Company_Handbook.md")


def get_vault_statistics(vault_path: Path) -> Dict[str, int]:
    """
    Get task counts for all vault folders.

    Args:
        vault_path: Path to vault root

    Returns:
        Dict with folder names and task counts
    """
    folders = [
        "Inbox",
        "Needs_Action",
        "In_Progress",
        "Done",
        "Approvals",
        "Briefings",
        "Attachments",
    ]

    stats = {}
    for folder in folders:
        folder_path = vault_path / folder
        if folder_path.exists():
            # Count markdown files
            task_files = list(folder_path.glob("*.md"))
            stats[folder] = len(task_files)
        else:
            stats[folder] = 0

    return stats


def parse_approval_file(approval_path: Path) -> Dict:
    """
    Parse approval file and extract YAML frontmatter.

    Args:
        approval_path: Path to approval file

    Returns:
        Dict with approval data

    Raises:
        ApprovalNotFoundError: File not found
        ValueError: Invalid YAML
    """
    if not approval_path.exists():
        raise ApprovalNotFoundError(approval_path.name)

    content = approval_path.read_text()

    # Extract YAML frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid approval file format: {approval_path.name}")

    frontmatter_text = match.group(1)
    body_text = match.group(2)

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in approval file: {e}")

    return {
        "frontmatter": frontmatter,
        "body": body_text,
        "raw_content": content,
        "path": approval_path,
    }


def validate_nonce(approval_data: Dict) -> bool:
    """
    Validate approval nonce format.

    Args:
        approval_data: Parsed approval data

    Returns:
        True if nonce valid

    Raises:
        ApprovalInvalidNonceError: Invalid nonce
    """
    frontmatter = approval_data["frontmatter"]
    nonce = frontmatter.get("nonce")

    if not nonce:
        raise ApprovalInvalidNonceError(approval_data["path"].name)

    # Basic UUID format validation
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    if not re.match(uuid_pattern, str(nonce).lower()):
        raise ApprovalInvalidNonceError(approval_data["path"].name)

    return True


def compute_file_hash(content: str) -> str:
    """
    Compute SHA256 hash of file content.

    Args:
        content: File content

    Returns:
        Hex digest of SHA256 hash
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def verify_integrity(approval_data: Dict) -> bool:
    """
    Verify file integrity using stored hash.

    Args:
        approval_data: Parsed approval data

    Returns:
        True if integrity check passes

    Raises:
        ApprovalIntegrityError: If integrity check fails
    """
    frontmatter = approval_data["frontmatter"]
    body_text = approval_data.get("body", "")

    # Check required fields exist
    required_fields = [
        "task_id",
        "approval_id",
        "nonce",
        "action_type",
        "approval_status",
    ]
    for field in required_fields:
        if field not in frontmatter:
            raise ApprovalIntegrityError(approval_data["path"].name)

    # Verify integrity hash if present
    stored_hash = frontmatter.get("integrity_hash")
    if stored_hash:
        # Compute current hash of body content
        current_hash = compute_file_hash(body_text)

        # Compare hashes
        if stored_hash != current_hash:
            raise ApprovalIntegrityError(
                approval_data["path"].name,
                details=f"Hash mismatch: file has been modified",
            )
    else:
        # No hash stored - warn but don't fail for backward compatibility
        pass

    return True


def add_integrity_hash(file_path: Path) -> None:
    """
    Add integrity hash to a file's frontmatter.

    Args:
        file_path: Path to the file

    Raises:
        ValueError: If file format is invalid
    """
    content = file_path.read_text()

    # Extract frontmatter and body
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid file format: {file_path.name}")

    frontmatter_text = match.group(1)
    body_text = match.group(2)

    # Parse frontmatter
    frontmatter = yaml.safe_load(frontmatter_text)

    # Compute and store hash of body content
    body_hash = compute_file_hash(body_text)
    frontmatter["integrity_hash"] = body_hash

    # Write updated content
    updated_content = (
        f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n{body_text}"
    )
    file_path.write_text(updated_content)


def update_approval_status(
    approval_path: Path, status: str, reason: Optional[str] = None
) -> None:
    """
    Update approval file status.

    Args:
        approval_path: Path to approval file
        status: New status (approved, rejected)
        reason: Optional rejection reason
    """
    content = approval_path.read_text()

    # Extract and update frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        raise ValueError(f"Invalid approval file format")

    frontmatter_text = match.group(1)
    body_text = match.group(2)

    frontmatter = yaml.safe_load(frontmatter_text)
    frontmatter["approval_status"] = status
    frontmatter["reviewed_at"] = datetime.now(timezone.utc).isoformat() + "Z"

    if reason:
        frontmatter["rejection_reason"] = reason

    # Write updated content
    updated_content = (
        f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n{body_text}"
    )
    approval_path.write_text(updated_content)


# CLI Commands


@click.group(name="vault")
def vault_group():
    """Vault management commands"""
    pass


@vault_group.command(name="init")
@click.option(
    "--vault-path",
    type=click.Path(path_type=Path),
    help="Path to create vault (overrides config)",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing vault structure",
)
@click.pass_context
def vault_init_command(ctx: click.Context, vault_path: Optional[Path], force: bool):
    """
    Initialize vault folder structure.

    Creates all required folders and template files.

    \b
    Examples:
      fte vault init                    # Use config path
      fte vault init --vault-path ~/vault  # Custom path
      fte vault init --force            # Overwrite existing
    """
    try:
        # Resolve vault path
        if vault_path is None:
            vault_path = resolve_vault_path()
        else:
            vault_path = expand_path(str(vault_path))

        display_info(f"Initializing vault at: {vault_path}")

        # Check if vault already exists
        if is_valid_vault(vault_path) and not force:
            display_warning("Vault already exists and is valid.")
            if not click.confirm("Do you want to recreate it?"):
                display_info("Vault initialization cancelled.")
                return

        # Create vault structure
        create_vault_structure(vault_path)

        # Update checkpoint
        checkpoint_manager = get_checkpoint_manager()
        checkpoint_manager.update_vault(path=str(vault_path), initialized=True)

        display_success(f"\nVault initialized successfully at: {vault_path}")
        display_info("\nNext steps:")
        display_info("  1. Edit Company_Handbook.md to customize AI behavior")
        display_info("  2. Run 'fte status' to verify vault")
        display_info("  3. Start watchers: 'fte watcher start <name>'")

    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@vault_group.command(name="status")
@click.option(
    "--vault-path",
    type=click.Path(path_type=Path),
    help="Path to vault (overrides config)",
)
@click.pass_context
def vault_status_command(ctx: click.Context, vault_path: Optional[Path]):
    """
    Show detailed vault statistics.

    Displays task counts for all folders and vault health.

    \b
    Examples:
      fte vault status                  # Show vault stats
      fte vault status --vault-path ~/vault  # Check specific vault
    """
    try:
        # Resolve vault path
        if vault_path is None:
            vault_path = resolve_vault_path()
        else:
            vault_path = expand_path(str(vault_path))

        # Validate vault
        if not is_valid_vault(vault_path):
            raise VaultNotFoundError(
                f"Invalid vault at: {vault_path}\n"
                f"Run 'fte vault init' to create a valid vault."
            )

        display_info(f"Vault: {vault_path}\n")

        # Get statistics
        stats = get_vault_statistics(vault_path)

        # Create status table
        table = Table(
            title="Vault Statistics", show_header=True, header_style="bold cyan"
        )
        table.add_column("Folder", style="cyan", width=20)
        table.add_column("Task Count", style="white", justify="right")
        table.add_column("Status", style="white")

        for folder, count in stats.items():
            # Status indicator
            if count > 0:
                status = f"[green]●[/green] {count} tasks"
            else:
                status = "[dim]empty[/dim]"

            table.add_row(folder, str(count), status)

        console.print(table)

        # Summary
        total_tasks = sum(stats.values())
        display_info(f"\nTotal tasks: {total_tasks}")

        # Alerts
        if stats.get("Approvals", 0) > 0:
            display_warning(
                f"\n⚠ {stats['Approvals']} pending approvals - run 'fte approval pending'"
            )

        if stats.get("Needs_Action", 0) > 10:
            display_warning(
                f"\n⚠ {stats['Needs_Action']} tasks in Needs_Action - consider prioritizing"
            )

    except VaultNotFoundError as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@vault_group.command(name="approve")
@click.argument("approval_id")
@click.option(
    "--vault-path",
    type=click.Path(path_type=Path),
    help="Path to vault (overrides config)",
)
@click.pass_context
def vault_approve_command(
    ctx: click.Context, approval_id: str, vault_path: Optional[Path]
):
    """
    Approve a pending action.

    Validates nonce, checks integrity, and updates approval status.

    \b
    Examples:
      fte vault approve PAYMENT_Vendor_A_2026-01-28
      fte vault approve EMAIL_Client_B_2026-01-28
    """
    try:
        # Resolve vault path
        if vault_path is None:
            vault_path = resolve_vault_path()
        else:
            vault_path = expand_path(str(vault_path))

        # Validate vault
        if not is_valid_vault(vault_path):
            raise VaultNotFoundError(f"Invalid vault at: {vault_path}")

        # Find approval file
        approvals_dir = vault_path / "Approvals"
        approval_file = approvals_dir / f"{approval_id}.md"

        if not approval_file.exists():
            raise ApprovalNotFoundError(approval_id)

        display_info(f"Processing approval: {approval_id}")

        # Parse approval file
        approval_data = parse_approval_file(approval_file)

        # Validate nonce
        validate_nonce(approval_data)
        display_success("✓ Nonce validation passed")

        # Verify integrity
        verify_integrity(approval_data)
        display_success("✓ Integrity check passed")

        # Check if already processed
        status = approval_data["frontmatter"].get("approval_status")
        if status != "pending":
            display_warning(f"Approval already processed (status: {status})")
            return

        # Update status
        update_approval_status(approval_file, "approved")

        # Update checkpoint
        checkpoint_manager = get_checkpoint_manager()
        checkpoint_manager.update_approval(action="approve")

        display_success(f"\n✓ Approval '{approval_id}' approved successfully")

        # Log to audit trail (basic console output for now)
        display_info(f"Audit: Approved at {datetime.now(timezone.utc).isoformat()}Z")

    except (
        ApprovalNotFoundError,
        ApprovalInvalidNonceError,
        ApprovalIntegrityError,
    ) as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@vault_group.command(name="reject")
@click.argument("approval_id")
@click.option(
    "--vault-path",
    type=click.Path(path_type=Path),
    help="Path to vault (overrides config)",
)
@click.option(
    "--reason",
    "-r",
    help="Rejection reason",
)
@click.pass_context
def vault_reject_command(
    ctx: click.Context,
    approval_id: str,
    vault_path: Optional[Path],
    reason: Optional[str],
):
    """
    Reject a pending action.

    Validates nonce, checks integrity, and updates approval status.

    \b
    Examples:
      fte vault reject PAYMENT_Vendor_A_2026-01-28
      fte vault reject EMAIL_Client_B_2026-01-28 --reason "Incorrect amount"
    """
    try:
        # Resolve vault path
        if vault_path is None:
            vault_path = resolve_vault_path()
        else:
            vault_path = expand_path(str(vault_path))

        # Validate vault
        if not is_valid_vault(vault_path):
            raise VaultNotFoundError(f"Invalid vault at: {vault_path}")

        # Find approval file
        approvals_dir = vault_path / "Approvals"
        approval_file = approvals_dir / f"{approval_id}.md"

        if not approval_file.exists():
            raise ApprovalNotFoundError(approval_id)

        display_info(f"Processing rejection: {approval_id}")

        # Parse approval file
        approval_data = parse_approval_file(approval_file)

        # Validate nonce
        validate_nonce(approval_data)
        display_success("✓ Nonce validation passed")

        # Verify integrity
        verify_integrity(approval_data)
        display_success("✓ Integrity check passed")

        # Check if already processed
        status = approval_data["frontmatter"].get("approval_status")
        if status != "pending":
            display_warning(f"Approval already processed (status: {status})")
            return

        # Prompt for reason if not provided
        if reason is None:
            reason = Prompt.ask("Rejection reason")

        # Update status
        update_approval_status(approval_file, "rejected", reason=reason)

        # Update checkpoint
        checkpoint_manager = get_checkpoint_manager()
        checkpoint_manager.update_approval(action="reject")

        display_success(f"\n✓ Approval '{approval_id}' rejected successfully")
        display_info(f"Reason: {reason}")

        # Log to audit trail
        display_info(f"Audit: Rejected at {datetime.now(timezone.utc).isoformat()}Z")

    except (
        ApprovalNotFoundError,
        ApprovalInvalidNonceError,
        ApprovalIntegrityError,
    ) as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


def _find_validation_script(name: str) -> Path:
    """Locate a validation script relative to the repo root."""
    candidate = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = candidate.parent
        script = candidate / ".vault_schema" / "validation_scripts" / name
        if script.exists():
            return script
    raise FileNotFoundError(f"Validation script '{name}' not found")


@vault_group.command(name="validate")
@click.option(
    "--vault-path",
    type=click.Path(path_type=Path),
    help="Path to vault (overrides config)",
)
@click.option(
    "--state-only",
    is_flag=True,
    help="Run only state-transition validation",
)
@click.pass_context
def vault_validate_command(
    ctx: click.Context,
    vault_path: Optional[Path],
    state_only: bool,
):
    """
    Validate vault structure and state transitions.

    Runs the full vault validator and the state-transition validator
    against the vault at the given path.

    \b
    Examples:
      fte vault validate                        # Full validation
      fte vault validate --vault-path ~/vault   # Custom path
      fte vault validate --state-only           # State transitions only
    """
    try:
        if vault_path is None:
            vault_path = resolve_vault_path()
        else:
            vault_path = expand_path(str(vault_path))

        if not vault_path.is_dir():
            raise VaultNotFoundError(f"Vault path does not exist: {vault_path}")

        exit_code = 0

        if not state_only:
            display_info("Running full vault validation...")
            vault_script = _find_validation_script("validate_vault.py")
            result = subprocess.run(
                [sys.executable, str(vault_script), str(vault_path)],
                capture_output=True,
                text=True,
            )
            console.print(result.stdout)
            if result.returncode != 0:
                exit_code = 1

        display_info("Running state-transition validation...")
        state_script = _find_validation_script("validate_state.py")
        result = subprocess.run(
            [sys.executable, str(state_script), str(vault_path)],
            capture_output=True,
            text=True,
        )
        console.print(result.stdout)
        if result.returncode != 0:
            exit_code = 1

        display_info("Running filename validation...")
        filename_script = _find_validation_script("validate_filename.py")
        result = subprocess.run(
            [sys.executable, str(filename_script), str(vault_path)],
            capture_output=True,
            text=True,
        )
        console.print(result.stdout)
        if result.returncode != 0:
            exit_code = 1

        if exit_code == 0:
            display_success("\nAll validations passed.")
        else:
            display_warning("\nValidation completed with errors.")
            ctx.exit(1)

    except VaultNotFoundError as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except FileNotFoundError as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)

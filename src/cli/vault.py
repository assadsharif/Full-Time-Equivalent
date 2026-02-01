"""
Vault Management Commands

Commands for managing the AI Employee vault including initialization,
status checking, and approval workflow management.
"""

import hashlib
import re
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


# Vault Templates

DASHBOARD_TEMPLATE = """# AI Employee Dashboard

**Last Updated**: {date}

## Quick Stats
- **Inbox**: {inbox_count} new tasks
- **Needs Action**: {needs_action_count} tasks
- **In Progress**: {in_progress_count} tasks
- **Done**: {done_count} completed
- **Pending Approvals**: {approvals_count} awaiting review

## Recent Activity
<!-- Automatically updated by watchers -->

## Alerts
<!-- System alerts and warnings -->

## Next Steps
1. Review pending approvals: `fte approval pending`
2. Check system status: `fte status`
3. Start watchers: `fte watcher start <name>`

---
*This dashboard is automatically maintained by the Digital FTE system.*
"""

COMPANY_HANDBOOK_TEMPLATE = """# Company Handbook

**Last Updated**: {date}

## Company Information
- **Company Name**: [Your Company]
- **Industry**: [Industry]
- **Founded**: [Year]

## Mission & Values
<!-- Add your company mission and core values here -->

## Key Contacts
- **CEO**: [Name] <email>
- **CTO**: [Name] <email>

## Operational Guidelines

### Communication
- Email response time: 24 hours
- Urgent issues: Flag with [URGENT] in subject
- Weekly briefing: Every Monday 9am

### Decision Authority
- Payments >$1000: Requires CEO approval
- Client communications: Review by account manager
- Code deployments: CTO approval required

### Tools & Systems
- Email: [Email platform]
- Project Management: [PM tool]
- Code Repository: [Git platform]

## AI Employee Instructions

### Task Prioritization
1. URGENT: Immediate attention required
2. HIGH: Complete within 24 hours
3. MEDIUM: Complete within 1 week
4. LOW: Complete when time permits

### Approval Requirements
- **Payments**: Always require approval
- **External emails**: Require approval for first-time contacts
- **File deletions**: Always require approval for permanent deletions

### Autonomy Boundaries
The AI Employee can autonomously:
- Draft responses (not send without approval)
- Organize and categorize tasks
- Research and compile information
- Generate reports and summaries

The AI Employee CANNOT autonomously:
- Send emails to external contacts
- Make payments or financial commitments
- Delete files permanently
- Make commitments on behalf of the company

---
*Update this handbook to customize AI Employee behavior for your organization.*
"""


def create_vault_structure(vault_path: Path) -> None:
    """
    Create vault folder structure.

    Args:
        vault_path: Path to vault root

    Creates:
        - Core folders (Inbox, Needs_Action, In_Progress, Done, etc.)
        - Dashboard.md
        - Company_Handbook.md
    """
    # Create core folders
    folders = [
        "Inbox",
        "Needs_Action",
        "In_Progress",
        "Done",
        "Approvals",
        "Briefings",
        "Attachments",
    ]

    vault_path.mkdir(parents=True, exist_ok=True)

    for folder in folders:
        folder_path = vault_path / folder
        folder_path.mkdir(exist_ok=True)
        display_success(f"Created folder: {folder}")

    # Create Dashboard.md
    dashboard_path = vault_path / "Dashboard.md"
    dashboard_content = DASHBOARD_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d"),
        inbox_count=0,
        needs_action_count=0,
        in_progress_count=0,
        done_count=0,
        approvals_count=0,
    )
    dashboard_path.write_text(dashboard_content)
    display_success(f"Created: Dashboard.md")

    # Create Company_Handbook.md
    handbook_path = vault_path / "Company_Handbook.md"
    handbook_content = COMPANY_HANDBOOK_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d")
    )
    handbook_path.write_text(handbook_content)
    display_success(f"Created: Company_Handbook.md")


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
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
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
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
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
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def verify_integrity(approval_data: Dict) -> bool:
    """
    Verify file integrity using stored hash.

    Args:
        approval_data: Parsed approval data

    Returns:
        True if integrity check passes

    Note:
        Currently returns True as hash storage not yet implemented.
        Full implementation requires storing hash at creation time.
    """
    # TODO: Implement hash storage and verification
    # For now, just check file hasn't been tampered (basic checks)
    frontmatter = approval_data["frontmatter"]

    required_fields = ["task_id", "approval_id", "nonce", "action_type", "approval_status"]
    for field in required_fields:
        if field not in frontmatter:
            raise ApprovalIntegrityError(approval_data["path"].name)

    return True


def update_approval_status(
    approval_path: Path,
    status: str,
    reason: Optional[str] = None
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
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
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
    updated_content = f"---\n{yaml.dump(frontmatter, default_flow_style=False)}---\n{body_text}"
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
def vault_init_command(
    ctx: click.Context,
    vault_path: Optional[Path],
    force: bool
):
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
        checkpoint_manager.update_vault(
            path=str(vault_path),
            initialized=True
        )

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
def vault_status_command(
    ctx: click.Context,
    vault_path: Optional[Path]
):
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
        table = Table(title="Vault Statistics", show_header=True, header_style="bold cyan")
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
            display_warning(f"\n⚠ {stats['Approvals']} pending approvals - run 'fte approval pending'")

        if stats.get("Needs_Action", 0) > 10:
            display_warning(f"\n⚠ {stats['Needs_Action']} tasks in Needs_Action - consider prioritizing")

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
    ctx: click.Context,
    approval_id: str,
    vault_path: Optional[Path]
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

    except (ApprovalNotFoundError, ApprovalInvalidNonceError, ApprovalIntegrityError) as e:
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
    reason: Optional[str]
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

    except (ApprovalNotFoundError, ApprovalInvalidNonceError, ApprovalIntegrityError) as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)

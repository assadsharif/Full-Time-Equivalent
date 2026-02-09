"""
Approval Workflow Commands

Interactive commands for reviewing and managing approval requests.
Provides rich context display and interactive decision prompts.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from cli.checkpoint import get_checkpoint_manager
from cli.config import get_config
from cli.errors import (
    ApprovalExpiredError,
    ApprovalIntegrityError,
    ApprovalInvalidNonceError,
    ApprovalNotFoundError,
)
from cli.utils import (
    display_error,
    display_info,
    display_success,
    display_warning,
    resolve_vault_path,
    validate_vault_or_error,
)
from cli.vault import (
    parse_approval_file,
    update_approval_status,
    validate_nonce,
    verify_integrity,
)

console = Console()


def scan_pending_approvals(vault_path: Path) -> List[Dict]:
    """
    Scan /Approvals folder for pending approval files.

    Args:
        vault_path: Path to vault

    Returns:
        List of approval data dictionaries with metadata
    """
    approvals_dir = vault_path / "Approvals"

    if not approvals_dir.exists():
        return []

    pending_approvals = []

    # Scan for .md files
    for approval_file in approvals_dir.glob("*.md"):
        try:
            # Parse approval file
            approval_data = parse_approval_file(approval_file)
            frontmatter = approval_data.get("frontmatter", {})

            # Check if pending
            status = frontmatter.get("approval_status", "")
            if status != "pending":
                continue

            # Check if expired
            expires_at = frontmatter.get("expires_at")
            if expires_at:
                try:
                    # Handle both string and datetime objects (YAML may parse dates automatically)
                    if isinstance(expires_at, str):
                        expiry_time = datetime.fromisoformat(
                            expires_at.replace("Z", "+00:00")
                        )
                    elif isinstance(expires_at, datetime):
                        expiry_time = expires_at
                        if expiry_time.tzinfo is None:
                            expiry_time = expiry_time.replace(tzinfo=timezone.utc)
                    else:
                        # Unknown type, include the approval
                        expiry_time = None

                    if expiry_time and datetime.now(timezone.utc) > expiry_time:
                        # Expired, skip
                        continue
                except (ValueError, AttributeError, TypeError):
                    # Invalid expiry format, include anyway
                    pass

            # Add to list
            pending_approvals.append(
                {
                    "file": approval_file,
                    "approval_id": frontmatter.get("approval_id", approval_file.stem),
                    "action_type": frontmatter.get("action_type", "unknown"),
                    "risk_level": frontmatter.get("risk_level", "unknown"),
                    "created_at": frontmatter.get("created_at", ""),
                    "expires_at": expires_at,
                    "task_id": frontmatter.get("task_id", ""),
                    "frontmatter": frontmatter,
                    "body": approval_data.get("body", ""),
                }
            )

        except Exception:
            # Skip files that can't be parsed
            continue

    return pending_approvals


def display_pending_approvals(approvals: List[Dict]) -> None:
    """
    Display pending approvals in Rich table.

    Args:
        approvals: List of approval dictionaries
    """
    if not approvals:
        console.print("[yellow]No pending approvals[/yellow]")
        console.print("\nAll approvals have been processed.")
        return

    # Create table
    table = Table(
        title="Pending Approvals",
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("ID", style="bold")
    table.add_column("Type")
    table.add_column("Risk", justify="center")
    table.add_column("Created")
    table.add_column("Expires")
    table.add_column("Task ID", overflow="fold")

    # Add rows
    for approval in approvals:
        approval_id = approval["approval_id"]
        action_type = approval["action_type"]
        risk_level = approval["risk_level"]
        created_at = approval["created_at"]
        expires_at = approval["expires_at"] or "-"
        task_id = (
            approval["task_id"][:30] + "..."
            if len(approval["task_id"]) > 30
            else approval["task_id"]
        )

        # Color code risk level
        if risk_level.lower() == "high":
            risk_colored = "[red]HIGH[/red]"
        elif risk_level.lower() == "medium":
            risk_colored = "[yellow]MEDIUM[/yellow]"
        else:
            risk_colored = "[green]LOW[/green]"

        # Format dates
        try:
            if isinstance(created_at, str):
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            elif isinstance(created_at, datetime):
                created_dt = created_at
            else:
                created_dt = None

            if created_dt:
                created_str = created_dt.strftime("%Y-%m-%d %H:%M")
            else:
                created_str = str(created_at)[:16] if created_at else "-"
        except (ValueError, AttributeError, TypeError):
            created_str = str(created_at)[:16] if created_at else "-"

        try:
            if expires_at != "-":
                if isinstance(expires_at, str):
                    expires_dt = datetime.fromisoformat(
                        expires_at.replace("Z", "+00:00")
                    )
                elif isinstance(expires_at, datetime):
                    expires_dt = expires_at
                else:
                    expires_dt = None

                if expires_dt:
                    expires_str = expires_dt.strftime("%Y-%m-%d %H:%M")
                else:
                    expires_str = str(expires_at)[:16]
            else:
                expires_str = "-"
        except (ValueError, AttributeError, TypeError):
            expires_str = str(expires_at)[:16] if expires_at else "-"

        table.add_row(
            approval_id,
            action_type,
            risk_colored,
            created_str,
            expires_str,
            task_id,
        )

    console.print(table)
    console.print(f"\n[dim]Found {len(approvals)} pending approvals[/dim]")
    console.print("\nReview an approval: [cyan]fte approval review <id>[/cyan]")


def display_approval_details(approval_data: Dict) -> None:
    """
    Display approval details in Rich panel.

    Args:
        approval_data: Approval data dictionary
    """
    frontmatter = approval_data["frontmatter"]
    body = approval_data["body"]

    approval_id = frontmatter.get("approval_id", "unknown")
    action_type = frontmatter.get("action_type", "unknown")
    risk_level = frontmatter.get("risk_level", "unknown")
    task_id = frontmatter.get("task_id", "unknown")
    created_at = frontmatter.get("created_at", "unknown")
    nonce = frontmatter.get("nonce", "unknown")

    # Color code risk level
    if risk_level.lower() == "high":
        risk_colored = "[red bold]HIGH RISK[/red bold]"
    elif risk_level.lower() == "medium":
        risk_colored = "[yellow]MEDIUM RISK[/yellow]"
    else:
        risk_colored = "[green]LOW RISK[/green]"

    # Build details text
    details = f"""[bold]Approval ID:[/bold] {approval_id}
[bold]Action Type:[/bold] {action_type}
[bold]Risk Level:[/bold] {risk_colored}
[bold]Task ID:[/bold] {task_id}
[bold]Created:[/bold] {created_at}
[bold]Nonce:[/bold] {nonce[:16]}...

[bold cyan]Action Details:[/bold cyan]
{body.strip()}
"""

    # Display in panel
    panel = Panel(
        details,
        title=f"[bold]Approval Review: {approval_id}[/bold]",
        border_style="cyan",
        expand=False,
    )

    console.print()
    console.print(panel)
    console.print()


def prompt_approval_decision() -> str:
    """
    Prompt user for approval decision.

    Returns:
        Decision: "approve", "reject", or "skip"
    """
    console.print("[bold]What would you like to do?[/bold]")
    console.print("  [green]1.[/green] Approve this action")
    console.print("  [red]2.[/red] Reject this action")
    console.print("  [yellow]3.[/yellow] Skip (review later)")

    while True:
        choice = Prompt.ask("\nEnter your choice", choices=["1", "2", "3"], default="3")

        if choice == "1":
            confirm = Confirm.ask("[yellow]Are you sure you want to approve?[/yellow]")
            if confirm:
                return "approve"
        elif choice == "2":
            confirm = Confirm.ask("[yellow]Are you sure you want to reject?[/yellow]")
            if confirm:
                return "reject"
        elif choice == "3":
            return "skip"


def log_approval_decision(
    approval_id: str, decision: str, reason: Optional[str] = None
) -> None:
    """
    Log approval decision to audit trail.

    Args:
        approval_id: Approval ID
        decision: Decision (approve/reject/skip)
        reason: Optional rejection reason
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # Log to console (in production, log to file/database)
    log_message = f"[{timestamp}] Approval {approval_id}: {decision.upper()}"
    if reason:
        log_message += f" - {reason}"

    display_info(f"Audit: {log_message}")


# CLI Commands


@click.group(name="approval")
def approval_group():
    """Approval workflow commands"""
    pass


@approval_group.command(name="pending")
@click.option(
    "--vault-path",
    type=click.Path(path_type=Path),
    help="Path to vault (overrides config)",
)
@click.pass_context
def approval_pending_command(ctx: click.Context, vault_path: Optional[Path]):
    """
    List pending approvals.

    Displays all approval requests that require user review.
    Only shows approvals with status=pending that haven't expired.

    Examples:
        fte approval pending
        fte approval pending --vault-path ~/AI_Employee_Vault
    """
    try:
        # Resolve vault path
        if vault_path is None:
            vault_path = resolve_vault_path()

        # Validate vault
        validate_vault_or_error(vault_path)

        display_info("Scanning for pending approvals...")

        # Scan for pending approvals
        approvals = scan_pending_approvals(vault_path)

        console.print()  # Blank line
        display_pending_approvals(approvals)

    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


@approval_group.command(name="review")
@click.argument("approval_id")
@click.option(
    "--vault-path",
    type=click.Path(path_type=Path),
    help="Path to vault (overrides config)",
)
@click.pass_context
def approval_review_command(
    ctx: click.Context, approval_id: str, vault_path: Optional[Path]
):
    """
    Review and decide on approval.

    Displays approval details and prompts for interactive decision.
    User can approve, reject, or skip the approval.

    Examples:
        fte approval review PAYMENT_APPROVAL_001
        fte approval review EMAIL_SEND_002 --vault-path ~/AI_Employee_Vault
    """
    try:
        # Resolve vault path
        if vault_path is None:
            vault_path = resolve_vault_path()

        # Validate vault
        validate_vault_or_error(vault_path)

        # Find approval file
        approval_file = vault_path / "Approvals" / f"{approval_id}.md"

        if not approval_file.exists():
            raise ApprovalNotFoundError(approval_id)

        # Parse approval file
        approval_data = parse_approval_file(approval_file)
        frontmatter = approval_data["frontmatter"]

        # Check if already processed
        status = frontmatter.get("approval_status")
        if status != "pending":
            display_warning(f"Approval already processed (status: {status})")
            return

        # Check if expired
        expires_at = frontmatter.get("expires_at")
        if expires_at:
            try:
                # Handle both string and datetime objects (YAML may parse dates automatically)
                if isinstance(expires_at, str):
                    expiry_time = datetime.fromisoformat(
                        expires_at.replace("Z", "+00:00")
                    )
                    expires_at_str = expires_at
                elif isinstance(expires_at, datetime):
                    expiry_time = expires_at
                    if expiry_time.tzinfo is None:
                        expiry_time = expiry_time.replace(tzinfo=timezone.utc)
                    expires_at_str = expiry_time.isoformat()
                else:
                    # Unknown type, proceed anyway
                    expiry_time = None
                    expires_at_str = str(expires_at)

                if expiry_time and datetime.now(timezone.utc) > expiry_time:
                    raise ApprovalExpiredError(approval_id, expires_at_str)
            except (ValueError, TypeError):
                # Invalid expiry format, proceed anyway
                pass

        # Validate nonce
        validate_nonce(approval_data)

        # Verify integrity
        verify_integrity(approval_data)

        # Display approval details
        display_approval_details(approval_data)

        # Prompt for decision
        decision = prompt_approval_decision()

        # Process decision
        if decision == "approve":
            # Update status to approved
            update_approval_status(approval_file, "approved")

            # Update checkpoint
            checkpoint_manager = get_checkpoint_manager()
            checkpoint_manager.update_approval(action="approve")

            # Log decision
            log_approval_decision(approval_id, "approve")

            display_success(f"\n✓ Approval '{approval_id}' approved successfully")

        elif decision == "reject":
            # Prompt for rejection reason
            reason = Prompt.ask("\n[yellow]Enter rejection reason[/yellow]")

            # Update status to rejected
            update_approval_status(approval_file, "rejected", reason=reason)

            # Update checkpoint
            checkpoint_manager = get_checkpoint_manager()
            checkpoint_manager.update_approval(action="reject")

            # Log decision
            log_approval_decision(approval_id, "reject", reason=reason)

            display_success(f"\n✓ Approval '{approval_id}' rejected successfully")

        elif decision == "skip":
            display_info("\nApproval skipped. No changes made.")
            log_approval_decision(approval_id, "skip")

    except (
        ApprovalNotFoundError,
        ApprovalExpiredError,
        ApprovalInvalidNonceError,
        ApprovalIntegrityError,
    ) as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)


# ---------------------------------------------------------------------------
# Audit trail display helpers
# ---------------------------------------------------------------------------

_STATUS_COLORS = {
    "pending": "yellow",
    "approved": "green",
    "rejected": "red",
    "timeout": "orange1",
}


def _display_audit_events(events: List[Dict]) -> None:
    """Render approval audit events as a Rich table."""
    if not events:
        console.print("[yellow]No audit events found[/yellow]")
        return

    table = Table(
        title="Approval Audit Trail", show_header=True, header_style="bold cyan"
    )
    table.add_column("Timestamp", style="dim")
    table.add_column("Event", style="bold")
    table.add_column("Approval ID", overflow="fold")
    table.add_column("Task ID", overflow="fold")
    table.add_column("Action", style="cyan")
    table.add_column("Risk", justify="center")
    table.add_column("Status")
    table.add_column("Details")

    for e in events:
        status = e.get("status", "")
        color = _STATUS_COLORS.get(status, "white")
        details_parts: List[str] = []
        if e.get("approver"):
            details_parts.append(f"approver={e['approver']}")
        if e.get("reason"):
            details_parts.append(f"reason={e['reason']}")

        table.add_row(
            e.get("timestamp", "-")[:19],
            e.get("event_type", "-").replace("approval_", ""),
            e.get("approval_id", "-"),
            e.get("task_id", "-"),
            e.get("action_type", "-"),
            f"[{color}]{e.get('risk_level', '-').upper()}[/{color}]",
            f"[{color}]{status.upper()}[/{color}]",
            " | ".join(details_parts) if details_parts else "-",
        )

    console.print(table)
    console.print(f"\n[dim]{len(events)} event(s)[/dim]")


def _display_audit_stats(stats: Dict) -> None:
    """Render aggregate approval statistics as a Rich table."""
    table = Table(title="Approval Statistics", show_header=False, border_style="cyan")
    table.add_column("Metric", style="bold", width=30)
    table.add_column("Value", justify="right")

    table.add_row("Total Events", str(stats["total_events"]))
    table.add_row("Approved", f"[green]{stats['approved_count']}[/green]")
    table.add_row("Rejected", f"[red]{stats['rejected_count']}[/red]")
    table.add_row("Timed Out", f"[orange1]{stats['timeout_count']}[/orange1]")
    table.add_row("Approval Rate", f"{stats['approval_rate'] * 100:.1f}%")
    table.add_row("Avg Response Time", f"{stats['avg_response_time_seconds']:.1f}s")

    console.print(table)


# ---------------------------------------------------------------------------
# Audit CLI command
# ---------------------------------------------------------------------------


@approval_group.command(name="audit")
@click.option("--task-id", type=str, default=None, help="Filter by task ID")
@click.option("--approval-id", type=str, default=None, help="Filter by approval ID")
@click.option(
    "--status",
    type=click.Choice(["pending", "approved", "rejected", "timeout"]),
    default=None,
    help="Filter by status",
)
@click.option("--stats", "show_stats", is_flag=True, help="Show aggregate statistics")
@click.option(
    "--vault-path",
    type=click.Path(path_type=Path),
    help="Path to vault (overrides config)",
)
@click.pass_context
def approval_audit_command(
    ctx: click.Context,
    task_id: Optional[str],
    approval_id: Optional[str],
    status: Optional[str],
    show_stats: bool,
    vault_path: Optional[Path],
):
    """
    Display the approval audit trail.

    Shows all recorded approval lifecycle events with optional filters.
    Use --stats for aggregate statistics (approval rate, response time).

    Examples:
        fte approval audit
        fte approval audit --task-id task-123
        fte approval audit --status approved
        fte approval audit --stats
    """
    try:
        if vault_path is None:
            vault_path = resolve_vault_path()
        validate_vault_or_error(vault_path)

        from approval.audit_query import ApprovalAuditQuery

        audit_log_path = vault_path / ".fte" / "approval_audit.log"
        query_svc = ApprovalAuditQuery(audit_log_path)

        if show_stats:
            stats = query_svc.query_approval_stats()
            _display_audit_stats(stats)
        else:
            events = query_svc.query_approval_events(
                task_id=task_id,
                approval_id=approval_id,
                status=status,
            )
            _display_audit_events(events)

    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        ctx.exit(1)

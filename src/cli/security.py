"""
Security CLI — commands for MCP security monitoring (spec 004 Platinum).

Provides commands for:
- Viewing anomaly alerts
- Scanning for anomalies
- Checking circuit breaker status
- Resetting circuit breakers
"""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from cli.config import get_config
from src.security.anomaly_detector import AnomalyDetector
from src.security.incident_response import IncidentResponse
from src.security.credential_vault import CredentialVault


console = Console()


@click.group(name="security")
def security_group():
    """
    Security monitoring and management commands.

    \b
    Examples:
      fte security alerts              # View recent anomaly alerts
      fte security scan                # Scan for current anomalies
      fte security circuit-status      # View circuit breaker status
      fte security reset-circuit <mcp> # Reset circuit breaker
    """
    pass


@security_group.command(name="alerts")
@click.option(
    "--limit",
    "-n",
    default=20,
    help="Number of recent alerts to show (default: 20)",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output alerts as JSON",
)
def alerts_command(limit: int, json_output: bool):
    """
    View recent anomaly alerts.

    Shows alerts for unusual MCP usage patterns detected by the
    anomaly detection system (volume spikes, timing anomalies,
    unexpected action sequences).
    """
    try:
        config = get_config()
        vault_path = Path(config.vault_path)

        # Initialize anomaly detector
        audit_log = vault_path / "Logs" / "security_audit.log"
        alert_log = vault_path / "Logs" / "anomaly_alerts.log"

        detector = AnomalyDetector(audit_log, alert_log)
        alerts = detector.get_recent_alerts(limit=limit)

        if json_output:
            import json
            console.print(json.dumps(alerts, indent=2))
            return

        if not alerts:
            console.print("[yellow]No anomaly alerts found[/yellow]")
            return

        # Display alerts in table
        table = Table(title=f"Recent Anomaly Alerts (last {len(alerts)})")
        table.add_column("Time", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Severity", style="yellow")
        table.add_column("Server", style="green")
        table.add_column("Description", style="white")

        for alert in reversed(alerts):  # Most recent first
            # Parse timestamp
            from datetime import datetime
            ts = datetime.fromisoformat(alert["timestamp"].replace("Z", "+00:00"))
            time_str = ts.strftime("%Y-%m-%d %H:%M:%S")

            # Color code severity
            severity = alert["severity"]
            if severity == "critical":
                severity_color = "[red]CRITICAL[/red]"
            elif severity == "high":
                severity_color = "[orange1]HIGH[/orange1]"
            elif severity == "medium":
                severity_color = "[yellow]MEDIUM[/yellow]"
            else:
                severity_color = "[green]LOW[/green]"

            table.add_row(
                time_str,
                alert["anomaly_type"],
                severity_color,
                alert["mcp_server"],
                alert["description"],
            )

        console.print(table)

        # Show summary
        console.print(
            f"\n[dim]Showing {len(alerts)} most recent alerts. "
            f"Use --limit to see more.[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@security_group.command(name="scan")
@click.option(
    "--server",
    "-s",
    help="Specific MCP server to scan (default: all)",
)
def scan_command(server: str):
    """
    Scan for current anomalies across all MCP servers.

    Performs real-time anomaly detection and reports any
    suspicious patterns found.
    """
    try:
        config = get_config()
        vault_path = Path(config.vault_path)

        # Initialize anomaly detector
        audit_log = vault_path / "Logs" / "security_audit.log"
        alert_log = vault_path / "Logs" / "anomaly_alerts.log"

        detector = AnomalyDetector(audit_log, alert_log)

        console.print("[cyan]Scanning for anomalies...[/cyan]")

        if server:
            # Scan specific server
            alerts = []
            if alert := detector.detect_unusual_volume(server):
                alerts.append(alert)
            if alert := detector.detect_unusual_timing(server):
                alerts.append(alert)
            if alert := detector.detect_unusual_sequence(server):
                alerts.append(alert)
        else:
            # Scan all servers
            alerts = detector.scan_all_servers()

        if not alerts:
            console.print("[green]✓ No anomalies detected[/green]")
            return

        # Display detected anomalies
        console.print(f"\n[yellow]⚠ Found {len(alerts)} anomalies:[/yellow]\n")

        for alert in alerts:
            severity_icon = "🔴" if alert.severity.value in ["critical", "high"] else "🟡"
            console.print(f"{severity_icon} [{alert.severity.value.upper()}] {alert.description}")
            console.print(f"   Server: {alert.mcp_server}")
            console.print(f"   Type: {alert.anomaly_type}")
            console.print(
                f"   Baseline: {alert.baseline_value:.1f} | "
                f"Observed: {alert.observed_value:.1f}"
            )
            console.print()

        console.print(
            f"[dim]Alerts logged to: {alert_log.relative_to(vault_path.parent)}[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@security_group.command(name="circuit-status")
@click.option(
    "--server",
    "-s",
    help="Specific MCP server to check (default: all)",
)
def circuit_status_command(server: str):
    """
    View circuit breaker status for MCP servers.

    Shows the current state (CLOSED/OPEN/HALF_OPEN) of circuit
    breakers protecting MCP server calls.
    """
    try:
        console.print("[yellow]Circuit breaker status not yet implemented[/yellow]")
        console.print(
            "[dim]This requires integration with MCPGuard to expose "
            "circuit breaker states.[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@security_group.command(name="reset-circuit")
@click.argument("mcp_server")
@click.option(
    "--confirm",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def reset_circuit_command(mcp_server: str, confirm: bool):
    """
    Reset circuit breaker for a specific MCP server.

    This manually closes an open circuit breaker, allowing
    requests to the server to proceed again.
    """
    try:
        if not confirm:
            if not click.confirm(
                f"Reset circuit breaker for {mcp_server}?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                return

        console.print("[yellow]Circuit breaker reset not yet implemented[/yellow]")
        console.print(
            "[dim]This requires integration with MCPGuard to expose "
            "circuit breaker reset functionality.[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@security_group.command(name="incident-report")
@click.option(
    "--since",
    default="1h",
    help="Time window to analyze (e.g., 1h, 24h, 7d)",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output report as JSON",
)
def incident_report_command(since: str, json_output: bool):
    """
    Generate security incident investigation report.

    Analyzes audit logs for suspicious patterns, failed operations,
    and high-risk events. Provides actionable recommendations.

    \b
    Examples:
      fte security incident-report --since 1h   # Last hour
      fte security incident-report --since 24h  # Last day
      fte security incident-report --json       # JSON output
    """
    try:
        config = get_config()
        vault_path = Path(config.vault_path)

        # Parse time window
        time_hours = _parse_time_window(since)

        # Initialize incident response
        audit_log = vault_path / "Logs" / "security_audit.log"
        incident_log = vault_path / "Logs" / "incident_response.log"

        incident_response = IncidentResponse(audit_log, incident_log)

        console.print(f"[cyan]Analyzing security events (last {since})...[/cyan]\n")

        # Generate report
        report = incident_response.generate_incident_report(
            time_window_hours=time_hours
        )

        if json_output:
            import json
            output = {
                "report_id": report.report_id,
                "timestamp": report.timestamp.isoformat(),
                "time_window_hours": report.time_window_hours,
                "total_events": report.total_events,
                "high_risk_events": report.high_risk_events,
                "affected_servers": report.affected_servers,
                "suspicious_actions": report.suspicious_actions,
                "failed_operations": report.failed_operations,
                "summary": report.summary,
                "recommendations": report.recommendations,
            }
            console.print(json.dumps(output, indent=2))
            return

        # Display report
        console.print(f"[bold]Incident Report: {report.report_id}[/bold]\n")
        console.print(f"[dim]Generated: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}[/dim]")
        console.print(f"[dim]Time Window: {report.time_window_hours} hours[/dim]\n")

        # Summary
        console.print("[bold cyan]Summary[/bold cyan]")
        console.print(report.summary)
        console.print()

        # Metrics
        console.print("[bold cyan]Metrics[/bold cyan]")
        console.print(f"  Total Events: {report.total_events}")
        console.print(f"  High-Risk Events: {report.high_risk_events}")
        console.print(f"  Affected Servers: {len(report.affected_servers)}")
        if report.affected_servers:
            for server in report.affected_servers[:5]:
                console.print(f"    - {server}")
        console.print()

        # Suspicious actions
        if report.suspicious_actions:
            console.print("[bold yellow]Suspicious Activity[/bold yellow]")
            for action in report.suspicious_actions:
                severity_icon = "🔴" if action.get("severity") == "high" else "🟡"
                console.print(f"  {severity_icon} {action['type']}: {action.get('count', 'N/A')} occurrences")
            console.print()

        # Failed operations
        if report.failed_operations:
            console.print("[bold red]Recent Failures[/bold red]")
            for fail in report.failed_operations[:5]:
                console.print(f"  • {fail.get('server', 'unknown')}: {fail.get('result', 'error')}")
            console.print()

        # Recommendations
        console.print("[bold green]Recommendations[/bold green]")
        for rec in report.recommendations:
            console.print(f"  {rec}")

        console.print(f"\n[dim]Report ID: {report.report_id}[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@security_group.command(name="isolate")
@click.argument("mcp_server")
@click.option(
    "--reason",
    "-r",
    required=True,
    help="Reason for isolation",
)
@click.option(
    "--confirm",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def isolate_command(mcp_server: str, reason: str, confirm: bool):
    """
    Isolate a compromised MCP server.

    Marks the server as isolated and logs the action. This is an
    emergency response action for active security incidents.

    \b
    Example:
      fte security isolate suspicious-server -r "Credential leak detected"
    """
    try:
        if not confirm:
            console.print(f"\n[bold red]⚠️  WARNING: This will isolate {mcp_server}[/bold red]")
            console.print("All requests to this server will be blocked.\n")

            if not click.confirm("Proceed with isolation?", default=False):
                console.print("[yellow]Cancelled[/yellow]")
                return

        config = get_config()
        vault_path = Path(config.vault_path)

        # Initialize incident response
        audit_log = vault_path / "Logs" / "security_audit.log"
        incident_log = vault_path / "Logs" / "incident_response.log"

        incident_response = IncidentResponse(audit_log, incident_log)

        # Isolate server
        record = incident_response.isolate_mcp(
            mcp_server=mcp_server,
            reason=reason,
            isolated_by="cli",
        )

        console.print(f"\n[green]✓ Server isolated successfully[/green]")
        console.print(f"\n  Server: {record.mcp_server}")
        console.print(f"  Reason: {record.reason}")
        console.print(f"  Isolation ID: {record.isolation_id}")
        console.print(f"  Timestamp: {record.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        console.print(
            f"\n[yellow]⚠️  To restore: fte security restore {mcp_server}[/yellow]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@security_group.command(name="restore")
@click.argument("mcp_server")
@click.option(
    "--confirm",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def restore_command(mcp_server: str, confirm: bool):
    """
    Restore a previously isolated MCP server.

    Re-enables requests to the server after isolation.

    \b
    Example:
      fte security restore suspicious-server
    """
    try:
        if not confirm:
            if not click.confirm(
                f"Restore {mcp_server} and allow requests?",
                default=False,
            ):
                console.print("[yellow]Cancelled[/yellow]")
                return

        config = get_config()
        vault_path = Path(config.vault_path)

        # Initialize incident response
        audit_log = vault_path / "Logs" / "security_audit.log"
        incident_log = vault_path / "Logs" / "incident_response.log"

        incident_response = IncidentResponse(audit_log, incident_log)

        # Restore server
        record = incident_response.restore_mcp(
            mcp_server=mcp_server,
            restored_by="cli",
        )

        console.print(f"\n[green]✓ Server restored successfully[/green]")
        console.print(f"\n  Server: {record.mcp_server}")
        console.print(f"  Timestamp: {record.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@security_group.command(name="rotate-all")
@click.option(
    "--reason",
    "-r",
    required=True,
    help="Reason for mass rotation",
)
@click.option(
    "--confirm",
    "-y",
    is_flag=True,
    help="Skip confirmation prompt",
)
def rotate_all_command(reason: str, confirm: bool):
    """
    Perform emergency mass credential rotation.

    Rotates ALL stored credentials. This is a last-resort action
    for severe security incidents (e.g., credential database compromise).

    \b
    Example:
      fte security rotate-all -r "Credential vault compromised"
    """
    try:
        if not confirm:
            console.print("\n[bold red]⚠️  CRITICAL ACTION: MASS CREDENTIAL ROTATION[/bold red]")
            console.print("This will invalidate ALL stored credentials.")
            console.print("Service interruption is expected.\n")

            if not click.confirm("Are you absolutely sure?", default=False):
                console.print("[yellow]Cancelled[/yellow]")
                return

        config = get_config()
        vault_path = Path(config.vault_path)

        # Initialize incident response with vault
        audit_log = vault_path / "Logs" / "security_audit.log"
        incident_log = vault_path / "Logs" / "incident_response.log"

        # Note: CredentialVault requires keyring backend
        # For now, just log the action
        incident_response = IncidentResponse(audit_log, incident_log, vault=None)

        # Initiate rotation
        result = incident_response.rotate_all_credentials(
            reason=reason,
            rotated_by="cli",
        )

        console.print(f"\n[yellow]⚠️  Mass rotation initiated[/yellow]")
        console.print(f"\n  Reason: {reason}")
        console.print(f"  Status: {result['status']}")
        console.print(f"\n[dim]{result['note']}[/dim]")

        console.print(
            "\n[bold]Manual Steps Required:[/bold]"
            "\n  1. Update credentials for each service"
            "\n  2. Test service connectivity"
            "\n  3. Update credential vault with new values"
            "\n  4. Verify all services operational"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


@security_group.command(name="isolated")
def isolated_command():
    """
    List currently isolated MCP servers.

    Shows which servers are currently blocked due to security incidents.
    """
    try:
        config = get_config()
        vault_path = Path(config.vault_path)

        # Initialize incident response
        audit_log = vault_path / "Logs" / "security_audit.log"
        incident_log = vault_path / "Logs" / "incident_response.log"

        incident_response = IncidentResponse(audit_log, incident_log)

        isolated = incident_response.get_isolated_servers()

        if not isolated:
            console.print("[green]No servers currently isolated[/green]")
            return

        console.print(f"[yellow]Isolated Servers ({len(isolated)}):[/yellow]\n")
        for server in isolated:
            console.print(f"  • {server}")

        console.print(
            f"\n[dim]Use 'fte security restore <server>' to restore access[/dim]"
        )

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()


def _parse_time_window(time_str: str) -> int:
    """Parse time window string to hours."""
    time_str = time_str.lower().strip()

    if time_str.endswith("h"):
        return int(time_str[:-1])
    elif time_str.endswith("d"):
        return int(time_str[:-1]) * 24
    elif time_str.endswith("m"):
        return max(1, int(time_str[:-1]) // 60)
    else:
        # Assume hours
        return int(time_str)

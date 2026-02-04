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

"""
Incident Response Toolkit — rapid response to security incidents (spec 004 Platinum US14).

Provides CLI commands and automation for:
- Generating incident reports from audit logs
- Isolating compromised MCP servers
- Mass credential rotation
- Incident response playbooks

Designed for fast response during active security events.
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.security.audit_logger import SecurityAuditLogger
from src.security.credential_vault import CredentialVault
from src.security.models import RiskLevel


@dataclass
class IncidentReport:
    """Incident investigation report."""

    report_id: str
    timestamp: datetime
    time_window_hours: int
    total_events: int
    high_risk_events: int
    affected_servers: list[str]
    suspicious_actions: list[dict]
    failed_operations: list[dict]
    summary: str
    recommendations: list[str]


@dataclass
class IsolationRecord:
    """Record of an MCP server isolation."""

    isolation_id: str
    timestamp: datetime
    mcp_server: str
    reason: str
    isolated_by: str
    status: str  # isolated | restored


class IncidentResponse:
    """
    Incident response toolkit for security events.

    Args:
        audit_log_path: Path to security audit log
        incident_log_path: Path to write incident response actions
        vault: CredentialVault instance for credential rotation
    """

    def __init__(
        self,
        audit_log_path: Path,
        incident_log_path: Path,
        vault: Optional[CredentialVault] = None,
    ):
        self._audit_log = audit_log_path
        self._incident_log = incident_log_path
        self._vault = vault
        self._incident_log.parent.mkdir(parents=True, exist_ok=True)
        self._isolated_servers: set[str] = set()

    # ------------------------------------------------------------------
    # Public incident response methods
    # ------------------------------------------------------------------

    def generate_incident_report(
        self,
        time_window_hours: int = 1,
        min_risk_level: RiskLevel = RiskLevel.MEDIUM,
    ) -> IncidentReport:
        """
        Generate incident investigation report from audit logs.

        Args:
            time_window_hours: Time window to analyze
            min_risk_level: Minimum risk level to include

        Returns:
            IncidentReport with analysis and recommendations
        """
        events = self._load_events()
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(hours=time_window_hours)

        # Filter events in time window
        recent_events = [
            e for e in events if self._parse_timestamp(e["timestamp"]) >= window_start
        ]

        # Analyze events
        high_risk = [
            e
            for e in recent_events
            if self._get_risk_level(e.get("risk_level", "low")) >= min_risk_level
        ]

        affected_servers = list(
            set(e.get("mcp_server") for e in recent_events if e.get("mcp_server"))
        )

        # Find suspicious patterns
        suspicious = self._identify_suspicious_actions(recent_events)
        failed_ops = self._identify_failed_operations(recent_events)

        # Generate summary and recommendations
        summary = self._generate_summary(
            len(recent_events), len(high_risk), len(affected_servers)
        )
        recommendations = self._generate_recommendations(
            high_risk, suspicious, failed_ops
        )

        report = IncidentReport(
            report_id=self._generate_id("incident"),
            timestamp=now,
            time_window_hours=time_window_hours,
            total_events=len(recent_events),
            high_risk_events=len(high_risk),
            affected_servers=affected_servers,
            suspicious_actions=suspicious,
            failed_operations=failed_ops,
            summary=summary,
            recommendations=recommendations,
        )

        self._log_action(
            "incident_report_generated",
            {
                "report_id": report.report_id,
                "time_window_hours": time_window_hours,
                "total_events": report.total_events,
                "high_risk_events": report.high_risk_events,
            },
        )

        return report

    def isolate_mcp(
        self,
        mcp_server: str,
        reason: str,
        isolated_by: str = "system",
    ) -> IsolationRecord:
        """
        Isolate a compromised MCP server (disable and quarantine).

        This marks the server as isolated and logs the action.
        Actual enforcement requires integration with MCPGuard.

        Args:
            mcp_server: MCP server to isolate
            reason: Reason for isolation
            isolated_by: Who initiated isolation

        Returns:
            IsolationRecord documenting the isolation
        """
        record = IsolationRecord(
            isolation_id=self._generate_id("isolation"),
            timestamp=datetime.now(timezone.utc),
            mcp_server=mcp_server,
            reason=reason,
            isolated_by=isolated_by,
            status="isolated",
        )

        self._isolated_servers.add(mcp_server)

        self._log_action(
            "mcp_isolated",
            {
                "isolation_id": record.isolation_id,
                "mcp_server": mcp_server,
                "reason": reason,
                "isolated_by": isolated_by,
            },
        )

        return record

    def restore_mcp(
        self,
        mcp_server: str,
        restored_by: str = "system",
    ) -> IsolationRecord:
        """
        Restore a previously isolated MCP server.

        Args:
            mcp_server: MCP server to restore
            restored_by: Who initiated restoration

        Returns:
            IsolationRecord documenting the restoration
        """
        if mcp_server in self._isolated_servers:
            self._isolated_servers.remove(mcp_server)

        record = IsolationRecord(
            isolation_id=self._generate_id("restoration"),
            timestamp=datetime.now(timezone.utc),
            mcp_server=mcp_server,
            reason="restored after isolation",
            isolated_by=restored_by,
            status="restored",
        )

        self._log_action(
            "mcp_restored",
            {
                "mcp_server": mcp_server,
                "restored_by": restored_by,
            },
        )

        return record

    def is_isolated(self, mcp_server: str) -> bool:
        """Check if an MCP server is currently isolated."""
        return mcp_server in self._isolated_servers

    def rotate_all_credentials(
        self,
        reason: str,
        rotated_by: str = "system",
    ) -> dict:
        """
        Perform mass credential rotation for all services.

        This is an emergency response action for credential compromise.

        Args:
            reason: Reason for mass rotation
            rotated_by: Who initiated rotation

        Returns:
            Dict with rotation results
        """
        # Log the action regardless of vault configuration
        self._log_action(
            "mass_credential_rotation",
            {
                "reason": reason,
                "rotated_by": rotated_by,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        if self._vault is None:
            # Vault not configured - log intent only
            return {
                "status": "initiated",
                "reason": reason,
                "rotated_by": rotated_by,
                "note": "CredentialVault not configured. Manual rotation required per service.",
            }

        # Get all stored credentials from vault
        # Note: This requires vault to expose a list_all method
        # TODO: Integrate with vault.list_all() when available
        # TODO: Implement actual rotation logic per service

        return {
            "status": "initiated",
            "reason": reason,
            "rotated_by": rotated_by,
            "note": "Mass rotation logged. Manual rotation required per service.",
        }

    def get_isolated_servers(self) -> list[str]:
        """Get list of currently isolated servers."""
        return list(self._isolated_servers)

    def get_incident_history(self, limit: int = 20) -> list[dict]:
        """
        Get recent incident response actions.

        Args:
            limit: Maximum number of actions to return

        Returns:
            List of incident action records
        """
        if not self._incident_log.exists():
            return []

        lines = self._incident_log.read_text().strip().split("\n")
        actions = [json.loads(line) for line in lines[-limit:] if line]
        return actions

    # ------------------------------------------------------------------
    # Internal helper methods
    # ------------------------------------------------------------------

    def _load_events(self) -> list[dict]:
        """Load all events from audit log."""
        if not self._audit_log.exists():
            return []

        lines = self._audit_log.read_text().strip().split("\n")
        return [json.loads(line) for line in lines if line]

    def _parse_timestamp(self, ts_str: str) -> datetime:
        """Parse ISO timestamp string."""
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

    def _get_risk_level(self, risk_str: str) -> RiskLevel:
        """Convert risk level string to enum."""
        risk_map = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL,
        }
        return risk_map.get(risk_str.lower(), RiskLevel.LOW)

    def _identify_suspicious_actions(self, events: list[dict]) -> list[dict]:
        """Identify suspicious actions from events."""
        suspicious = []

        # Multiple failed operations
        failure_counts = defaultdict(int)
        for event in events:
            if event.get("result") and "error" in event.get("result", ""):
                server = event.get("mcp_server", "unknown")
                failure_counts[server] += 1

        for server, count in failure_counts.items():
            if count >= 5:
                suspicious.append(
                    {
                        "type": "multiple_failures",
                        "server": server,
                        "count": count,
                        "severity": "high",
                    }
                )

        # Rate limit violations
        rate_limit_violations = [
            e for e in events if e.get("result") == "rate_limit_exceeded"
        ]
        if len(rate_limit_violations) >= 3:
            suspicious.append(
                {
                    "type": "rate_limit_abuse",
                    "count": len(rate_limit_violations),
                    "severity": "medium",
                }
            )

        # Circuit breaker trips
        circuit_trips = [e for e in events if e.get("result") == "circuit_open"]
        if len(circuit_trips) >= 2:
            suspicious.append(
                {
                    "type": "circuit_breaker_trips",
                    "count": len(circuit_trips),
                    "severity": "high",
                }
            )

        return suspicious

    def _identify_failed_operations(self, events: list[dict]) -> list[dict]:
        """Extract failed operations from events."""
        failed = []

        for event in events:
            result = event.get("result", "")
            if "error" in result or result in ["rate_limit_exceeded", "circuit_open"]:
                failed.append(
                    {
                        "timestamp": event.get("timestamp"),
                        "server": event.get("mcp_server"),
                        "action": event.get("action"),
                        "result": result,
                    }
                )

        return failed[:10]  # Limit to 10 most recent

    def _generate_summary(self, total: int, high_risk: int, servers: int) -> str:
        """Generate incident summary text."""
        if high_risk == 0:
            return f"Analyzed {total} events across {servers} servers. No high-risk activity detected."

        risk_pct = (high_risk / total * 100) if total > 0 else 0
        return (
            f"Security incident detected: {high_risk} high-risk events ({risk_pct:.1f}%) "
            f"across {servers} MCP servers in the analyzed period."
        )

    def _generate_recommendations(
        self,
        high_risk: list[dict],
        suspicious: list[dict],
        failed: list[dict],
    ) -> list[str]:
        """Generate incident response recommendations."""
        recommendations = []

        if len(high_risk) >= 10:
            recommendations.append(
                "⚠️  High volume of risk events detected. Consider isolating affected servers."
            )

        if any(s["type"] == "multiple_failures" for s in suspicious):
            recommendations.append(
                "🔍 Multiple failures detected. Investigate server health and authentication."
            )

        if any(s["type"] == "rate_limit_abuse" for s in suspicious):
            recommendations.append(
                "🛡️  Rate limit abuse detected. Review rate limit thresholds and consider IP blocking."
            )

        if any(s["type"] == "circuit_breaker_trips" for s in suspicious):
            recommendations.append(
                "⚡ Circuit breakers tripping. Check downstream service health."
            )

        if len(failed) >= 5:
            recommendations.append(
                "🔧 High failure rate. Review error logs and consider service rollback."
            )

        if not recommendations:
            recommendations.append(
                "✅ No immediate action required. Continue monitoring."
            )

        return recommendations

    def _log_action(self, action_type: str, details: dict):
        """Log incident response action."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_type": action_type,
            "details": details,
        }

        with open(self._incident_log, "a") as fh:
            fh.write(json.dumps(record) + "\n")

    def _generate_id(self, prefix: str) -> str:
        """Generate unique ID for records."""
        import uuid

        return f"{prefix}-{uuid.uuid4().hex[:12]}"

"""
Security Audit Logger — append-only JSON-lines audit trail (spec 004 Bronze).

Every security-relevant event (MCP action, credential access, scan result)
is written as a single JSON line.  The log is append-only; no line is ever
overwritten or deleted by this module.
"""

import json
from pathlib import Path
from typing import Optional

from src.security.models import RiskLevel, SecurityEvent


class SecurityAuditLogger:
    """Append-only audit logger for security events."""

    def __init__(self, log_path: Path):
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Typed event helpers
    # ------------------------------------------------------------------

    def log_mcp_action(
        self,
        mcp_server: str,
        action: str,
        approved: bool,
        risk_level: RiskLevel,
        approval_id: Optional[str] = None,
        nonce: Optional[str] = None,
        result: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Record an MCP action regardless of success or failure."""
        self._append(
            SecurityEvent(
                event_type="mcp_action",
                mcp_server=mcp_server,
                action=action,
                approved=approved,
                approval_id=approval_id,
                nonce=nonce,
                risk_level=risk_level,
                result=result,
                duration_ms=duration_ms,
            )
        )

    def log_credential_access(
        self,
        service: str,
        operation: str,  # store | retrieve | delete
        username: str,
    ) -> None:
        """Record a credential-vault operation (always CRITICAL)."""
        self._append(
            SecurityEvent(
                event_type="credential_access",
                risk_level=RiskLevel.CRITICAL,
                details={
                    "service": service,
                    "operation": operation,
                    "username": username,
                },
            )
        )

    def log_scan_result(
        self,
        scan_target: str,
        findings: list[dict],
    ) -> None:
        """Record a secrets-scan outcome."""
        self._append(
            SecurityEvent(
                event_type="scan_result",
                risk_level=RiskLevel.HIGH if findings else RiskLevel.LOW,
                details={
                    "target": scan_target,
                    "finding_count": len(findings),
                    "findings": findings,
                },
            )
        )

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def query_recent(self, limit: int = 100) -> list[dict]:
        """Return the most recent *limit* events as dicts."""
        if not self._log_path.exists():
            return []
        lines = self._log_path.read_text().strip().split("\n")
        return [json.loads(line) for line in lines[-limit:] if line]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _append(self, event: SecurityEvent) -> None:
        record = {
            "timestamp": event.timestamp.isoformat(),
            "event_type": event.event_type,
            "mcp_server": event.mcp_server,
            "action": event.action,
            "approved": event.approved,
            "approval_id": event.approval_id,
            "nonce": event.nonce,
            "risk_level": event.risk_level.value,
            "result": event.result,
            "duration_ms": event.duration_ms,
            "details": event.details,
        }
        with open(self._log_path, "a") as fh:
            fh.write(json.dumps(record) + "\n")

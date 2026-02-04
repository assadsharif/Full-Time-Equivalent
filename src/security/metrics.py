"""
Security Metrics — event-level telemetry for the security sub-system (spec 004 Polish T044).

Reads the append-only audit log and derives time-series metrics on demand.
No background writer — every query scans the tail of the log, keeping the
module stateless and crash-safe.

Exposed metrics
    credential_access_count   – total credential-vault operations
    verification_failure_count – MCP verification failures
    rate_limit_hit_count      – times a rate-limit was exceeded
    circuit_open_count        – times a circuit breaker tripped
    mcp_action_count          – total MCP guard calls
    error_rate                – fraction of MCP actions that returned an error
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


class SecurityMetrics:
    """
    On-demand security metrics from the audit log.

    Args:
        audit_log_path: Path to the security_audit.log (JSON lines).
    """

    def __init__(self, audit_log_path: Path):
        self._audit_log = audit_log_path

    # ------------------------------------------------------------------
    # Aggregated counts
    # ------------------------------------------------------------------

    def credential_access_count(self, since: Optional[datetime] = None) -> int:
        """Number of credential-vault operations."""
        return self._count_events("credential_access", since=since)

    def verification_failure_count(self, since: Optional[datetime] = None) -> int:
        """MCP verification failures (result contains 'verification')."""
        events = self._load_events(since=since)
        return sum(
            1 for e in events
            if "verification" in (e.get("result") or "").lower()
        )

    def rate_limit_hit_count(self, since: Optional[datetime] = None) -> int:
        """Times a rate-limit was exceeded."""
        events = self._load_events(since=since)
        return sum(
            1 for e in events
            if e.get("result") == "rate_limit_exceeded"
        )

    def circuit_open_count(self, since: Optional[datetime] = None) -> int:
        """Times a circuit breaker fired."""
        events = self._load_events(since=since)
        return sum(
            1 for e in events
            if e.get("result") == "circuit_open"
        )

    def mcp_action_count(self, since: Optional[datetime] = None) -> int:
        """Total MCP guard calls."""
        return self._count_events("mcp_action", since=since)

    def error_rate(self, since: Optional[datetime] = None) -> float:
        """Fraction of MCP actions that returned an error (0.0 – 1.0)."""
        events = self._load_events(since=since)
        mcp_events = [e for e in events if e.get("event_type") == "mcp_action"]
        if not mcp_events:
            return 0.0
        errors = sum(1 for e in mcp_events if self._is_error(e))
        return errors / len(mcp_events)

    # ------------------------------------------------------------------
    # Per-server breakdown
    # ------------------------------------------------------------------

    def per_server_actions(self, since: Optional[datetime] = None) -> dict[str, int]:
        """Return {server_name: action_count}."""
        events = self._load_events(since=since)
        counts: dict[str, int] = defaultdict(int)
        for e in events:
            server = e.get("mcp_server")
            if server and e.get("event_type") == "mcp_action":
                counts[server] += 1
        return dict(counts)

    def per_server_errors(self, since: Optional[datetime] = None) -> dict[str, int]:
        """Return {server_name: error_count}."""
        events = self._load_events(since=since)
        counts: dict[str, int] = defaultdict(int)
        for e in events:
            server = e.get("mcp_server")
            if server and e.get("event_type") == "mcp_action" and self._is_error(e):
                counts[server] += 1
        return dict(counts)

    # ------------------------------------------------------------------
    # Summary dict (for CLI / JSON output)
    # ------------------------------------------------------------------

    def summary(self, since: Optional[datetime] = None) -> dict:
        """Single dict of every metric – convenient for CLI display."""
        return {
            "credential_access_count": self.credential_access_count(since),
            "verification_failure_count": self.verification_failure_count(since),
            "rate_limit_hit_count": self.rate_limit_hit_count(since),
            "circuit_open_count": self.circuit_open_count(since),
            "mcp_action_count": self.mcp_action_count(since),
            "error_rate": round(self.error_rate(since), 4),
            "per_server_actions": self.per_server_actions(since),
            "per_server_errors": self.per_server_errors(since),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_events(self, since: Optional[datetime] = None) -> list[dict]:
        if not self._audit_log.exists():
            return []
        lines = self._audit_log.read_text().strip().split("\n")
        events = [json.loads(ln) for ln in lines if ln]
        if since:
            events = [
                e for e in events
                if self._parse_ts(e["timestamp"]) >= since
            ]
        return events

    def _count_events(self, event_type: str, since: Optional[datetime] = None) -> int:
        return sum(
            1 for e in self._load_events(since=since)
            if e.get("event_type") == event_type
        )

    @staticmethod
    def _is_error(event: dict) -> bool:
        result = event.get("result") or ""
        return "error" in result.lower() or result in (
            "rate_limit_exceeded", "circuit_open"
        )

    @staticmethod
    def _parse_ts(ts_str: str) -> datetime:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

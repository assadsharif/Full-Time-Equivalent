"""
Security Dashboard — real-time security posture aggregator (spec 004 Platinum US13).

Collects live status from every security sub-system and surfaces it
in a single, human-readable view.  Each ``get_*`` method can also be
called individually by the CLI or by other tooling.

Data sources:
    CredentialVault   → stored-service count
    MCPVerifier       → trusted vs unverified servers
    RateLimiter       → per-bucket remaining tokens
    CircuitBreaker    → open / half-open circuits
    AuditLogger       → latest security events
    AnomalyDetector   → recent anomaly alerts
    IncidentResponse  → isolation status
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data classes – every status section has its own typed container so the CLI
# (or a future JSON API) can serialize each section independently.
# ---------------------------------------------------------------------------


@dataclass
class CredentialStatus:
    services: list[str]
    count: int
    keyring_backed: bool


@dataclass
class VerificationStatus:
    trusted_servers: list[str]
    trusted_count: int


@dataclass
class RateLimitEntry:
    server: str
    action_type: str
    tokens_remaining: float
    max_tokens: int


@dataclass
class RateLimitStatus:
    buckets: list[RateLimitEntry]
    throttled_count: int  # buckets below 10 %


@dataclass
class CircuitEntry:
    server: str
    state: str  # closed | open | half_open


@dataclass
class CircuitBreakerStatus:
    circuits: list[CircuitEntry]
    open_count: int
    half_open_count: int


@dataclass
class AlertEntry:
    timestamp: str
    anomaly_type: str
    severity: str
    mcp_server: str
    description: str


@dataclass
class DashboardSnapshot:
    """Immutable point-in-time view of the whole security posture."""

    timestamp: datetime
    credentials: CredentialStatus
    verification: VerificationStatus
    rate_limits: RateLimitStatus
    circuit_breakers: CircuitBreakerStatus
    recent_alerts: list[AlertEntry]
    isolated_servers: list[str]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class SecurityDashboard:
    """
    Aggregate security-posture data for display.

    Args:
        audit_log_path:    path to security_audit.log (JSON lines)
        alert_log_path:    path to anomaly_alerts.log
        incident_log_path: path to incident_response.log
        credential_vault:  optional CredentialVault instance
        mcp_verifier:      optional MCPVerifier instance
        rate_limiter:      optional RateLimiter instance
    """

    def __init__(
        self,
        audit_log_path: Path,
        alert_log_path: Path,
        incident_log_path: Path,
        credential_vault=None,
        mcp_verifier=None,
        rate_limiter=None,
    ):
        self._audit_log = audit_log_path
        self._alert_log = alert_log_path
        self._incident_log = incident_log_path
        self._vault = credential_vault
        self._verifier = mcp_verifier
        self._rate_limiter = rate_limiter

    # ------------------------------------------------------------------
    # Individual status methods
    # ------------------------------------------------------------------

    def get_credential_status(self) -> CredentialStatus:
        """Return count and list of stored credential services."""
        if self._vault is None:
            return CredentialStatus(services=[], count=0, keyring_backed=False)

        services = self._vault.list_services()
        # list_services returns [] when keyring is the active backend
        keyring_backed = len(services) == 0  # likely keyring if nothing listed
        return CredentialStatus(
            services=services,
            count=len(services),
            keyring_backed=keyring_backed,
        )

    def get_mcp_verification_status(self) -> VerificationStatus:
        """Return trusted server names from the MCP verifier trust store."""
        if self._verifier is None:
            return VerificationStatus(trusted_servers=[], trusted_count=0)

        trusted = self._verifier.list_trusted()  # {name: sig}
        return VerificationStatus(
            trusted_servers=list(trusted.keys()),
            trusted_count=len(trusted),
        )

    def get_rate_limit_status(self) -> RateLimitStatus:
        """Return current token levels for all active rate-limit buckets."""
        if self._rate_limiter is None:
            return RateLimitStatus(buckets=[], throttled_count=0)

        entries: list[RateLimitEntry] = []
        throttled = 0

        # Access internal buckets dict – keys are "server:action_type"
        for key, bucket in self._rate_limiter._buckets.items():
            parts = key.split(":", 1)
            server = parts[0] if parts else key
            action_type = parts[1] if len(parts) > 1 else "unknown"

            # Refill before reading
            self._rate_limiter._refill(bucket)

            entry = RateLimitEntry(
                server=server,
                action_type=action_type,
                tokens_remaining=round(bucket.tokens, 2),
                max_tokens=bucket.max_tokens,
            )
            entries.append(entry)

            # Flag as throttled if below 10 %
            if bucket.tokens < bucket.max_tokens * 0.1:
                throttled += 1

        return RateLimitStatus(buckets=entries, throttled_count=throttled)

    def get_recent_alerts(self, limit: int = 10) -> list[AlertEntry]:
        """Return the most recent anomaly alerts."""
        if not self._alert_log.exists():
            return []

        import json

        lines = self._alert_log.read_text().strip().split("\n")
        alerts = []
        for line in lines[-limit:]:
            if not line:
                continue
            raw = json.loads(line)
            alerts.append(AlertEntry(
                timestamp=raw.get("timestamp", ""),
                anomaly_type=raw.get("anomaly_type", ""),
                severity=raw.get("severity", ""),
                mcp_server=raw.get("mcp_server", ""),
                description=raw.get("description", ""),
            ))
        return alerts

    def get_circuit_breaker_status(self) -> CircuitBreakerStatus:
        """Return state of every circuit breaker known to the runtime.

        Reads the isolated-servers log so that at least isolation records
        are surfaced even when no live MCPGuard instance is available.
        """
        circuits: list[CircuitEntry] = []
        open_count = 0
        half_open_count = 0

        # Surface isolation records as "open" circuits
        if self._incident_log.exists():
            import json

            lines = self._incident_log.read_text().strip().split("\n")
            isolated_set: set[str] = set()
            for line in lines:
                if not line:
                    continue
                record = json.loads(line)
                details = record.get("details", {})
                if record.get("action_type") == "mcp_isolated":
                    isolated_set.add(details.get("mcp_server", ""))
                elif record.get("action_type") == "mcp_restored":
                    isolated_set.discard(details.get("mcp_server", ""))

            for server in isolated_set:
                circuits.append(CircuitEntry(server=server, state="open"))
                open_count += 1

        return CircuitBreakerStatus(
            circuits=circuits,
            open_count=open_count,
            half_open_count=half_open_count,
        )

    # ------------------------------------------------------------------
    # Full snapshot
    # ------------------------------------------------------------------

    def snapshot(self, alert_limit: int = 10) -> DashboardSnapshot:
        """Build a complete point-in-time dashboard snapshot."""
        return DashboardSnapshot(
            timestamp=datetime.now(timezone.utc),
            credentials=self.get_credential_status(),
            verification=self.get_mcp_verification_status(),
            rate_limits=self.get_rate_limit_status(),
            circuit_breakers=self.get_circuit_breaker_status(),
            recent_alerts=self.get_recent_alerts(limit=alert_limit),
            isolated_servers=[
                c.server for c in self.get_circuit_breaker_status().circuits
                if c.state == "open"
            ],
        )

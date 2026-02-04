"""
Security Webhook Notifier – fire-and-forget HTTP POST for security events
(spec 004 Polish T047).

Loads the webhook URL from ``config/security.yaml`` (key
``notifications.webhook_url``).  Falls back to the environment variable
``FTE_SECURITY_WEBHOOK_URL``.  If neither is set the notifier is a no-op.

Payload schema (JSON)
    {
        "source":      "fte-security",
        "event_type":  str,          # e.g. "anomaly_detected"
        "severity":    str,          # low | medium | high | critical
        "timestamp":   ISO-8601,
        "details":     dict          # event-specific payload
    }
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class SecurityWebhook:
    """
    Send security-event notifications via HTTP POST.

    Args:
        webhook_url: target URL.  If *None* the class will attempt to
                     resolve the URL from ``config/security.yaml`` and
                     then from the ``FTE_SECURITY_WEBHOOK_URL`` env var.
        timeout_s:   HTTP request timeout in seconds (default 5).
    """

    def __init__(self, webhook_url: Optional[str] = None, timeout_s: float = 5.0):
        self._url = webhook_url or self._resolve_url()
        self._timeout = timeout_s

    # ------------------------------------------------------------------
    # High-level event helpers
    # ------------------------------------------------------------------

    def notify_anomaly(self, alert: dict) -> bool:
        """Send notification for a detected anomaly."""
        return self._send(
            event_type="anomaly_detected",
            severity=alert.get("severity", "medium"),
            details={
                "alert_id": alert.get("alert_id"),
                "anomaly_type": alert.get("anomaly_type"),
                "mcp_server": alert.get("mcp_server"),
                "description": alert.get("description"),
                "baseline_value": alert.get("baseline_value"),
                "observed_value": alert.get("observed_value"),
            },
        )

    def notify_isolation(self, mcp_server: str, reason: str) -> bool:
        """Send notification when an MCP server is isolated."""
        return self._send(
            event_type="mcp_isolated",
            severity="high",
            details={"mcp_server": mcp_server, "reason": reason},
        )

    def notify_credential_rotation(self, reason: str) -> bool:
        """Send notification for mass credential rotation."""
        return self._send(
            event_type="credential_rotation",
            severity="critical",
            details={"reason": reason, "scope": "all"},
        )

    def notify_circuit_trip(self, server: str) -> bool:
        """Send notification when a circuit breaker trips."""
        return self._send(
            event_type="circuit_breaker_tripped",
            severity="high",
            details={"mcp_server": server},
        )

    def notify_health_degraded(self, checks: dict) -> bool:
        """Send notification when health check detects degradation."""
        return self._send(
            event_type="health_degraded",
            severity="medium",
            details=checks,
        )

    # ------------------------------------------------------------------
    # Core send
    # ------------------------------------------------------------------

    def _send(self, event_type: str, severity: str, details: dict) -> bool:
        """POST a JSON payload.  Returns True on success, False otherwise."""
        if not self._url:
            return False  # no-op when URL not configured

        payload = {
            "source": "fte-security",
            "event_type": event_type,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        }

        try:
            import urllib.request

            body = json.dumps(payload).encode()
            req = urllib.request.Request(
                self._url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return resp.status < 400
        except Exception:
            # Fire-and-forget – never let webhook failure break the caller
            return False

    # ------------------------------------------------------------------
    # URL resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_url() -> Optional[str]:
        """Try config file first, then env var."""
        # 1. config/security.yaml
        config_path = Path("config") / "security.yaml"
        if config_path.exists():
            try:
                # Minimal YAML parse – avoid pulling in PyYAML just for this
                for line in config_path.read_text().splitlines():
                    stripped = line.strip()
                    if stripped.startswith("webhook_url:"):
                        url = stripped.split(":", 1)[1].strip().strip("'\"")
                        if url and url != "null":
                            return url
            except Exception:
                pass

        # 2. environment variable
        return os.environ.get("FTE_SECURITY_WEBHOOK_URL")

"""
Webhook Notifications — fire-and-forget HTTP POST for orchestrator events.

Sends event notifications to configured webhook URL (e.g., Slack, Discord, custom).
All operations are non-blocking and failures are logged but don't affect orchestrator.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class WebhookNotifier:
    """
    Fire-and-forget webhook notifier for orchestrator events.

    Sends HTTP POST to configured webhook URL. Failures are silently ignored
    to prevent webhook issues from blocking the orchestrator.
    """

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        enabled: bool = True,
        timeout: float = 5.0,
    ):
        self.webhook_url = webhook_url
        self.enabled = enabled and REQUESTS_AVAILABLE and webhook_url
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Event notifications
    # ------------------------------------------------------------------

    def task_failed(self, task_name: str, error: str, priority: float = 0.0) -> None:
        """Notify that a task has failed."""
        if not self.enabled:
            return

        payload = {
            "event": "task_failed",
            "task_name": task_name,
            "error": error[:200],
            "priority": round(priority, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._send(payload)

    def health_degraded(self, status: str, message: str) -> None:
        """Notify that orchestrator health is degraded or unhealthy."""
        if not self.enabled:
            return

        payload = {
            "event": "health_degraded",
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._send(payload)

    def orchestrator_stopped(self, reason: str = "unknown") -> None:
        """Notify that the orchestrator has stopped."""
        if not self.enabled:
            return

        payload = {
            "event": "orchestrator_stopped",
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._send(payload)

    def orchestrator_started(self, vault_path: Path, dry_run: bool = False) -> None:
        """Notify that the orchestrator has started."""
        if not self.enabled:
            return

        payload = {
            "event": "orchestrator_started",
            "vault_path": str(vault_path),
            "dry_run": dry_run,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._send(payload)

    def high_error_rate(self, error_rate: float, threshold: float) -> None:
        """Notify that error rate has exceeded threshold."""
        if not self.enabled:
            return

        payload = {
            "event": "high_error_rate",
            "error_rate": round(error_rate, 4),
            "threshold": round(threshold, 4),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._send(payload)

    # ------------------------------------------------------------------
    # Slack-specific formatting
    # ------------------------------------------------------------------

    def format_for_slack(self, payload: dict) -> dict:
        """
        Format payload as Slack message with rich formatting.

        Returns a Slack-compatible payload with blocks and attachments.
        """
        event = payload.get("event", "unknown")

        # Color coding
        colors = {
            "task_failed": "#ff0000",  # red
            "health_degraded": "#ff9900",  # orange
            "high_error_rate": "#ff9900",  # orange
            "orchestrator_stopped": "#999999",  # gray
            "orchestrator_started": "#00ff00",  # green
        }

        # Build Slack message
        slack_payload = {
            "attachments": [
                {
                    "color": colors.get(event, "#999999"),
                    "title": f"Orchestrator Event: {event.replace('_', ' ').title()}",
                    "fields": [],
                    "footer": "AI Employee Orchestrator",
                    "ts": int(datetime.fromisoformat(payload["timestamp"]).timestamp()),
                }
            ]
        }

        # Add event-specific fields
        for key, value in payload.items():
            if key not in ["event", "timestamp"]:
                slack_payload["attachments"][0]["fields"].append(
                    {
                        "title": key.replace("_", " ").title(),
                        "value": str(value),
                        "short": True,
                    }
                )

        return slack_payload

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _send(self, payload: dict) -> bool:
        """
        Send payload to webhook URL.

        Returns True on success, False on failure.
        Failures are logged but don't raise exceptions.
        """
        if not self.enabled or not REQUESTS_AVAILABLE:
            return False

        try:
            # Detect if webhook is Slack
            is_slack = "slack.com" in self.webhook_url.lower()

            if is_slack:
                payload = self.format_for_slack(payload)

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"},
            )

            # Don't raise on HTTP errors - just log and continue
            if response.status_code >= 400:
                return False

            return True

        except Exception:
            # Silently fail - webhook errors shouldn't block orchestrator
            return False

    # ------------------------------------------------------------------
    # Configuration helper
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls, config: "OrchestratorConfig") -> "WebhookNotifier":
        """
        Create WebhookNotifier from orchestrator config.

        Reads webhook settings from config.notifications dict.
        """
        if not hasattr(config, "notifications_enabled"):
            # No notifications config - disabled
            return cls(enabled=False)

        return cls(
            webhook_url=config.notification_webhook_url,
            enabled=config.notifications_enabled,
            timeout=5.0,
        )

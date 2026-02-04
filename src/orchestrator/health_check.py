"""
Health Check — orchestrator monitoring and status assessment.

Exposes health checks for scheduler liveness, task backlog, error rate,
and completion staleness.  Aggregates into a single health status
(healthy / degraded / unhealthy) suitable for monitoring tools.
"""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.orchestrator.metrics import MetricsCollector


class HealthCheck:
    """Orchestrator health assessment with configurable thresholds."""

    def __init__(
        self,
        vault_path: Path,
        metrics_collector: Optional[MetricsCollector] = None,
    ):
        """
        Args:
            vault_path: Orchestrator vault (e.g., ~/AI_Employee_Vault)
            metrics_collector: Optional MetricsCollector instance; if None,
                will instantiate one at default path.
        """
        self._vault_path = vault_path
        self._checkpoint_path = vault_path.parent / ".fte" / "orchestrator.checkpoint.json"
        if metrics_collector:
            self._metrics = metrics_collector
        else:
            metrics_path = vault_path.parent / ".fte" / "orchestrator_metrics.log"
            self._metrics = MetricsCollector(log_path=metrics_path)

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def check_scheduler_alive(self, max_stale_seconds: int = 300) -> tuple[bool, str]:
        """Check if orchestrator checkpoint has been updated recently.

        Args:
            max_stale_seconds: Checkpoint older than this is considered stale (default: 5 min)

        Returns:
            (is_healthy, message)
        """
        if not self._checkpoint_path.exists():
            return False, "Checkpoint file not found — orchestrator may not have run yet"

        mtime = self._checkpoint_path.stat().st_mtime
        age = time.time() - mtime
        if age > max_stale_seconds:
            return False, f"Checkpoint stale ({int(age)}s old, threshold {max_stale_seconds}s)"
        return True, f"Checkpoint fresh ({int(age)}s old)"

    def check_task_backlog(self, threshold: int = 20) -> tuple[bool, str]:
        """Check pending task count in Needs_Action folder.

        Args:
            threshold: Warn if pending tasks exceed this number

        Returns:
            (is_healthy, message)
        """
        needs_action = self._vault_path / "Needs_Action"
        if not needs_action.exists():
            return True, "No Needs_Action folder — backlog is 0"

        pending = list(needs_action.glob("*.md"))
        count = len(pending)
        if count > threshold:
            return False, f"Task backlog high: {count} tasks pending (threshold {threshold})"
        return True, f"Task backlog OK: {count} tasks pending"

    def check_error_rate(self, threshold: float = 0.10, window_hours: int = 24) -> tuple[bool, str]:
        """Check recent error rate from metrics.

        Args:
            threshold: Warn if error rate exceeds this fraction (e.g., 0.10 = 10%)
            window_hours: Time window for error rate calculation

        Returns:
            (is_healthy, message)
        """
        since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        error_rate = self._metrics.calculate_error_rate(since=since)

        if error_rate > threshold:
            return False, f"Error rate high: {error_rate * 100:.1f}% (threshold {threshold * 100:.1f}%)"
        return True, f"Error rate OK: {error_rate * 100:.1f}%"

    def check_last_completion_time(self, max_idle_seconds: int = 3600) -> tuple[bool, str]:
        """Check time since last task completion.

        Args:
            max_idle_seconds: Warn if no completions in the last N seconds (default: 1 hour)

        Returns:
            (is_healthy, message)
        """
        events = self._metrics._load_events()
        completed = [e for e in events if e["event"] == "task_completed"]

        if not completed:
            return False, "No completed tasks recorded — orchestrator may not have run"

        last_ts = datetime.fromisoformat(completed[-1]["timestamp"])
        idle = (datetime.now(timezone.utc) - last_ts).total_seconds()

        if idle > max_idle_seconds:
            return False, f"No completions in {int(idle)}s (threshold {max_idle_seconds}s)"
        return True, f"Last completion {int(idle)}s ago"

    # ------------------------------------------------------------------
    # Aggregate status
    # ------------------------------------------------------------------

    def get_health_status(
        self,
        max_stale_seconds: int = 300,
        backlog_threshold: int = 20,
        error_rate_threshold: float = 0.10,
        max_idle_seconds: int = 3600,
    ) -> dict:
        """Run all health checks and aggregate into a single status.

        Returns:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "timestamp": ISO timestamp,
                "checks": {
                    "scheduler_alive": {"ok": bool, "message": str},
                    "task_backlog": {"ok": bool, "message": str},
                    "error_rate": {"ok": bool, "message": str},
                    "last_completion": {"ok": bool, "message": str},
                }
            }

        Status rules:
            - healthy: all checks pass
            - degraded: 1-2 checks fail
            - unhealthy: 3+ checks fail
        """
        checks = {
            "scheduler_alive": self.check_scheduler_alive(max_stale_seconds),
            "task_backlog": self.check_task_backlog(backlog_threshold),
            "error_rate": self.check_error_rate(error_rate_threshold),
            "last_completion": self.check_last_completion_time(max_idle_seconds),
        }

        checks_formatted = {
            name: {"ok": ok, "message": msg}
            for name, (ok, msg) in checks.items()
        }

        failed_count = sum(1 for ok, _ in checks.values() if not ok)

        if failed_count == 0:
            status = "healthy"
        elif failed_count <= 2:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks_formatted,
        }

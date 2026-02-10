"""Tests for HealthCheck (spec 006 US9)."""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from orchestrator.health_check import HealthCheck
from orchestrator.metrics import MetricsCollector

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vault_path(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


@pytest.fixture
def metrics_collector(tmp_path):
    log = tmp_path / ".fte" / "orchestrator_metrics.log"
    return MetricsCollector(log_path=log)


@pytest.fixture
def health_check(vault_path, metrics_collector):
    return HealthCheck(vault_path=vault_path, metrics_collector=metrics_collector)


def _seed_checkpoint(vault_path: Path, age_seconds: int = 0) -> None:
    """Create a checkpoint file with specified age."""
    ckpt_path = vault_path.parent / ".fte" / "orchestrator.checkpoint.json"
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    ckpt_path.write_text('{"last_iteration": 1}')
    if age_seconds > 0:
        # Backdate the file
        mtime = time.time() - age_seconds
        import os

        os.utime(ckpt_path, (mtime, mtime))


def _seed_metrics(collector: MetricsCollector, events: list[dict]) -> None:
    """Seed metrics log with pre-timestamped events."""
    collector._log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(collector._log_path, "w") as fh:
        for ev in events:
            fh.write(json.dumps(ev) + "\n")


def _seed_needs_action(vault_path: Path, count: int) -> None:
    """Create N .md files in Needs_Action folder."""
    needs_action = vault_path / "Needs_Action"
    needs_action.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (needs_action / f"task_{i}.md").write_text(f"# Task {i}")


# ---------------------------------------------------------------------------
# Scheduler alive check
# ---------------------------------------------------------------------------


class TestSchedulerAlive:
    def test_no_checkpoint_returns_unhealthy(self, health_check):
        ok, msg = health_check.check_scheduler_alive()
        assert ok is False
        assert "not found" in msg.lower()

    def test_fresh_checkpoint_returns_healthy(self, vault_path, health_check):
        _seed_checkpoint(vault_path, age_seconds=10)
        ok, msg = health_check.check_scheduler_alive()
        assert ok is True
        assert "fresh" in msg.lower()

    def test_stale_checkpoint_returns_unhealthy(self, vault_path, health_check):
        _seed_checkpoint(vault_path, age_seconds=600)  # 10 min old
        ok, msg = health_check.check_scheduler_alive(max_stale_seconds=300)
        assert ok is False
        assert "stale" in msg.lower()

    def test_custom_stale_threshold(self, vault_path, health_check):
        _seed_checkpoint(vault_path, age_seconds=400)
        ok, msg = health_check.check_scheduler_alive(max_stale_seconds=500)
        assert ok is True


# ---------------------------------------------------------------------------
# Task backlog check
# ---------------------------------------------------------------------------


class TestTaskBacklog:
    def test_no_needs_action_folder_returns_healthy(self, health_check):
        ok, msg = health_check.check_task_backlog()
        assert ok is True
        assert "0" in msg

    def test_below_threshold_returns_healthy(self, vault_path, health_check):
        _seed_needs_action(vault_path, count=5)
        ok, msg = health_check.check_task_backlog(threshold=20)
        assert ok is True
        assert "5 tasks" in msg

    def test_above_threshold_returns_unhealthy(self, vault_path, health_check):
        _seed_needs_action(vault_path, count=25)
        ok, msg = health_check.check_task_backlog(threshold=20)
        assert ok is False
        assert "25 tasks" in msg
        assert "high" in msg.lower()

    def test_exactly_at_threshold_returns_healthy(self, vault_path, health_check):
        _seed_needs_action(vault_path, count=20)
        ok, msg = health_check.check_task_backlog(threshold=20)
        assert ok is True


# ---------------------------------------------------------------------------
# Error rate check
# ---------------------------------------------------------------------------


class TestErrorRateCheck:
    def test_no_events_returns_healthy(self, health_check):
        ok, msg = health_check.check_error_rate(threshold=0.10)
        assert ok is True
        assert "0.0%" in msg

    def test_below_threshold_returns_healthy(self, health_check, metrics_collector):
        now = datetime.now(timezone.utc)
        _seed_metrics(
            metrics_collector,
            [
                {
                    "event": "task_completed",
                    "task_name": "a.md",
                    "duration_seconds": 5.0,
                    "timestamp": (now - timedelta(hours=1)).isoformat(),
                },
                {
                    "event": "task_completed",
                    "task_name": "b.md",
                    "duration_seconds": 5.0,
                    "timestamp": (now - timedelta(hours=1)).isoformat(),
                },
                {
                    "event": "task_failed",
                    "task_name": "c.md",
                    "duration_seconds": 5.0,
                    "error": "e",
                    "timestamp": (now - timedelta(hours=1)).isoformat(),
                },
            ],
        )
        # 1/3 = 33% > 10%, but let's use a more realistic test
        ok, msg = health_check.check_error_rate(threshold=0.40)  # 40%
        assert ok is True
        assert "33." in msg  # 33.3%

    def test_above_threshold_returns_unhealthy(self, health_check, metrics_collector):
        now = datetime.now(timezone.utc)
        _seed_metrics(
            metrics_collector,
            [
                {
                    "event": "task_completed",
                    "task_name": "a.md",
                    "duration_seconds": 5.0,
                    "timestamp": (now - timedelta(hours=1)).isoformat(),
                },
                {
                    "event": "task_failed",
                    "task_name": "b.md",
                    "duration_seconds": 5.0,
                    "error": "e",
                    "timestamp": (now - timedelta(hours=1)).isoformat(),
                },
                {
                    "event": "task_failed",
                    "task_name": "c.md",
                    "duration_seconds": 5.0,
                    "error": "e",
                    "timestamp": (now - timedelta(hours=1)).isoformat(),
                },
            ],
        )
        # 2/3 = 66.7% > 10%
        ok, msg = health_check.check_error_rate(threshold=0.10)
        assert ok is False
        assert "66." in msg
        assert "high" in msg.lower()

    def test_window_excludes_old_events(self, health_check, metrics_collector):
        now = datetime.now(timezone.utc)
        _seed_metrics(
            metrics_collector,
            [
                {
                    "event": "task_failed",
                    "task_name": "old.md",
                    "duration_seconds": 5.0,
                    "error": "e",
                    "timestamp": (now - timedelta(hours=48)).isoformat(),
                },
                {
                    "event": "task_completed",
                    "task_name": "new.md",
                    "duration_seconds": 5.0,
                    "timestamp": (now - timedelta(hours=1)).isoformat(),
                },
            ],
        )
        # Only the completed event is in the 24h window → 0% error
        ok, msg = health_check.check_error_rate(threshold=0.10, window_hours=24)
        assert ok is True
        assert "0.0%" in msg


# ---------------------------------------------------------------------------
# Last completion time check
# ---------------------------------------------------------------------------


class TestLastCompletionTime:
    def test_no_completions_returns_unhealthy(self, health_check):
        ok, msg = health_check.check_last_completion_time()
        assert ok is False
        assert "no completed" in msg.lower()

    def test_recent_completion_returns_healthy(self, health_check, metrics_collector):
        now = datetime.now(timezone.utc)
        _seed_metrics(
            metrics_collector,
            [
                {
                    "event": "task_completed",
                    "task_name": "a.md",
                    "duration_seconds": 5.0,
                    "timestamp": (now - timedelta(seconds=30)).isoformat(),
                },
            ],
        )
        ok, msg = health_check.check_last_completion_time(max_idle_seconds=3600)
        assert ok is True
        assert "30" in msg or "3" in msg  # "30s ago" or similar

    def test_stale_completion_returns_unhealthy(self, health_check, metrics_collector):
        now = datetime.now(timezone.utc)
        _seed_metrics(
            metrics_collector,
            [
                {
                    "event": "task_completed",
                    "task_name": "a.md",
                    "duration_seconds": 5.0,
                    "timestamp": (now - timedelta(seconds=7200)).isoformat(),
                },
            ],
        )
        ok, msg = health_check.check_last_completion_time(max_idle_seconds=3600)
        assert ok is False
        assert "7200" in msg or "72" in msg
        assert "no completions" in msg.lower()

    def test_custom_idle_threshold(self, health_check, metrics_collector):
        now = datetime.now(timezone.utc)
        _seed_metrics(
            metrics_collector,
            [
                {
                    "event": "task_completed",
                    "task_name": "a.md",
                    "duration_seconds": 5.0,
                    "timestamp": (now - timedelta(seconds=500)).isoformat(),
                },
            ],
        )
        ok, msg = health_check.check_last_completion_time(max_idle_seconds=600)
        assert ok is True


# ---------------------------------------------------------------------------
# Aggregate health status
# ---------------------------------------------------------------------------


class TestAggregateHealthStatus:
    def test_all_checks_pass_returns_healthy(
        self, vault_path, health_check, metrics_collector
    ):
        # Seed checkpoint, low backlog, low error rate, recent completion
        _seed_checkpoint(vault_path, age_seconds=10)
        _seed_needs_action(vault_path, count=5)
        now = datetime.now(timezone.utc)
        _seed_metrics(
            metrics_collector,
            [
                {
                    "event": "task_completed",
                    "task_name": "a.md",
                    "duration_seconds": 5.0,
                    "timestamp": (now - timedelta(seconds=30)).isoformat(),
                },
            ],
        )

        result = health_check.get_health_status()
        assert result["status"] == "healthy"
        assert all(c["ok"] for c in result["checks"].values())

    def test_one_check_fails_returns_degraded(
        self, vault_path, health_check, metrics_collector
    ):
        # Good checkpoint, high backlog, low error rate, recent completion
        _seed_checkpoint(vault_path, age_seconds=10)
        _seed_needs_action(vault_path, count=50)  # high backlog
        now = datetime.now(timezone.utc)
        _seed_metrics(
            metrics_collector,
            [
                {
                    "event": "task_completed",
                    "task_name": "a.md",
                    "duration_seconds": 5.0,
                    "timestamp": (now - timedelta(seconds=30)).isoformat(),
                },
            ],
        )

        result = health_check.get_health_status()
        assert result["status"] == "degraded"
        assert result["checks"]["task_backlog"]["ok"] is False
        assert result["checks"]["scheduler_alive"]["ok"] is True

    def test_two_checks_fail_returns_degraded(
        self, vault_path, health_check, metrics_collector
    ):
        # Stale checkpoint, high backlog, low error rate, recent completion
        _seed_checkpoint(vault_path, age_seconds=600)  # stale
        _seed_needs_action(vault_path, count=50)  # high backlog
        now = datetime.now(timezone.utc)
        _seed_metrics(
            metrics_collector,
            [
                {
                    "event": "task_completed",
                    "task_name": "a.md",
                    "duration_seconds": 5.0,
                    "timestamp": (now - timedelta(seconds=30)).isoformat(),
                },
            ],
        )

        result = health_check.get_health_status()
        assert result["status"] == "degraded"
        failed = [name for name, check in result["checks"].items() if not check["ok"]]
        assert len(failed) == 2

    def test_three_checks_fail_returns_unhealthy(
        self, vault_path, health_check, metrics_collector
    ):
        # No checkpoint, high backlog, high error rate, recent completion
        _seed_needs_action(vault_path, count=50)
        now = datetime.now(timezone.utc)
        _seed_metrics(
            metrics_collector,
            [
                {
                    "event": "task_failed",
                    "task_name": "a.md",
                    "duration_seconds": 5.0,
                    "error": "e",
                    "timestamp": (now - timedelta(seconds=30)).isoformat(),
                },
                {
                    "event": "task_failed",
                    "task_name": "b.md",
                    "duration_seconds": 5.0,
                    "error": "e",
                    "timestamp": (now - timedelta(seconds=30)).isoformat(),
                },
            ],
        )

        result = health_check.get_health_status()
        assert result["status"] == "unhealthy"
        failed = [name for name, check in result["checks"].items() if not check["ok"]]
        assert len(failed) >= 3

    def test_result_structure(self, health_check):
        result = health_check.get_health_status()
        assert "status" in result
        assert "timestamp" in result
        assert "checks" in result
        assert isinstance(result["checks"], dict)
        for check_name in [
            "scheduler_alive",
            "task_backlog",
            "error_rate",
            "last_completion",
        ]:
            assert check_name in result["checks"]
            assert "ok" in result["checks"][check_name]
            assert "message" in result["checks"][check_name]

    def test_custom_thresholds(self, vault_path, health_check, metrics_collector):
        _seed_checkpoint(vault_path, age_seconds=10)
        _seed_needs_action(vault_path, count=25)
        now = datetime.now(timezone.utc)
        _seed_metrics(
            metrics_collector,
            [
                {
                    "event": "task_completed",
                    "task_name": "a.md",
                    "duration_seconds": 5.0,
                    "timestamp": (now - timedelta(seconds=30)).isoformat(),
                },
            ],
        )

        # With default threshold (20), backlog fails
        result1 = health_check.get_health_status()
        assert result1["checks"]["task_backlog"]["ok"] is False

        # With raised threshold (30), backlog passes
        result2 = health_check.get_health_status(backlog_threshold=30)
        assert result2["checks"]["task_backlog"]["ok"] is True


# ---------------------------------------------------------------------------
# Integration with Orchestrator (smoke test)
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_health_check_via_orchestrator_instance(self, tmp_path):
        """Smoke test: instantiate Orchestrator and verify HealthCheck can read its state."""
        from src.orchestrator.models import OrchestratorConfig
        from src.orchestrator.scheduler import Orchestrator

        vault = tmp_path / "vault"
        vault.mkdir()
        cfg = OrchestratorConfig(vault_path=vault)
        orch = Orchestrator(config=cfg, dry_run=True)

        # Seed a completed event
        now = datetime.now(timezone.utc)
        orch._metrics._log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(orch._metrics._log_path, "w") as fh:
            fh.write(
                json.dumps(
                    {
                        "event": "task_completed",
                        "task_name": "test.md",
                        "duration_seconds": 2.5,
                        "timestamp": (now - timedelta(seconds=30)).isoformat(),
                    }
                )
                + "\n"
            )

        # Create HealthCheck pointing at same vault + metrics
        health = HealthCheck(vault_path=vault, metrics_collector=orch._metrics)
        result = health.get_health_status()

        # Scheduler alive will fail (no checkpoint yet), but last_completion should pass
        assert result["checks"]["last_completion"]["ok"] is True

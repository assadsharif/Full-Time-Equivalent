"""Tests for MetricsCollector (spec 006 US8)."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.orchestrator.metrics import MetricsCollector


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def log_path(tmp_path):
    return tmp_path / "metrics.log"


@pytest.fixture
def collector(log_path):
    return MetricsCollector(log_path=log_path)


def _ts(minutes_ago: int = 0) -> str:
    """Return an ISO timestamp N minutes in the past."""
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def _seed(log_path: Path, events: list[dict]) -> None:
    """Write pre-stamped events directly to the log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w") as fh:
        for ev in events:
            fh.write(json.dumps(ev) + "\n")


# ---------------------------------------------------------------------------
# Event writing
# ---------------------------------------------------------------------------


class TestEventWriting:
    def test_task_started_creates_log(self, collector, log_path):
        collector.task_started("my_task.md", priority=3.5)
        assert log_path.exists()
        event = json.loads(log_path.read_text().strip())
        assert event["event"] == "task_started"
        assert event["task_name"] == "my_task.md"
        assert event["priority"] == 3.5
        assert "timestamp" in event

    def test_task_completed_appends(self, collector, log_path):
        collector.task_started("t.md")
        collector.task_completed("t.md", duration_seconds=12.5)
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 2
        ev = json.loads(lines[1])
        assert ev["event"] == "task_completed"
        assert ev["duration_seconds"] == 12.5

    def test_task_failed_records_error(self, collector, log_path):
        collector.task_started("t.md")
        collector.task_failed("t.md", duration_seconds=5.0, error="timeout")
        lines = log_path.read_text().strip().split("\n")
        ev = json.loads(lines[1])
        assert ev["event"] == "task_failed"
        assert ev["error"] == "timeout"
        assert ev["duration_seconds"] == 5.0

    def test_multiple_tasks_append_sequentially(self, collector, log_path):
        for i in range(5):
            collector.task_started(f"task_{i}.md")
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 5

    def test_duration_rounds_to_three_decimals(self, collector, log_path):
        collector.task_completed("t.md", duration_seconds=1.23456789)
        ev = json.loads(log_path.read_text().strip())
        assert ev["duration_seconds"] == 1.235

    def test_parent_dirs_created_automatically(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "metrics.log"
        c = MetricsCollector(log_path=deep)
        c.task_started("x.md")
        assert deep.exists()


# ---------------------------------------------------------------------------
# Event loading with since filter
# ---------------------------------------------------------------------------


class TestEventLoading:
    def test_load_empty_log(self, collector, log_path):
        log_path.write_text("")
        assert collector._load_events() == []

    def test_load_nonexistent_log(self, collector):
        # log_path does not exist yet
        assert collector._load_events() == []

    def test_load_all_events(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_started", "task_name": "a.md", "priority": 1.0, "timestamp": _ts(60)},
            {"event": "task_completed", "task_name": "a.md", "duration_seconds": 10.0, "timestamp": _ts(55)},
        ])
        events = collector._load_events()
        assert len(events) == 2

    def test_since_filter_excludes_old_events(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_started", "task_name": "old.md", "priority": 1.0, "timestamp": _ts(120)},
            {"event": "task_started", "task_name": "new.md", "priority": 2.0, "timestamp": _ts(5)},
        ])
        since = datetime.now(timezone.utc) - timedelta(minutes=10)
        events = collector._load_events(since=since)
        assert len(events) == 1
        assert events[0]["task_name"] == "new.md"

    def test_malformed_lines_are_skipped(self, collector, log_path):
        log_path.write_text(
            '{"event": "task_started", "task_name": "ok.md", "priority": 0, "timestamp": "' + _ts(5) + '"}\n'
            "not-json\n"
        )
        events = collector._load_events()
        assert len(events) == 1

    def test_blank_lines_are_skipped(self, collector, log_path):
        log_path.write_text(
            '{"event": "task_started", "task_name": "ok.md", "priority": 0, "timestamp": "' + _ts(5) + '"}\n'
            "\n\n"
        )
        events = collector._load_events()
        assert len(events) == 1


# ---------------------------------------------------------------------------
# Throughput
# ---------------------------------------------------------------------------


class TestThroughput:
    def test_no_events_returns_zero(self, collector):
        assert collector.calculate_throughput() == 0.0

    def test_no_completed_events_returns_zero(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_started", "task_name": "a.md", "priority": 1.0, "timestamp": _ts(30)},
        ])
        assert collector.calculate_throughput() == 0.0

    def test_throughput_calculation(self, collector, log_path):
        # 3 completions, earliest 60 minutes ago → ~3 tasks / ~1 hr
        _seed(log_path, [
            {"event": "task_completed", "task_name": "a.md", "duration_seconds": 10.0, "timestamp": _ts(60)},
            {"event": "task_completed", "task_name": "b.md", "duration_seconds": 10.0, "timestamp": _ts(30)},
            {"event": "task_completed", "task_name": "c.md", "duration_seconds": 10.0, "timestamp": _ts(5)},
        ])
        tp = collector.calculate_throughput()
        # Window ≈ 60 min; 3 tasks → ~3.0 tasks/hr (allow ±0.5 for timing)
        assert 2.5 <= tp <= 3.5

    def test_throughput_with_since(self, collector, log_path):
        # 2 completions in last 30 minutes; 1 old completion excluded
        _seed(log_path, [
            {"event": "task_completed", "task_name": "old.md", "duration_seconds": 10.0, "timestamp": _ts(120)},
            {"event": "task_completed", "task_name": "a.md", "duration_seconds": 10.0, "timestamp": _ts(20)},
            {"event": "task_completed", "task_name": "b.md", "duration_seconds": 10.0, "timestamp": _ts(10)},
        ])
        since = datetime.now(timezone.utc) - timedelta(minutes=30)
        tp = collector.calculate_throughput(since=since)
        # 2 tasks / 0.5 hr = 4.0 (±1.0 tolerance)
        assert 3.0 <= tp <= 5.0

    def test_failed_events_not_counted_in_throughput(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_completed", "task_name": "a.md", "duration_seconds": 5.0, "timestamp": _ts(60)},
            {"event": "task_failed", "task_name": "b.md", "duration_seconds": 5.0, "error": "x", "timestamp": _ts(30)},
        ])
        tp = collector.calculate_throughput()
        # Only 1 completion → ~1 task / ~1 hr
        assert 0.5 <= tp <= 1.5


# ---------------------------------------------------------------------------
# Average latency
# ---------------------------------------------------------------------------


class TestAvgLatency:
    def test_no_events_returns_zero(self, collector):
        assert collector.calculate_avg_latency() == 0.0

    def test_only_started_returns_zero(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_started", "task_name": "a.md", "priority": 1.0, "timestamp": _ts(10)},
        ])
        assert collector.calculate_avg_latency() == 0.0

    def test_avg_latency_completed_only(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_completed", "task_name": "a.md", "duration_seconds": 10.0, "timestamp": _ts(10)},
            {"event": "task_completed", "task_name": "b.md", "duration_seconds": 20.0, "timestamp": _ts(5)},
        ])
        assert collector.calculate_avg_latency() == 15.0

    def test_avg_latency_includes_failed(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_completed", "task_name": "a.md", "duration_seconds": 10.0, "timestamp": _ts(10)},
            {"event": "task_failed", "task_name": "b.md", "duration_seconds": 30.0, "error": "err", "timestamp": _ts(5)},
        ])
        # (10 + 30) / 2 = 20.0
        assert collector.calculate_avg_latency() == 20.0

    def test_avg_latency_with_since(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_completed", "task_name": "old.md", "duration_seconds": 100.0, "timestamp": _ts(120)},
            {"event": "task_completed", "task_name": "new.md", "duration_seconds": 5.0, "timestamp": _ts(5)},
        ])
        since = datetime.now(timezone.utc) - timedelta(minutes=10)
        assert collector.calculate_avg_latency(since=since) == 5.0

    def test_avg_latency_single_event(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_completed", "task_name": "solo.md", "duration_seconds": 42.0, "timestamp": _ts(5)},
        ])
        assert collector.calculate_avg_latency() == 42.0


# ---------------------------------------------------------------------------
# Error rate
# ---------------------------------------------------------------------------


class TestErrorRate:
    def test_no_events_returns_zero(self, collector):
        assert collector.calculate_error_rate() == 0.0

    def test_all_completed_returns_zero(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_completed", "task_name": "a.md", "duration_seconds": 5.0, "timestamp": _ts(10)},
            {"event": "task_completed", "task_name": "b.md", "duration_seconds": 5.0, "timestamp": _ts(5)},
        ])
        assert collector.calculate_error_rate() == 0.0

    def test_error_rate_one_of_four(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_completed", "task_name": "a.md", "duration_seconds": 5.0, "timestamp": _ts(10)},
            {"event": "task_completed", "task_name": "b.md", "duration_seconds": 5.0, "timestamp": _ts(8)},
            {"event": "task_completed", "task_name": "c.md", "duration_seconds": 5.0, "timestamp": _ts(6)},
            {"event": "task_failed", "task_name": "d.md", "duration_seconds": 5.0, "error": "e", "timestamp": _ts(4)},
        ])
        # 1 / 4 = 0.25
        assert collector.calculate_error_rate() == 0.25

    def test_error_rate_all_failed(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_failed", "task_name": "a.md", "duration_seconds": 5.0, "error": "e", "timestamp": _ts(10)},
            {"event": "task_failed", "task_name": "b.md", "duration_seconds": 5.0, "error": "e", "timestamp": _ts(5)},
        ])
        assert collector.calculate_error_rate() == 1.0

    def test_error_rate_with_since_excludes_old_failure(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_failed", "task_name": "old.md", "duration_seconds": 5.0, "error": "e", "timestamp": _ts(120)},
            {"event": "task_completed", "task_name": "new.md", "duration_seconds": 5.0, "timestamp": _ts(5)},
        ])
        since = datetime.now(timezone.utc) - timedelta(minutes=10)
        # Only the completed event is in window → 0/1 = 0.0
        assert collector.calculate_error_rate(since=since) == 0.0

    def test_started_events_not_counted_in_error_rate(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_started", "task_name": "a.md", "priority": 1.0, "timestamp": _ts(10)},
            {"event": "task_completed", "task_name": "a.md", "duration_seconds": 5.0, "timestamp": _ts(5)},
        ])
        # 1 terminal event (completed), 0 failed
        assert collector.calculate_error_rate() == 0.0

    def test_error_rate_two_of_three(self, collector, log_path):
        _seed(log_path, [
            {"event": "task_completed", "task_name": "ok.md", "duration_seconds": 5.0, "timestamp": _ts(10)},
            {"event": "task_failed", "task_name": "f1.md", "duration_seconds": 5.0, "error": "e", "timestamp": _ts(8)},
            {"event": "task_failed", "task_name": "f2.md", "duration_seconds": 5.0, "error": "e", "timestamp": _ts(5)},
        ])
        # 2 / 3 ≈ 0.6667
        assert collector.calculate_error_rate() == round(2 / 3, 4)


# ---------------------------------------------------------------------------
# Scheduler integration smoke test
# ---------------------------------------------------------------------------


class TestSchedulerIntegration:
    """Verify MetricsCollector wires correctly into the Orchestrator constructor.

    We instantiate Orchestrator with a tmp vault and confirm the metrics log
    path is set to <vault_parent>/.fte/orchestrator_metrics.log.
    """

    def test_orchestrator_has_metrics_collector(self, tmp_path):
        from src.orchestrator.models import OrchestratorConfig
        from src.orchestrator.scheduler import Orchestrator

        vault = tmp_path / "vault"
        vault.mkdir()
        cfg = OrchestratorConfig(vault_path=vault)
        orch = Orchestrator(config=cfg, dry_run=True)

        expected_log = tmp_path / ".fte" / "orchestrator_metrics.log"
        assert orch._metrics._log_path == expected_log

    def test_metrics_collector_is_functional_on_orchestrator(self, tmp_path):
        import json

        from src.orchestrator.models import OrchestratorConfig
        from src.orchestrator.scheduler import Orchestrator

        vault = tmp_path / "vault"
        vault.mkdir()
        cfg = OrchestratorConfig(vault_path=vault)
        orch = Orchestrator(config=cfg, dry_run=True)

        # Seed a completed event 30 minutes in the past so throughput window > 0
        now = datetime.now(timezone.utc)
        log_path = orch._metrics._log_path
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w") as fh:
            fh.write(json.dumps({
                "event": "task_completed",
                "task_name": "smoke.md",
                "duration_seconds": 2.5,
                "timestamp": (now - timedelta(minutes=30)).isoformat(),
            }) + "\n")

        since = now - timedelta(hours=1)
        assert orch._metrics.calculate_throughput(since=since) > 0
        assert orch._metrics.calculate_avg_latency() == 2.5
        assert orch._metrics.calculate_error_rate() == 0.0

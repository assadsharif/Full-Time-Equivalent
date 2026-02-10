"""
Unit tests for CLI telemetry module.

Tests TelemetryCollector with explicit enabled/disabled override
(avoids touching config or disk paths that need vault setup).
Covers record_command, record_feature_use, record_performance,
flush, get_stats, clear_data, TelemetryContext, and get_telemetry_status.
"""

import json
import sys
import time
import types
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, ".")


# ---------------------------------------------------------------------------
# Test configuration stub
# telemetry.py uses relative imports, so we import from src.cli.telemetry
# ---------------------------------------------------------------------------
class _StubConfig:
    class telemetry:
        enabled = False

    class vault:
        path = "/tmp"


# Import from src.cli.telemetry (matches installed package structure)
from src.cli.telemetry import (
    TelemetryCollector,
    TelemetryContext,
    get_telemetry_status,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collector(tmp_path, enabled=True) -> TelemetryCollector:
    """Create a collector with an isolated telemetry file."""
    c = TelemetryCollector(enabled=enabled)
    c.telemetry_file = tmp_path / "usage_stats.json"
    return c


# ---------------------------------------------------------------------------
# Disabled collector — no-ops
# ---------------------------------------------------------------------------


def test_disabled_collector_ignores_all(tmp_path):
    c = _collector(tmp_path, enabled=False)
    c.record_command("status")
    c.record_feature_use("vault", "init")
    c.record_performance("startup", 42.0)
    assert c.events == []


def test_disabled_collector_flush_is_noop(tmp_path):
    c = _collector(tmp_path, enabled=False)
    c.flush()
    assert not (tmp_path / "usage_stats.json").exists()


# ---------------------------------------------------------------------------
# record_command
# ---------------------------------------------------------------------------


def test_record_command_appends_event(tmp_path):
    c = _collector(tmp_path)
    c.record_command("vault list", duration_ms=12.5, success=True)

    assert len(c.events) == 1
    ev = c.events[0]
    assert ev["type"] == "command"
    assert ev["command"] == "vault list"
    assert ev["duration_ms"] == 12.5
    assert ev["success"] is True
    assert "timestamp" in ev
    assert "session_id" in ev


def test_record_command_failure(tmp_path):
    c = _collector(tmp_path)
    c.record_command("mcp test", success=False, error_type="TimeoutError")

    ev = c.events[0]
    assert ev["success"] is False
    assert ev["error_type"] == "TimeoutError"


# ---------------------------------------------------------------------------
# record_feature_use
# ---------------------------------------------------------------------------


def test_record_feature_use(tmp_path):
    c = _collector(tmp_path)
    c.record_feature_use("approval", "review", metadata={"id": "A1"})

    ev = c.events[0]
    assert ev["type"] == "feature"
    assert ev["feature"] == "approval"
    assert ev["action"] == "review"
    assert ev["metadata"]["id"] == "A1"


# ---------------------------------------------------------------------------
# record_performance
# ---------------------------------------------------------------------------


def test_record_performance(tmp_path):
    c = _collector(tmp_path)
    c.record_performance("status_check", 87.3, unit="ms")

    ev = c.events[0]
    assert ev["type"] == "performance"
    assert ev["metric"] == "status_check"
    assert ev["value"] == 87.3
    assert ev["unit"] == "ms"


# ---------------------------------------------------------------------------
# flush / get_stats
# ---------------------------------------------------------------------------


def test_flush_writes_to_disk(tmp_path):
    c = _collector(tmp_path)
    c.record_command("init")
    c.flush()

    data = json.loads((tmp_path / "usage_stats.json").read_text())
    assert len(data) == 1
    assert data[0]["command"] == "init"
    assert c.events == []  # cleared after flush


def test_flush_appends_to_existing(tmp_path):
    path = tmp_path / "usage_stats.json"
    path.write_text(json.dumps([{"type": "command", "command": "old"}]))

    c = _collector(tmp_path)
    c.record_command("new")
    c.flush()

    data = json.loads(path.read_text())
    assert len(data) == 2
    assert data[0]["command"] == "old"
    assert data[1]["command"] == "new"


def test_flush_caps_at_1000_events(tmp_path):
    path = tmp_path / "usage_stats.json"
    # Seed 999 old events
    old = [{"type": "command", "command": f"cmd{i}"} for i in range(999)]
    path.write_text(json.dumps(old))

    c = _collector(tmp_path)
    # Add 5 new events → 1004 total → trimmed to 1000
    for i in range(5):
        c.record_command(f"new{i}")
    c.flush()

    data = json.loads(path.read_text())
    assert len(data) == 1000


def test_flush_handles_corrupt_file(tmp_path):
    (tmp_path / "usage_stats.json").write_text("{{broken")
    c = _collector(tmp_path)
    c.record_command("after_corrupt")
    c.flush()  # should not raise; starts fresh

    data = json.loads((tmp_path / "usage_stats.json").read_text())
    assert len(data) == 1


def test_get_stats_aggregates(tmp_path):
    path = tmp_path / "usage_stats.json"
    events = [
        {"type": "command", "command": "init"},
        {"type": "command", "command": "init"},
        {"type": "command", "command": "status"},
        {"type": "feature", "feature": "vault", "action": "list"},
    ]
    path.write_text(json.dumps(events))

    c = _collector(tmp_path)
    stats = c.get_stats()
    assert stats["total_events"] == 4
    assert stats["commands"]["init"] == 2
    assert stats["commands"]["status"] == 1
    assert stats["features"]["vault.list"] == 1


def test_get_stats_missing_file(tmp_path):
    c = _collector(tmp_path)
    stats = c.get_stats()
    assert stats["total_events"] == 0


# ---------------------------------------------------------------------------
# clear_data
# ---------------------------------------------------------------------------


def test_clear_data_removes_file(tmp_path):
    path = tmp_path / "usage_stats.json"
    path.write_text("[]")
    c = _collector(tmp_path)
    c.clear_data()
    assert not path.exists()


def test_clear_data_no_file_is_safe(tmp_path):
    c = _collector(tmp_path)
    c.clear_data()  # should not raise


# ---------------------------------------------------------------------------
# TelemetryContext (context manager)
# ---------------------------------------------------------------------------


def test_telemetry_context_records_success(tmp_path):
    c = _collector(tmp_path)
    # Monkey-patch the global instance used by TelemetryContext
    import src.cli.telemetry as tel_mod

    original = tel_mod._telemetry
    tel_mod._telemetry = c

    try:
        with TelemetryContext("test cmd"):
            pass  # no exception

        assert len(c.events) == 1, f"Expected 1 event, got {len(c.events)}: {c.events}"
        assert c.events[0]["success"] is True
        assert c.events[0]["command"] == "test cmd"
        assert c.events[0]["duration_ms"] is not None
        assert c.events[0]["duration_ms"] >= 0
    finally:
        tel_mod._telemetry = original


def test_telemetry_context_records_failure(tmp_path):
    c = _collector(tmp_path)
    import src.cli.telemetry as tel_mod

    original = tel_mod._telemetry
    tel_mod._telemetry = c

    try:
        try:
            with TelemetryContext("failing cmd"):
                raise ValueError("oops")
        except ValueError:
            pass

        assert len(c.events) == 1, f"Expected 1 event, got {len(c.events)}: {c.events}"
        assert c.events[0]["success"] is False
        assert c.events[0]["error_type"] == "ValueError"
    finally:
        tel_mod._telemetry = original


# ---------------------------------------------------------------------------
# get_telemetry_status
# ---------------------------------------------------------------------------


def test_get_telemetry_status_shape():
    import src.cli.telemetry as tel_mod

    original = tel_mod._telemetry
    tel_mod._telemetry = TelemetryCollector(enabled=False)

    try:
        status = get_telemetry_status()
        assert "enabled" in status
        assert status["enabled"] is False
        assert "opt_out_methods" in status
        assert "data_collected" in status
        assert "data_not_collected" in status
    finally:
        tel_mod._telemetry = original

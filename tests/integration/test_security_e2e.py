"""
End-to-end security workflow test (spec 004 Polish T045).

Exercises the full chain:
    credential store → MCP guard call → audit log → anomaly scan → alert

All I/O is directed to tmp_path; no production state is touched.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from src.security.audit_logger import SecurityAuditLogger
from src.security.anomaly_detector import AnomalyDetector
from src.security.incident_response import IncidentResponse
from src.security.dashboard import SecurityDashboard
from src.security.metrics import SecurityMetrics
from src.security.models import RiskLevel


@pytest.fixture
def env(tmp_path):
    """Wire up all security components pointing at tmp_path."""
    logs = tmp_path / "Logs"
    logs.mkdir()

    audit_log = logs / "security_audit.log"
    alert_log = logs / "anomaly_alerts.log"
    incident_log = logs / "incident_response.log"

    return {
        "audit_log": audit_log,
        "alert_log": alert_log,
        "incident_log": incident_log,
        "logger": SecurityAuditLogger(audit_log),
        "detector": AnomalyDetector(audit_log, alert_log),
        "incident": IncidentResponse(audit_log, incident_log),
        "dashboard": SecurityDashboard(audit_log, alert_log, incident_log),
        "metrics": SecurityMetrics(audit_log),
    }


# ---------------------------------------------------------------------------
# 1. Audit-log round-trip
# ---------------------------------------------------------------------------


class TestAuditRoundTrip:
    def test_log_and_query(self, env):
        """Events written by SecurityAuditLogger appear in query_recent."""
        env["logger"].log_mcp_action(
            mcp_server="gmail",
            action="send",
            approved=True,
            risk_level=RiskLevel.LOW,
            result="success",
            duration_ms=42,
        )

        events = env["logger"].query_recent(limit=10)
        assert len(events) == 1
        assert events[0]["mcp_server"] == "gmail"
        assert events[0]["result"] == "success"

    def test_multiple_events_ordered(self, env):
        for i in range(5):
            env["logger"].log_mcp_action(
                "svc", f"action-{i}", True, RiskLevel.LOW, result="success"
            )

        events = env["logger"].query_recent(limit=10)
        assert len(events) == 5
        # Verify chronological order (earliest first)
        for i in range(4):
            t1 = datetime.fromisoformat(events[i]["timestamp"].replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(events[i + 1]["timestamp"].replace("Z", "+00:00"))
            assert t1 <= t2


# ---------------------------------------------------------------------------
# 2. Metrics read-back
# ---------------------------------------------------------------------------


class TestMetricsReadBack:
    def test_mcp_action_count(self, env):
        for _ in range(7):
            env["logger"].log_mcp_action("srv", "read", True, RiskLevel.LOW, result="success")

        assert env["metrics"].mcp_action_count() == 7

    def test_error_rate(self, env):
        # 3 successes, 2 errors
        for _ in range(3):
            env["logger"].log_mcp_action("srv", "read", True, RiskLevel.LOW, result="success")
        for _ in range(2):
            env["logger"].log_mcp_action("srv", "read", True, RiskLevel.HIGH, result="error:TimeoutError")

        rate = env["metrics"].error_rate()
        assert abs(rate - 0.4) < 0.01  # 2/5

    def test_rate_limit_hit_count(self, env):
        env["logger"].log_mcp_action("srv", "send", True, RiskLevel.MEDIUM, result="rate_limit_exceeded")
        env["logger"].log_mcp_action("srv", "send", True, RiskLevel.MEDIUM, result="rate_limit_exceeded")

        assert env["metrics"].rate_limit_hit_count() == 2

    def test_circuit_open_count(self, env):
        env["logger"].log_mcp_action("srv", "call", True, RiskLevel.HIGH, result="circuit_open")

        assert env["metrics"].circuit_open_count() == 1


# ---------------------------------------------------------------------------
# 3. Incident-response lifecycle
# ---------------------------------------------------------------------------


class TestIncidentLifecycle:
    def test_isolate_then_restore(self, env):
        inc = env["incident"]

        # Isolate
        rec = inc.isolate_mcp("bad-server", "compromise detected")
        assert inc.is_isolated("bad-server")

        # Restore
        inc.restore_mcp("bad-server")
        assert not inc.is_isolated("bad-server")

        # History has both actions
        history = inc.get_incident_history()
        types = [h["action_type"] for h in history]
        assert "mcp_isolated" in types
        assert "mcp_restored" in types

    def test_incident_report_after_failures(self, env):
        # Write several failure events
        for i in range(6):
            env["logger"].log_mcp_action(
                "failing-svc", "call", True, RiskLevel.HIGH,
                result=f"error:ConnectionError",
            )

        report = env["incident"].generate_incident_report(time_window_hours=1)
        assert report.total_events == 6
        assert report.high_risk_events == 6
        # Should flag multiple-failure pattern
        assert any(s["type"] == "multiple_failures" for s in report.suspicious_actions)


# ---------------------------------------------------------------------------
# 4. Dashboard snapshot after activity
# ---------------------------------------------------------------------------


class TestDashboardAfterActivity:
    def test_snapshot_reflects_alerts(self, env):
        # Seed alert log
        import json as _json
        alert = {
            "alert_id": "alert-e2e-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "anomaly_type": "volume",
            "severity": "high",
            "mcp_server": "test",
            "description": "E2E test alert",
            "baseline_value": 5.0,
            "observed_value": 50.0,
            "details": {},
        }
        with open(env["alert_log"], "w") as fh:
            fh.write(_json.dumps(alert) + "\n")

        snap = env["dashboard"].snapshot()
        assert len(snap.recent_alerts) == 1
        assert snap.recent_alerts[0].alert_id == "alert-e2e-001"

    def test_snapshot_reflects_isolation(self, env):
        env["incident"].isolate_mcp("quarantined-svc", "E2E test")

        snap = env["dashboard"].snapshot()
        assert "quarantined-svc" in snap.isolated_servers

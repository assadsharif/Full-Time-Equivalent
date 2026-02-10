"""Tests for incident response toolkit (spec 004 Platinum US14)."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from security.incident_response import (
    IncidentResponse,
    IncidentReport,
    IsolationRecord,
)
from security.models import RiskLevel


@pytest.fixture
def temp_logs(tmp_path):
    """Create temporary log files for testing."""
    audit_log = tmp_path / "audit.log"
    incident_log = tmp_path / "incident.log"
    return audit_log, incident_log


@pytest.fixture
def incident_response(temp_logs):
    """Create IncidentResponse instance."""
    audit_log, incident_log = temp_logs
    return IncidentResponse(
        audit_log_path=audit_log,
        incident_log_path=incident_log,
        vault=None,
    )


def create_audit_event(
    event_type: str = "mcp_action",
    mcp_server: str = "test-server",
    action: str = "read",
    timestamp: datetime = None,
    risk_level: str = "low",
    result: str = "success",
) -> dict:
    """Helper to create audit event."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    return {
        "timestamp": timestamp.isoformat(),
        "event_type": event_type,
        "mcp_server": mcp_server,
        "action": action,
        "approved": True,
        "risk_level": risk_level,
        "result": result,
        "duration_ms": 100,
    }


def write_audit_events(audit_log: Path, events: list[dict]):
    """Write events to audit log."""
    with open(audit_log, "w") as fh:
        for event in events:
            fh.write(json.dumps(event) + "\n")


class TestIncidentReportGeneration:
    """Tests for incident report generation."""

    def test_generate_basic_report(self, incident_response, temp_logs):
        """Should generate incident report from audit logs."""
        audit_log, _ = temp_logs
        now = datetime.now(timezone.utc)

        # Create some events
        events = [
            create_audit_event(timestamp=now - timedelta(minutes=i)) for i in range(10)
        ]
        write_audit_events(audit_log, events)

        # Generate report
        report = incident_response.generate_incident_report(time_window_hours=1)

        assert isinstance(report, IncidentReport)
        assert report.report_id.startswith("incident-")
        assert report.total_events == 10
        assert report.time_window_hours == 1
        assert len(report.affected_servers) > 0

    def test_report_filters_by_time_window(self, incident_response, temp_logs):
        """Should only include events within time window."""
        audit_log, _ = temp_logs
        now = datetime.now(timezone.utc)

        # Create events spanning 3 hours
        events = [
            create_audit_event(timestamp=now - timedelta(hours=i)) for i in range(3)
        ]
        write_audit_events(audit_log, events)

        # Request 1-hour window
        report = incident_response.generate_incident_report(time_window_hours=1)

        # Should only include events from last hour
        assert report.total_events == 1

    def test_report_identifies_high_risk_events(self, incident_response, temp_logs):
        """Should count high-risk events separately."""
        audit_log, _ = temp_logs
        now = datetime.now(timezone.utc)

        # Mix of low and high risk events
        events = [
            create_audit_event(risk_level="low", timestamp=now - timedelta(minutes=1)),
            create_audit_event(risk_level="high", timestamp=now - timedelta(minutes=2)),
            create_audit_event(
                risk_level="critical", timestamp=now - timedelta(minutes=3)
            ),
            create_audit_event(risk_level="low", timestamp=now - timedelta(minutes=4)),
        ]
        write_audit_events(audit_log, events)

        # Generate report
        report = incident_response.generate_incident_report(
            min_risk_level=RiskLevel.HIGH
        )

        assert report.total_events == 4
        assert report.high_risk_events == 2  # high + critical

    def test_report_identifies_failed_operations(self, incident_response, temp_logs):
        """Should identify failed operations."""
        audit_log, _ = temp_logs
        now = datetime.now(timezone.utc)

        # Mix of successful and failed operations
        events = [
            create_audit_event(result="success", timestamp=now - timedelta(minutes=1)),
            create_audit_event(
                result="error:TimeoutError", timestamp=now - timedelta(minutes=2)
            ),
            create_audit_event(
                result="rate_limit_exceeded", timestamp=now - timedelta(minutes=3)
            ),
            create_audit_event(
                result="circuit_open", timestamp=now - timedelta(minutes=4)
            ),
        ]
        write_audit_events(audit_log, events)

        # Generate report
        report = incident_response.generate_incident_report()

        assert len(report.failed_operations) == 3

    def test_report_detects_multiple_failures(self, incident_response, temp_logs):
        """Should detect pattern of multiple failures."""
        audit_log, _ = temp_logs
        now = datetime.now(timezone.utc)

        # Create multiple failures for same server
        events = [
            create_audit_event(
                mcp_server="failing-server",
                result="error:ConnectionError",
                timestamp=now - timedelta(minutes=i),
            )
            for i in range(6)
        ]
        write_audit_events(audit_log, events)

        # Generate report
        report = incident_response.generate_incident_report()

        # Should identify as suspicious
        suspicious = [
            s for s in report.suspicious_actions if s["type"] == "multiple_failures"
        ]
        assert len(suspicious) > 0
        assert suspicious[0]["server"] == "failing-server"
        assert suspicious[0]["count"] >= 5

    def test_report_generates_recommendations(self, incident_response, temp_logs):
        """Should generate actionable recommendations."""
        audit_log, _ = temp_logs
        now = datetime.now(timezone.utc)

        # Create high-risk scenario
        events = [
            create_audit_event(
                risk_level="high",
                result="error:AuthenticationError",
                timestamp=now - timedelta(minutes=i),
            )
            for i in range(15)
        ]
        write_audit_events(audit_log, events)

        # Generate report
        report = incident_response.generate_incident_report()

        assert len(report.recommendations) > 0
        # Should recommend action for high volume of risk events
        assert any("isolat" in r.lower() for r in report.recommendations)


class TestServerIsolation:
    """Tests for MCP server isolation."""

    def test_isolate_server(self, incident_response):
        """Should isolate MCP server and log action."""
        record = incident_response.isolate_mcp(
            mcp_server="compromised-server",
            reason="Credential leak detected",
            isolated_by="admin",
        )

        assert isinstance(record, IsolationRecord)
        assert record.mcp_server == "compromised-server"
        assert record.reason == "Credential leak detected"
        assert record.status == "isolated"
        assert record.isolated_by == "admin"

    def test_isolated_server_tracked(self, incident_response):
        """Should track isolated servers."""
        incident_response.isolate_mcp(
            mcp_server="server-1",
            reason="Test isolation",
        )

        assert incident_response.is_isolated("server-1")
        assert not incident_response.is_isolated("server-2")

    def test_restore_server(self, incident_response):
        """Should restore previously isolated server."""
        # First isolate
        incident_response.isolate_mcp(
            mcp_server="test-server",
            reason="Test",
        )
        assert incident_response.is_isolated("test-server")

        # Then restore
        record = incident_response.restore_mcp(
            mcp_server="test-server",
            restored_by="admin",
        )

        assert isinstance(record, IsolationRecord)
        assert record.mcp_server == "test-server"
        assert record.status == "restored"
        assert not incident_response.is_isolated("test-server")

    def test_get_isolated_servers(self, incident_response):
        """Should list all isolated servers."""
        # Isolate multiple servers
        incident_response.isolate_mcp("server-1", "Test 1")
        incident_response.isolate_mcp("server-2", "Test 2")
        incident_response.isolate_mcp("server-3", "Test 3")

        # Restore one
        incident_response.restore_mcp("server-2")

        isolated = incident_response.get_isolated_servers()
        assert len(isolated) == 2
        assert "server-1" in isolated
        assert "server-3" in isolated
        assert "server-2" not in isolated


class TestCredentialRotation:
    """Tests for credential rotation."""

    def test_rotate_all_without_vault(self, incident_response):
        """Should log mass rotation intent when vault not configured."""
        result = incident_response.rotate_all_credentials(
            reason="Security incident",
            rotated_by="admin",
        )

        assert result["status"] == "initiated"
        assert result["reason"] == "Security incident"
        assert "Manual rotation required" in result["note"]

    def test_rotate_all_requires_vault(self, incident_response):
        """Should handle missing vault gracefully."""
        # With vault=None, should still log the action
        result = incident_response.rotate_all_credentials(
            reason="Test",
            rotated_by="system",
        )

        assert result is not None
        assert "status" in result


class TestIncidentHistory:
    """Tests for incident action logging."""

    def test_actions_logged(self, incident_response, temp_logs):
        """Should log all incident response actions."""
        _, incident_log = temp_logs

        # Perform various actions
        incident_response.isolate_mcp("server-1", "Test isolation")
        incident_response.restore_mcp("server-1")
        incident_response.generate_incident_report(time_window_hours=1)

        # Check incident log
        assert incident_log.exists()
        actions = incident_response.get_incident_history()
        assert len(actions) >= 3

        # Verify action types
        action_types = [a["action_type"] for a in actions]
        assert "mcp_isolated" in action_types
        assert "mcp_restored" in action_types
        assert "incident_report_generated" in action_types

    def test_get_incident_history_limit(self, incident_response, temp_logs):
        """Should respect limit when retrieving history."""
        _, incident_log = temp_logs

        # Create many actions
        for i in range(10):
            incident_response.isolate_mcp(f"server-{i}", "Test")

        # Get limited history
        history = incident_response.get_incident_history(limit=3)
        assert len(history) == 3

        # Should get most recent
        assert "server-9" in str(history[-1])

    def test_empty_history(self, incident_response):
        """Should handle empty incident log."""
        history = incident_response.get_incident_history()
        assert history == []


class TestEmptyLogs:
    """Tests for handling empty or missing logs."""

    def test_generate_report_with_no_events(self, incident_response):
        """Should handle empty audit log gracefully."""
        report = incident_response.generate_incident_report()

        assert report.total_events == 0
        assert report.high_risk_events == 0
        assert len(report.affected_servers) == 0
        assert "No high-risk activity" in report.summary

    def test_actions_work_without_audit_log(self, incident_response):
        """Should allow incident response actions without audit log."""
        # These shouldn't raise errors
        incident_response.isolate_mcp("test-server", "Test")
        isolated = incident_response.get_isolated_servers()
        assert "test-server" in isolated


class TestReportSummaryGeneration:
    """Tests for report summary and recommendation generation."""

    def test_summary_with_no_risk(self, incident_response, temp_logs):
        """Should generate appropriate summary when no risk detected."""
        audit_log, _ = temp_logs
        now = datetime.now(timezone.utc)

        # All low-risk events
        events = [
            create_audit_event(risk_level="low", timestamp=now - timedelta(minutes=i))
            for i in range(5)
        ]
        write_audit_events(audit_log, events)

        report = incident_response.generate_incident_report()
        assert "No high-risk activity" in report.summary

    def test_summary_with_high_risk(self, incident_response, temp_logs):
        """Should flag security incident in summary."""
        audit_log, _ = temp_logs
        now = datetime.now(timezone.utc)

        # Mix with high risk
        events = [
            create_audit_event(risk_level="high", timestamp=now - timedelta(minutes=i))
            for i in range(3)
        ]
        events.extend(
            [
                create_audit_event(
                    risk_level="low", timestamp=now - timedelta(minutes=i)
                )
                for i in range(3, 5)
            ]
        )
        write_audit_events(audit_log, events)

        report = incident_response.generate_incident_report(
            min_risk_level=RiskLevel.MEDIUM
        )
        assert "Security incident detected" in report.summary
        assert report.high_risk_events == 3

    def test_recommendations_for_rate_limit_abuse(self, incident_response, temp_logs):
        """Should recommend action for rate limit abuse."""
        audit_log, _ = temp_logs
        now = datetime.now(timezone.utc)

        # Multiple rate limit violations
        events = [
            create_audit_event(
                result="rate_limit_exceeded",
                timestamp=now - timedelta(minutes=i),
            )
            for i in range(4)
        ]
        write_audit_events(audit_log, events)

        report = incident_response.generate_incident_report()
        recommendations_text = " ".join(report.recommendations).lower()
        assert "rate limit" in recommendations_text

    def test_recommendations_for_circuit_trips(self, incident_response, temp_logs):
        """Should recommend action for circuit breaker trips."""
        audit_log, _ = temp_logs
        now = datetime.now(timezone.utc)

        # Multiple circuit breaker trips
        events = [
            create_audit_event(
                result="circuit_open",
                timestamp=now - timedelta(minutes=i),
            )
            for i in range(3)
        ]
        write_audit_events(audit_log, events)

        report = incident_response.generate_incident_report()
        recommendations_text = " ".join(report.recommendations).lower()
        assert "circuit" in recommendations_text

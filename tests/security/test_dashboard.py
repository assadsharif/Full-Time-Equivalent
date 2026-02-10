"""Tests for SecurityDashboard (spec 004 Platinum US13)."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from security.dashboard import SecurityDashboard, DashboardSnapshot


@pytest.fixture
def log_paths(tmp_path):
    """Create temporary log files."""
    return {
        "audit": tmp_path / "audit.log",
        "alerts": tmp_path / "alerts.log",
        "incident": tmp_path / "incident.log",
    }


@pytest.fixture
def dashboard(log_paths):
    return SecurityDashboard(
        audit_log_path=log_paths["audit"],
        alert_log_path=log_paths["alerts"],
        incident_log_path=log_paths["incident"],
    )


def _write_jsonl(path: Path, records: list[dict]):
    with open(path, "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")


# ---------------------------------------------------------------------------
# Credential status
# ---------------------------------------------------------------------------


class TestCredentialStatus:
    def test_no_vault_returns_zero(self, dashboard):
        status = dashboard.get_credential_status()
        assert status.count == 0
        assert status.services == []

    def test_with_vault_lists_services(self, log_paths):
        """Simulate a vault that returns services via list_services()."""

        class _FakeVault:
            def list_services(self):
                return ["gmail", "slack", "github"]

        d = SecurityDashboard(
            log_paths["audit"],
            log_paths["alerts"],
            log_paths["incident"],
            credential_vault=_FakeVault(),
        )
        status = d.get_credential_status()
        assert status.count == 3
        assert "gmail" in status.services


# ---------------------------------------------------------------------------
# Verification status
# ---------------------------------------------------------------------------


class TestVerificationStatus:
    def test_no_verifier_returns_zero(self, dashboard):
        status = dashboard.get_mcp_verification_status()
        assert status.trusted_count == 0

    def test_with_verifier_lists_trusted(self, log_paths):
        class _FakeVerifier:
            def list_trusted(self):
                return {"gmail-mcp": "abc123", "slack-mcp": "def456"}

        d = SecurityDashboard(
            log_paths["audit"],
            log_paths["alerts"],
            log_paths["incident"],
            mcp_verifier=_FakeVerifier(),
        )
        status = d.get_mcp_verification_status()
        assert status.trusted_count == 2
        assert "gmail-mcp" in status.trusted_servers


# ---------------------------------------------------------------------------
# Rate-limit status
# ---------------------------------------------------------------------------


class TestRateLimitStatus:
    def test_no_limiter_returns_empty(self, dashboard):
        status = dashboard.get_rate_limit_status()
        assert status.buckets == []
        assert status.throttled_count == 0

    def test_with_limiter_shows_buckets(self, log_paths):
        """Fake RateLimiter with internal bucket dict."""
        from dataclasses import dataclass

        @dataclass
        class _Bucket:
            max_tokens: int = 100
            tokens: float = 95.0

        class _FakeLimiter:
            _buckets = {
                "gmail:email": _Bucket(),
                "payment-svc:payment": _Bucket(max_tokens=10, tokens=0.5),  # throttled
            }

            @staticmethod
            def _refill(bucket):
                pass  # no-op in test

        d = SecurityDashboard(
            log_paths["audit"],
            log_paths["alerts"],
            log_paths["incident"],
            rate_limiter=_FakeLimiter(),
        )
        status = d.get_rate_limit_status()
        assert len(status.buckets) == 2
        assert status.throttled_count == 1  # payment bucket < 10 %


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


class TestRecentAlerts:
    def test_empty_alert_log(self, dashboard):
        alerts = dashboard.get_recent_alerts()
        assert alerts == []

    def test_reads_alerts(self, dashboard, log_paths):
        now = datetime.now(timezone.utc)
        records = [
            {
                "alert_id": f"alert-{i}",
                "timestamp": (now - timedelta(minutes=i)).isoformat(),
                "anomaly_type": "volume",
                "severity": "high",
                "mcp_server": "test-server",
                "description": f"Alert {i}",
                "baseline_value": 5.0,
                "observed_value": 20.0,
                "details": {},
            }
            for i in range(15)
        ]
        _write_jsonl(log_paths["alerts"], records)

        alerts = dashboard.get_recent_alerts(limit=5)
        assert len(alerts) == 5


# ---------------------------------------------------------------------------
# Circuit-breaker status (derived from incident log)
# ---------------------------------------------------------------------------


class TestCircuitBreakerStatus:
    def test_no_incident_log(self, dashboard):
        status = dashboard.get_circuit_breaker_status()
        assert status.open_count == 0

    def test_isolated_servers_shown_as_open(self, dashboard, log_paths):
        now = datetime.now(timezone.utc)
        records = [
            {
                "timestamp": now.isoformat(),
                "action_type": "mcp_isolated",
                "details": {"mcp_server": "bad-svc"},
            },
            {
                "timestamp": now.isoformat(),
                "action_type": "mcp_isolated",
                "details": {"mcp_server": "sus-svc"},
            },
            {
                "timestamp": now.isoformat(),
                "action_type": "mcp_restored",
                "details": {"mcp_server": "bad-svc"},
            },
        ]
        _write_jsonl(log_paths["incident"], records)

        status = dashboard.get_circuit_breaker_status()
        # bad-svc was restored, only sus-svc remains
        assert status.open_count == 1
        assert any(c.server == "sus-svc" for c in status.circuits)


# ---------------------------------------------------------------------------
# Full snapshot
# ---------------------------------------------------------------------------


class TestSnapshot:
    def test_returns_snapshot_type(self, dashboard):
        snap = dashboard.snapshot()
        assert isinstance(snap, DashboardSnapshot)
        assert snap.timestamp is not None

    def test_snapshot_populates_all_sections(self, dashboard):
        snap = dashboard.snapshot()
        assert snap.credentials is not None
        assert snap.verification is not None
        assert snap.rate_limits is not None
        assert snap.circuit_breakers is not None
        assert isinstance(snap.recent_alerts, list)
        assert isinstance(snap.isolated_servers, list)

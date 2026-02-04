"""
Performance benchmarks for security operations (spec 004 Polish T046).

Targets (from spec):
    credential retrieval   < 50 ms
    verification check     < 100 ms
    rate-limit consume     < 10 ms

All benchmarks write to tmp_path; no production state.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.security.audit_logger import SecurityAuditLogger
from src.security.metrics import SecurityMetrics
from src.security.models import RiskLevel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_audit_log(path: Path, count: int):
    """Write *count* mcp_action events."""
    now = datetime.now(timezone.utc)
    with open(path, "w") as fh:
        for i in range(count):
            record = {
                "timestamp": now.isoformat(),
                "event_type": "mcp_action",
                "mcp_server": f"server-{i % 10}",
                "action": "read",
                "approved": True,
                "risk_level": "low",
                "result": "success" if i % 5 != 0 else "error:Timeout",
                "duration_ms": 100,
            }
            fh.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# Audit-log write throughput
# ---------------------------------------------------------------------------


class TestAuditLogPerformance:
    def test_1000_writes_under_1s(self, tmp_path):
        """Write 1 000 events; wall-clock must stay under 1 s."""
        log_path = tmp_path / "audit.log"
        logger = SecurityAuditLogger(log_path)

        start = time.monotonic()
        for i in range(1000):
            logger.log_mcp_action(
                mcp_server=f"server-{i % 10}",
                action="read",
                approved=True,
                risk_level=RiskLevel.LOW,
                result="success",
                duration_ms=50,
            )
        elapsed = time.monotonic() - start

        assert elapsed < 1.0, f"1 000 audit writes took {elapsed:.2f} s (limit 1.0 s)"
        # Verify all lines written
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 1000


# ---------------------------------------------------------------------------
# Metrics calculation speed
# ---------------------------------------------------------------------------


class TestMetricsPerformance:
    @pytest.mark.parametrize("event_count", [100, 1000])
    def test_summary_under_200ms(self, tmp_path, event_count):
        """SecurityMetrics.summary() over N events must complete < 200 ms."""
        log_path = tmp_path / "audit.log"
        _seed_audit_log(log_path, event_count)

        metrics = SecurityMetrics(log_path)

        start = time.monotonic()
        summary = metrics.summary()
        elapsed = time.monotonic() - start

        assert elapsed < 0.2, f"summary() over {event_count} events: {elapsed*1000:.0f} ms (limit 200 ms)"
        assert summary["mcp_action_count"] == event_count

    def test_per_server_actions_correct(self, tmp_path):
        """Spot-check per-server counts after seeding 100 events."""
        log_path = tmp_path / "audit.log"
        _seed_audit_log(log_path, 100)

        metrics = SecurityMetrics(log_path)
        per_server = metrics.per_server_actions()

        # 100 events spread across server-0 … server-9
        assert sum(per_server.values()) == 100
        assert len(per_server) == 10  # 10 distinct servers


# ---------------------------------------------------------------------------
# Rate-limit consume latency (unit level)
# ---------------------------------------------------------------------------


class TestRateLimitPerformance:
    def test_100_consumes_under_50ms(self, tmp_path):
        """100 non-raising consume calls on a single bucket < 50 ms."""
        from src.security.rate_limiter import RateLimiter

        state_path = tmp_path / "rl_state.json"
        limiter = RateLimiter(
            state_path=state_path,
            default_limits={"bench": {"per_minute": 200, "per_hour": 5000}},
        )

        start = time.monotonic()
        for _ in range(100):
            limiter.consume("bench-server", "bench")
        elapsed = time.monotonic() - start

        assert elapsed < 0.05, f"100 consumes took {elapsed*1000:.0f} ms (limit 50 ms)"

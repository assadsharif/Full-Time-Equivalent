"""Tests for approval audit trail (spec 010 US4)."""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.approval.audit_logger import ApprovalAuditLogger
from src.approval.audit_query import ApprovalAuditQuery


@pytest.fixture
def audit_log(tmp_path):
    return tmp_path / "approval_audit.log"


@pytest.fixture
def logger(audit_log):
    return ApprovalAuditLogger(audit_log)


@pytest.fixture
def query(audit_log):
    return ApprovalAuditQuery(audit_log)


# ---------------------------------------------------------------------------
# Audit Logger — event writers
# ---------------------------------------------------------------------------


class TestApprovalAuditLogger:
    def test_log_created_writes_event(self, logger, audit_log):
        logger.log_created("APR-001", "task-1", "email", "medium")

        lines = audit_log.read_text().strip().split("\n")
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["event_type"] == "approval_created"
        assert event["approval_id"] == "APR-001"
        assert event["task_id"] == "task-1"
        assert event["action_type"] == "email"
        assert event["status"] == "pending"
        assert "timestamp" in event

    def test_log_approved_writes_event(self, logger, audit_log):
        logger.log_approved("APR-002", "task-2", "deploy", "high", approver="alice")

        event = json.loads(audit_log.read_text().strip())
        assert event["event_type"] == "approval_approved"
        assert event["status"] == "approved"
        assert event["approver"] == "alice"

    def test_log_rejected_writes_event(self, logger, audit_log):
        logger.log_rejected(
            "APR-003", "task-3", "payment", "critical",
            reason="too risky", approver="bob",
        )

        event = json.loads(audit_log.read_text().strip())
        assert event["event_type"] == "approval_rejected"
        assert event["status"] == "rejected"
        assert event["reason"] == "too risky"
        assert event["approver"] == "bob"

    def test_log_timeout_writes_event(self, logger, audit_log):
        logger.log_timeout("APR-004", "task-4", "email", "medium")

        event = json.loads(audit_log.read_text().strip())
        assert event["event_type"] == "approval_timeout"
        assert event["status"] == "timeout"

    def test_multiple_events_appended_in_order(self, logger, audit_log):
        logger.log_created("APR-001", "t1", "email", "low")
        logger.log_approved("APR-001", "t1", "email", "low")
        logger.log_rejected("APR-002", "t2", "pay", "high", reason="no")

        lines = audit_log.read_text().strip().split("\n")
        assert len(lines) == 3
        assert json.loads(lines[0])["event_type"] == "approval_created"
        assert json.loads(lines[1])["event_type"] == "approval_approved"
        assert json.loads(lines[2])["event_type"] == "approval_rejected"

    def test_creates_parent_directory(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "audit.log"
        logger = ApprovalAuditLogger(nested)
        logger.log_created("APR-X", "t", "e", "low")
        assert nested.exists()


# ---------------------------------------------------------------------------
# Audit Query — query_approval_events
# ---------------------------------------------------------------------------


def _seed_lifecycle(logger: ApprovalAuditLogger):
    """Seed two full lifecycles: one approved, one rejected."""
    logger.log_created("APR-001", "task-A", "email", "low")
    logger.log_approved("APR-001", "task-A", "email", "low", approver="alice")
    logger.log_created("APR-002", "task-B", "payment", "high")
    logger.log_rejected("APR-002", "task-B", "payment", "high", reason="denied", approver="bob")


class TestQueryApprovalEvents:
    def test_no_filter_returns_all(self, logger, query):
        _seed_lifecycle(logger)
        assert len(query.query_approval_events()) == 4

    def test_filter_by_task_id(self, logger, query):
        _seed_lifecycle(logger)
        events = query.query_approval_events(task_id="task-A")
        assert len(events) == 2
        assert all(e["task_id"] == "task-A" for e in events)

    def test_filter_by_approval_id(self, logger, query):
        _seed_lifecycle(logger)
        events = query.query_approval_events(approval_id="APR-002")
        assert len(events) == 2
        assert all(e["approval_id"] == "APR-002" for e in events)

    def test_filter_by_status(self, logger, query):
        _seed_lifecycle(logger)
        events = query.query_approval_events(status="approved")
        assert len(events) == 1
        assert events[0]["approval_id"] == "APR-001"

    def test_combined_filters(self, logger, query):
        _seed_lifecycle(logger)
        events = query.query_approval_events(task_id="task-A", status="pending")
        assert len(events) == 1
        assert events[0]["event_type"] == "approval_created"

    def test_empty_log_returns_empty(self, query):
        assert query.query_approval_events() == []


# ---------------------------------------------------------------------------
# Audit Query — query_approver_history
# ---------------------------------------------------------------------------


class TestQueryApproverHistory:
    def test_returns_decisions_by_approver(self, logger, query):
        logger.log_approved("APR-001", "t1", "email", "low", approver="alice")
        logger.log_rejected("APR-002", "t2", "pay", "high", reason="x", approver="alice")
        logger.log_approved("APR-003", "t3", "deploy", "med", approver="bob")

        history = query.query_approver_history("alice")
        assert len(history) == 2
        assert all(e["approver"] == "alice" for e in history)

    def test_excludes_non_decision_events(self, logger, query):
        logger.log_created("APR-001", "t1", "email", "low")
        logger.log_approved("APR-001", "t1", "email", "low", approver="alice")

        # created event has no approver; only the approved event matches
        assert len(query.query_approver_history("alice")) == 1

    def test_unknown_approver_returns_empty(self, logger, query):
        logger.log_approved("APR-001", "t1", "email", "low", approver="alice")
        assert query.query_approver_history("nobody") == []


# ---------------------------------------------------------------------------
# Audit Query — query_approval_stats
# ---------------------------------------------------------------------------


class TestQueryApprovalStats:
    def test_empty_log_returns_zeros(self, query):
        stats = query.query_approval_stats()
        assert stats["total_events"] == 0
        assert stats["approval_rate"] == 0.0
        assert stats["avg_response_time_seconds"] == 0.0

    def test_counts_all_statuses(self, logger, query):
        logger.log_created("APR-001", "t1", "email", "low")      # pending
        logger.log_approved("APR-001", "t1", "email", "low")     # approved
        logger.log_created("APR-002", "t2", "pay", "high")       # pending
        logger.log_rejected("APR-002", "t2", "pay", "high", reason="x")  # rejected
        logger.log_created("APR-003", "t3", "deploy", "med")     # pending
        logger.log_timeout("APR-003", "t3", "deploy", "med")     # timeout

        stats = query.query_approval_stats()
        assert stats["total_events"] == 6
        assert stats["pending_count"] == 3   # 3 created events
        assert stats["approved_count"] == 1
        assert stats["rejected_count"] == 1
        assert stats["timeout_count"] == 1

    def test_approval_rate_calculation(self, logger, query):
        # 2 approved, 1 rejected → rate = 2/3
        logger.log_approved("APR-1", "t", "e", "l")
        logger.log_approved("APR-2", "t", "e", "l")
        logger.log_rejected("APR-3", "t", "e", "l", reason="x")

        stats = query.query_approval_stats()
        assert abs(stats["approval_rate"] - round(2 / 3, 4)) < 0.001

    def test_avg_response_time(self, audit_log):
        """Manually seed events with known 30-second gap."""
        now = datetime.now(timezone.utc)
        created = {
            "event_type": "approval_created",
            "approval_id": "APR-RT",
            "task_id": "t1",
            "action_type": "email",
            "risk_level": "low",
            "status": "pending",
            "timestamp": now.isoformat(),
        }
        approved = {
            "event_type": "approval_approved",
            "approval_id": "APR-RT",
            "task_id": "t1",
            "action_type": "email",
            "risk_level": "low",
            "status": "approved",
            "approver": "alice",
            "timestamp": (now + timedelta(seconds=30)).isoformat(),
        }
        with open(audit_log, "w") as fh:
            fh.write(json.dumps(created) + "\n")
            fh.write(json.dumps(approved) + "\n")

        stats = ApprovalAuditQuery(audit_log).query_approval_stats()
        assert stats["avg_response_time_seconds"] == 30.0

    def test_since_filter(self, audit_log):
        now = datetime.now(timezone.utc)
        old = {
            "event_type": "approval_created", "approval_id": "OLD",
            "task_id": "t", "action_type": "e", "risk_level": "l",
            "status": "pending", "timestamp": (now - timedelta(hours=2)).isoformat(),
        }
        new = {
            "event_type": "approval_created", "approval_id": "NEW",
            "task_id": "t", "action_type": "e", "risk_level": "l",
            "status": "pending", "timestamp": now.isoformat(),
        }
        with open(audit_log, "w") as fh:
            fh.write(json.dumps(old) + "\n")
            fh.write(json.dumps(new) + "\n")

        stats = ApprovalAuditQuery(audit_log).query_approval_stats(
            since=now - timedelta(hours=1)
        )
        assert stats["total_events"] == 1


# ---------------------------------------------------------------------------
# ApprovalManager integration — audit logger wired in
# ---------------------------------------------------------------------------


class TestApprovalManagerAuditIntegration:
    def _make_manager(self, tmp_path):
        from src.approval.approval_manager import ApprovalManager

        approvals_dir = tmp_path / "Approvals"
        audit_log = tmp_path / "approval_audit.log"
        return ApprovalManager(approvals_dir, approval_audit_log_path=audit_log), audit_log

    def _load_events(self, audit_log: Path) -> list[dict]:
        return [json.loads(ln) for ln in audit_log.read_text().strip().split("\n") if ln]

    def test_create_logs_event(self, tmp_path):
        mgr, audit_log = self._make_manager(tmp_path)
        mgr.create("task-1", "email", ["send"])

        events = self._load_events(audit_log)
        assert len(events) == 1
        assert events[0]["event_type"] == "approval_created"
        assert events[0]["task_id"] == "task-1"
        assert events[0]["action_type"] == "email"

    def test_approve_logs_event(self, tmp_path):
        mgr, audit_log = self._make_manager(tmp_path)
        req = mgr.create("task-2", "email", ["send"])
        mgr.approve(req.approval_id)

        events = self._load_events(audit_log)
        assert len(events) == 2
        assert events[0]["event_type"] == "approval_created"
        assert events[1]["event_type"] == "approval_approved"
        assert events[1]["approval_id"] == req.approval_id

    def test_reject_logs_event_with_reason(self, tmp_path):
        mgr, audit_log = self._make_manager(tmp_path)
        req = mgr.create("task-3", "email", ["send"])
        mgr.reject(req.approval_id, reason="not needed")

        events = self._load_events(audit_log)
        assert len(events) == 2
        assert events[1]["event_type"] == "approval_rejected"
        assert events[1]["reason"] == "not needed"

    def test_timeout_logs_event(self, tmp_path):
        mgr, audit_log = self._make_manager(tmp_path)
        # timeout_hours=0 makes expires_at == now; a brief pause ensures expiry
        mgr.create("task-4", "email", ["send"], timeout_hours=0)
        time.sleep(0.02)
        expired = mgr.check_expired()

        assert len(expired) == 1
        events = self._load_events(audit_log)
        assert len(events) == 2  # created + timeout
        assert events[1]["event_type"] == "approval_timeout"
        assert events[1]["task_id"] == "task-4"

"""
Unit tests for audit logger

Constitutional compliance:
- Section 8 (Auditability & Logging): Tests verify append-only, structured logging
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from src.control_plane.models import WorkflowState, StateTransition
from src.control_plane.logger import AuditLogger


class TestAuditLogger:
    """Tests for AuditLogger class."""

    def test_log_transition_creates_entry(self, isolated_fs):
        """
        Verify AuditLogger.log_transition() creates log entry.

        Constitutional requirement (Section 8): Every action must be logged.
        """
        logger = AuditLogger(log_dir=isolated_fs / "Logs")

        transition = StateTransition(
            transition_id="trans-001",
            task_id="task-001",
            from_state=WorkflowState.INBOX,
            to_state=WorkflowState.NEEDS_ACTION,
            timestamp=datetime(2026, 1, 27, 10, 0, 0),
            reason="Validation complete",
            actor="system",
            logged=True
        )

        logger.log_transition(transition)

        # Verify log file exists
        log_file = isolated_fs / "Logs" / "2026-01-27.log"
        assert log_file.exists(), "Log file should be created"

    def test_log_transition_json_format(self, isolated_fs):
        """
        Verify log entries are in JSON format.

        Constitutional requirement (Section 8): Structured logging for programmatic analysis.
        """
        logger = AuditLogger(log_dir=isolated_fs / "Logs")

        transition = StateTransition(
            transition_id="trans-002",
            task_id="task-002",
            from_state=WorkflowState.NEEDS_ACTION,
            to_state=WorkflowState.PLANS,
            timestamp=datetime(2026, 1, 27, 11, 0, 0),
            reason="Planning started",
            actor="system",
            logged=True
        )

        logger.log_transition(transition)

        # Read log file and verify JSON format
        log_file = isolated_fs / "Logs" / "2026-01-27.log"
        log_content = log_file.read_text().strip()

        # Parse JSON
        log_entry = json.loads(log_content)

        # Verify required fields
        assert "timestamp" in log_entry
        assert "action" in log_entry
        assert "task_id" in log_entry
        assert log_entry["task_id"] == "task-002"
        assert "from_state" in log_entry
        assert "to_state" in log_entry
        assert "result" in log_entry

    def test_log_transition_required_fields(self, isolated_fs):
        """
        Verify log entries contain all required fields.

        Constitutional requirement (Section 8): Logs must include timestamp, action type,
        triggering file, result, approval status.
        """
        logger = AuditLogger(log_dir=isolated_fs / "Logs")

        transition = StateTransition(
            transition_id="trans-003",
            task_id="task-003",
            from_state=WorkflowState.PENDING_APPROVAL,
            to_state=WorkflowState.APPROVED,
            timestamp=datetime(2026, 1, 27, 12, 0, 0),
            reason="Approved by human",
            actor="human",
            logged=True
        )

        logger.log_transition(transition)

        log_file = isolated_fs / "Logs" / "2026-01-27.log"
        log_entry = json.loads(log_file.read_text().strip())

        # Verify all constitutional required fields
        assert "timestamp" in log_entry  # Constitutional requirement
        assert "action" in log_entry  # Constitutional requirement
        assert "task_id" in log_entry  # Constitutional requirement (triggering file)
        assert "result" in log_entry  # Constitutional requirement
        assert "approval_status" in log_entry or "actor" in log_entry  # Constitutional requirement

    def test_log_transition_append_only(self, isolated_fs):
        """
        Verify log entries are append-only (multiple transitions append to same file).

        Constitutional requirement (Section 8): Logs must be append-only.
        """
        logger = AuditLogger(log_dir=isolated_fs / "Logs")

        # Log first transition
        transition1 = StateTransition(
            transition_id="trans-004",
            task_id="task-004",
            from_state=WorkflowState.INBOX,
            to_state=WorkflowState.NEEDS_ACTION,
            timestamp=datetime(2026, 1, 27, 10, 0, 0),
            reason="First transition",
            actor="system",
            logged=True
        )
        logger.log_transition(transition1)

        # Log second transition
        transition2 = StateTransition(
            transition_id="trans-005",
            task_id="task-005",
            from_state=WorkflowState.NEEDS_ACTION,
            to_state=WorkflowState.PLANS,
            timestamp=datetime(2026, 1, 27, 10, 30, 0),
            reason="Second transition",
            actor="system",
            logged=True
        )
        logger.log_transition(transition2)

        # Verify both entries exist in log file
        log_file = isolated_fs / "Logs" / "2026-01-27.log"
        log_lines = log_file.read_text().strip().split('\n')

        assert len(log_lines) == 2, "Should have 2 log entries"

        # Parse both entries
        entry1 = json.loads(log_lines[0])
        entry2 = json.loads(log_lines[1])

        assert entry1["task_id"] == "task-004"
        assert entry2["task_id"] == "task-005"

    def test_log_transition_daily_rotation(self, isolated_fs):
        """
        Verify log files are organized by date (YYYY-MM-DD.log).

        Constitutional requirement (Section 8): Log organization for auditability.
        """
        logger = AuditLogger(log_dir=isolated_fs / "Logs")

        # Log transitions on different dates
        transition1 = StateTransition(
            transition_id="trans-006",
            task_id="task-006",
            from_state=WorkflowState.INBOX,
            to_state=WorkflowState.NEEDS_ACTION,
            timestamp=datetime(2026, 1, 27, 10, 0, 0),
            reason="Transition on Jan 27",
            actor="system",
            logged=True
        )
        logger.log_transition(transition1)

        transition2 = StateTransition(
            transition_id="trans-007",
            task_id="task-007",
            from_state=WorkflowState.INBOX,
            to_state=WorkflowState.NEEDS_ACTION,
            timestamp=datetime(2026, 1, 28, 10, 0, 0),
            reason="Transition on Jan 28",
            actor="system",
            logged=True
        )
        logger.log_transition(transition2)

        # Verify separate log files created
        log_file_27 = isolated_fs / "Logs" / "2026-01-27.log"
        log_file_28 = isolated_fs / "Logs" / "2026-01-28.log"

        assert log_file_27.exists(), "Log file for Jan 27 should exist"
        assert log_file_28.exists(), "Log file for Jan 28 should exist"

    def test_log_transition_with_error(self, isolated_fs):
        """
        Verify log entries can include error information.

        Constitutional requirement (Section 9): Errors must never be hidden.
        """
        logger = AuditLogger(log_dir=isolated_fs / "Logs")

        transition = StateTransition(
            transition_id="trans-008",
            task_id="task-008",
            from_state=WorkflowState.APPROVED,
            to_state=WorkflowState.REJECTED,
            timestamp=datetime(2026, 1, 27, 13, 0, 0),
            reason="Execution failed",
            actor="system",
            logged=True,
            error="Disk full"
        )

        logger.log_transition(transition)

        log_file = isolated_fs / "Logs" / "2026-01-27.log"
        log_entry = json.loads(log_file.read_text().strip())

        assert "error" in log_entry
        assert log_entry["error"] == "Disk full"

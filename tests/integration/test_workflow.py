"""
Integration tests for complete workflow lifecycle

Constitutional compliance:
- Section 2 (Source of Truth): Files on disk define state
- Section 4 (File-Driven Control Plane): State transitions via atomic file moves
- Section 6-7 (Autonomy & HITL): Approval requirements enforced
- Section 8 (Auditability): All transitions logged
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
from control_plane.models import WorkflowState, TaskFile, StateTransition
from control_plane.state_machine import StateMachine
from control_plane.logger import AuditLogger
from control_plane.errors import InvalidTransitionError, FileOperationError


class TestCompleteWorkflow:
    """Integration tests for complete task lifecycle."""

    def test_complete_workflow_inbox_to_done(self, isolated_fs):
        """
        Verify complete workflow: Inbox → Needs_Action → Plans → Pending_Approval → Approved → Done.

        Constitutional requirements:
        - Section 2: File location defines state
        - Section 4: Atomic state transitions
        - Section 6-7: Approval enforced at Pending_Approval
        - Section 8: All transitions logged
        """
        # Initialize components
        state_machine = StateMachine(root_dir=isolated_fs)
        audit_logger = AuditLogger(log_dir=isolated_fs / "Logs")

        # Create task in Inbox
        task_path = isolated_fs / "Inbox" / "task-001.md"
        task_content = """---
id: task-001
state: Inbox
priority: P1
created_at: 2026-01-27T10:00:00Z
modified_at: 2026-01-27T10:00:00Z
metadata:
  tags: [integration-test]
---

# Task: Integration Test

This is an integration test task.
"""
        task_path.write_text(task_content)

        # Load task
        task = TaskFile.from_file(task_path)
        assert task.state == WorkflowState.INBOX
        assert task.id == "task-001"

        # Transition 1: Inbox → Needs_Action
        new_task = state_machine.transition(
            task=task,
            to_state=WorkflowState.NEEDS_ACTION,
            reason="Initial validation complete",
            actor="system",
        )
        assert new_task.state == WorkflowState.NEEDS_ACTION
        assert new_task.file_path == isolated_fs / "Needs_Action" / "task-001.md"
        assert not (isolated_fs / "Inbox" / "task-001.md").exists()

        # Transition 2: Needs_Action → Plans
        new_task = state_machine.transition(
            task=new_task,
            to_state=WorkflowState.PLANS,
            reason="Planning started",
            actor="system",
        )
        assert new_task.state == WorkflowState.PLANS
        assert new_task.file_path == isolated_fs / "Plans" / "task-001.md"
        assert not (isolated_fs / "Needs_Action" / "task-001.md").exists()

        # Transition 3: Plans → Pending_Approval
        new_task = state_machine.transition(
            task=new_task,
            to_state=WorkflowState.PENDING_APPROVAL,
            reason="Plan ready for review",
            actor="system",
        )
        assert new_task.state == WorkflowState.PENDING_APPROVAL
        assert new_task.file_path == isolated_fs / "Pending_Approval" / "task-001.md"
        assert not (isolated_fs / "Plans" / "task-001.md").exists()

        # Transition 4: Pending_Approval → Approved (HUMAN APPROVAL)
        # Constitutional requirement (Section 7): Human approval required
        new_task = state_machine.transition(
            task=new_task,
            to_state=WorkflowState.APPROVED,
            reason="Plan approved by human",
            actor="human",
        )
        assert new_task.state == WorkflowState.APPROVED
        assert new_task.file_path == isolated_fs / "Approved" / "task-001.md"
        assert not (isolated_fs / "Pending_Approval" / "task-001.md").exists()

        # Transition 5: Approved → Done
        new_task = state_machine.transition(
            task=new_task,
            to_state=WorkflowState.DONE,
            reason="Execution complete",
            actor="system",
        )
        assert new_task.state == WorkflowState.DONE
        assert new_task.file_path == isolated_fs / "Done" / "task-001.md"
        assert not (isolated_fs / "Approved" / "task-001.md").exists()

        # Verify all transitions logged
        log_file = isolated_fs / "Logs" / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        assert log_file.exists(), "Log file should exist"

        log_lines = log_file.read_text().strip().split("\n")
        assert len(log_lines) == 5, "Should have 5 logged transitions"

        # Verify log entries are valid JSON
        for line in log_lines:
            log_entry = json.loads(line)
            assert "timestamp" in log_entry
            assert "action" in log_entry
            assert "task_id" in log_entry
            assert log_entry["task_id"] == "task-001"

    def test_workflow_rejection_path(self, isolated_fs):
        """
        Verify rejection workflow: Plans → Pending_Approval → Rejected → Inbox.

        Constitutional requirement (Section 6-7): Human can reject plans.
        """
        state_machine = StateMachine(root_dir=isolated_fs)
        audit_logger = AuditLogger(log_dir=isolated_fs / "Logs")

        # Create task in Plans (skip earlier states for brevity)
        task_path = isolated_fs / "Plans" / "task-002.md"
        task_content = """---
id: task-002
state: Plans
priority: P1
created_at: 2026-01-27T11:00:00Z
modified_at: 2026-01-27T11:00:00Z
metadata:
  tags: [rejection-test]
---

# Task: Rejection Test

This task will be rejected.
"""
        task_path.write_text(task_content)

        task = TaskFile.from_file(task_path)

        # Transition: Plans → Pending_Approval
        new_task = state_machine.transition(
            task=task,
            to_state=WorkflowState.PENDING_APPROVAL,
            reason="Plan ready for review",
            actor="system",
        )
        assert new_task.state == WorkflowState.PENDING_APPROVAL

        # Transition: Pending_Approval → Rejected (HUMAN REJECTION)
        new_task = state_machine.transition(
            task=new_task,
            to_state=WorkflowState.REJECTED,
            reason="Plan rejected by human - needs revision",
            actor="human",
        )
        assert new_task.state == WorkflowState.REJECTED
        assert new_task.file_path == isolated_fs / "Rejected" / "task-002.md"

        # Transition: Rejected → Inbox (retry with revised approach)
        new_task = state_machine.transition(
            task=new_task,
            to_state=WorkflowState.INBOX,
            reason="Retry with revised approach",
            actor="system",
        )
        assert new_task.state == WorkflowState.INBOX
        assert new_task.file_path == isolated_fs / "Inbox" / "task-002.md"

    def test_workflow_forbidden_transition(self, isolated_fs):
        """
        Verify forbidden transition raises InvalidTransitionError.

        Constitutional requirement (Section 6-7): Cannot skip approval.
        """
        state_machine = StateMachine(root_dir=isolated_fs)

        # Create task in Plans
        task_path = isolated_fs / "Plans" / "task-003.md"
        task_content = """---
id: task-003
state: Plans
priority: P1
created_at: 2026-01-27T12:00:00Z
modified_at: 2026-01-27T12:00:00Z
metadata:
  tags: [forbidden-test]
---

# Task: Forbidden Transition Test

This task will attempt forbidden transition.
"""
        task_path.write_text(task_content)

        task = TaskFile.from_file(task_path)

        # Attempt forbidden transition: Plans → Approved (skips Pending_Approval)
        from control_plane.errors import InvalidTransitionError

        with pytest.raises(InvalidTransitionError) as exc_info:
            state_machine.transition(
                task=task,
                to_state=WorkflowState.APPROVED,
                reason="Attempt to skip approval",
                actor="system",
            )

        assert (
            "Plans → Approved" in str(exc_info.value)
            or "invalid" in str(exc_info.value).lower()
        )

    def test_workflow_atomicity_on_failure(self, isolated_fs):
        """
        Verify workflow maintains atomicity on failure (no partial states).

        Constitutional requirement (Section 4): Atomic operations, no partial states.
        """
        from unittest.mock import patch
        from control_plane.errors import FileOperationError

        state_machine = StateMachine(root_dir=isolated_fs)

        # Create task in Inbox
        task_path = isolated_fs / "Inbox" / "task-004.md"
        task_content = """---
id: task-004
state: Inbox
priority: P1
created_at: 2026-01-27T13:00:00Z
modified_at: 2026-01-27T13:00:00Z
metadata:
  tags: [atomicity-test]
---

# Task: Atomicity Test

This task tests atomicity on failure.
"""
        task_path.write_text(task_content)

        task = TaskFile.from_file(task_path)

        # Mock atomic_move to fail
        with patch(
            "src.control_plane.state_machine.atomic_move",
            side_effect=FileOperationError("Disk full"),
        ):
            with pytest.raises(FileOperationError):
                state_machine.transition(
                    task=task,
                    to_state=WorkflowState.NEEDS_ACTION,
                    reason="Test atomicity",
                    actor="system",
                )

        # Verify source file still exists (no partial state)
        assert (
            task_path.exists()
        ), "Source file should still exist after failed transition"
        destination_path = isolated_fs / "Needs_Action" / "task-004.md"
        assert (
            not destination_path.exists()
        ), "Destination file should not exist after failed transition"

    def test_workflow_logging_completeness(self, isolated_fs):
        """
        Verify all workflow transitions are logged with required fields.

        Constitutional requirement (Section 8): All actions logged with complete information.
        """
        state_machine = StateMachine(root_dir=isolated_fs)
        audit_logger = AuditLogger(log_dir=isolated_fs / "Logs")

        # Create task and perform transition
        task_path = isolated_fs / "Inbox" / "task-005.md"
        task_content = """---
id: task-005
state: Inbox
priority: P1
created_at: 2026-01-27T14:00:00Z
modified_at: 2026-01-27T14:00:00Z
metadata:
  tags: [logging-test]
---

# Task: Logging Test
"""
        task_path.write_text(task_content)

        task = TaskFile.from_file(task_path)

        # Perform transition
        new_task = state_machine.transition(
            task=task,
            to_state=WorkflowState.NEEDS_ACTION,
            reason="Testing logging",
            actor="system",
        )

        # Verify log entry has all required fields
        log_file = isolated_fs / "Logs" / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        log_content = log_file.read_text().strip().split("\n")[-1]
        log_entry = json.loads(log_content)

        # Constitutional requirement (Section 8): Required fields
        assert "timestamp" in log_entry, "Log must include timestamp"
        assert "action" in log_entry, "Log must include action type"
        assert "task_id" in log_entry, "Log must include triggering file"
        assert log_entry["task_id"] == "task-005"
        assert (
            "result" in log_entry or "to_state" in log_entry
        ), "Log must include result"
        assert "actor" in log_entry, "Log must include approval status/actor"
        assert log_entry["actor"] == "system"

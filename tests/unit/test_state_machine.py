"""
Unit tests for state machine

Constitutional compliance:
- Section 4 (File-Driven Control Plane): Tests verify valid state transitions
- Section 6-7 (Autonomy & HITL): Tests verify approval requirements
"""

import pytest
import os
import time
from pathlib import Path
from unittest.mock import patch, Mock
from src.control_plane.models import WorkflowState, TaskFile
from src.control_plane.state_machine import StateMachine
from src.utils.file_ops import atomic_move
from src.control_plane.errors import FileOperationError
from datetime import datetime


class TestStateMachine:
    """Tests for StateMachine class."""

    def test_validate_transition_inbox_to_needs_action(self):
        """
        Verify transition from Inbox to Needs_Action is valid.
        """
        sm = StateMachine()
        assert (
            sm.validate_transition(WorkflowState.INBOX, WorkflowState.NEEDS_ACTION)
            is True
        )

    def test_validate_transition_needs_action_to_plans(self):
        """
        Verify transition from Needs_Action to Plans is valid.
        """
        sm = StateMachine()
        assert (
            sm.validate_transition(WorkflowState.NEEDS_ACTION, WorkflowState.PLANS)
            is True
        )

    def test_validate_transition_plans_to_pending_approval(self):
        """
        Verify transition from Plans to Pending_Approval is valid.
        """
        sm = StateMachine()
        assert (
            sm.validate_transition(WorkflowState.PLANS, WorkflowState.PENDING_APPROVAL)
            is True
        )

    def test_validate_transition_plans_to_needs_action(self):
        """
        Verify transition from Plans back to Needs_Action is valid (clarifications needed).
        """
        sm = StateMachine()
        assert (
            sm.validate_transition(WorkflowState.PLANS, WorkflowState.NEEDS_ACTION)
            is True
        )

    def test_validate_transition_pending_approval_to_approved(self):
        """
        Verify transition from Pending_Approval to Approved is valid (human approval).

        Constitutional requirement (Section 7): Human approval via file move.
        """
        sm = StateMachine()
        assert (
            sm.validate_transition(
                WorkflowState.PENDING_APPROVAL, WorkflowState.APPROVED
            )
            is True
        )

    def test_validate_transition_pending_approval_to_rejected(self):
        """
        Verify transition from Pending_Approval to Rejected is valid (human rejection).
        """
        sm = StateMachine()
        assert (
            sm.validate_transition(
                WorkflowState.PENDING_APPROVAL, WorkflowState.REJECTED
            )
            is True
        )

    def test_validate_transition_approved_to_done(self):
        """
        Verify transition from Approved to Done is valid (execution succeeded).
        """
        sm = StateMachine()
        assert (
            sm.validate_transition(WorkflowState.APPROVED, WorkflowState.DONE) is True
        )

    def test_validate_transition_approved_to_rejected(self):
        """
        Verify transition from Approved to Rejected is valid (execution failed).
        """
        sm = StateMachine()
        assert (
            sm.validate_transition(WorkflowState.APPROVED, WorkflowState.REJECTED)
            is True
        )

    def test_validate_transition_rejected_to_inbox(self):
        """
        Verify transition from Rejected to Inbox is valid (retry with revised approach).
        """
        sm = StateMachine()
        assert (
            sm.validate_transition(WorkflowState.REJECTED, WorkflowState.INBOX) is True
        )

    def test_validate_transition_plans_to_approved_forbidden(self):
        """
        Verify transition from Plans to Approved is FORBIDDEN (skips approval).

        Constitutional requirement (Section 6-7): Sensitive actions require approval.
        """
        sm = StateMachine()
        assert (
            sm.validate_transition(WorkflowState.PLANS, WorkflowState.APPROVED) is False
        )

    def test_validate_transition_inbox_to_approved_forbidden(self):
        """
        Verify transition from Inbox to Approved is FORBIDDEN (skips planning + approval).
        """
        sm = StateMachine()
        assert (
            sm.validate_transition(WorkflowState.INBOX, WorkflowState.APPROVED) is False
        )

    def test_validate_transition_plans_to_done_forbidden(self):
        """
        Verify transition from Plans to Done is FORBIDDEN (skips approval + execution).
        """
        sm = StateMachine()
        assert sm.validate_transition(WorkflowState.PLANS, WorkflowState.DONE) is False

    def test_validate_transition_done_to_any_forbidden(self):
        """
        Verify transitions from Done are FORBIDDEN (terminal state).

        Constitutional requirement (Section 13): Task in Done is complete.
        """
        sm = StateMachine()

        # Test Done → all other states (all should be False)
        for state in WorkflowState:
            if state != WorkflowState.DONE:
                assert (
                    sm.validate_transition(WorkflowState.DONE, state) is False
                ), f"Done → {state} should be forbidden"

    def test_validate_transition_needs_action_to_approved_forbidden(self):
        """
        Verify transition from Needs_Action to Approved is FORBIDDEN (skips planning + approval).
        """
        sm = StateMachine()
        assert (
            sm.validate_transition(WorkflowState.NEEDS_ACTION, WorkflowState.APPROVED)
            is False
        )

    def test_validate_transition_inbox_to_done_forbidden(self):
        """
        Verify transition from Inbox to Done is FORBIDDEN (skips all workflow steps).
        """
        sm = StateMachine()
        assert sm.validate_transition(WorkflowState.INBOX, WorkflowState.DONE) is False

    def test_transition_retry_succeeds_on_second_attempt(self, isolated_fs):
        """
        Verify transient failure succeeds on retry with exponential backoff.

        Constitutional requirement (Section 9): Retry transient errors.
        """
        # Create state machine with isolated filesystem
        sm = StateMachine(root_dir=isolated_fs, log_dir=isolated_fs / "Logs")

        # Create a task in Inbox
        task_path = isolated_fs / "Inbox" / "task-005.md"
        task = TaskFile(
            id="task-005",
            state=WorkflowState.INBOX,
            priority="P1",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            metadata={},
            file_path=task_path,
            content="# Test retry logic",
        )
        task.to_file(task_path)

        # Mock atomic_move to fail on first attempt, succeed on second
        call_count = 0
        original_atomic_move = atomic_move

        def mock_atomic_move(src, dst):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First attempt: simulate transient error
                try:
                    raise OSError("Network glitch")
                except OSError as e:
                    raise FileOperationError(f"Transient error: {src} -> {dst}") from e
            else:
                # Second attempt: succeed
                return original_atomic_move(src, dst)

        # Measure time to verify backoff
        with patch(
            "src.control_plane.state_machine.atomic_move", side_effect=mock_atomic_move
        ):
            start_time = time.time()
            result = sm.transition(
                task=task,
                to_state=WorkflowState.NEEDS_ACTION,
                reason="Test retry logic",
                actor="system",
            )
            elapsed = time.time() - start_time

        # Verify success
        assert call_count == 2, "Should have retried once"
        assert result.state == WorkflowState.NEEDS_ACTION
        assert result.file_path == isolated_fs / "Needs_Action" / "task-005.md"
        assert result.file_path.exists()

        # Verify exponential backoff (first backoff is 0.1s)
        assert (
            elapsed >= 0.1
        ), f"Should have waited at least 0.1s for backoff, got {elapsed:.3f}s"
        assert (
            elapsed < 0.5
        ), f"Should not have waited more than 0.5s, got {elapsed:.3f}s"

        # Verify log entry shows success
        log_file = isolated_fs / "Logs" / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        assert log_file.exists()
        log_content = log_file.read_text()
        assert '"result": "success"' in log_content

    def test_transition_retry_exhausted_after_max_attempts(self, isolated_fs):
        """
        Verify all retries exhausted after 3 attempts with proper error logging.

        Constitutional requirement (Section 9): Log errors at CRITICAL level.
        """
        # Create state machine with isolated filesystem
        sm = StateMachine(root_dir=isolated_fs, log_dir=isolated_fs / "Logs")

        # Create a task in Inbox
        task_path = isolated_fs / "Inbox" / "task-006.md"
        task = TaskFile(
            id="task-006",
            state=WorkflowState.INBOX,
            priority="P1",
            created_at=datetime.now(),
            modified_at=datetime.now(),
            metadata={},
            file_path=task_path,
            content="# Test retry exhaustion",
        )
        task.to_file(task_path)

        # Mock atomic_move to always fail with transient error
        call_count = 0

        def mock_atomic_move(src, dst):
            nonlocal call_count
            call_count += 1
            # Always fail with transient error
            try:
                raise OSError("Network glitch")
            except OSError as e:
                raise FileOperationError(f"Transient error: {src} -> {dst}") from e

        # Measure time to verify all backoffs: 0.1s + 0.2s + 0.4s = 0.7s (but last attempt doesn't backoff)
        # So total should be 0.1s + 0.2s = 0.3s
        with patch(
            "src.control_plane.state_machine.atomic_move", side_effect=mock_atomic_move
        ):
            start_time = time.time()
            with pytest.raises(FileOperationError):
                sm.transition(
                    task=task,
                    to_state=WorkflowState.NEEDS_ACTION,
                    reason="Test retry exhaustion",
                    actor="system",
                )
            elapsed = time.time() - start_time

        # Verify all 3 attempts were made
        assert call_count == 3, f"Should have made 3 attempts, got {call_count}"

        # Verify exponential backoff timing: 0.1s + 0.2s = 0.3s
        assert (
            elapsed >= 0.3
        ), f"Should have waited at least 0.3s for backoffs, got {elapsed:.3f}s"
        assert (
            elapsed < 0.8
        ), f"Should not have waited more than 0.8s, got {elapsed:.3f}s"

        # Verify task stayed in original state
        assert task.state == WorkflowState.INBOX
        assert task.file_path == task_path
        assert task_path.exists()

        # Verify CRITICAL log entry with attempt count
        log_file = isolated_fs / "Logs" / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        assert log_file.exists()
        log_content = log_file.read_text()
        assert '"result": "failure"' in log_content
        assert "CRITICAL: File operation failed after 3 attempt(s)" in log_content


class TestAtomicFileMove:
    """Tests for atomic file move operations used by StateMachine."""

    def test_atomic_move_success(self, isolated_fs):
        """
        Verify atomic_move successfully moves file from source to destination.

        Constitutional requirement (Section 4): File moves must be atomic.
        """
        # Create source file
        source = isolated_fs / "Inbox" / "task-001.md"
        source.write_text("Test content")

        # Move to destination
        destination = isolated_fs / "Needs_Action" / "task-001.md"
        atomic_move(source, destination)

        # Verify move succeeded
        assert not source.exists(), "Source file should not exist after move"
        assert destination.exists(), "Destination file should exist after move"
        assert destination.read_text() == "Test content", "Content should be preserved"

    def test_atomic_move_disk_full(self, isolated_fs):
        """
        Verify atomic_move raises FileOperationError on disk full (OSError errno 28).

        Constitutional requirement (Section 9): Errors never hidden.
        """
        source = isolated_fs / "Inbox" / "task-002.md"
        source.write_text("Test content")
        destination = isolated_fs / "Needs_Action" / "task-002.md"

        # Mock Path.rename to raise OSError with errno 28 (disk full)
        with patch.object(
            Path, "rename", side_effect=OSError(28, "No space left on device")
        ):
            with pytest.raises(FileOperationError) as exc_info:
                atomic_move(source, destination)

            assert "No space left on device" in str(exc_info.value)

    def test_atomic_move_permission_error(self, isolated_fs):
        """
        Verify atomic_move raises FileOperationError on permission error.

        Constitutional requirement (Section 9): Errors never hidden.
        """
        source = isolated_fs / "Inbox" / "task-003.md"
        source.write_text("Test content")
        destination = isolated_fs / "Needs_Action" / "task-003.md"

        # Mock Path.rename to raise PermissionError
        with patch.object(
            Path, "rename", side_effect=PermissionError("Permission denied")
        ):
            with pytest.raises(FileOperationError) as exc_info:
                atomic_move(source, destination)

            assert "Permission denied" in str(exc_info.value)

    def test_atomic_move_preserves_atomicity(self, isolated_fs):
        """
        Verify atomic_move is truly atomic (no partial state on failure).

        Constitutional requirement (Section 4): Atomic operations, no partial states.
        """
        source = isolated_fs / "Inbox" / "task-004.md"
        source.write_text("Test content")
        destination = isolated_fs / "Needs_Action" / "task-004.md"

        # Mock rename to fail
        with patch.object(Path, "rename", side_effect=OSError("Simulated failure")):
            try:
                atomic_move(source, destination)
            except FileOperationError:
                pass

        # Verify source still exists (no partial state)
        assert source.exists(), "Source should still exist after failed move"
        assert (
            not destination.exists()
        ), "Destination should not exist after failed move"

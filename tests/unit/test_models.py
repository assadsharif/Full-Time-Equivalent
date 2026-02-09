"""
Unit tests for data models

Constitutional compliance:
- Section 2 (Source of Truth): Tests verify file-backed state representation
- Section 4 (File-Driven Control Plane): Tests verify fixed workflow states
"""

import pytest
from pathlib import Path
from datetime import datetime
from src.control_plane.models import WorkflowState, TaskFile, StateTransition


class TestWorkflowState:
    """Tests for WorkflowState enum."""

    def test_has_exactly_7_states(self):
        """
        Verify WorkflowState has exactly 7 states.

        Constitutional requirement (Section 4): Fixed set of 8 workflow folders
        (7 states + Logs folder).
        """
        assert len(WorkflowState) == 7

    def test_inbox_state(self):
        """Verify INBOX state maps to 'Inbox' folder."""
        assert WorkflowState.INBOX.value == "Inbox"

    def test_needs_action_state(self):
        """Verify NEEDS_ACTION state maps to 'Needs_Action' folder."""
        assert WorkflowState.NEEDS_ACTION.value == "Needs_Action"

    def test_plans_state(self):
        """Verify PLANS state maps to 'Plans' folder."""
        assert WorkflowState.PLANS.value == "Plans"

    def test_pending_approval_state(self):
        """Verify PENDING_APPROVAL state maps to 'Pending_Approval' folder."""
        assert WorkflowState.PENDING_APPROVAL.value == "Pending_Approval"

    def test_approved_state(self):
        """Verify APPROVED state maps to 'Approved' folder."""
        assert WorkflowState.APPROVED.value == "Approved"

    def test_rejected_state(self):
        """Verify REJECTED state maps to 'Rejected' folder."""
        assert WorkflowState.REJECTED.value == "Rejected"

    def test_done_state(self):
        """Verify DONE state maps to 'Done' folder."""
        assert WorkflowState.DONE.value == "Done"

    def test_all_state_values(self):
        """Verify all state values match expected folder names."""
        expected_values = [
            "Inbox",
            "Needs_Action",
            "Plans",
            "Pending_Approval",
            "Approved",
            "Rejected",
            "Done",
        ]
        actual_values = [state.value for state in WorkflowState]
        assert sorted(actual_values) == sorted(expected_values)


class TestTaskFile:
    """Tests for TaskFile entity."""

    def test_from_file_reads_yaml_frontmatter(self, isolated_fs):
        """
        Verify TaskFile.from_file() reads and parses YAML frontmatter.

        Constitutional requirement (Section 2): Files are facts, state derived from disk.
        """
        # Create task file with YAML frontmatter
        task_path = isolated_fs / "Inbox" / "task-001.md"
        task_content = """---
id: task-001
state: Inbox
priority: P1
created_at: 2026-01-27T10:00:00Z
modified_at: 2026-01-27T10:00:00Z
metadata:
  tags: [test]
---

# Task: Test task

This is a test task.
"""
        task_path.write_text(task_content)

        # Load task file
        task = TaskFile.from_file(task_path)

        # Verify fields parsed correctly
        assert task.id == "task-001"
        assert task.state == WorkflowState.INBOX
        assert task.priority == "P1"
        assert task.file_path == task_path
        assert "This is a test task." in task.content

    def test_to_file_writes_yaml_frontmatter(self, isolated_fs):
        """
        Verify TaskFile.to_file() writes YAML frontmatter and markdown content.
        """
        task_path = isolated_fs / "Inbox" / "task-002.md"

        # Create TaskFile
        task = TaskFile(
            id="task-002",
            state=WorkflowState.INBOX,
            priority="P2",
            created_at=datetime(2026, 1, 27, 10, 0, 0),
            modified_at=datetime(2026, 1, 27, 10, 0, 0),
            metadata={"tags": ["test"]},
            file_path=task_path,
            content="# Task: Another test\n\nTest content.",
        )

        # Write to file
        task.to_file(task_path)

        # Verify file exists and contains expected content
        assert task_path.exists()
        content = task_path.read_text()
        assert "id: task-002" in content
        assert "state: Inbox" in content
        assert "priority: P2" in content
        assert "# Task: Another test" in content

    def test_derive_state_from_location(self, isolated_fs):
        """
        Verify TaskFile.derive_state_from_location() maps folder to WorkflowState.

        Constitutional requirement (Section 4): Folder state defines workflow state.
        """
        # Test each workflow folder
        test_cases = [
            ("Inbox", WorkflowState.INBOX),
            ("Needs_Action", WorkflowState.NEEDS_ACTION),
            ("Plans", WorkflowState.PLANS),
            ("Pending_Approval", WorkflowState.PENDING_APPROVAL),
            ("Approved", WorkflowState.APPROVED),
            ("Rejected", WorkflowState.REJECTED),
            ("Done", WorkflowState.DONE),
        ]

        for folder_name, expected_state in test_cases:
            task_path = isolated_fs / folder_name / "task.md"
            task_content = f"""---
id: test
state: {folder_name}
priority: P1
created_at: 2026-01-27T10:00:00Z
modified_at: 2026-01-27T10:00:00Z
---
Content"""
            task_path.write_text(task_content)

            task = TaskFile.from_file(task_path)
            derived_state = task.derive_state_from_location()

            assert (
                derived_state == expected_state
            ), f"Failed for folder {folder_name}: expected {expected_state}, got {derived_state}"

    def test_yaml_parsing_with_nested_metadata(self, isolated_fs):
        """
        Verify YAML parsing handles nested metadata structures.
        """
        task_path = isolated_fs / "Inbox" / "task-003.md"
        task_content = """---
id: task-003
state: Inbox
priority: P1
created_at: 2026-01-27T10:00:00Z
modified_at: 2026-01-27T10:00:00Z
metadata:
  tags: [feature, backend]
  estimated_hours: 8
  assigned_to: null
---

# Complex task
"""
        task_path.write_text(task_content)

        task = TaskFile.from_file(task_path)

        assert task.metadata["tags"] == ["feature", "backend"]
        assert task.metadata["estimated_hours"] == 8
        assert task.metadata["assigned_to"] is None


class TestStateTransition:
    """Tests for StateTransition entity."""

    def test_state_transition_all_fields(self):
        """
        Verify StateTransition has all required fields.

        Constitutional requirement (Section 8): Logs must include timestamp, action,
        triggering file, result, approval status.
        """
        transition = StateTransition(
            transition_id="trans-001",
            task_id="task-001",
            from_state=WorkflowState.INBOX,
            to_state=WorkflowState.NEEDS_ACTION,
            timestamp=datetime(2026, 1, 27, 10, 0, 0),
            reason="Validation complete",
            actor="system",
            logged=True,
            error=None,
        )

        assert transition.transition_id == "trans-001"
        assert transition.task_id == "task-001"
        assert transition.from_state == WorkflowState.INBOX
        assert transition.to_state == WorkflowState.NEEDS_ACTION
        assert transition.timestamp == datetime(2026, 1, 27, 10, 0, 0)
        assert transition.reason == "Validation complete"
        assert transition.actor == "system"
        assert transition.logged is True
        assert transition.error is None

    def test_state_transition_with_error(self):
        """
        Verify StateTransition can store error information.

        Constitutional requirement (Section 9): Errors must never be hidden.
        """
        transition = StateTransition(
            transition_id="trans-002",
            task_id="task-002",
            from_state=WorkflowState.PLANS,
            to_state=WorkflowState.REJECTED,
            timestamp=datetime(2026, 1, 27, 10, 30, 0),
            reason="Execution failed",
            actor="system",
            logged=True,
            error="Disk full",
        )

        assert transition.error == "Disk full"
        assert transition.to_state == WorkflowState.REJECTED

    def test_state_transition_actor_values(self):
        """
        Verify StateTransition supports 'system' and 'human' actors.

        Constitutional requirement (Section 7): Human approval is explicit.
        """
        # System actor
        system_transition = StateTransition(
            transition_id="trans-003",
            task_id="task-003",
            from_state=WorkflowState.NEEDS_ACTION,
            to_state=WorkflowState.PLANS,
            timestamp=datetime(2026, 1, 27, 11, 0, 0),
            reason="Planning started",
            actor="system",
            logged=True,
        )
        assert system_transition.actor == "system"

        # Human actor
        human_transition = StateTransition(
            transition_id="trans-004",
            task_id="task-004",
            from_state=WorkflowState.PENDING_APPROVAL,
            to_state=WorkflowState.APPROVED,
            timestamp=datetime(2026, 1, 27, 11, 30, 0),
            reason="Approved by human",
            actor="human",
            logged=True,
        )
        assert human_transition.actor == "human"

    def test_state_transition_logged_field(self):
        """
        Verify StateTransition tracks logging status.

        Constitutional requirement (Section 8): If action not logged, considered not executed.
        """
        transition = StateTransition(
            transition_id="trans-005",
            task_id="task-005",
            from_state=WorkflowState.APPROVED,
            to_state=WorkflowState.DONE,
            timestamp=datetime(2026, 1, 27, 12, 0, 0),
            reason="Execution complete",
            actor="system",
            logged=True,
        )

        assert transition.logged is True

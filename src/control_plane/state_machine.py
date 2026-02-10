"""
State machine for File-Driven Control Plane workflow transitions

Constitutional compliance:
- Section 4 (File-Driven Control Plane): Enforces valid workflow state transitions
- Section 6-7 (Autonomy & HITL): Requires approval for sensitive actions
- Section 13 (Task Lifecycle): Done is a terminal state
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set
import time
import uuid

from .models import WorkflowState, TaskFile, StateTransition
from .errors import InvalidTransitionError, FileOperationError
from .logger import AuditLogger
from utils.file_ops import atomic_move


class StateMachine:
    """
    State machine that validates workflow transitions.

    Constitutional requirement (Section 4): Only valid transitions are allowed.
    Constitutional requirement (Section 6-7): Approval steps cannot be skipped.
    Constitutional requirement (Section 13): Done is a terminal state.
    """

    def __init__(self, root_dir: Optional[Path] = None, log_dir: Optional[Path] = None):
        """
        Initialize state machine with transition matrix.

        Args:
            root_dir: Root directory containing workflow folders (Inbox, Needs_Action, etc.).
                     If None, defaults to current working directory.
            log_dir: Directory for audit logs. If None, defaults to root_dir/Logs.

        The transition matrix defines all valid state transitions.
        """
        # Store root directory for file operations
        self.root_dir = root_dir if root_dir is not None else Path.cwd()

        # Initialize audit logger
        # Constitutional requirement (Section 8): All transitions must be logged
        if log_dir is None:
            log_dir = self.root_dir / "Logs"
        self.audit_logger = AuditLogger(log_dir=log_dir)
        # Define valid transitions as a dictionary: from_state -> set of valid to_states
        self._transition_matrix: Dict[WorkflowState, Set[WorkflowState]] = {
            # Inbox: Can only move to Needs_Action (initial processing)
            WorkflowState.INBOX: {
                WorkflowState.NEEDS_ACTION,
            },
            # Needs_Action: Can move to Plans (start planning)
            WorkflowState.NEEDS_ACTION: {
                WorkflowState.PLANS,
            },
            # Plans: Can move to Pending_Approval (ready for review)
            #        or back to Needs_Action (clarifications needed)
            WorkflowState.PLANS: {
                WorkflowState.PENDING_APPROVAL,
                WorkflowState.NEEDS_ACTION,
            },
            # Pending_Approval: Can be Approved or Rejected (human decision)
            # Constitutional requirement (Section 7): Human approval required
            WorkflowState.PENDING_APPROVAL: {
                WorkflowState.APPROVED,
                WorkflowState.REJECTED,
            },
            # Approved: Can move to Done (execution succeeded)
            #           or to Rejected (execution failed)
            WorkflowState.APPROVED: {
                WorkflowState.DONE,
                WorkflowState.REJECTED,
            },
            # Rejected: Can move back to Inbox (retry with revised approach)
            WorkflowState.REJECTED: {
                WorkflowState.INBOX,
            },
            # Done: Terminal state - no transitions allowed
            # Constitutional requirement (Section 13): Done is complete
            WorkflowState.DONE: set(),
        }

    def validate_transition(
        self, from_state: WorkflowState, to_state: WorkflowState
    ) -> bool:
        """
        Validate whether a state transition is allowed.

        Constitutional requirement (Section 4): Only predefined transitions are valid.
        Constitutional requirement (Section 6-7): Approval steps cannot be skipped.

        Args:
            from_state: Current workflow state
            to_state: Target workflow state

        Returns:
            True if transition is valid, False otherwise
        """
        # Get valid target states for the current state
        valid_targets = self._transition_matrix.get(from_state, set())

        # Check if target state is in the set of valid targets
        return to_state in valid_targets

    def transition(
        self, task: TaskFile, to_state: WorkflowState, reason: str, actor: str
    ) -> TaskFile:
        """
        Perform state transition for a task.

        Constitutional requirement (Section 4): Atomic state transitions.
        Constitutional requirement (Section 6-7): Approval requirements enforced.
        Constitutional requirement (Section 8): All transitions must be logged.

        Args:
            task: TaskFile to transition
            to_state: Target workflow state
            reason: Reason for the transition
            actor: Actor initiating transition ('system' or 'human')

        Returns:
            Updated TaskFile with new state and file path

        Raises:
            InvalidTransitionError: If transition is not allowed
            FileOperationError: If file operation fails
        """
        # Validate transition is allowed
        if not self.validate_transition(task.state, to_state):
            raise InvalidTransitionError(
                f"Invalid transition: {task.state.value} → {to_state.value}. "
                f"This transition is not allowed by the workflow rules."
            )

        # Store original state for logging
        from_state = task.state

        # Calculate destination path
        destination_folder = self.root_dir / to_state.value
        destination_path = destination_folder / task.file_path.name

        # Ensure destination folder exists
        destination_folder.mkdir(parents=True, exist_ok=True)

        # Store original path for atomic move
        source_path = task.file_path

        # Perform atomic file move with retry logic for transient failures
        # Constitutional requirement (Section 4): Atomic state transitions
        # Constitutional requirement (Section 9): Errors never hidden
        max_attempts = 3
        attempt = 0
        last_error = None

        while attempt < max_attempts:
            attempt += 1
            try:
                atomic_move(source_path, destination_path)
                last_error = None  # Clear error on success
                break  # Success - exit retry loop
            except FileOperationError as e:
                last_error = e

                # Check error type to determine if we should retry
                is_permission_error = isinstance(
                    e.__cause__, PermissionError
                ) or "Permission denied" in str(e)
                is_disk_full = (
                    (isinstance(e.__cause__, OSError) and e.__cause__.errno == 28)
                    or "No space left on device" in str(e)
                    or "[Errno 28]" in str(e)
                )

                # Don't retry disk full or permission errors
                if is_disk_full or is_permission_error:
                    break

                # For transient errors, retry with exponential backoff
                if attempt < max_attempts:
                    backoff_time = 0.1 * (2 ** (attempt - 1))  # 0.1s, 0.2s, 0.4s
                    time.sleep(backoff_time)
                    continue  # Retry

                # All retries exhausted - will handle error below
                break

        # Check if we have an error after retry loop
        if last_error is not None:
            e = last_error

            # Check if this is a permission error
            is_permission_error = isinstance(
                e.__cause__, PermissionError
            ) or "Permission denied" in str(e)

            if is_permission_error:
                # T039: Permission errors → move to /Rejected if possible
                try:
                    rejected_folder = self.root_dir / WorkflowState.REJECTED.value
                    rejected_folder.mkdir(parents=True, exist_ok=True)
                    rejected_path = rejected_folder / task.file_path.name

                    # Try to move to /Rejected instead
                    atomic_move(source_path, rejected_path)

                    # Update task to reflect /Rejected state
                    task.file_path = rejected_path
                    task.state = WorkflowState.REJECTED
                    task.to_file(rejected_path)

                    # Log the rejection with error details
                    rejection_transition = StateTransition(
                        transition_id=str(uuid.uuid4()),
                        task_id=task.id,
                        from_state=from_state,
                        to_state=WorkflowState.REJECTED,
                        timestamp=datetime.now(),
                        reason=f"Permission error: {reason}",
                        actor=actor,
                        logged=True,
                        error=f"Permission denied - moved to Rejected: {str(e)}",
                    )
                    self.audit_logger.log_transition(rejection_transition)

                    # Return the rejected task (don't raise)
                    return task

                except FileOperationError:
                    # Can't even move to /Rejected - log CRITICAL and re-raise original
                    pass

            # Log failed transition at CRITICAL level
            # (disk full, permission error that couldn't be salvaged, or transient error after all retries)
            # Task remains in original state (file not moved)
            error_msg = (
                f"CRITICAL: File operation failed after {attempt} attempt(s) - {str(e)}"
            )
            failed_transition = StateTransition(
                transition_id=str(uuid.uuid4()),
                task_id=task.id,
                from_state=from_state,
                to_state=to_state,
                timestamp=datetime.now(),
                reason=reason,
                actor=actor,
                logged=True,
                error=error_msg,
            )
            self.audit_logger.log_transition(failed_transition)

            # Re-raise the error (don't swallow it)
            # Constitutional requirement (Section 9): Errors never hidden
            raise e

        # Update task's file_path to new location
        task.file_path = destination_path

        # Update task's state to match new location
        # Constitutional requirement (Section 4): Folder location defines state
        task.update_state()

        # Persist updated task to disk (update frontmatter)
        task.to_file(destination_path)

        # Create StateTransition for logging (success)
        # Constitutional requirement (Section 8): All transitions must be logged
        transition = StateTransition(
            transition_id=str(uuid.uuid4()),
            task_id=task.id,
            from_state=from_state,
            to_state=to_state,
            timestamp=datetime.now(),
            reason=reason,
            actor=actor,
            logged=True,
            error=None,
        )

        # Log the successful transition
        self.audit_logger.log_transition(transition)

        return task

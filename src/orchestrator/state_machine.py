"""
State Machine — validates and executes task state transitions.

Allowed transitions (directed graph):

    NEEDS_ACTION  → PLANNING
    PLANNING      → PENDING_APPROVAL | EXECUTING
    PENDING_APPROVAL → EXECUTING | REJECTED
    EXECUTING     → DONE | REJECTED
    DONE          → (terminal)
    REJECTED      → (terminal)

Any attempt to move outside this graph raises TransitionError.
The machine also physically moves the task .md file between vault
folders to keep the file system in sync with logical state.
"""

from pathlib import Path

from .models import TaskState

# Adjacency map: state → set of valid next states
_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.NEEDS_ACTION: {TaskState.PLANNING},
    TaskState.PLANNING: {TaskState.PENDING_APPROVAL, TaskState.EXECUTING},
    TaskState.PENDING_APPROVAL: {TaskState.EXECUTING, TaskState.REJECTED},
    TaskState.EXECUTING: {TaskState.DONE, TaskState.REJECTED},
    TaskState.DONE: set(),  # terminal
    TaskState.REJECTED: set(),  # terminal
}

# Logical state → vault folder name
_STATE_FOLDERS: dict[TaskState, str] = {
    TaskState.NEEDS_ACTION: "Needs_Action",
    TaskState.PLANNING: "In_Progress",
    TaskState.PENDING_APPROVAL: "Approvals",
    TaskState.EXECUTING: "In_Progress",
    TaskState.DONE: "Done",
    TaskState.REJECTED: "Needs_Action",  # rejected tasks go back for review
}


class TransitionError(Exception):
    """Raised when a state transition is not allowed."""


class StateMachine:
    """Validates transitions and moves files between vault folders."""

    def __init__(self, vault_path: Path):
        self._vault = vault_path

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def is_valid_transition(current: TaskState, target: TaskState) -> bool:
        """Return True if current → target is an allowed edge."""
        return target in _TRANSITIONS.get(current, set())

    @staticmethod
    def valid_next_states(current: TaskState) -> set[TaskState]:
        """Return the set of states reachable from *current*."""
        return _TRANSITIONS.get(current, set())

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def transition(
        self, task_path: Path, current: TaskState, target: TaskState
    ) -> Path:
        """
        Validate current → target, move the file, return new path.

        Raises:
            TransitionError: if the edge is not in the graph.
            FileNotFoundError: if task_path does not exist.
        """
        if not self.is_valid_transition(current, target):
            raise TransitionError(
                f"Invalid transition: {current.value} → {target.value} "
                f"(allowed: {[s.value for s in self.valid_next_states(current)]})"
            )

        if not task_path.exists():
            raise FileNotFoundError(f"Task file not found: {task_path}")

        target_folder = self._vault / _STATE_FOLDERS[target]
        target_folder.mkdir(parents=True, exist_ok=True)

        new_path = target_folder / task_path.name
        # If source and dest are the same folder, skip the move
        if task_path.parent.resolve() != target_folder.resolve():
            task_path.rename(new_path)

        return new_path

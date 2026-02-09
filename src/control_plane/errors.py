"""
Custom exceptions for File-Driven Control Plane

Constitutional compliance:
- Section 9 (Error Handling): Errors never hidden, explicit error types
"""


class ControlPlaneError(Exception):
    """
    Base exception for all control plane errors.

    Constitutional requirement (Section 9): Errors must never be hidden.
    """

    pass


class InvalidTransitionError(ControlPlaneError):
    """
    Raised when a state transition is not allowed per the transition matrix.

    Example: Attempting to move from Plans → Approved (skipping approval requirement)
    """

    pass


class ApprovalRequiredError(ControlPlaneError):
    """
    Raised when attempting to execute a sensitive action without approval.

    Constitutional requirement (Section 6-7): Sensitive actions require approval.
    """

    pass


class StateInconsistencyError(ControlPlaneError):
    """
    Raised when file location does not match metadata state.

    Constitutional requirement (Section 2): File system is source of truth.
    """

    pass


class LogWriteError(ControlPlaneError):
    """
    Raised when unable to write to append-only log.

    Constitutional requirement (Section 8): Every action must be logged.
    """

    pass


class FileOperationError(ControlPlaneError):
    """
    Raised when atomic file operation fails (disk full, permissions, etc.).

    Constitutional requirement (Section 4): File moves must be atomic.
    """

    pass

"""
Structured logging configuration for File-Driven Control Plane

Constitutional compliance:
- Section 8 (Auditability & Logging): Append-only, structured logging with required fields
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import StateTransition

# Note: structlog configuration available but not required for AuditLogger
# import logging
# import structlog
#
# def configure_structlog() -> None:
#     """Configure structlog for append-only JSON logging."""
#     structlog.configure(
#         processors=[
#             structlog.contextvars.merge_contextvars,
#             structlog.processors.add_log_level,
#             structlog.processors.TimeStamper(fmt="iso", utc=True),
#             structlog.processors.StackInfoRenderer(),
#             structlog.processors.format_exc_info,
#             structlog.processors.JSONRenderer(),
#         ],
#         wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
#         context_class=dict,
#         logger_factory=structlog.PrintLoggerFactory(),
#         cache_logger_on_first_use=True,
#     )
#
# # Configure on module import
# configure_structlog()


class AuditLogger:
    """
    Audit logger for state transitions.

    Constitutional requirement (Section 8): All state changes must be logged
    with timestamp, action type, triggering file, result, and approval status.
    """

    def __init__(self, log_dir: Path):
        """
        Initialize audit logger.

        Args:
            log_dir: Directory where log files will be stored
        """
        self.log_dir = log_dir
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_transition(self, transition: StateTransition) -> None:
        """
        Log a state transition to daily log file.

        Constitutional requirement (Section 8): Append-only, structured logging.

        Args:
            transition: StateTransition to log

        Raises:
            IOError: If log file cannot be written
        """
        # Determine log file based on transition timestamp
        log_date = transition.timestamp.strftime("%Y-%m-%d")
        log_file = self.log_dir / f"{log_date}.log"

        # Build log entry with all required fields
        # Constitutional requirement (Section 8): timestamp, action, task_id, result, approval_status
        log_entry = {
            "timestamp": transition.timestamp.isoformat(),
            "action": "state_transition",
            "transition_id": transition.transition_id,
            "task_id": transition.task_id,
            "from_state": transition.from_state.value,
            "to_state": transition.to_state.value,
            "result": "success" if transition.error is None else "failure",
            "reason": transition.reason,
            "actor": transition.actor,
            "approval_status": transition.actor,  # 'system' or 'human'
        }

        # Include error if present
        if transition.error is not None:
            log_entry["error"] = transition.error

        # Write JSON entry to log file (append mode)
        # Constitutional requirement (Section 8): Append-only logging
        with open(log_file, "a", encoding="utf-8") as f:
            json.dump(log_entry, f)
            f.write("\n")  # Newline for readability

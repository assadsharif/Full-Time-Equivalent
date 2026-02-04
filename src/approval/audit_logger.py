"""
Approval Audit Logger — append-only JSON-lines event log for the
HITL approval lifecycle (spec 010, US4 Audit Trail).

Every state transition (create → approve | reject | timeout) is
recorded as a single JSON line.  The log is stateless and crash-safe:
each ``log_*`` call opens, appends, and closes the file.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class ApprovalAuditLogger:
    """
    Append-only logger for approval lifecycle events.

    Args:
        log_path: Path to the approval_audit.log (JSON lines).
    """

    def __init__(self, log_path: Path):
        self._log_path = log_path

    # ------------------------------------------------------------------
    # Event writers
    # ------------------------------------------------------------------

    def log_created(
        self,
        approval_id: str,
        task_id: str,
        action_type: str,
        risk_level: str,
    ) -> None:
        """Record an approval-request creation event."""
        self._write({
            "event_type": "approval_created",
            "approval_id": approval_id,
            "task_id": task_id,
            "action_type": action_type,
            "risk_level": risk_level,
            "status": "pending",
        })

    def log_approved(
        self,
        approval_id: str,
        task_id: str,
        action_type: str,
        risk_level: str,
        approver: Optional[str] = None,
    ) -> None:
        """Record an approval event."""
        self._write({
            "event_type": "approval_approved",
            "approval_id": approval_id,
            "task_id": task_id,
            "action_type": action_type,
            "risk_level": risk_level,
            "status": "approved",
            "approver": approver,
        })

    def log_rejected(
        self,
        approval_id: str,
        task_id: str,
        action_type: str,
        risk_level: str,
        reason: str = "",
        approver: Optional[str] = None,
    ) -> None:
        """Record a rejection event."""
        self._write({
            "event_type": "approval_rejected",
            "approval_id": approval_id,
            "task_id": task_id,
            "action_type": action_type,
            "risk_level": risk_level,
            "status": "rejected",
            "reason": reason,
            "approver": approver,
        })

    def log_timeout(
        self,
        approval_id: str,
        task_id: str,
        action_type: str,
        risk_level: str,
    ) -> None:
        """Record a timeout event."""
        self._write({
            "event_type": "approval_timeout",
            "approval_id": approval_id,
            "task_id": task_id,
            "action_type": action_type,
            "risk_level": risk_level,
            "status": "timeout",
        })

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write(self, record: dict) -> None:
        record["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._log_path, "a") as fh:
            fh.write(json.dumps(record) + "\n")

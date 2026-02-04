"""
Approval Audit Query Service — reads the approval audit log and
exposes filtered views (spec 010, US4 Audit Trail).

All queries are stateless: each call scans the log file on demand.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class ApprovalAuditQuery:
    """
    Query interface over the approval audit log.

    Args:
        log_path: Path to the approval_audit.log (JSON lines).
    """

    def __init__(self, log_path: Path):
        self._log_path = log_path

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def query_approval_events(
        self,
        *,
        task_id: Optional[str] = None,
        approval_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict]:
        """
        Return events, optionally filtered by task_id, approval_id,
        and/or status.  Results are in chronological order (oldest first).
        """
        events = self._load()
        if task_id:
            events = [e for e in events if e.get("task_id") == task_id]
        if approval_id:
            events = [e for e in events if e.get("approval_id") == approval_id]
        if status:
            events = [e for e in events if e.get("status") == status]
        return events

    def query_approver_history(self, approver: str) -> list[dict]:
        """Return all decision events (approved / rejected) made by *approver*."""
        return [
            e for e in self._load()
            if e.get("approver") == approver
            and e.get("event_type") in ("approval_approved", "approval_rejected")
        ]

    def query_approval_stats(self, since: Optional[datetime] = None) -> dict:
        """
        Return aggregate statistics:

        - total_events
        - approved_count / rejected_count / timeout_count / pending_count
        - approval_rate  (approved / (approved + rejected))
        - avg_response_time_seconds  (created → decided, paired by approval_id)
        """
        events = self._load()
        if since:
            events = [
                e for e in events
                if self._parse_ts(e["timestamp"]) >= since
            ]

        counts: dict[str, int] = {"approved": 0, "rejected": 0, "timeout": 0, "pending": 0}
        created_at: dict[str, datetime] = {}
        decided_at: dict[str, datetime] = {}

        for e in events:
            status = e.get("status", "")
            if status in counts:
                counts[status] += 1

            aid = e.get("approval_id")
            ts = self._parse_ts(e["timestamp"]) if e.get("timestamp") else None
            if not ts or not aid:
                continue

            if e.get("event_type") == "approval_created":
                created_at[aid] = ts
            elif e.get("event_type") in ("approval_approved", "approval_rejected"):
                decided_at[aid] = ts

        decided = counts["approved"] + counts["rejected"]
        approval_rate = counts["approved"] / decided if decided else 0.0

        deltas = [
            (decided_at[aid] - created_at[aid]).total_seconds()
            for aid in decided_at
            if aid in created_at
        ]
        avg_response = sum(deltas) / len(deltas) if deltas else 0.0

        return {
            "total_events": len(events),
            "approved_count": counts["approved"],
            "rejected_count": counts["rejected"],
            "timeout_count": counts["timeout"],
            "pending_count": counts["pending"],
            "approval_rate": round(approval_rate, 4),
            "avg_response_time_seconds": round(avg_response, 2),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> list[dict]:
        if not self._log_path.exists():
            return []
        lines = self._log_path.read_text().strip().split("\n")
        return [json.loads(ln) for ln in lines if ln]

    @staticmethod
    def _parse_ts(ts_str: str) -> datetime:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))

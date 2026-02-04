"""
Orchestrator Dashboard — real-time status and task queue visibility.

Provides methods for querying orchestrator state: running/stopped status,
pending task queue with priorities, active tasks, and recent completions.
Designed for CLI dashboard and monitoring displays.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.orchestrator.priority_scorer import PriorityScorer
from src.orchestrator.models import OrchestratorConfig


class OrchestratorDashboard:
    """Real-time dashboard data provider for orchestrator state."""

    def __init__(self, vault_path: Path, config: Optional[OrchestratorConfig] = None):
        """
        Args:
            vault_path: Orchestrator vault (e.g., ~/AI_Employee_Vault)
            config: Optional OrchestratorConfig for priority scoring
        """
        self._vault_path = vault_path
        self._checkpoint_path = vault_path.parent / ".fte" / "orchestrator.checkpoint.json"
        self._config = config or OrchestratorConfig(vault_path=vault_path)
        self._scorer = PriorityScorer(self._config)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """Return orchestrator operational status.

        Returns:
            {
                "state": "running" | "stopped" | "error",
                "last_seen": ISO timestamp or None,
                "last_iteration": int or None,
                "message": str,
            }
        """
        if not self._checkpoint_path.exists():
            return {
                "state": "stopped",
                "last_seen": None,
                "last_iteration": None,
                "message": "Checkpoint not found — orchestrator has not run yet",
            }

        try:
            checkpoint = json.loads(self._checkpoint_path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            return {
                "state": "error",
                "last_seen": None,
                "last_iteration": None,
                "message": f"Checkpoint read error: {exc}",
            }

        mtime = self._checkpoint_path.stat().st_mtime
        age_seconds = int(time.time() - mtime)
        last_seen = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

        # Consider "running" if checkpoint updated in last 5 minutes
        if age_seconds < 300:
            state = "running"
            message = f"Active (checkpoint {age_seconds}s ago)"
        else:
            state = "stopped"
            message = f"Idle (checkpoint {age_seconds}s ago)"

        return {
            "state": state,
            "last_seen": last_seen,
            "last_iteration": checkpoint.get("last_iteration"),
            "message": message,
        }

    # ------------------------------------------------------------------
    # Queue
    # ------------------------------------------------------------------

    def get_queue(self) -> list[dict]:
        """Return pending tasks from Needs_Action with priority scores.

        Returns:
            List of dicts sorted by priority (highest first):
            [
                {
                    "name": "task.md",
                    "priority": 3.5,
                    "path": "/path/to/task.md",
                },
                ...
            ]
        """
        needs_action = self._vault_path / "Needs_Action"
        if not needs_action.exists():
            return []

        tasks: list[dict] = []
        for md in needs_action.glob("*.md"):
            try:
                score = self._scorer.score(md)
                tasks.append({
                    "name": md.name,
                    "priority": round(score, 2),
                    "path": str(md),
                })
            except Exception:
                # Skip files that can't be scored
                continue

        tasks.sort(key=lambda t: t["priority"], reverse=True)
        return tasks

    # ------------------------------------------------------------------
    # Active tasks
    # ------------------------------------------------------------------

    def get_active_tasks(self) -> list[dict]:
        """Return currently executing tasks from checkpoint.

        Returns:
            List of active task dicts:
            [
                {
                    "name": "task.md",
                    "state": "executing",
                    "priority": 2.5,
                    "attempts": 1,
                },
                ...
            ]
        """
        if not self._checkpoint_path.exists():
            return []

        try:
            checkpoint = json.loads(self._checkpoint_path.read_text())
        except (json.JSONDecodeError, OSError):
            return []

        active = checkpoint.get("active_tasks", {})
        return [
            {
                "name": name,
                "state": task_data.get("state", "unknown"),
                "priority": round(task_data.get("priority", 0.0), 2),
                "attempts": task_data.get("attempts", 0),
            }
            for name, task_data in active.items()
        ]

    # ------------------------------------------------------------------
    # Recent completions
    # ------------------------------------------------------------------

    def get_recent_completions(self, limit: int = 10) -> list[dict]:
        """Return last N completed tasks from checkpoint exit_log.

        Args:
            limit: Maximum number of completions to return

        Returns:
            List of completion dicts (most recent first):
            [
                {
                    "task": "task.md",
                    "success": True,
                    "final_state": "done",
                    "duration_s": 15.3,
                    "timestamp": ISO timestamp,
                },
                ...
            ]
        """
        if not self._checkpoint_path.exists():
            return []

        try:
            checkpoint = json.loads(self._checkpoint_path.read_text())
        except (json.JSONDecodeError, OSError):
            return []

        exit_log = checkpoint.get("exit_log", [])
        # Most recent first
        recent = exit_log[-limit:] if len(exit_log) > limit else exit_log
        recent.reverse()

        return [
            {
                "task": entry.get("task", "unknown"),
                "success": entry.get("success", False),
                "final_state": entry.get("final_state", "unknown"),
                "duration_s": entry.get("duration_s", 0.0),
                "timestamp": entry.get("timestamp", ""),
            }
            for entry in recent
        ]

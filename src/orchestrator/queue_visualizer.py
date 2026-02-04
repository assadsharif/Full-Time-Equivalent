"""
Queue Visualizer — formatting and rendering for the orchestrator task queue.

Provides methods for formatting task entries with priority scores and wait times,
and rendering the queue as ASCII tables for CLI display.
"""

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.orchestrator.priority_scorer import PriorityScorer
from src.orchestrator.models import OrchestratorConfig


class QueueVisualizer:
    """Task queue formatter and renderer."""

    def __init__(self, vault_path: Path, config: Optional[OrchestratorConfig] = None):
        """
        Args:
            vault_path: Orchestrator vault (e.g., ~/AI_Employee_Vault)
            config: Optional OrchestratorConfig for priority scoring
        """
        self._vault_path = vault_path
        self._config = config or OrchestratorConfig(vault_path=vault_path)
        self._scorer = PriorityScorer(self._config)

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_task_entry(self, task_path: Path, verbose: bool = False) -> dict:
        """Format a single task entry with name, priority, and wait time.

        Args:
            task_path: Path to task file
            verbose: If True, include additional details (file path, etc.)

        Returns:
            {
                "name": "task.md",
                "priority": 3.5,
                "wait_time_seconds": 120,
                "wait_time_display": "2m",
                "path": "/full/path/to/task.md" (if verbose),
            }
        """
        try:
            score = self._scorer.score(task_path)
        except Exception:
            score = 0.0

        # Wait time = time since file was last modified
        mtime = task_path.stat().st_mtime
        wait_seconds = int(time.time() - mtime)

        # Format wait time for display
        if wait_seconds < 60:
            wait_display = f"{wait_seconds}s"
        elif wait_seconds < 3600:
            wait_display = f"{wait_seconds // 60}m"
        elif wait_seconds < 86400:
            wait_display = f"{wait_seconds // 3600}h"
        else:
            wait_display = f"{wait_seconds // 86400}d"

        entry = {
            "name": task_path.name,
            "priority": round(score, 2),
            "wait_time_seconds": wait_seconds,
            "wait_time_display": wait_display,
        }

        if verbose:
            entry["path"] = str(task_path)

        return entry

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render_queue_table(self, verbose: bool = False) -> list[dict]:
        """Render the task queue as a list of formatted entries.

        Args:
            verbose: If True, include additional details in each entry

        Returns:
            List of task entry dicts sorted by priority (highest first)
        """
        needs_action = self._vault_path / "Needs_Action"
        if not needs_action.exists():
            return []

        tasks: list[dict] = []
        for md in needs_action.glob("*.md"):
            try:
                entry = self.format_task_entry(md, verbose=verbose)
                tasks.append(entry)
            except Exception:
                # Skip files that can't be processed
                continue

        # Sort by priority (highest first)
        tasks.sort(key=lambda t: t["priority"], reverse=True)
        return tasks

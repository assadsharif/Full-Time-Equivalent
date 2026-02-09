"""Tests for OrchestratorDashboard (spec 006 US7)."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.orchestrator.dashboard import OrchestratorDashboard

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vault_path(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


@pytest.fixture
def dashboard(vault_path):
    return OrchestratorDashboard(vault_path=vault_path)


def _seed_checkpoint(vault_path: Path, data: dict, age_seconds: int = 0) -> None:
    """Create a checkpoint file with specified content and age."""
    ckpt_path = vault_path.parent / ".fte" / "orchestrator.checkpoint.json"
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    ckpt_path.write_text(json.dumps(data))
    if age_seconds > 0:
        import os

        mtime = time.time() - age_seconds
        os.utime(ckpt_path, (mtime, mtime))


def _seed_queue(vault_path: Path, tasks: list[tuple[str, str]]) -> None:
    """Seed Needs_Action with tasks. Each task is (name, content)."""
    needs_action = vault_path / "Needs_Action"
    needs_action.mkdir(parents=True, exist_ok=True)
    for name, content in tasks:
        (needs_action / name).write_text(content)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


class TestGetStatus:
    def test_no_checkpoint_returns_stopped(self, dashboard):
        status = dashboard.get_status()
        assert status["state"] == "stopped"
        assert status["last_seen"] is None
        assert "not found" in status["message"].lower()

    def test_fresh_checkpoint_returns_running(self, vault_path, dashboard):
        _seed_checkpoint(vault_path, {"last_iteration": 5}, age_seconds=10)
        status = dashboard.get_status()
        assert status["state"] == "running"
        assert status["last_iteration"] == 5
        assert "10s ago" in status["message"] or "active" in status["message"].lower()

    def test_stale_checkpoint_returns_stopped(self, vault_path, dashboard):
        _seed_checkpoint(vault_path, {"last_iteration": 3}, age_seconds=600)
        status = dashboard.get_status()
        assert status["state"] == "stopped"
        assert "600s ago" in status["message"] or "idle" in status["message"].lower()

    def test_malformed_checkpoint_returns_error(self, vault_path, dashboard):
        ckpt_path = vault_path.parent / ".fte" / "orchestrator.checkpoint.json"
        ckpt_path.parent.mkdir(parents=True, exist_ok=True)
        ckpt_path.write_text("not valid json")
        status = dashboard.get_status()
        assert status["state"] == "error"
        assert "read error" in status["message"].lower()


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------


class TestGetQueue:
    def test_no_needs_action_returns_empty(self, dashboard):
        queue = dashboard.get_queue()
        assert queue == []

    def test_empty_needs_action_returns_empty(self, vault_path, dashboard):
        (vault_path / "Needs_Action").mkdir()
        queue = dashboard.get_queue()
        assert queue == []

    def test_returns_tasks_with_priorities(self, vault_path, dashboard):
        _seed_queue(
            vault_path,
            [
                ("task1.md", "# Task 1\n**Priority**: High\n**Urgency**: ASAP\n"),
                ("task2.md", "# Task 2\n**Priority**: Low\n"),
            ],
        )
        queue = dashboard.get_queue()
        assert len(queue) == 2
        assert all("name" in t and "priority" in t and "path" in t for t in queue)
        # High priority should come first
        assert queue[0]["name"] == "task1.md"
        assert queue[0]["priority"] > queue[1]["priority"]

    def test_queue_sorted_descending_by_priority(self, vault_path, dashboard):
        _seed_queue(
            vault_path,
            [
                ("low.md", "# Low Priority\n"),
                ("high.md", "# High Priority\n**Priority**: High\n**Urgency**: ASAP\n"),
                ("mid.md", "# Mid Priority\n**Priority**: Medium\n"),
            ],
        )
        queue = dashboard.get_queue()
        priorities = [t["priority"] for t in queue]
        assert priorities == sorted(priorities, reverse=True)

    def test_skips_malformed_tasks(self, vault_path, dashboard):
        _seed_queue(
            vault_path,
            [
                ("good.md", "# Good Task\n"),
                ("bad.md", ""),  # Empty file might cause scoring issues
            ],
        )
        queue = dashboard.get_queue()
        # At least the good task should be present
        assert any(t["name"] == "good.md" for t in queue)


# ---------------------------------------------------------------------------
# Active tasks
# ---------------------------------------------------------------------------


class TestGetActiveTasks:
    def test_no_checkpoint_returns_empty(self, dashboard):
        active = dashboard.get_active_tasks()
        assert active == []

    def test_checkpoint_without_active_tasks_returns_empty(self, vault_path, dashboard):
        _seed_checkpoint(vault_path, {"last_iteration": 1})
        active = dashboard.get_active_tasks()
        assert active == []

    def test_returns_active_tasks_from_checkpoint(self, vault_path, dashboard):
        _seed_checkpoint(
            vault_path,
            {
                "last_iteration": 2,
                "active_tasks": {
                    "task1.md": {"state": "executing", "priority": 3.5, "attempts": 1},
                    "task2.md": {"state": "planning", "priority": 2.0, "attempts": 0},
                },
            },
        )
        active = dashboard.get_active_tasks()
        assert len(active) == 2
        names = {t["name"] for t in active}
        assert names == {"task1.md", "task2.md"}
        task1 = next(t for t in active if t["name"] == "task1.md")
        assert task1["state"] == "executing"
        assert task1["priority"] == 3.5
        assert task1["attempts"] == 1

    def test_malformed_checkpoint_returns_empty(self, vault_path, dashboard):
        ckpt_path = vault_path.parent / ".fte" / "orchestrator.checkpoint.json"
        ckpt_path.parent.mkdir(parents=True, exist_ok=True)
        ckpt_path.write_text("not valid json")
        active = dashboard.get_active_tasks()
        assert active == []


# ---------------------------------------------------------------------------
# Recent completions
# ---------------------------------------------------------------------------


class TestGetRecentCompletions:
    def test_no_checkpoint_returns_empty(self, dashboard):
        recent = dashboard.get_recent_completions()
        assert recent == []

    def test_checkpoint_without_exit_log_returns_empty(self, vault_path, dashboard):
        _seed_checkpoint(vault_path, {"last_iteration": 1})
        recent = dashboard.get_recent_completions()
        assert recent == []

    def test_returns_recent_completions_from_exit_log(self, vault_path, dashboard):
        _seed_checkpoint(
            vault_path,
            {
                "last_iteration": 1,
                "exit_log": [
                    {
                        "task": "task1.md",
                        "success": True,
                        "final_state": "done",
                        "duration_s": 10.5,
                        "timestamp": "2026-02-05T12:00:00Z",
                    },
                    {
                        "task": "task2.md",
                        "success": False,
                        "final_state": "rejected",
                        "duration_s": 5.2,
                        "timestamp": "2026-02-05T12:05:00Z",
                    },
                ],
            },
        )
        recent = dashboard.get_recent_completions(limit=10)
        assert len(recent) == 2
        # Most recent first
        assert recent[0]["task"] == "task2.md"
        assert recent[1]["task"] == "task1.md"
        assert recent[0]["success"] is False
        assert recent[1]["success"] is True

    def test_respects_limit(self, vault_path, dashboard):
        exit_log = [
            {
                "task": f"task{i}.md",
                "success": True,
                "final_state": "done",
                "duration_s": 1.0,
                "timestamp": f"2026-02-05T12:{i:02d}:00Z",
            }
            for i in range(20)
        ]
        _seed_checkpoint(vault_path, {"last_iteration": 1, "exit_log": exit_log})
        recent = dashboard.get_recent_completions(limit=5)
        assert len(recent) == 5
        # Should return the last 5 (most recent)
        assert recent[0]["task"] == "task19.md"
        assert recent[4]["task"] == "task15.md"

    def test_less_than_limit_returns_all(self, vault_path, dashboard):
        exit_log = [
            {
                "task": "task1.md",
                "success": True,
                "final_state": "done",
                "duration_s": 1.0,
                "timestamp": "2026-02-05T12:00:00Z",
            },
        ]
        _seed_checkpoint(vault_path, {"last_iteration": 1, "exit_log": exit_log})
        recent = dashboard.get_recent_completions(limit=10)
        assert len(recent) == 1


# ---------------------------------------------------------------------------
# Integration smoke test
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_dashboard_with_realistic_checkpoint(self, vault_path, dashboard):
        """Smoke test: create a realistic checkpoint and verify all methods work."""
        _seed_checkpoint(
            vault_path,
            {
                "last_iteration": 10,
                "active_tasks": {
                    "executing.md": {
                        "state": "executing",
                        "priority": 4.0,
                        "attempts": 1,
                    },
                },
                "exit_log": [
                    {
                        "task": "done1.md",
                        "success": True,
                        "final_state": "done",
                        "duration_s": 15.3,
                        "timestamp": "2026-02-05T10:00:00Z",
                    },
                    {
                        "task": "done2.md",
                        "success": True,
                        "final_state": "done",
                        "duration_s": 8.7,
                        "timestamp": "2026-02-05T10:10:00Z",
                    },
                ],
            },
            age_seconds=30,
        )

        _seed_queue(
            vault_path,
            [
                ("pending1.md", "# Pending 1\n**Priority**: High\n"),
                ("pending2.md", "# Pending 2\n"),
            ],
        )

        # All methods should work
        status = dashboard.get_status()
        assert status["state"] == "running"
        assert status["last_iteration"] == 10

        queue = dashboard.get_queue()
        assert len(queue) == 2

        active = dashboard.get_active_tasks()
        assert len(active) == 1
        assert active[0]["name"] == "executing.md"

        recent = dashboard.get_recent_completions()
        assert len(recent) == 2
        assert recent[0]["task"] == "done2.md"  # Most recent first

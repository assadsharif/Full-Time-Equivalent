"""Tests for QueueVisualizer (spec 006 US10)."""

import time
from pathlib import Path

import pytest

from orchestrator.queue_visualizer import QueueVisualizer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vault_path(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault


@pytest.fixture
def visualizer(vault_path):
    return QueueVisualizer(vault_path=vault_path)


def _seed_task(vault_path: Path, name: str, content: str, age_seconds: int = 0) -> None:
    """Create a task file in Needs_Action with specified age."""
    needs_action = vault_path / "Needs_Action"
    needs_action.mkdir(parents=True, exist_ok=True)
    task_path = needs_action / name
    task_path.write_text(content)
    if age_seconds > 0:
        import os

        mtime = time.time() - age_seconds
        os.utime(task_path, (mtime, mtime))


# ---------------------------------------------------------------------------
# Format task entry
# ---------------------------------------------------------------------------


class TestFormatTaskEntry:
    def test_formats_entry_with_priority_and_wait_time(self, vault_path, visualizer):
        _seed_task(
            vault_path, "task.md", "# Task\n**Priority**: High\n", age_seconds=120
        )
        task_path = vault_path / "Needs_Action" / "task.md"
        entry = visualizer.format_task_entry(task_path)
        assert entry["name"] == "task.md"
        assert entry["priority"] > 0
        assert entry["wait_time_seconds"] >= 120
        assert entry["wait_time_display"] == "2m"

    def test_wait_time_display_seconds(self, vault_path, visualizer):
        _seed_task(vault_path, "task.md", "# Task\n", age_seconds=30)
        task_path = vault_path / "Needs_Action" / "task.md"
        entry = visualizer.format_task_entry(task_path)
        assert entry["wait_time_display"] == "30s"

    def test_wait_time_display_minutes(self, vault_path, visualizer):
        _seed_task(vault_path, "task.md", "# Task\n", age_seconds=300)
        task_path = vault_path / "Needs_Action" / "task.md"
        entry = visualizer.format_task_entry(task_path)
        assert entry["wait_time_display"] == "5m"

    def test_wait_time_display_hours(self, vault_path, visualizer):
        _seed_task(vault_path, "task.md", "# Task\n", age_seconds=7200)
        task_path = vault_path / "Needs_Action" / "task.md"
        entry = visualizer.format_task_entry(task_path)
        assert entry["wait_time_display"] == "2h"

    def test_wait_time_display_days(self, vault_path, visualizer):
        _seed_task(vault_path, "task.md", "# Task\n", age_seconds=172800)
        task_path = vault_path / "Needs_Action" / "task.md"
        entry = visualizer.format_task_entry(task_path)
        assert entry["wait_time_display"] == "2d"

    def test_verbose_includes_path(self, vault_path, visualizer):
        _seed_task(vault_path, "task.md", "# Task\n")
        task_path = vault_path / "Needs_Action" / "task.md"
        entry = visualizer.format_task_entry(task_path, verbose=True)
        assert "path" in entry
        assert entry["path"] == str(task_path)

    def test_non_verbose_excludes_path(self, vault_path, visualizer):
        _seed_task(vault_path, "task.md", "# Task\n")
        task_path = vault_path / "Needs_Action" / "task.md"
        entry = visualizer.format_task_entry(task_path, verbose=False)
        assert "path" not in entry

    def test_handles_scoring_errors_gracefully(self, vault_path, visualizer):
        _seed_task(vault_path, "bad.md", "")  # Empty file
        task_path = vault_path / "Needs_Action" / "bad.md"
        entry = visualizer.format_task_entry(task_path)
        # Should still return an entry, even if scoring fails
        assert entry["name"] == "bad.md"
        assert "priority" in entry


# ---------------------------------------------------------------------------
# Render queue table
# ---------------------------------------------------------------------------


class TestRenderQueueTable:
    def test_no_needs_action_returns_empty(self, visualizer):
        queue = visualizer.render_queue_table()
        assert queue == []

    def test_empty_needs_action_returns_empty(self, vault_path, visualizer):
        (vault_path / "Needs_Action").mkdir()
        queue = visualizer.render_queue_table()
        assert queue == []

    def test_returns_sorted_queue(self, vault_path, visualizer):
        _seed_task(vault_path, "low.md", "# Low Task\n", age_seconds=60)
        _seed_task(
            vault_path,
            "high.md",
            "# High Task\n**Priority**: High\n**Urgency**: ASAP\n",
            age_seconds=120,
        )
        _seed_task(
            vault_path, "mid.md", "# Mid Task\n**Priority**: Medium\n", age_seconds=90
        )

        queue = visualizer.render_queue_table()
        assert len(queue) == 3
        # Should be sorted by priority (highest first)
        priorities = [t["priority"] for t in queue]
        assert priorities == sorted(priorities, reverse=True)
        assert queue[0]["name"] == "high.md"

    def test_verbose_includes_paths(self, vault_path, visualizer):
        _seed_task(vault_path, "task.md", "# Task\n")
        queue = visualizer.render_queue_table(verbose=True)
        assert len(queue) == 1
        assert "path" in queue[0]

    def test_non_verbose_excludes_paths(self, vault_path, visualizer):
        _seed_task(vault_path, "task.md", "# Task\n")
        queue = visualizer.render_queue_table(verbose=False)
        assert len(queue) == 1
        assert "path" not in queue[0]

    def test_skips_malformed_tasks(self, vault_path, visualizer):
        _seed_task(vault_path, "good.md", "# Good Task\n")
        # Create a file that might cause issues
        needs_action = vault_path / "Needs_Action"
        (needs_action / "not_md.txt").write_text("Not a markdown file")
        queue = visualizer.render_queue_table()
        # Should include at least the good task
        assert any(t["name"] == "good.md" for t in queue)

    def test_all_entries_have_required_fields(self, vault_path, visualizer):
        _seed_task(vault_path, "task1.md", "# Task 1\n")
        _seed_task(vault_path, "task2.md", "# Task 2\n**Priority**: High\n")
        queue = visualizer.render_queue_table()
        for entry in queue:
            assert "name" in entry
            assert "priority" in entry
            assert "wait_time_seconds" in entry
            assert "wait_time_display" in entry


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_realistic_queue_rendering(self, vault_path, visualizer):
        """Smoke test: create a realistic queue and verify rendering."""
        _seed_task(
            vault_path,
            "urgent.md",
            "# Urgent Task\n**Priority**: High\n**Urgency**: ASAP\n",
            age_seconds=3600,
        )
        _seed_task(vault_path, "normal.md", "# Normal Task\n", age_seconds=1800)
        _seed_task(
            vault_path, "old.md", "# Old Task\n**Priority**: Low\n", age_seconds=86400
        )

        queue = visualizer.render_queue_table(verbose=True)
        assert len(queue) == 3

        # Verify sorting (highest priority first)
        assert queue[0]["name"] == "urgent.md"

        # Verify wait times
        assert queue[0]["wait_time_display"] == "1h"
        assert queue[1]["wait_time_display"] == "30m"
        assert queue[2]["wait_time_display"] == "1d"

        # Verify verbose fields
        assert all("path" in t for t in queue)

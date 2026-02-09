"""
End-to-end orchestrator test (spec 006 Phase 7 T043).

Tests complete workflow: task discovery → prioritization → execution → completion
"""

import json
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vault_path(tmp_path):
    """Create a temporary vault structure."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Create required directories
    (vault / "Needs_Action").mkdir()
    (vault / "Planning").mkdir()
    (vault / "In_Progress").mkdir()
    (vault / "Done").mkdir()
    (vault / "Rejected").mkdir()
    (vault / "Approvals").mkdir()

    return vault


@pytest.fixture
def config_file(tmp_path, vault_path):
    """Create a test orchestrator config."""
    config_path = tmp_path / "orchestrator.yaml"
    config_content = f"""
orchestrator:
  vault_path: {vault_path}
  poll_interval: 1
  max_concurrent_tasks: 1
  claude_timeout: 10
  stop_hook_file: .claude_stop
  max_iterations: 5

priority_weights:
  urgency: 0.4
  deadline: 0.3
  sender: 0.3

vip_senders: []

approval_keywords:
  - deploy
  - production

retry:
  max_attempts: 2
  base_delay: 0.5
  max_delay: 2.0
  jitter: 0.2

metrics:
  enabled: true
  retention_days: 30
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def orchestrator(config_file, vault_path):
    """Create an Orchestrator instance for testing."""
    from src.orchestrator.models import OrchestratorConfig
    from src.orchestrator.scheduler import Orchestrator

    config = OrchestratorConfig.from_yaml(config_file, vault_path_override=vault_path)
    orch = Orchestrator(config=config, dry_run=True)  # Dry-run for E2E test
    return orch


def _create_task(
    vault_path: Path, name: str, content: str, age_seconds: int = 0
) -> Path:
    """Helper to create a task file in Needs_Action."""
    task_path = vault_path / "Needs_Action" / name
    task_path.write_text(content)
    if age_seconds > 0:
        import os

        mtime = time.time() - age_seconds
        os.utime(task_path, (mtime, mtime))
    return task_path


# ---------------------------------------------------------------------------
# E2E Workflow Tests
# ---------------------------------------------------------------------------


class TestTaskDiscovery:
    """Test task discovery phase."""

    def test_discovers_tasks_in_needs_action(self, orchestrator, vault_path):
        """Orchestrator discovers all tasks in Needs_Action."""
        _create_task(vault_path, "task1.md", "# Task 1\n")
        _create_task(vault_path, "task2.md", "# Task 2\n")
        _create_task(vault_path, "task3.md", "# Task 3\n")

        # Run discovery (via run_once which calls _discover_and_score)
        exits = orchestrator.run_once()

        # Should process all 3 tasks (dry-run mode, so they complete immediately)
        assert len(exits) >= 3

    def test_ignores_non_markdown_files(self, orchestrator, vault_path):
        """Orchestrator ignores non-.md files."""
        _create_task(vault_path, "task.md", "# Valid Task\n")
        (vault_path / "Needs_Action" / "README.txt").write_text("Not a task")
        (vault_path / "Needs_Action" / ".hidden").write_text("Hidden file")

        exits = orchestrator.run_once()

        # Should only process the .md file
        assert len(exits) == 1
        assert exits[0].task_name == "task.md"


class TestPriorityScoring:
    """Test priority scoring and ordering."""

    def test_scores_tasks_by_urgency(self, orchestrator, vault_path):
        """High urgency tasks get higher scores."""
        _create_task(vault_path, "urgent.md", "# URGENT Task\n**Priority**: High\n")
        _create_task(vault_path, "normal.md", "# Normal Task\n")
        _create_task(vault_path, "low.md", "# Low Priority Task\n**Priority**: Low\n")

        # Check that tasks are scored
        from src.orchestrator.priority_scorer import PriorityScorer

        scorer = PriorityScorer(orchestrator.config)

        urgent_score = scorer.score(vault_path / "Needs_Action" / "urgent.md")
        normal_score = scorer.score(vault_path / "Needs_Action" / "normal.md")
        low_score = scorer.score(vault_path / "Needs_Action" / "low.md")

        assert urgent_score > normal_score > low_score

    def test_age_based_priority_boost(self, orchestrator, vault_path):
        """Old tasks get priority boost."""
        _create_task(
            vault_path, "fresh.md", "# Fresh\n**Priority**: Low\n", age_seconds=60
        )
        _create_task(
            vault_path,
            "old.md",
            "# Old\n**Priority**: Low\n",
            age_seconds=7 * 86400 + 3600,
        )

        from src.orchestrator.priority_scorer import PriorityScorer

        scorer = PriorityScorer(orchestrator.config)

        fresh_score = scorer.score(vault_path / "Needs_Action" / "fresh.md")
        old_score = scorer.score(vault_path / "Needs_Action" / "old.md")

        # Old task should have +1.0 boost (>7 days)
        assert old_score > fresh_score


class TestApprovalGate:
    """Test HITL approval enforcement."""

    def test_approval_required_for_dangerous_keywords(self, orchestrator, vault_path):
        """Tasks with approval keywords require HITL approval."""
        task_path = _create_task(
            vault_path, "deploy.md", "# Deploy to production\nPlease deploy the app.\n"
        )

        from src.orchestrator.approval_checker import ApprovalChecker

        checker = ApprovalChecker(orchestrator.config)

        assert checker.requires_approval(task_path) is True

    def test_no_approval_for_safe_tasks(self, orchestrator, vault_path):
        """Normal tasks don't require approval."""
        task_path = _create_task(
            vault_path, "safe.md", "# Update documentation\nFix the README typo.\n"
        )

        from src.orchestrator.approval_checker import ApprovalChecker

        checker = ApprovalChecker(orchestrator.config)

        assert checker.requires_approval(task_path) is False


class TestExecution:
    """Test task execution phase."""

    def test_dry_run_mode_skips_execution(self, orchestrator, vault_path):
        """Dry-run mode doesn't actually invoke Claude."""
        _create_task(vault_path, "task.md", "# Task\n")

        # Run in dry-run mode (fixture default)
        exits = orchestrator.run_once()

        # Task completes immediately in dry-run
        assert len(exits) == 1
        assert exits[0].success is True
        assert "dry-run" in exits[0].reason.lower()

    def test_stop_hook_interrupts_execution(self, orchestrator, vault_path):
        """Stop hook halts the orchestrator."""
        _create_task(vault_path, "task.md", "# Task\n")

        # Create stop hook
        (vault_path / ".claude_stop").touch()

        # Should not process any tasks
        exits = orchestrator.run_once()

        # Stop hook detected before processing
        assert len(exits) == 0 or (exits and not exits[0].success)


class TestStateTransitions:
    """Test task state transitions."""

    def test_task_moves_through_states(self, orchestrator, vault_path):
        """Task transitions from Needs_Action → Done in dry-run."""
        task_path = _create_task(vault_path, "task.md", "# Task\n")

        # Initially in Needs_Action
        assert task_path.exists()
        assert task_path.parent.name == "Needs_Action"

        # Process task
        exits = orchestrator.run_once()

        # Task should move (in dry-run, moves to Done)
        assert len(exits) == 1
        # Check that task no longer in Needs_Action
        assert not (vault_path / "Needs_Action" / "task.md").exists()


class TestCheckpointing:
    """Test orchestrator state persistence."""

    def test_checkpoint_created_after_run(self, orchestrator, vault_path):
        """Checkpoint file created after orchestrator run."""
        _create_task(vault_path, "task.md", "# Task\n")

        checkpoint_path = vault_path.parent / ".fte" / "orchestrator.checkpoint.json"

        # Checkpoint shouldn't exist yet
        # (might exist from fixture initialization)

        # Run orchestrator
        orchestrator.run_once()

        # Checkpoint should exist now
        assert checkpoint_path.exists()

        # Checkpoint should have valid JSON
        data = json.loads(checkpoint_path.read_text())
        assert "last_iteration" in data
        assert "exit_log" in data


class TestMetricsCollection:
    """Test metrics logging during E2E workflow."""

    def test_metrics_logged_for_task_execution(self, orchestrator, vault_path):
        """Metrics collector logs events during task execution."""
        _create_task(vault_path, "task.md", "# Task\n")

        metrics_path = vault_path.parent / ".fte" / "orchestrator_metrics.log"

        # Clear any existing metrics
        if metrics_path.exists():
            metrics_path.unlink()

        # Process task
        orchestrator.run_once()

        # Metrics should be logged
        assert metrics_path.exists()

        # Read metrics
        lines = metrics_path.read_text().strip().split("\n")
        events = [json.loads(line) for line in lines if line]

        # Should have at least task_started and task_completed events
        event_types = [e["event"] for e in events]
        assert "task_started" in event_types
        assert "task_completed" in event_types or "task_failed" in event_types


# ---------------------------------------------------------------------------
# Complete E2E Scenario
# ---------------------------------------------------------------------------


class TestCompleteE2E:
    """Complete end-to-end workflow test."""

    def test_full_orchestrator_workflow(self, orchestrator, vault_path):
        """
        Full E2E test: create multiple tasks with different priorities,
        run orchestrator, verify execution order and completion.
        """
        # Create tasks with different priorities and ages
        _create_task(
            vault_path,
            "urgent.md",
            "# URGENT Task\n**Priority**: High\n**Urgency**: ASAP\n",
            age_seconds=3600,
        )
        _create_task(
            vault_path,
            "normal.md",
            "# Normal Task\n**Priority**: Medium\n",
            age_seconds=1800,
        )
        _create_task(
            vault_path,
            "old_low.md",
            "# Old Low Priority\n**Priority**: Low\n",
            age_seconds=10 * 86400,  # 10 days old
        )

        # Run orchestrator
        exits = orchestrator.run_once()

        # All tasks should be processed
        assert len(exits) == 3

        # Urgent task should be processed first (highest score)
        assert exits[0].task_name == "urgent.md"

        # Old low-priority task should get age boost and be processed
        task_names = [e.task_name for e in exits]
        assert "old_low.md" in task_names

        # All should succeed in dry-run
        assert all(e.success for e in exits)

        # Metrics should be collected
        metrics_path = vault_path.parent / ".fte" / "orchestrator_metrics.log"
        assert metrics_path.exists()

        # Checkpoint should be updated
        checkpoint_path = vault_path.parent / ".fte" / "orchestrator.checkpoint.json"
        assert checkpoint_path.exists()

        data = json.loads(checkpoint_path.read_text())
        assert data["last_iteration"] >= 1
        assert len(data["exit_log"]) == 3

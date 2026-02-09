"""
Orchestrator unit tests — models, priority scorer, stop hook,
approval checker, state machine, claude invoker, and full-loop smoke.
"""

import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _vault(tmp: Path) -> Path:
    """Create a minimal vault structure under tmp and return vault root."""
    for folder in (
        "Inbox",
        "Needs_Action",
        "In_Progress",
        "Done",
        "Approvals",
        "Briefings",
    ):
        (tmp / folder).mkdir(exist_ok=True)
    return tmp


def _task_md(
    tmp: Path,
    name: str = "test-task.md",
    folder: str = "Needs_Action",
    body: str = "Some task body\n",
    priority: str = "high",
    sender: str = "dev@company.com",
) -> Path:
    """Write a synthetic task .md and return its path."""
    badges = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
    content = (
        f"# {name}\n\n"
        f"**Priority**: {badges.get(priority, '⚪')} {priority.capitalize()}\n"
        f"**Status**: New\n"
        f"**From**: {sender}\n\n"
        f"---\n\n{body}\n"
    )
    path = tmp / folder / name
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vault_dir():
    d = Path(tempfile.mkdtemp())
    _vault(d)
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ===========================================================================
# TaskState / OrchestratorConfig (models)
# ===========================================================================


class TestModels:
    def test_task_state_values(self):
        from src.orchestrator.models import TaskState

        assert TaskState.NEEDS_ACTION.value == "needs_action"
        assert TaskState.DONE.value == "done"
        assert TaskState.REJECTED.value == "rejected"

    def test_config_defaults(self):
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig()
        assert cfg.poll_interval == 30
        assert cfg.urgency_weight == 0.4
        assert cfg.max_iterations == 100
        assert "ceo@company.com" in cfg.vip_senders

    def test_config_from_yaml_missing_file(self, vault_dir):
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig.from_yaml(vault_dir / "nonexistent.yaml")
        # Should return defaults
        assert cfg.poll_interval == 30

    def test_task_record_name(self, vault_dir):
        from src.orchestrator.models import TaskRecord

        p = vault_dir / "Needs_Action" / "my-task.md"
        p.touch()
        rec = TaskRecord(file_path=p)
        assert rec.name == "my-task.md"


# ===========================================================================
# PriorityScorer
# ===========================================================================


class TestPriorityScorer:
    def test_urgent_ceo_scores_high(self, vault_dir):
        from src.orchestrator.priority_scorer import PriorityScorer
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)
        scorer = PriorityScorer(cfg)

        path = _task_md(
            vault_dir,
            name="ceo-urgent.md",
            priority="urgent",
            sender="ceo@company.com",
            body="[URGENT] Please handle this by end of day",
        )
        score = scorer.score(path)
        assert score >= 4.0, f"Expected >=4.0 for urgent CEO task, got {score}"

    def test_low_newsletter_scores_low(self, vault_dir):
        from src.orchestrator.priority_scorer import PriorityScorer
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)
        scorer = PriorityScorer(cfg)

        path = _task_md(
            vault_dir,
            name="newsletter.md",
            priority="low",
            sender="newsletter@spam.com",
            body="Weekly digest. Read whenever you have time.",
        )
        score = scorer.score(path)
        assert score <= 3.0, f"Expected <=3.0 for low-priority newsletter, got {score}"

    def test_client_medium_scores_middle(self, vault_dir):
        from src.orchestrator.priority_scorer import PriorityScorer
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)
        scorer = PriorityScorer(cfg)

        path = _task_md(
            vault_dir,
            name="client-task.md",
            priority="medium",
            sender="sarah@client-corp.com",
            body="Client kickoff meeting request",
        )
        score = scorer.score(path)
        assert 2.0 <= score <= 4.5

    def test_deadline_today_boosts_score(self, vault_dir):
        from src.orchestrator.priority_scorer import PriorityScorer
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)
        scorer = PriorityScorer(cfg)

        path = _task_md(
            vault_dir,
            name="deadline-today.md",
            priority="high",
            sender="dev@company.com",
            body="Finish this by end of day today",
        )
        score = scorer.score(path)
        assert score >= 3.5


# ===========================================================================
# StopHook
# ===========================================================================


class TestStopHook:
    def test_not_set_initially(self, vault_dir):
        from src.orchestrator.stop_hook import StopHook

        hook = StopHook(vault_dir)
        assert hook.is_set is False

    def test_set_and_clear(self, vault_dir):
        from src.orchestrator.stop_hook import StopHook

        hook = StopHook(vault_dir)
        hook.set()
        assert hook.is_set is True
        hook.clear()
        assert hook.is_set is False

    def test_custom_filename(self, vault_dir):
        from src.orchestrator.stop_hook import StopHook

        hook = StopHook(vault_dir, hook_filename=".my_stop")
        hook.set()
        assert (vault_dir / ".my_stop").exists()
        hook.clear()
        assert not (vault_dir / ".my_stop").exists()


# ===========================================================================
# ApprovalChecker
# ===========================================================================


class TestApprovalChecker:
    def test_detects_deploy_keyword(self, vault_dir):
        from src.orchestrator.approval_checker import ApprovalChecker
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)
        checker = ApprovalChecker(cfg)

        path = _task_md(vault_dir, body="Please deploy this to production")
        assert checker.requires_approval(path) is True
        assert "deploy" in checker.matched_keywords(path)
        assert "production" in checker.matched_keywords(path)

    def test_safe_task_no_approval(self, vault_dir):
        from src.orchestrator.approval_checker import ApprovalChecker
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)
        checker = ApprovalChecker(cfg)

        path = _task_md(
            vault_dir, body="Review the dashboard mockups and leave comments"
        )
        assert checker.requires_approval(path) is False

    def test_create_approval_request(self, vault_dir):
        from src.orchestrator.approval_checker import ApprovalChecker
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)
        checker = ApprovalChecker(cfg)

        path = _task_md(vault_dir, name="risky.md", body="deploy to production")
        approval_path = checker.create_approval_request(path, ["deploy", "production"])

        assert approval_path.exists()
        content = approval_path.read_text()
        assert "pending" in content  # approval_status: pending (YAML frontmatter)
        assert "deploy" in content
        assert "production" in content

    def test_is_approved_false_when_pending(self, vault_dir):
        from src.orchestrator.approval_checker import ApprovalChecker
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)
        checker = ApprovalChecker(cfg)

        path = _task_md(vault_dir, name="pending.md", body="deploy")
        checker.create_approval_request(path, ["deploy"])
        assert checker.is_approved(path) is False

    def test_is_approved_true_when_approved(self, vault_dir):
        from src.orchestrator.approval_checker import ApprovalChecker
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)
        checker = ApprovalChecker(cfg)

        path = _task_md(vault_dir, name="approved-task.md", body="deploy")
        # Write a manually-approved file
        approval = vault_dir / "Approvals" / "approval-approved-task.md"
        approval.write_text("# Approved\n**Status**: ✅ Approved\n")
        assert checker.is_approved(path) is True


# ===========================================================================
# StateMachine
# ===========================================================================


class TestStateMachine:
    def test_valid_transitions(self):
        from src.orchestrator.state_machine import StateMachine
        from src.orchestrator.models import TaskState

        assert StateMachine.is_valid_transition(
            TaskState.NEEDS_ACTION, TaskState.PLANNING
        )
        assert StateMachine.is_valid_transition(TaskState.PLANNING, TaskState.EXECUTING)
        assert StateMachine.is_valid_transition(TaskState.EXECUTING, TaskState.DONE)

    def test_invalid_transition_raises(self):
        from src.orchestrator.state_machine import StateMachine, TransitionError
        from src.orchestrator.models import TaskState

        assert (
            StateMachine.is_valid_transition(TaskState.DONE, TaskState.PLANNING)
            is False
        )

    def test_transition_moves_file(self, vault_dir):
        from src.orchestrator.state_machine import StateMachine
        from src.orchestrator.models import TaskState

        sm = StateMachine(vault_dir)
        task = _task_md(vault_dir, name="move-me.md")

        new_path = sm.transition(task, TaskState.NEEDS_ACTION, TaskState.PLANNING)
        assert new_path.parent.name == "In_Progress"
        assert new_path.exists()
        assert not task.exists()  # original moved

    def test_full_happy_path(self, vault_dir):
        from src.orchestrator.state_machine import StateMachine
        from src.orchestrator.models import TaskState

        sm = StateMachine(vault_dir)
        path = _task_md(vault_dir, name="happy.md")

        path = sm.transition(path, TaskState.NEEDS_ACTION, TaskState.PLANNING)
        path = sm.transition(path, TaskState.PLANNING, TaskState.EXECUTING)
        path = sm.transition(path, TaskState.EXECUTING, TaskState.DONE)

        assert path.parent.name == "Done"
        assert path.exists()

    def test_transition_error_on_bad_edge(self, vault_dir):
        from src.orchestrator.state_machine import StateMachine, TransitionError
        from src.orchestrator.models import TaskState

        sm = StateMachine(vault_dir)
        path = _task_md(vault_dir, name="bad.md")

        with pytest.raises(TransitionError):
            sm.transition(path, TaskState.NEEDS_ACTION, TaskState.DONE)

    def test_transition_error_on_missing_file(self, vault_dir):
        from src.orchestrator.state_machine import StateMachine
        from src.orchestrator.models import TaskState

        sm = StateMachine(vault_dir)
        with pytest.raises(FileNotFoundError):
            sm.transition(
                vault_dir / "ghost.md", TaskState.NEEDS_ACTION, TaskState.PLANNING
            )

    def test_terminal_states_have_no_successors(self):
        from src.orchestrator.state_machine import StateMachine
        from src.orchestrator.models import TaskState

        assert StateMachine.valid_next_states(TaskState.DONE) == set()
        assert StateMachine.valid_next_states(TaskState.REJECTED) == set()


# ===========================================================================
# ClaudeInvoker
# ===========================================================================


class TestClaudeInvoker:
    def test_dry_run_returns_success(self, vault_dir):
        from src.orchestrator.claude_invoker import ClaudeInvoker

        invoker = ClaudeInvoker()
        path = _task_md(vault_dir, name="dry.md")
        result = invoker.dry_run(path)

        assert result.success is True
        assert "DRY-RUN" in result.stdout
        assert result.returncode == 0

    def test_missing_binary_returns_failure(self, vault_dir):
        from src.orchestrator.claude_invoker import ClaudeInvoker

        invoker = ClaudeInvoker(claude_binary="/nonexistent/binary")
        path = _task_md(vault_dir, name="fail.md")
        result = invoker.invoke(path)

        assert result.success is False
        assert "not found" in result.stderr


# ===========================================================================
# Full Orchestrator loop (dry-run, single sweep)
# ===========================================================================


class TestOrchestratorLoop:
    def test_single_sweep_processes_safe_task(self, vault_dir):
        from src.orchestrator.scheduler import Orchestrator
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)
        _task_md(vault_dir, name="safe-task.md", body="Review dashboard mockups")

        orch = Orchestrator(config=cfg, dry_run=True)
        exits = orch.run_once()

        assert len(exits) == 1
        assert exits[0].success is True
        assert exits[0].reason == "done"
        # File should be in Done
        assert (vault_dir / "Done" / "safe-task.md").exists()

    def test_single_sweep_parks_approval_task(self, vault_dir):
        from src.orchestrator.scheduler import Orchestrator
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)
        _task_md(vault_dir, name="deploy-task.md", body="deploy to production now")

        orch = Orchestrator(config=cfg, dry_run=True)
        exits = orch.run_once()

        assert len(exits) == 1
        assert exits[0].reason == "pending_approval"
        assert exits[0].success is False
        # Approval request should exist
        approvals = list((vault_dir / "Approvals").glob("*.md"))
        assert len(approvals) >= 1

    def test_single_sweep_empty_inbox(self, vault_dir):
        from src.orchestrator.scheduler import Orchestrator
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)
        # No tasks in Needs_Action
        orch = Orchestrator(config=cfg, dry_run=True)
        exits = orch.run_once()

        assert exits == []

    def test_single_sweep_multiple_tasks_priority_order(self, vault_dir):
        from src.orchestrator.scheduler import Orchestrator
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)

        # Low priority first (alphabetically) — should be processed second
        _task_md(
            vault_dir,
            name="aaa-low.md",
            priority="low",
            sender="newsletter@spam.com",
            body="No rush on this one",
        )
        # High priority — should be processed first
        _task_md(
            vault_dir,
            name="zzz-urgent.md",
            priority="urgent",
            sender="ceo@company.com",
            body="[URGENT] Handle this ASAP",
        )

        orch = Orchestrator(config=cfg, dry_run=True)
        exits = orch.run_once()

        # Both processed; urgent one first in exit log
        assert len(exits) == 2
        # The urgent/ceo task should have exited first
        assert "zzz-urgent" in exits[0].task_path.name

    def test_stop_hook_prevents_loop(self, vault_dir):
        from src.orchestrator.stop_hook import StopHook
        from src.orchestrator.scheduler import Orchestrator
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir, poll_interval=0)
        _task_md(vault_dir, name="blocked.md", body="Review something")

        # Set stop hook before starting
        StopHook(vault_dir).set()

        orch = Orchestrator(config=cfg, dry_run=True)
        # run() should exit immediately due to stop hook
        orch.run()

        # Task should NOT have been processed (still in Needs_Action)
        assert (vault_dir / "Needs_Action" / "blocked.md").exists()

    def test_checkpoint_written(self, vault_dir):
        from src.orchestrator.scheduler import Orchestrator
        from src.orchestrator.models import OrchestratorConfig
        import json

        cfg = OrchestratorConfig(vault_path=vault_dir)
        _task_md(vault_dir, name="checkpoint-task.md", body="Simple task")

        orch = Orchestrator(config=cfg, dry_run=True)
        orch.run_once()

        # Checkpoint should exist
        fte_dir = vault_dir.parent / ".fte"
        cp = fte_dir / "orchestrator.checkpoint.json"
        assert cp.exists()
        data = json.loads(cp.read_text())
        assert "exit_log" in data
        assert len(data["exit_log"]) == 1


# ===========================================================================
# HITL Resume Flow — park → approve → resume → done
# ===========================================================================


class TestHITLResumeFlow:
    """Integration tests for the full approve-then-resume cycle."""

    def test_approve_and_resume_completes_task(self, vault_dir):
        """Full cycle: deploy task parked → approved → resumed → done."""
        from src.orchestrator.scheduler import Orchestrator
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)

        # Sweep 1: task with approval keyword gets parked
        _task_md(vault_dir, name="deploy-svc.md", body="deploy to production")
        orch = Orchestrator(config=cfg, dry_run=True)
        exits1 = orch.run_once()

        assert len(exits1) == 1
        assert exits1[0].reason == "pending_approval"
        assert (vault_dir / "Approvals" / "deploy-svc.md").exists()

        # Simulate human approval via legacy approval file
        (vault_dir / "Approvals" / "approval-deploy-svc.md").write_text(
            "# Approved\n**Status**: ✅ Approved\n"
        )

        # Sweep 2: fresh orchestrator discovers and resumes the approved task
        orch2 = Orchestrator(config=cfg, dry_run=True)
        exits2 = orch2.run_once()

        assert len(exits2) == 1
        assert exits2[0].success is True
        assert exits2[0].reason == "done"
        assert (vault_dir / "Done" / "deploy-svc.md").exists()

    def test_unapproved_task_not_resumed(self, vault_dir):
        """A parked task that hasn't been approved stays in Approvals."""
        from src.orchestrator.scheduler import Orchestrator
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)

        # Sweep 1: park the task
        _task_md(vault_dir, name="risky-deploy.md", body="deploy to production")
        orch = Orchestrator(config=cfg, dry_run=True)
        exits1 = orch.run_once()
        assert exits1[0].reason == "pending_approval"

        # Sweep 2: no approval written — nothing should resume
        orch2 = Orchestrator(config=cfg, dry_run=True)
        exits2 = orch2.run_once()

        assert exits2 == []
        assert (vault_dir / "Approvals" / "risky-deploy.md").exists()

    def test_apr_request_files_not_resumed(self, vault_dir):
        """APR-* files in Approvals are approval requests, not resumable tasks."""
        from src.orchestrator.scheduler import Orchestrator
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)

        # Write a fake APR-* file directly (simulates a created approval request)
        (vault_dir / "Approvals" / "APR-deploy-svc-20260204.md").write_text(
            "---\n"
            "approval_id: APR-deploy-svc-20260204\n"
            "nonce: abc\n"
            "approval_status: approved\n"
            "created_at: '2026-02-04T10:00:00+00:00'\n"
            "expires_at: '2026-02-04T22:00:00+00:00'\n"
            "---\n\n# Approval Request\n"
        )

        orch = Orchestrator(config=cfg, dry_run=True)
        exits = orch.run_once()

        # APR-* file should not be picked up as a resumable task
        assert exits == []

    def test_resume_exit_log_has_correct_final_state(self, vault_dir):
        """Resumed task exit log records final_state as 'done'."""
        from src.orchestrator.scheduler import Orchestrator
        from src.orchestrator.models import OrchestratorConfig, TaskState

        cfg = OrchestratorConfig(vault_path=vault_dir)

        # Park a deploy task
        _task_md(vault_dir, name="deploy-check.md", body="deploy to production")
        Orchestrator(config=cfg, dry_run=True).run_once()

        # Approve it
        (vault_dir / "Approvals" / "approval-deploy-check.md").write_text(
            "# Approved\n**Status**: ✅ Approved\n"
        )

        # Resume
        exits = Orchestrator(config=cfg, dry_run=True).run_once()
        assert len(exits) == 1
        assert exits[0].final_state == TaskState.DONE

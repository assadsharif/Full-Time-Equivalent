"""
Persistence Loop unit + integration tests.

Coverage map:
  TestRetryPolicy          — backoff math, jitter bounds, clamping
  TestTransientClassify    — transient vs hard error classification
  TestCheckpointIO         — YAML frontmatter read / write / roundtrip
  TestPersistenceLoopRun   — success, hard fail, transient retry, budget
                             exhaustion, max-iterations, resume, invoke mode
  TestPersistenceLoopStop  — stop-hook interruption mid-retry
  TestPersistenceWarning   — 80 % threshold warning
  TestOrchestratorPersist  — full-loop integration (safe task, transient
                             recovery via patched invoker)
"""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.orchestrator.persistence_loop import PersistenceLoop, RetryPolicy, Checkpoint
from src.orchestrator.claude_invoker import ClaudeInvoker, InvocationResult
from src.orchestrator.stop_hook import StopHook


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _vault(tmp: Path) -> Path:
    for folder in ("Inbox", "Needs_Action", "In_Progress", "Done", "Approvals", "Briefings"):
        (tmp / folder).mkdir(exist_ok=True)
    return tmp


def _task_md(tmp: Path, name: str = "task.md", body: str = "Do something\n") -> Path:
    path = tmp / "In_Progress" / name
    path.write_text(f"# {name}\n\n{body}\n")
    return path


def _make_loop(
    tmp: Path,
    max_iterations: int = 5,
    max_attempts: int = 3,
    base_delay: float = 0.0,
    max_delay: float = 0.0,
    jitter: float = 0.0,
) -> tuple[PersistenceLoop, MagicMock, StopHook]:
    """PersistenceLoop with a mock invoker, zero-delay policy, real stop hook."""
    invoker = MagicMock(spec=ClaudeInvoker)
    stop_hook = StopHook(tmp)
    policy = RetryPolicy(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        jitter=jitter,
    )
    loop = PersistenceLoop(
        max_iterations=max_iterations,
        retry_policy=policy,
        invoker=invoker,
        stop_hook=stop_hook,
    )
    return loop, invoker, stop_hook


@pytest.fixture
def vault_dir():
    d = Path(tempfile.mkdtemp())
    _vault(d)
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ===========================================================================
# RetryPolicy / backoff math
# ===========================================================================


class TestRetryPolicy:
    def test_default_values(self):
        p = RetryPolicy()
        assert p.max_attempts == 3
        assert p.base_delay == 1.0
        assert p.max_delay == 16.0
        assert p.jitter == 0.2

    def test_backoff_sequence_no_jitter(self, vault_dir):
        """With jitter=0 and high max_delay the sequence is 1, 2, 4, 8, 16."""
        loop, _, _ = _make_loop(vault_dir, base_delay=1.0, max_delay=16.0, jitter=0.0)
        assert loop._backoff_delay(1) == 1.0
        assert loop._backoff_delay(2) == 2.0
        assert loop._backoff_delay(3) == 4.0
        assert loop._backoff_delay(4) == 8.0
        assert loop._backoff_delay(5) == 16.0

    def test_backoff_clamped_at_max_delay(self, vault_dir):
        loop, _, _ = _make_loop(vault_dir, base_delay=1.0, max_delay=4.0, jitter=0.0)
        # attempt 4 → raw 8.0, clamped to 4.0
        assert loop._backoff_delay(4) == 4.0
        # attempt 5 → raw 16.0, clamped to 4.0
        assert loop._backoff_delay(5) == 4.0

    def test_backoff_jitter_stays_in_bounds(self, vault_dir):
        """±20 % jitter on base=1 attempt=1 → delay in [0.8, 1.2]."""
        loop, _, _ = _make_loop(vault_dir, base_delay=1.0, max_delay=16.0, jitter=0.2)
        for _ in range(200):
            d = loop._backoff_delay(1)
            assert 0.8 <= d <= 1.2, f"delay {d} out of [0.8, 1.2]"


# ===========================================================================
# Transient vs Hard error classification
# ===========================================================================


class TestTransientClassify:
    def test_timed_out_flag_is_transient(self):
        assert PersistenceLoop.is_transient(
            InvocationResult(success=False, timed_out=True, stderr="")
        )

    def test_timeout_in_stderr_is_transient(self):
        assert PersistenceLoop.is_transient(
            InvocationResult(success=False, stderr="Claude invocation timed out after 3600s")
        )

    def test_rate_limit_is_transient(self):
        assert PersistenceLoop.is_transient(
            InvocationResult(success=False, stderr="429 rate limit exceeded")
        )

    def test_503_is_transient(self):
        assert PersistenceLoop.is_transient(
            InvocationResult(success=False, stderr="503 Service Unavailable")
        )

    def test_connection_refused_is_transient(self):
        assert PersistenceLoop.is_transient(
            InvocationResult(success=False, stderr="connection refused")
        )

    def test_connection_reset_is_transient(self):
        assert PersistenceLoop.is_transient(
            InvocationResult(success=False, stderr="connection reset by peer")
        )

    def test_try_again_later_is_transient(self):
        assert PersistenceLoop.is_transient(
            InvocationResult(success=False, stderr="Please try again later")
        )

    def test_lock_timeout_is_transient(self):
        assert PersistenceLoop.is_transient(
            InvocationResult(success=False, stderr="lock timeout waiting for resource")
        )

    def test_permission_denied_is_hard(self):
        assert not PersistenceLoop.is_transient(
            InvocationResult(success=False, stderr="Permission denied")
        )

    def test_not_found_is_hard(self):
        assert not PersistenceLoop.is_transient(
            InvocationResult(success=False, stderr="Resource not found")
        )

    def test_syntax_error_is_hard(self):
        assert not PersistenceLoop.is_transient(
            InvocationResult(success=False, stderr="SyntaxError: invalid syntax at line 5")
        )

    def test_empty_stderr_is_hard(self):
        assert not PersistenceLoop.is_transient(
            InvocationResult(success=False, stderr="")
        )


# ===========================================================================
# Checkpoint I/O (YAML frontmatter)
# ===========================================================================


class TestCheckpointIO:
    def test_read_none_when_no_frontmatter(self, vault_dir):
        path = _task_md(vault_dir, body="No frontmatter")
        assert PersistenceLoop._read_checkpoint(path) is None

    def test_read_none_when_frontmatter_lacks_persistence_loop(self, vault_dir):
        path = vault_dir / "In_Progress" / "bare-fm.md"
        path.write_text("---\ntitle: hello\n---\n# Body\n")
        assert PersistenceLoop._read_checkpoint(path) is None

    def test_write_read_roundtrip(self, vault_dir):
        path = _task_md(vault_dir)
        cp = Checkpoint(iteration=7, consecutive_retries=2, last_error="timeout")
        PersistenceLoop._write_checkpoint(path, cp)

        loaded = PersistenceLoop._read_checkpoint(path)
        assert loaded is not None
        assert loaded.iteration == 7
        assert loaded.consecutive_retries == 2
        assert loaded.last_error == "timeout"

    def test_write_preserves_original_body(self, vault_dir):
        path = _task_md(vault_dir, body="Review the docs carefully.")
        PersistenceLoop._write_checkpoint(path, Checkpoint(iteration=1))

        text = path.read_text()
        assert "Review the docs carefully." in text
        assert "persistence_loop:" in text

    def test_write_merges_into_existing_frontmatter(self, vault_dir):
        path = vault_dir / "In_Progress" / "has-fm.md"
        path.write_text("---\ntitle: my-task\n---\n# Body\n")

        PersistenceLoop._write_checkpoint(path, Checkpoint(iteration=3))

        text = path.read_text()
        assert "title: my-task" in text
        assert "persistence_loop:" in text

        loaded = PersistenceLoop._read_checkpoint(path)
        assert loaded.iteration == 3

    def test_repeated_writes_stay_consistent(self, vault_dir):
        path = _task_md(vault_dir)
        for i in range(5):
            PersistenceLoop._write_checkpoint(path, Checkpoint(iteration=i))

        loaded = PersistenceLoop._read_checkpoint(path)
        assert loaded.iteration == 4  # last written value

    def test_state_data_roundtrips(self, vault_dir):
        path = _task_md(vault_dir)
        cp = Checkpoint(iteration=1, state_data={"api_attempt": 2, "last_error": "x"})
        PersistenceLoop._write_checkpoint(path, cp)

        loaded = PersistenceLoop._read_checkpoint(path)
        assert loaded.state_data == {"api_attempt": 2, "last_error": "x"}


# ===========================================================================
# PersistenceLoop.run() — core paths
# ===========================================================================


class TestPersistenceLoopRun:
    def test_immediate_success(self, vault_dir):
        loop, invoker, _ = _make_loop(vault_dir)
        path = _task_md(vault_dir)
        invoker.dry_run.return_value = InvocationResult(success=True, stdout="ok", returncode=0)

        result = loop.run(path, dry_run=True)

        assert result.success is True
        invoker.dry_run.assert_called_once_with(path)
        cp = PersistenceLoop._read_checkpoint(path)
        assert cp.iteration == 1
        assert cp.consecutive_retries == 0

    def test_immediate_hard_failure(self, vault_dir):
        loop, invoker, _ = _make_loop(vault_dir)
        path = _task_md(vault_dir)
        invoker.dry_run.return_value = InvocationResult(
            success=False, stderr="Permission denied", returncode=1
        )

        result = loop.run(path, dry_run=True)

        assert result.success is False
        assert "Permission denied" in result.stderr
        invoker.dry_run.assert_called_once()
        # Checkpoint records the error
        cp = PersistenceLoop._read_checkpoint(path)
        assert cp.last_error == "Permission denied"

    def test_transient_then_success(self, vault_dir):
        """First call transient, second succeeds — task recovers."""
        loop, invoker, _ = _make_loop(vault_dir)
        path = _task_md(vault_dir)
        invoker.dry_run.side_effect = [
            InvocationResult(success=False, stderr="connection refused", returncode=1),
            InvocationResult(success=True, stdout="recovered", returncode=0),
        ]

        result = loop.run(path, dry_run=True)

        assert result.success is True
        assert result.stdout == "recovered"
        assert invoker.dry_run.call_count == 2
        cp = PersistenceLoop._read_checkpoint(path)
        assert cp.consecutive_retries == 0  # reset on success

    def test_transient_exhausts_retry_budget(self, vault_dir):
        """3 consecutive transient errors → reported as hard failure."""
        loop, invoker, _ = _make_loop(vault_dir, max_attempts=3)
        path = _task_md(vault_dir)
        invoker.dry_run.return_value = InvocationResult(
            success=False, stderr="connection refused", returncode=1
        )

        result = loop.run(path, dry_run=True)

        assert result.success is False
        assert "3 times" in result.stderr
        assert invoker.dry_run.call_count == 3
        cp = PersistenceLoop._read_checkpoint(path)
        assert cp.consecutive_retries == 3

    def test_max_iterations_exceeded(self, vault_dir):
        """Transient errors keep looping until overall iteration cap."""
        loop, invoker, _ = _make_loop(vault_dir, max_iterations=3, max_attempts=100)
        path = _task_md(vault_dir)
        invoker.dry_run.return_value = InvocationResult(
            success=False, stderr="connection refused", returncode=1
        )

        result = loop.run(path, dry_run=True)

        assert result.success is False
        assert "Max iterations (3)" in result.stderr
        assert invoker.dry_run.call_count == 3
        cp = PersistenceLoop._read_checkpoint(path)
        assert cp.state_data.get("max_iterations_exceeded") is True

    def test_invoke_mode_calls_invoke_not_dry_run(self, vault_dir):
        loop, invoker, _ = _make_loop(vault_dir)
        path = _task_md(vault_dir)
        invoker.invoke.return_value = InvocationResult(success=True, stdout="real", returncode=0)

        result = loop.run(path, dry_run=False)

        assert result.success is True
        invoker.invoke.assert_called_once_with(path)
        invoker.dry_run.assert_not_called()

    def test_resumes_from_existing_checkpoint(self, vault_dir):
        """Pre-seed checkpoint at iteration=2; loop starts there."""
        loop, invoker, _ = _make_loop(vault_dir, max_iterations=5)
        path = _task_md(vault_dir)
        PersistenceLoop._write_checkpoint(path, Checkpoint(iteration=2))

        invoker.dry_run.return_value = InvocationResult(success=True, stdout="resumed", returncode=0)

        result = loop.run(path, dry_run=True)

        assert result.success is True
        invoker.dry_run.assert_called_once()
        cp = PersistenceLoop._read_checkpoint(path)
        assert cp.iteration == 3  # 2 → 3

    def test_hard_failure_after_transient_recovery(self, vault_dir):
        """transient → success → (separate run) hard failure sequence."""
        loop, invoker, _ = _make_loop(vault_dir, max_iterations=5)
        path = _task_md(vault_dir)

        # First run: transient then success
        invoker.dry_run.side_effect = [
            InvocationResult(success=False, stderr="connection refused"),
            InvocationResult(success=True, stdout="ok"),
        ]
        result = loop.run(path, dry_run=True)
        assert result.success is True

        # Second run (simulates resume after new task content): hard failure
        invoker.dry_run.side_effect = [
            InvocationResult(success=False, stderr="Permission denied"),
        ]
        result = loop.run(path, dry_run=True)
        assert result.success is False
        assert "Permission denied" in result.stderr


# ===========================================================================
# Stop hook during persistence loop
# ===========================================================================


class TestPersistenceLoopStop:
    def test_stop_hook_prevents_invocation(self, vault_dir):
        loop, invoker, stop_hook = _make_loop(vault_dir)
        path = _task_md(vault_dir)
        stop_hook.set()

        result = loop.run(path, dry_run=True)

        assert result.success is False
        assert "stop hook" in result.stderr.lower()
        invoker.dry_run.assert_not_called()

    def test_stop_hook_set_between_retries(self, vault_dir):
        """Stop hook set after first transient error; second iteration sees it."""
        loop, invoker, stop_hook = _make_loop(vault_dir, max_attempts=5)
        path = _task_md(vault_dir)

        call_count = [0]

        def side_effect(task_path):
            call_count[0] += 1
            if call_count[0] == 1:
                # After first invocation, arm the stop hook
                stop_hook.set()
                return InvocationResult(success=False, stderr="connection refused")
            return InvocationResult(success=True, stdout="should not reach")

        invoker.dry_run.side_effect = side_effect

        result = loop.run(path, dry_run=True)

        assert result.success is False
        assert "stop hook" in result.stderr.lower()
        # Only one invocation happened before stop was detected
        assert invoker.dry_run.call_count == 1


# ===========================================================================
# Warning threshold
# ===========================================================================


class TestPersistenceWarning:
    def test_warning_printed_at_80_percent(self, vault_dir, capsys):
        """max_iterations=5 → warn_at=4. Seed checkpoint at iteration=3."""
        loop, invoker, _ = _make_loop(vault_dir, max_iterations=5, max_attempts=100)
        path = _task_md(vault_dir)
        PersistenceLoop._write_checkpoint(path, Checkpoint(iteration=3))

        invoker.dry_run.side_effect = [
            InvocationResult(success=False, stderr="connection refused"),  # iter 3 (< 4, no warn)
            InvocationResult(success=True, stdout="ok"),                   # iter 4 (>= 4, warn)
        ]

        loop.run(path, dry_run=True)

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "5" in captured.out  # max_iterations appears in message


# ===========================================================================
# Full Orchestrator integration
# ===========================================================================


class TestOrchestratorPersist:
    def test_safe_task_reaches_done_with_checkpoint(self, vault_dir):
        """Orchestrator dry-run: safe task completes; persistence checkpoint in Done file."""
        from src.orchestrator.scheduler import Orchestrator
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)
        (vault_dir / "Needs_Action" / "persist-safe.md").write_text(
            "# persist-safe.md\n\n"
            "**Priority**: \U0001f7e0 High\n"
            "**Status**: New\n"
            "**From**: dev@company.com\n\n"
            "---\n\n"
            "Review the docs.\n"
        )

        orch = Orchestrator(config=cfg, dry_run=True)
        exits = orch.run_once()

        assert len(exits) == 1
        assert exits[0].success is True
        assert exits[0].reason == "done"

        done_file = vault_dir / "Done" / "persist-safe.md"
        assert done_file.exists()
        cp = PersistenceLoop._read_checkpoint(done_file)
        assert cp is not None
        assert cp.iteration >= 1

    def test_transient_retry_recovers_in_orchestrator(self, vault_dir):
        """Patch invoker: first call transient, second succeeds. Task → Done."""
        from src.orchestrator.scheduler import Orchestrator
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir, retry_base_delay=0.0)
        (vault_dir / "Needs_Action" / "retry-recover.md").write_text(
            "# retry-recover.md\n\n"
            "**Priority**: \U0001f7e0 High\n"
            "**Status**: New\n"
            "**From**: dev@company.com\n\n"
            "---\n\n"
            "Safe work — review something.\n"
        )

        orch = Orchestrator(config=cfg, dry_run=True)

        # Patch dry_run on the shared invoker object
        call_n = [0]

        def _patched(task_path):
            call_n[0] += 1
            if call_n[0] == 1:
                return InvocationResult(success=False, stderr="connection refused", returncode=1)
            return InvocationResult(
                success=True, stdout="[DRY-RUN] recovered", returncode=0, duration_seconds=0.1
            )

        orch._invoker.dry_run = _patched

        exits = orch.run_once()

        assert len(exits) == 1
        assert exits[0].success is True
        assert exits[0].reason == "done"
        assert (vault_dir / "Done" / "retry-recover.md").exists()

    def test_hard_failure_reaches_rejected(self, vault_dir):
        """Patch invoker to return hard failure; task → Rejected."""
        from src.orchestrator.scheduler import Orchestrator
        from src.orchestrator.models import OrchestratorConfig

        cfg = OrchestratorConfig(vault_path=vault_dir)
        (vault_dir / "Needs_Action" / "hard-fail.md").write_text(
            "# hard-fail.md\n\n"
            "**Priority**: \U0001f7e0 High\n"
            "**Status**: New\n"
            "**From**: dev@company.com\n\n"
            "---\n\n"
            "Review something.\n"
        )

        orch = Orchestrator(config=cfg, dry_run=True)
        orch._invoker.dry_run = lambda p: InvocationResult(
            success=False, stderr="Permission denied", returncode=1
        )

        exits = orch.run_once()

        assert len(exits) == 1
        assert exits[0].success is False
        assert exits[0].reason == "hard_failure"

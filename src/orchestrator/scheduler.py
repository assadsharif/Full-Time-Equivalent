"""
Orchestrator Scheduler — the Ralph Wiggum Loop.

Single entry-point class ``Orchestrator`` that:
    1. Discovers tasks in /Needs_Action
    2. Scores and sorts by priority
    3. Checks stop-hook before each task
    4. Runs the approval gate (HITL)
    5. Invokes Claude Code (or dry-run mode)
    6. Drives state transitions: NEEDS_ACTION → PLANNING → … → DONE|REJECTED
    7. Logs every iteration with full context
    8. Checkpoints state to .fte/orchestrator.checkpoint.json

Loop invariant (Ralph Wiggum Rule):
    A task is NEVER left in an intermediate state.  It reaches /Done or
    /Rejected, or the loop is explicitly interrupted and state is persisted.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.orchestrator.models import (
    OrchestratorConfig,
    TaskRecord,
    TaskState,
    LoopExit,
)
from src.orchestrator.priority_scorer import PriorityScorer
from src.orchestrator.stop_hook import StopHook
from src.orchestrator.approval_checker import ApprovalChecker
from src.orchestrator.state_machine import StateMachine, TransitionError
from src.orchestrator.claude_invoker import ClaudeInvoker
from src.orchestrator.persistence_loop import PersistenceLoop, RetryPolicy
from src.orchestrator.metrics import MetricsCollector
from src.orchestrator.webhooks import WebhookNotifier


class Orchestrator:
    """Main orchestration loop (Ralph Wiggum Loop)."""

    def __init__(
        self,
        config: Optional[OrchestratorConfig] = None,
        dry_run: bool = False,
    ):
        self.config = config or OrchestratorConfig()
        self.dry_run = dry_run

        # Sub-components
        self._scorer = PriorityScorer(self.config)
        self._stop = StopHook(self.config.vault_path, self.config.stop_hook_file)
        self._approvals = ApprovalChecker(self.config)
        self._state_machine = StateMachine(self.config.vault_path)
        self._invoker = ClaudeInvoker(timeout=self.config.claude_timeout)
        self._persistence = PersistenceLoop(
            max_iterations=self.config.max_iterations,
            retry_policy=RetryPolicy(
                max_attempts=self.config.retry_max_attempts,
                base_delay=self.config.retry_base_delay,
                max_delay=self.config.retry_max_delay,
                jitter=self.config.retry_jitter,
            ),
            invoker=self._invoker,
            stop_hook=self._stop,
        )

        # Vault folder shortcuts
        self._needs_action = self.config.vault_path / "Needs_Action"

        # Runtime tracking
        self._active_tasks: dict[str, TaskRecord] = {}
        self._exit_log: list[LoopExit] = []
        self._iteration = 0
        self._started_at: Optional[datetime] = None

        # Checkpoint path
        self._checkpoint_path = (
            self.config.vault_path.parent / ".fte" / "orchestrator.checkpoint.json"
        )

        # Metrics collector (append-only event log)
        self._metrics = MetricsCollector(
            log_path=self.config.vault_path.parent / ".fte" / "orchestrator_metrics.log"
        )

        # Webhook notifier (fire-and-forget HTTP POST)
        self._webhooks = WebhookNotifier.from_config(self.config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Start the orchestrator loop.  Blocks until stop-hook or SIGINT.

        Each sweep:
            discover → score → for each task: gate → execute → transition
        """
        self._started_at = datetime.now(timezone.utc)
        self._log("=" * 60)
        self._log("Orchestrator started (Ralph Wiggum Loop)")
        self._log(f"  Vault        : {self.config.vault_path}")
        self._log(f"  Needs_Action : {self._needs_action}")
        self._log(f"  Dry-run      : {self.dry_run}")
        self._log(f"  Poll interval: {self.config.poll_interval}s")
        self._log("=" * 60)

        # Notify via webhook
        self._webhooks.orchestrator_started(
            self.config.vault_path, dry_run=self.dry_run
        )

        try:
            while True:
                self._iteration += 1

                # --- capture resource snapshot ---
                self._metrics.resource_snapshot()

                # --- stop-hook check ---
                if self._stop.is_set:
                    self._log("Stop-hook detected — shutting down gracefully.")
                    break

                # --- discover & score ---
                tasks = self._discover()
                if tasks:
                    self._log(
                        f"[sweep {self._iteration}] {len(tasks)} task(s) discovered"
                    )
                    for task in tasks:
                        if self._stop.is_set:
                            self._log(
                                "Stop-hook detected mid-sweep — finishing current task only."
                            )
                            self._process_task(task)
                            break
                        self._process_task(task)
                else:
                    self._log(
                        f"[sweep {self._iteration}] No tasks — sleeping {self.config.poll_interval}s"
                    )

                # --- resume previously-approved tasks ---
                approved = self._discover_approved()
                if approved:
                    self._log(
                        f"[sweep {self._iteration}] {len(approved)} approved task(s) — resuming"
                    )
                    for task in approved:
                        self._resume_task(task)

                self._save_checkpoint()
                time.sleep(self.config.poll_interval)

        except KeyboardInterrupt:
            self._log("KeyboardInterrupt — saving checkpoint and exiting.")
            self._webhooks.orchestrator_stopped(reason="KeyboardInterrupt")
        finally:
            self._save_checkpoint()
            self._log("Orchestrator stopped.")
            self._print_summary()

    def run_once(self) -> list[LoopExit]:
        """
        Single sweep: discover new tasks, process them, then resume any
        previously-parked tasks whose approval has since been granted.
        Does NOT loop.  Useful for testing and CI.
        """
        self._started_at = datetime.now(timezone.utc)
        self._log("Orchestrator: single-sweep mode")

        # --- capture resource snapshot ---
        self._metrics.resource_snapshot()

        # --- new tasks ---
        tasks = self._discover()
        self._log(f"  Found {len(tasks)} new task(s)")
        for task in tasks:
            self._process_task(task)

        # --- resume approved tasks ---
        approved = self._discover_approved()
        if approved:
            self._log(f"  Found {len(approved)} approved task(s) — resuming")
        for task in approved:
            self._resume_task(task)

        self._save_checkpoint()
        self._print_summary()
        return list(self._exit_log)

    # ------------------------------------------------------------------
    # Internal — discovery
    # ------------------------------------------------------------------

    def _discover(self) -> list[TaskRecord]:
        """Scan Needs_Action, score, sort descending by priority."""
        if not self._needs_action.exists():
            return []

        records: list[TaskRecord] = []
        for md in self._needs_action.glob("*.md"):
            # Skip files already being processed
            if md.name in self._active_tasks:
                continue
            score = self._scorer.score(md)
            records.append(TaskRecord(file_path=md, priority_score=score))

        records.sort(key=lambda r: r.priority_score, reverse=True)
        return records

    def _discover_approved(self) -> list[TaskRecord]:
        """Scan Approvals for tasks whose approval has been granted.

        APR-* files are approval *requests* — skip them.  Everything else
        is a real task file that was moved here during PLANNING → PENDING_APPROVAL.
        """
        approvals_dir = self.config.vault_path / "Approvals"
        if not approvals_dir.exists():
            return []

        records: list[TaskRecord] = []
        for md in approvals_dir.glob("*.md"):
            # APR-* files are approval requests — skip
            if md.name.startswith("APR-"):
                continue
            if md.name in self._active_tasks:
                continue
            # Only consider files that have task structure; this filters out
            # approval-response files (legacy or otherwise) that were placed
            # in Approvals as side-channels.
            if "**Priority**:" not in md.read_text(encoding="utf-8"):
                continue
            if not self._approvals.is_approved(md):
                continue
            score = self._scorer.score(md)
            records.append(
                TaskRecord(
                    file_path=md,
                    priority_score=score,
                    state=TaskState.PENDING_APPROVAL,
                )
            )

        records.sort(key=lambda r: r.priority_score, reverse=True)
        return records

    # ------------------------------------------------------------------
    # Internal — task lifecycle
    # ------------------------------------------------------------------

    def _process_task(self, task: TaskRecord) -> None:
        """Drive one task from NEEDS_ACTION through to a terminal state."""
        self._active_tasks[task.name] = task
        start = time.monotonic()

        try:
            # 1. NEEDS_ACTION → PLANNING
            task.file_path = self._state_machine.transition(
                task.file_path, TaskState.NEEDS_ACTION, TaskState.PLANNING
            )
            task.state = TaskState.PLANNING
            self._log(
                f"  [{task.name}] → PLANNING (priority {task.priority_score:.2f})"
            )

            # 2. Approval gate
            if self._approvals.requires_approval(task.file_path):
                keywords = self._approvals.matched_keywords(task.file_path)
                self._log(f"  [{task.name}] ⚠ Approval required — keywords: {keywords}")

                # Check if already approved
                if not self._approvals.is_approved(task.file_path):
                    # Create approval request and park in PENDING_APPROVAL
                    approval_path = self._approvals.create_approval_request(
                        task.file_path, keywords
                    )
                    task.file_path = self._state_machine.transition(
                        task.file_path, TaskState.PLANNING, TaskState.PENDING_APPROVAL
                    )
                    task.state = TaskState.PENDING_APPROVAL
                    self._log(
                        f"  [{task.name}] → PENDING_APPROVAL  (approval at {approval_path.name})"
                    )
                    self._record_exit(task, "pending_approval", False, start)
                    return
                else:
                    self._log(f"  [{task.name}] ✓ Pre-approved — proceeding")

            # 3. PLANNING → EXECUTING
            task.file_path = self._state_machine.transition(
                task.file_path, TaskState.PLANNING, TaskState.EXECUTING
            )
            task.state = TaskState.EXECUTING
            self._log(f"  [{task.name}] → EXECUTING")

            # 4. Invoke Claude via persistence loop (bounded retry)
            self._metrics.task_started(task.name, task.priority_score)
            result = self._persistence.run(task.file_path, dry_run=self.dry_run)

            task.claude_pid = result.pid
            task.attempts += 1
            elapsed = round(time.monotonic() - start, 2)

            if result.success:
                # 5a. EXECUTING → DONE
                self._metrics.task_completed(task.name, elapsed)
                task.file_path = self._state_machine.transition(
                    task.file_path, TaskState.EXECUTING, TaskState.DONE
                )
                task.state = TaskState.DONE
                self._log(f"  [{task.name}] → DONE ✓ ({result.duration_seconds}s)")
                reason = "dry-run" if self.dry_run else "done"
                self._record_exit(task, reason, True, start)
            else:
                # 5b. EXECUTING → REJECTED
                task.error = result.stderr[:200]
                self._metrics.task_failed(task.name, elapsed, task.error)
                self._webhooks.task_failed(task.name, task.error, task.priority_score)
                task.file_path = self._state_machine.transition(
                    task.file_path, TaskState.EXECUTING, TaskState.REJECTED
                )
                task.state = TaskState.REJECTED
                self._log(f"  [{task.name}] → REJECTED ✗ — {task.error}")
                self._record_exit(task, "hard_failure", False, start)

        except TransitionError as exc:
            task.error = str(exc)
            self._log(f"  [{task.name}] TransitionError: {exc}")
            self._record_exit(task, "transition_error", False, start)

        except Exception as exc:
            task.error = str(exc)
            self._log(f"  [{task.name}] Unexpected error: {exc}")
            self._record_exit(task, "unexpected_error", False, start)

        finally:
            self._active_tasks.pop(task.name, None)

    def _resume_task(self, task: TaskRecord) -> None:
        """Resume a task that was parked in PENDING_APPROVAL after approval."""
        self._active_tasks[task.name] = task
        start = time.monotonic()

        try:
            # PENDING_APPROVAL → EXECUTING
            task.file_path = self._state_machine.transition(
                task.file_path, TaskState.PENDING_APPROVAL, TaskState.EXECUTING
            )
            task.state = TaskState.EXECUTING
            self._log(f"  [{task.name}] PENDING_APPROVAL → EXECUTING (resumed)")

            # Invoke Claude via persistence loop (bounded retry)
            self._metrics.task_started(task.name, task.priority_score)
            result = self._persistence.run(task.file_path, dry_run=self.dry_run)

            task.claude_pid = result.pid
            task.attempts += 1
            elapsed = round(time.monotonic() - start, 2)

            if result.success:
                self._metrics.task_completed(task.name, elapsed)
                task.file_path = self._state_machine.transition(
                    task.file_path, TaskState.EXECUTING, TaskState.DONE
                )
                task.state = TaskState.DONE
                self._log(f"  [{task.name}] → DONE ✓ ({result.duration_seconds}s)")
                reason = "dry-run" if self.dry_run else "done"
                self._record_exit(task, reason, True, start)
            else:
                task.error = result.stderr[:200]
                self._metrics.task_failed(task.name, elapsed, task.error)
                self._webhooks.task_failed(task.name, task.error, task.priority_score)
                task.file_path = self._state_machine.transition(
                    task.file_path, TaskState.EXECUTING, TaskState.REJECTED
                )
                task.state = TaskState.REJECTED
                self._log(f"  [{task.name}] → REJECTED ✗ — {task.error}")
                self._record_exit(task, "hard_failure", False, start)

        except TransitionError as exc:
            task.error = str(exc)
            self._log(f"  [{task.name}] TransitionError: {exc}")
            self._webhooks.task_failed(task.name, task.error, task.priority_score)
            self._record_exit(task, "transition_error", False, start)

        except Exception as exc:
            task.error = str(exc)
            self._log(f"  [{task.name}] Unexpected error: {exc}")
            self._record_exit(task, "unexpected_error", False, start)

        finally:
            self._active_tasks.pop(task.name, None)

    # ------------------------------------------------------------------
    # Internal — helpers
    # ------------------------------------------------------------------

    def _record_exit(
        self, task: TaskRecord, reason: str, success: bool, start: float
    ) -> None:
        self._exit_log.append(
            LoopExit(
                task_path=task.file_path,
                reason=reason,
                success=success,
                iteration_count=self._iteration,
                duration_seconds=round(time.monotonic() - start, 2),
                final_state=task.state,
                error=task.error,
            )
        )

    def _log(self, msg: str) -> None:
        """Timestamped print (stdout) + append to vault log file."""
        line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
        print(line, flush=True)
        log_path = self.config.vault_path / "orchestrator.log"
        with open(log_path, "a") as fh:
            fh.write(line + "\n")

    def _save_checkpoint(self) -> None:
        """Persist current state to JSON checkpoint file."""
        self._checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "last_iteration": self._iteration,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "active_tasks": {
                name: {
                    "file": str(t.file_path),
                    "state": t.state.value,
                    "priority": t.priority_score,
                    "attempts": t.attempts,
                }
                for name, t in self._active_tasks.items()
            },
            "exit_log": [
                {
                    "task": str(e.task_path.name),
                    "reason": e.reason,
                    "success": e.success,
                    "final_state": e.final_state.value,
                    "duration_s": e.duration_seconds,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in self._exit_log
            ],
            "stop_hook_set": self._stop.is_set,
        }
        self._checkpoint_path.write_text(json.dumps(state, indent=2))

    def _print_summary(self) -> None:
        total = len(self._exit_log)
        done = sum(1 for e in self._exit_log if e.success)
        self._log("=" * 60)
        self._log(f"Summary: {done}/{total} tasks completed successfully")
        for e in self._exit_log:
            icon = "✓" if e.success else "✗"
            self._log(
                f"  {icon} {e.task_path.name} → {e.final_state.value} ({e.reason}, {e.duration_seconds}s)"
            )
        self._log("=" * 60)

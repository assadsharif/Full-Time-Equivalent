"""
Persistence Loop — bounded retry with exponential backoff and
YAML-frontmatter checkpointing (Plan 04: Ralph Wiggum Persistence Rule).

Wraps a ClaudeInvoker.invoke / dry_run call in a retry loop that:
  • classifies failures as transient (retry) or hard (stop immediately)
  • applies exponential backoff with ±jitter between retries
  • checkpoints progress into the task file's YAML frontmatter
  • resumes from a previous checkpoint on restart
  • warns at 80 % of max_iterations; reports exhaustion on overflow
  • respects the stop hook between iterations

Constitutional compliance:
  Section 10.1 – multi-step tasks use persistence loop
  Section 10.2 – loop until /Done or hard failure
  Section 10.3 – infinite loops forbidden (max_iterations enforced)
"""

import random
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from src.orchestrator.claude_invoker import ClaudeInvoker, InvocationResult
from src.orchestrator.stop_hook import StopHook

# ---------------------------------------------------------------------------
# Transient-error heuristics (case-insensitive regex on stderr)
# ---------------------------------------------------------------------------

_TRANSIENT_PATTERNS: list[re.Pattern] = [
    re.compile(r"timed?\s*out", re.IGNORECASE),
    re.compile(r"rate[\s_-]*limit", re.IGNORECASE),
    re.compile(r"503|service\s+unavailable", re.IGNORECASE),
    re.compile(r"connection\s+(refused|reset|error)", re.IGNORECASE),
    re.compile(r"temporary\s+(error|failure)", re.IGNORECASE),
    re.compile(r"try\s+again\s+later", re.IGNORECASE),
    re.compile(r"lock\s+(acquisition|timeout)", re.IGNORECASE),
]

# ---------------------------------------------------------------------------
# Error type classification for smart retry strategies
# ---------------------------------------------------------------------------


class ErrorType:
    """Error classification for adaptive retry strategies."""

    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    CONNECTION = "connection"
    SERVICE_UNAVAILABLE = "service_unavailable"
    LOCK_CONTENTION = "lock_contention"
    GENERIC_TRANSIENT = "generic_transient"


_ERROR_TYPE_PATTERNS: dict[str, re.Pattern] = {
    ErrorType.RATE_LIMIT: re.compile(r"rate[\s_-]*limit", re.IGNORECASE),
    ErrorType.TIMEOUT: re.compile(r"timed?\s*out", re.IGNORECASE),
    ErrorType.CONNECTION: re.compile(
        r"connection\s+(refused|reset|error)", re.IGNORECASE
    ),
    ErrorType.SERVICE_UNAVAILABLE: re.compile(
        r"503|service\s+unavailable", re.IGNORECASE
    ),
    ErrorType.LOCK_CONTENTION: re.compile(
        r"lock\s+(acquisition|timeout)", re.IGNORECASE
    ),
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class RetryPolicy:
    """Configurable retry parameters."""

    max_attempts: int = 3  # consecutive transient failures before giving up
    base_delay: float = 1.0  # seconds (first backoff step)
    max_delay: float = 16.0  # seconds (backoff ceiling)
    jitter: float = 0.2  # ±fraction applied to each delay

    @classmethod
    def for_error_type(cls, error_type: str) -> "RetryPolicy":
        """
        Return error-type-specific retry policy (smart retry).

        Different error types benefit from different backoff strategies:
        - Rate limits: Longer backoff to respect API limits
        - Timeouts: Shorter backoff for transient network issues
        - Connection errors: Medium backoff for service recovery
        - Service unavailable: Longer backoff for maintenance windows
        - Lock contention: Shorter backoff for quick retry
        """
        strategies = {
            ErrorType.RATE_LIMIT: cls(
                max_attempts=4,
                base_delay=5.0,
                max_delay=60.0,
                jitter=0.2,
            ),
            ErrorType.TIMEOUT: cls(
                max_attempts=3,
                base_delay=1.0,
                max_delay=16.0,
                jitter=0.3,
            ),
            ErrorType.CONNECTION: cls(
                max_attempts=4,
                base_delay=2.0,
                max_delay=32.0,
                jitter=0.2,
            ),
            ErrorType.SERVICE_UNAVAILABLE: cls(
                max_attempts=3,
                base_delay=10.0,
                max_delay=120.0,
                jitter=0.2,
            ),
            ErrorType.LOCK_CONTENTION: cls(
                max_attempts=5,
                base_delay=0.5,
                max_delay=8.0,
                jitter=0.4,
            ),
            ErrorType.GENERIC_TRANSIENT: cls(
                max_attempts=3,
                base_delay=1.0,
                max_delay=16.0,
                jitter=0.2,
            ),
        }
        return strategies.get(error_type, strategies[ErrorType.GENERIC_TRANSIENT])


@dataclass
class Checkpoint:
    """Snapshot persisted into the task file's YAML frontmatter."""

    iteration: int = 0
    consecutive_retries: int = 0
    started_at: Optional[str] = None
    last_updated: Optional[str] = None
    last_error: Optional[str] = None
    last_error_type: Optional[str] = None
    state_data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------


class PersistenceLoop:
    """
    Bounded-retry wrapper around a ClaudeInvoker.

    Typical usage (inside Orchestrator._process_task):
        result = self._persistence.run(task.file_path, dry_run=self.dry_run)
    """

    def __init__(
        self,
        max_iterations: int,
        retry_policy: RetryPolicy,
        invoker: ClaudeInvoker,
        stop_hook: StopHook,
    ):
        self._max_iterations = max_iterations
        self._retry = retry_policy
        self._invoker = invoker
        self._stop = stop_hook
        self._warn_at = int(max_iterations * 0.8)

    # ------------------------------------------------------------------
    # Main entry-point
    # ------------------------------------------------------------------

    def run(self, task_path: Path, dry_run: bool = False) -> InvocationResult:
        """
        Execute the invoker with bounded persistence.

        Returns an InvocationResult on:
          • first success
          • first hard (non-transient) failure
          • retry-budget exhaustion (max_attempts consecutive transient errors)
          • max_iterations exhaustion
          • stop-hook interruption
        """
        checkpoint = self._read_checkpoint(task_path) or Checkpoint()
        if checkpoint.started_at is None:
            checkpoint.started_at = datetime.now(timezone.utc).isoformat()

        for iteration in range(checkpoint.iteration, self._max_iterations):
            # --- stop hook ---
            if self._stop.is_set:
                checkpoint.state_data["stopped"] = True
                self._write_checkpoint(task_path, checkpoint)
                return InvocationResult(
                    success=False,
                    stderr="Persistence loop interrupted by stop hook",
                )

            # --- 80 % warning ---
            if iteration >= self._warn_at:
                print(
                    f"[persistence] WARNING {task_path.name}: "
                    f"iteration {iteration + 1}/{self._max_iterations}"
                )

            # --- invoke ---
            result = (
                self._invoker.dry_run(task_path)
                if dry_run
                else self._invoker.invoke(task_path)
            )

            checkpoint.iteration = iteration + 1
            checkpoint.last_updated = datetime.now(timezone.utc).isoformat()

            # --- success ---
            if result.success:
                checkpoint.consecutive_retries = 0
                checkpoint.last_error = None
                self._write_checkpoint(task_path, checkpoint)
                return result

            # --- hard failure — return immediately ---
            if not self.is_transient(result):
                checkpoint.last_error = result.stderr[:200]
                self._write_checkpoint(task_path, checkpoint)
                return result

            # --- transient failure: classify error type & check retry budget ---
            error_type = self.classify_error_type(result)
            checkpoint.consecutive_retries += 1
            checkpoint.last_error = result.stderr[:200]
            checkpoint.last_error_type = error_type

            # Use error-type-specific retry policy (smart retry)
            retry_policy = RetryPolicy.for_error_type(error_type)

            if checkpoint.consecutive_retries >= retry_policy.max_attempts:
                self._write_checkpoint(task_path, checkpoint)
                return InvocationResult(
                    success=False,
                    stdout=result.stdout,
                    stderr=(
                        f"Transient failure ({error_type}) repeated {retry_policy.max_attempts} "
                        f"times: {result.stderr[:150]}"
                    ),
                    returncode=result.returncode,
                    duration_seconds=result.duration_seconds,
                    timed_out=result.timed_out,
                )

            # --- backoff & loop with error-type-specific policy ---
            self._write_checkpoint(task_path, checkpoint)
            time.sleep(
                self._backoff_delay(checkpoint.consecutive_retries, retry_policy)
            )

        # --- max iterations exceeded ---
        checkpoint.state_data["max_iterations_exceeded"] = True
        checkpoint.last_error = f"Max iterations ({self._max_iterations}) exceeded"
        self._write_checkpoint(task_path, checkpoint)
        return InvocationResult(
            success=False,
            stderr=f"Max iterations ({self._max_iterations}) exceeded for {task_path.name}",
            returncode=-2,
        )

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    @staticmethod
    def is_transient(result: InvocationResult) -> bool:
        """True if the failure looks transient / retriable."""
        if result.timed_out:
            return True
        return any(p.search(result.stderr) for p in _TRANSIENT_PATTERNS)

    @staticmethod
    def classify_error_type(result: InvocationResult) -> str:
        """
        Classify error type for smart retry strategy selection.

        Returns ErrorType constant (e.g., RATE_LIMIT, TIMEOUT) or GENERIC_TRANSIENT.
        """
        if result.timed_out:
            return ErrorType.TIMEOUT

        for error_type, pattern in _ERROR_TYPE_PATTERNS.items():
            if pattern.search(result.stderr):
                return error_type

        return ErrorType.GENERIC_TRANSIENT

    # ------------------------------------------------------------------
    # Backoff
    # ------------------------------------------------------------------

    def _backoff_delay(
        self, attempt: int, policy: Optional[RetryPolicy] = None
    ) -> float:
        """
        Exponential backoff clamped to max_delay, with ±jitter.

        If policy is provided, uses that policy's parameters (for smart retry).
        Otherwise uses the default policy.
        """
        retry_policy = policy if policy else self._retry
        raw = retry_policy.base_delay * (2 ** (attempt - 1))
        clamped = min(raw, retry_policy.max_delay)
        jitter_range = clamped * retry_policy.jitter
        return clamped + random.uniform(-jitter_range, jitter_range)

    # ------------------------------------------------------------------
    # Checkpoint I/O — YAML frontmatter in the task .md file
    # ------------------------------------------------------------------

    @staticmethod
    def _read_checkpoint(task_path: Path) -> Optional[Checkpoint]:
        """Extract persistence_loop section from YAML frontmatter, or None."""
        text = task_path.read_text()
        if not text.startswith("---"):
            return None
        end = text.find("---", 3)
        if end == -1:
            return None
        raw = yaml.safe_load(text[3:end])
        if not isinstance(raw, dict) or "persistence_loop" not in raw:
            return None
        pl = raw["persistence_loop"]
        return Checkpoint(
            iteration=pl.get("iteration", 0),
            consecutive_retries=pl.get("consecutive_retries", 0),
            started_at=pl.get("started_at"),
            last_updated=pl.get("last_updated"),
            last_error=pl.get("last_error"),
            last_error_type=pl.get("last_error_type"),
            state_data=pl.get("state_data", {}),
        )

    @staticmethod
    def _write_checkpoint(task_path: Path, cp: Checkpoint) -> None:
        """Insert or update the persistence_loop block in YAML frontmatter."""
        text = task_path.read_text()
        pl_data = {
            "persistence_loop": {
                "iteration": cp.iteration,
                "consecutive_retries": cp.consecutive_retries,
                "started_at": cp.started_at,
                "last_updated": cp.last_updated,
                "last_error": cp.last_error,
                "last_error_type": cp.last_error_type,
                "state_data": cp.state_data,
            }
        }

        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                existing = yaml.safe_load(text[3:end]) or {}
                existing.update(pl_data)
                new_fm = yaml.dump(existing, default_flow_style=False).rstrip()
                task_path.write_text(f"---\n{new_fm}\n---\n{text[end + 3:]}")
                return

        # No valid frontmatter — prepend one
        new_fm = yaml.dump(pl_data, default_flow_style=False).rstrip()
        task_path.write_text(f"---\n{new_fm}\n---\n{text}")

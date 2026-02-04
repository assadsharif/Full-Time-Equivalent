"""
Claude Invoker — subprocess wrapper around the Claude Code CLI.

Spawns ``claude`` (or a configurable binary) with the task file as
context, captures stdout/stderr, enforces a per-invocation timeout,
and returns a structured result.

ADR-003: subprocess chosen over HTTP/SDK because it uses the official
CLI, works offline, and isolates each invocation in its own process.
"""

import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class InvocationResult:
    """Outcome of a single Claude invocation."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int = -1
    pid: Optional[int] = None
    duration_seconds: float = 0.0
    timed_out: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ClaudeInvoker:
    """Spawns Claude Code and captures the result."""

    def __init__(
        self,
        claude_binary: str = "claude",
        timeout: int = 3600,
    ):
        self._binary = claude_binary
        self._timeout = timeout

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def invoke(self, task_path: Path) -> InvocationResult:
        """
        Run Claude Code on *task_path*.

        The invocation is:
            claude --no-interactive <task_path>

        Returns InvocationResult regardless of outcome (never raises).
        """
        start = time.monotonic()
        try:
            proc = subprocess.run(
                [self._binary, "--no-interactive", str(task_path)],
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            duration = time.monotonic() - start
            return InvocationResult(
                success=(proc.returncode == 0),
                stdout=proc.stdout,
                stderr=proc.stderr,
                returncode=proc.returncode,
                duration_seconds=round(duration, 2),
            )

        except subprocess.TimeoutExpired:
            duration = time.monotonic() - start
            return InvocationResult(
                success=False,
                stderr=f"Claude invocation timed out after {self._timeout}s",
                timed_out=True,
                duration_seconds=round(duration, 2),
            )

        except FileNotFoundError:
            return InvocationResult(
                success=False,
                stderr=f"Claude binary not found: {self._binary}",
            )

        except Exception as exc:
            duration = time.monotonic() - start
            return InvocationResult(
                success=False,
                stderr=str(exc),
                duration_seconds=round(duration, 2),
            )

    # ------------------------------------------------------------------
    # Dry-run / simulation
    # ------------------------------------------------------------------

    def dry_run(self, task_path: Path) -> InvocationResult:
        """
        Simulate a Claude invocation without actually running Claude.

        Useful for testing the orchestrator loop without a Claude binary.
        Always returns success after a 0.1 s sleep.
        """
        time.sleep(0.1)
        return InvocationResult(
            success=True,
            stdout=f"[DRY-RUN] Would invoke Claude on {task_path.name}",
            returncode=0,
            duration_seconds=0.1,
        )

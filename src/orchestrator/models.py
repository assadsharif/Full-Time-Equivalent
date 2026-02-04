"""
Orchestrator data models — enums, config, and runtime records.

All models are plain dataclasses / enums; no external deps beyond stdlib.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Task state machine
# ---------------------------------------------------------------------------


class TaskState(str, Enum):
    """Canonical states a task moves through in the orchestrator."""

    NEEDS_ACTION = "needs_action"
    PLANNING = "planning"
    PENDING_APPROVAL = "pending_approval"
    EXECUTING = "executing"
    DONE = "done"
    REJECTED = "rejected"


# ---------------------------------------------------------------------------
# Configuration (mirrors config/orchestrator.yaml)
# ---------------------------------------------------------------------------


@dataclass
class OrchestratorConfig:
    """Runtime configuration loaded from YAML or constructed programmatically."""

    vault_path: Path = field(default_factory=lambda: Path.home() / "AI_Employee_Vault")
    poll_interval: int = 30                   # seconds between discovery sweeps
    max_concurrent_tasks: int = 5             # parallel Claude invocations
    claude_timeout: int = 3600                # seconds per Claude invocation
    stop_hook_file: str = ".claude_stop"      # filename in vault root
    max_iterations: int = 100                 # Ralph Wiggum bound per task

    # Priority weights (must sum to 1.0)
    urgency_weight: float = 0.4
    deadline_weight: float = 0.3
    sender_weight: float = 0.3

    # VIP sender list (scores sender_importance = 5)
    vip_senders: list = field(default_factory=lambda: [
        "ceo@company.com",
        "board@company.com",
    ])

    # Approval-required action keywords
    approval_keywords: list = field(default_factory=lambda: [
        "deploy", "production", "delete", "payment", "wire",
        "send email", "execute", "remove",
    ])

    @classmethod
    def from_yaml(cls, path: Path) -> "OrchestratorConfig":
        """Load config from YAML file. Falls back to defaults if file missing."""
        import yaml  # noqa: E402  (lazy import — yaml is optional at module level)

        if not path.exists():
            return cls()
        with open(path) as fh:
            raw = yaml.safe_load(fh) or {}

        orch = raw.get("orchestrator", {})
        prio = raw.get("priority_weights", {})

        return cls(
            vault_path=Path(orch.get("vault_path", str(cls.vault_path))),
            poll_interval=orch.get("poll_interval", 30),
            max_concurrent_tasks=orch.get("max_concurrent_tasks", 5),
            claude_timeout=orch.get("claude_timeout", 3600),
            stop_hook_file=orch.get("stop_hook_file", ".claude_stop"),
            max_iterations=orch.get("max_iterations", 100),
            urgency_weight=prio.get("urgency", 0.4),
            deadline_weight=prio.get("deadline", 0.3),
            sender_weight=prio.get("sender", 0.3),
            vip_senders=raw.get("vip_senders", ["ceo@company.com", "board@company.com"]),
            approval_keywords=raw.get("approval_keywords", cls.approval_keywords),
        )


# ---------------------------------------------------------------------------
# Runtime records
# ---------------------------------------------------------------------------


@dataclass
class TaskRecord:
    """In-memory representation of a task being orchestrated."""

    file_path: Path
    state: TaskState = TaskState.NEEDS_ACTION
    priority_score: float = 0.0
    iteration: int = 0
    claude_pid: Optional[int] = None
    attempts: int = 0
    requires_approval: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None

    @property
    def name(self) -> str:
        return self.file_path.name


@dataclass
class LoopExit:
    """Record of how and why the orchestrator loop exited for a task."""

    task_path: Path
    reason: str                                  # done | hard_failure | max_iterations | stop_hook | interrupted
    success: bool
    iteration_count: int
    duration_seconds: float
    final_state: TaskState
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

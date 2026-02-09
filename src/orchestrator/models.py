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
    poll_interval: int = 30  # seconds between discovery sweeps
    max_concurrent_tasks: int = 5  # parallel Claude invocations
    claude_timeout: int = 3600  # seconds per Claude invocation
    stop_hook_file: str = ".claude_stop"  # filename in vault root
    max_iterations: int = 100  # Ralph Wiggum bound per task

    # Priority weights (must sum to 1.0)
    urgency_weight: float = 0.4
    deadline_weight: float = 0.3
    sender_weight: float = 0.3

    # VIP sender list (scores sender_importance = 5)
    vip_senders: list = field(
        default_factory=lambda: [
            "ceo@company.com",
            "board@company.com",
        ]
    )

    # Approval-required action keywords
    approval_keywords: list = field(
        default_factory=lambda: [
            "deploy",
            "production",
            "delete",
            "payment",
            "wire",
            "send email",
            "execute",
            "remove",
        ]
    )

    # Persistence-loop retry policy (Plan 04)
    retry_max_attempts: int = 3
    retry_base_delay: float = 1.0  # seconds
    retry_max_delay: float = 16.0  # seconds
    retry_jitter: float = 0.2  # ±fraction

    # Webhook notifications (Phase 7 T046)
    notifications_enabled: bool = False
    notification_webhook_url: Optional[str] = None
    notification_events: list[str] = field(
        default_factory=lambda: [
            "task_failed",
            "health_degraded",
            "orchestrator_stopped",
        ]
    )

    @classmethod
    def from_yaml(
        cls, path: Path, vault_path_override: Optional[Path] = None
    ) -> "OrchestratorConfig":
        """Load config from YAML file. Falls back to defaults if file missing."""
        import yaml  # noqa: E402  (lazy import — yaml is optional at module level)

        if not path.exists():
            config = cls()
            if vault_path_override:
                config.vault_path = vault_path_override
            return config

        with open(path) as fh:
            raw = yaml.safe_load(fh) or {}

        orch = raw.get("orchestrator", {})
        prio = raw.get("priority_weights", {})
        notifs = raw.get("notifications", {})

        vault = vault_path_override or Path(orch.get("vault_path", str(cls.vault_path)))

        return cls(
            vault_path=vault,
            poll_interval=orch.get("poll_interval", 30),
            max_concurrent_tasks=orch.get("max_concurrent_tasks", 5),
            claude_timeout=orch.get("claude_timeout", 3600),
            stop_hook_file=orch.get("stop_hook_file", ".claude_stop"),
            max_iterations=orch.get("max_iterations", 100),
            urgency_weight=prio.get("urgency", 0.4),
            deadline_weight=prio.get("deadline", 0.3),
            sender_weight=prio.get("sender", 0.3),
            vip_senders=raw.get(
                "vip_senders", ["ceo@company.com", "board@company.com"]
            ),
            approval_keywords=raw.get("approval_keywords", cls.approval_keywords),
            retry_max_attempts=raw.get("retry", {}).get("max_attempts", 3),
            retry_base_delay=raw.get("retry", {}).get("base_delay", 1.0),
            retry_max_delay=raw.get("retry", {}).get("max_delay", 16.0),
            retry_jitter=raw.get("retry", {}).get("jitter", 0.2),
            notifications_enabled=notifs.get("enabled", False),
            notification_webhook_url=notifs.get("webhook_url"),
            notification_events=notifs.get("events", cls.notification_events),
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
    reason: str  # done | hard_failure | max_iterations | stop_hook | interrupted
    success: bool
    iteration_count: int
    duration_seconds: float
    final_state: TaskState
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

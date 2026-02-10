"""
Orchestrator — autonomous task execution engine for Digital FTE.

Implements the "Ralph Wiggum Loop": continuously discovers tasks in
Needs_Action, scores priority, enforces HITL approvals, invokes Claude
Code, and drives tasks to /Done or /Rejected.  Never silently abandons
a task.

Constitutional Compliance:
- Section 4:  File-driven control plane (reads/writes vault folders only)
- Section 6-7: Autonomy with HITL enforcement before dangerous actions
- Section 8:  Full audit trail on every state transition
- Section 10: Ralph Wiggum Rule — loop until /Done or hard failure
"""

from .models import (
    TaskState,
    OrchestratorConfig,
    TaskRecord,
    LoopExit,
)
from .priority_scorer import PriorityScorer
from .stop_hook import StopHook
from .approval_checker import ApprovalChecker
from .state_machine import StateMachine
from .claude_invoker import ClaudeInvoker
from .persistence_loop import PersistenceLoop
from .metrics import MetricsCollector
from .health_check import HealthCheck
from .dashboard import OrchestratorDashboard
from .queue_visualizer import QueueVisualizer
from .webhooks import WebhookNotifier
from .scheduler import Orchestrator

__all__ = [
    # Models
    "TaskState",
    "OrchestratorConfig",
    "TaskRecord",
    "LoopExit",
    # Components
    "PriorityScorer",
    "StopHook",
    "ApprovalChecker",
    "StateMachine",
    "ClaudeInvoker",
    "PersistenceLoop",
    "MetricsCollector",
    "HealthCheck",
    "OrchestratorDashboard",
    "QueueVisualizer",
    "WebhookNotifier",
    # Main
    "Orchestrator",
]

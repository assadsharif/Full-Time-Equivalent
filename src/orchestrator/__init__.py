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

from src.orchestrator.models import (
    TaskState,
    OrchestratorConfig,
    TaskRecord,
    LoopExit,
)
from src.orchestrator.priority_scorer import PriorityScorer
from src.orchestrator.stop_hook import StopHook
from src.orchestrator.approval_checker import ApprovalChecker
from src.orchestrator.state_machine import StateMachine
from src.orchestrator.claude_invoker import ClaudeInvoker
from src.orchestrator.scheduler import Orchestrator

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
    # Main
    "Orchestrator",
]

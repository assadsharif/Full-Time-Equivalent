"""
Approval Checker — HITL gate before dangerous actions.

Scans a task's markdown body for approval-required keywords.  If a match
is found the task is routed to /Approvals and blocked until a human
approves or rejects it via ``fte vault approve``.

Zero-bypass guarantee: if keyword match → approval required, no
exceptions.  The orchestrator never executes a flagged task without an
explicit approval file in /Approvals with status "approved".
"""

import re
from pathlib import Path
from typing import Optional

from src.approval.approval_manager import ApprovalManager
from src.orchestrator.models import OrchestratorConfig

# Keyword → canonical action_type mapping (first match wins)
_ACTION_TYPE_MAP: list[tuple[list[str], str]] = [
    (["payment", "wire"], "payment"),
    (["deploy", "production"], "deploy"),
    (["delete", "remove"], "delete"),
    (["send email", "email"], "email"),
    (["execute"], "execute"),
]


def _derive_action_type(keywords: list[str]) -> str:
    """Map detected keywords to a canonical action type."""
    lower_kws = {kw.lower() for kw in keywords}
    for triggers, action_type in _ACTION_TYPE_MAP:
        if lower_kws & set(triggers):
            return action_type
    return "unknown"


class ApprovalChecker:
    """Determines whether a task needs HITL approval and checks status."""

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self._approvals_path = self.config.vault_path / "Approvals"
        # Pre-compile keyword patterns
        self._patterns = [
            re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
            for kw in self.config.approval_keywords
        ]
        # Full approval manager (nonce + integrity + timeout)
        self._manager = ApprovalManager(self._approvals_path)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def requires_approval(self, task_path: Path) -> bool:
        """Return True if task body contains any approval-required keyword."""
        text = task_path.read_text(encoding="utf-8")
        return any(p.search(text) for p in self._patterns)

    def matched_keywords(self, task_path: Path) -> list[str]:
        """Return list of keywords that matched in the task body."""
        text = task_path.read_text(encoding="utf-8")
        return [
            kw
            for kw, p in zip(self.config.approval_keywords, self._patterns)
            if p.search(text)
        ]

    def is_approved(self, task_path: Path) -> bool:
        """
        Check whether an approval file exists for this task and is approved.

        Tries the ApprovalManager path first (nonce-aware, expiry-aware).
        Falls back to legacy text-matching for hand-written approval files.
        """
        task_id = task_path.stem

        # New path: structured approvals via ApprovalManager
        if self._manager.is_approved(task_id):
            return True

        # Legacy fallback: plain-text "approved" in any file whose name
        # contains the task stem (supports hand-written approvals)
        if not self._approvals_path.exists():
            return False
        lower_stem = task_id.lower()
        for approval_file in self._approvals_path.glob("*.md"):
            if lower_stem in approval_file.name.lower():
                body = approval_file.read_text(encoding="utf-8").lower()
                if "approved" in body and "pending" not in body:
                    return True
        return False

    def create_approval_request(self, task_path: Path, keywords: list[str]) -> Path:
        """
        Create a structured approval request via ApprovalManager.

        Returns the path of the created file.
        """
        action_type = _derive_action_type(keywords)
        request = self._manager.create(
            task_id=task_path.stem,
            action_type=action_type,
            keywords=keywords,
        )
        return self._approvals_path / f"{request.approval_id}.md"

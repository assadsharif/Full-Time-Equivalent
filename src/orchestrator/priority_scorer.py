"""
Priority Scorer — weighted scoring for task triage.

Formula (all components normalised to 1-5):
    score = urgency_w * urgency + deadline_w * deadline_urgency + sender_w * sender_importance

Keyword tables and VIP list are driven by OrchestratorConfig so they can
be tuned in config/orchestrator.yaml without code changes.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.orchestrator.models import OrchestratorConfig


# ---------------------------------------------------------------------------
# Keyword → urgency score tables
# ---------------------------------------------------------------------------

_URGENCY_KEYWORDS: list[tuple[re.Pattern, int]] = [
    (re.compile(r"\bURGENT\b", re.IGNORECASE), 5),
    (re.compile(r"\bASAP\b|\bhigh.priority\b", re.IGNORECASE), 4),
    (re.compile(r"\blow.priority\b", re.IGNORECASE), 2),
    (re.compile(r"\bwhenever\b|\bno.rush\b", re.IGNORECASE), 1),
]

_DEADLINE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"by\s+(today|end.of.day|EOD)", re.IGNORECASE), "today"),
    (re.compile(r"by\s+(tomorrow|end.of.week|Friday|this week)", re.IGNORECASE), "3d"),
    (re.compile(r"by\s+(next\s+week|next\s+monday)", re.IGNORECASE), "7d"),
    (re.compile(r"by\s+(end.of.month|next\s+month)", re.IGNORECASE), "30d"),
]


class PriorityScorer:
    """Scores a task file and returns a float in [1.0, 5.0]."""

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()
        self._vip_set = {s.lower() for s in self.config.vip_senders}

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def score(self, task_path: Path) -> float:
        """Read task markdown, extract signals, return weighted score."""
        text = task_path.read_text(encoding="utf-8")
        urgency = self._score_urgency(text)
        deadline = self._score_deadline(text)
        sender = self._score_sender(text)

        raw = (
            self.config.urgency_weight * urgency
            + self.config.deadline_weight * deadline
            + self.config.sender_weight * sender
        )
        # Clamp to [1, 5]
        return max(1.0, min(5.0, raw))

    # ------------------------------------------------------------------
    # Internal scorers
    # ------------------------------------------------------------------

    def _score_urgency(self, text: str) -> float:
        """Keyword scan for urgency signals. Default 3 (normal)."""
        for pattern, score in _URGENCY_KEYWORDS:
            if pattern.search(text):
                return float(score)
        # Check the priority badge line produced by Gmail watcher
        if "🔴" in text or "urgent" in text.lower():
            return 5.0
        if "🟠" in text or "high" in text.lower():
            return 4.0
        if "🟡" in text or "medium" in text.lower():
            return 3.0
        if "🟢" in text or "low" in text.lower():
            return 2.0
        return 3.0

    def _score_deadline(self, text: str) -> float:
        """Detect deadline language. Default 1 (no deadline)."""
        for pattern, bucket in _DEADLINE_PATTERNS:
            if pattern.search(text):
                if bucket == "today":
                    return 5.0
                if bucket == "3d":
                    return 4.0
                if bucket == "7d":
                    return 3.0
                return 2.0
        # "by Friday", "by Monday" heuristic
        if re.search(r"by\s+(friday|monday|tuesday|wednesday|thursday|saturday|sunday)", text, re.IGNORECASE):
            return 4.0
        return 1.0

    def _score_sender(self, text: str) -> float:
        """Identify sender importance from **From** line or email header."""
        # Look for **From**: email@domain pattern
        match = re.search(r"\*\*From\*\*:\s*(\S+@\S+)", text)
        if not match:
            match = re.search(r"sender[:\s]+(\S+@\S+)", text, re.IGNORECASE)
        if not match:
            return 2.0  # unknown external

        sender = match.group(1).strip().lower()

        if sender in self._vip_set:
            return 5.0
        # Heuristic: "client" in domain or body near sender
        if "client" in sender or re.search(r"client", text[:500], re.IGNORECASE):
            return 4.0
        # Internal (same domain as VIP)
        vip_domains = {s.split("@")[1] for s in self._vip_set if "@" in s}
        sender_domain = sender.split("@")[1] if "@" in sender else ""
        if sender_domain in vip_domains:
            return 3.0
        return 2.0

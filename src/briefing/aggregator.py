"""
Briefing Aggregator — reads /Done files and builds BriefingData.

Parsing strategy:
  - If a file has YAML frontmatter (``---`` … ``---``) the persistence_loop
    section is extracted for iteration counts.
  - Markdown-formatted fields (``**Priority**:``, ``**From**:``, etc.) are
    parsed from the body with simple regex.
  - The human-readable body starts after the first ``---`` horizontal rule
    in the non-frontmatter content.
"""

import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from src.briefing.models import BriefingData, TaskSummary

# ---------------------------------------------------------------------------
# Field extractors (case-insensitive regex)
# ---------------------------------------------------------------------------

_PRIORITY_RE = re.compile(r"\*\*Priority\*\*\s*:\s*(.+)", re.IGNORECASE)
_FROM_RE = re.compile(r"\*\*From\*\*\s*:\s*(.+)", re.IGNORECASE)
_STATUS_RE = re.compile(r"\*\*Status\*\*\s*:\s*(.+)", re.IGNORECASE)

# Emoji → canonical priority label
_PRIORITY_EMOJI_MAP = {
    "🔴": "urgent",
    "🟠": "high",
    "🟡": "medium",
    "🟢": "low",
}


def _normalize_priority(raw: str) -> str:
    """Strip emoji and whitespace, lowercase."""
    raw = raw.strip()
    for emoji, label in _PRIORITY_EMOJI_MAP.items():
        if emoji in raw:
            return label
    # Fall back to the last word lowered (e.g. "⚪ Normal" → "normal")
    return raw.split()[-1].lower() if raw else "normal"


class BriefingAggregator:
    """Scans a vault /Done directory and produces a BriefingData summary."""

    def __init__(self, done_path: Path, lookback_days: int = 7):
        self._done = done_path
        self._lookback = timedelta(days=lookback_days)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def aggregate(self) -> BriefingData:
        """Scan /Done, parse every .md, compute stats, return BriefingData."""
        now = datetime.now(timezone.utc)
        period_start = now - self._lookback

        tasks: list[TaskSummary] = []
        if self._done.exists():
            for md_file in sorted(self._done.glob("*.md")):
                summary = self._parse_task_file(md_file)
                tasks.append(summary)

        data = BriefingData(
            period_start=period_start,
            period_end=now,
            generated_at=now,
            tasks=tasks,
        )
        self._compute_stats(data)
        return data

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_task_file(path: Path) -> TaskSummary:
        text = path.read_text(encoding="utf-8")
        persistence_iterations = 0
        body_text = text

        # --- strip YAML frontmatter if present ---
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                fm_raw = text[3:end]
                fm = yaml.safe_load(fm_raw) or {}
                pl = fm.get("persistence_loop", {})
                persistence_iterations = pl.get("iteration", 0)
                body_text = text[end + 3 :]

        # --- extract structured fields from markdown body ---
        priority_m = _PRIORITY_RE.search(body_text)
        from_m = _FROM_RE.search(body_text)

        priority = _normalize_priority(priority_m.group(1)) if priority_m else "normal"
        sender = from_m.group(1).strip() if from_m else "unknown"

        # --- body: everything after the first ``---`` horizontal rule ---
        hr_idx = body_text.find("\n---\n")
        human_body = (
            body_text[hr_idx + 5 :].strip() if hr_idx != -1 else body_text.strip()
        )

        return TaskSummary(
            name=path.stem,
            priority=priority,
            sender=sender,
            body=human_body,
            persistence_iterations=persistence_iterations,
        )

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_stats(data: BriefingData) -> None:
        data.total_tasks = len(data.tasks)

        priority_counter: Counter = Counter()
        sender_counter: Counter = Counter()
        iteration_sum = 0

        for t in data.tasks:
            priority_counter[t.priority] += 1
            sender_counter[t.sender] += 1
            iteration_sum += t.persistence_iterations

        data.by_priority = dict(priority_counter.most_common())
        data.by_sender = dict(sender_counter.most_common())
        data.top_senders = sender_counter.most_common(5)
        data.avg_iterations = (
            round(iteration_sum / data.total_tasks, 2) if data.total_tasks else 0.0
        )

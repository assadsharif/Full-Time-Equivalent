"""Briefing data models."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TaskSummary:
    """One completed-task record extracted from /Done."""

    name: str  # filename (without extension)
    priority: str = "normal"  # urgent | high | medium | low | normal
    sender: str = "unknown"
    status: str = "done"
    body: str = ""  # markdown body after the separator
    completed_at: datetime = field(default_factory=datetime.now)
    persistence_iterations: int = 0  # from YAML frontmatter if present
    keywords: list[str] = field(default_factory=list)  # approval keywords hit


@dataclass
class BriefingData:
    """Aggregate payload handed to the Jinja2 template."""

    period_start: datetime
    period_end: datetime
    generated_at: datetime = field(default_factory=datetime.now)
    tasks: list[TaskSummary] = field(default_factory=list)

    # --- computed properties (populated by aggregator) ---
    total_tasks: int = 0
    by_priority: dict = field(default_factory=dict)  # priority → count
    by_sender: dict = field(default_factory=dict)  # sender → count
    avg_iterations: float = 0.0
    top_senders: list[tuple[str, int]] = field(default_factory=list)

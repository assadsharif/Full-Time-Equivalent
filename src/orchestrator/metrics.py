"""
Metrics Collector — append-only event log for orchestrator performance.

Records task lifecycle events (started / completed / failed) as JSON lines
and exposes calculation methods for throughput, latency, and error rate.
All calculations are stateless: they scan the log on demand.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class MetricsCollector:
    """Append-only metrics event store with on-demand aggregation."""

    def __init__(self, log_path: Path):
        self._log_path = log_path

    # ------------------------------------------------------------------
    # Event writers
    # ------------------------------------------------------------------

    def task_started(self, task_name: str, priority: float = 0.0) -> None:
        """Record that a task has begun execution."""
        self._write({
            "event": "task_started",
            "task_name": task_name,
            "priority": priority,
        })

    def task_completed(self, task_name: str, duration_seconds: float) -> None:
        """Record successful task completion."""
        self._write({
            "event": "task_completed",
            "task_name": task_name,
            "duration_seconds": round(duration_seconds, 3),
        })

    def task_failed(self, task_name: str, duration_seconds: float, error: str = "") -> None:
        """Record a task failure."""
        self._write({
            "event": "task_failed",
            "task_name": task_name,
            "duration_seconds": round(duration_seconds, 3),
            "error": error,
        })

    # ------------------------------------------------------------------
    # Calculations
    # ------------------------------------------------------------------

    def calculate_throughput(self, since: Optional[datetime] = None) -> float:
        """Tasks completed per hour within the window.

        The window stretches from *since* (or the earliest completed-event
        timestamp when *since* is None) to now.  Returns 0.0 when no
        completed events exist or the window is shorter than one second.
        """
        events = self._load_events(since)
        completed = [e for e in events if e["event"] == "task_completed"]
        if not completed:
            return 0.0

        now = datetime.now(timezone.utc)
        if since:
            window_start = since
        else:
            window_start = datetime.fromisoformat(completed[0]["timestamp"])

        elapsed_hours = (now - window_start).total_seconds() / 3600.0
        if elapsed_hours < (1.0 / 3600):  # less than 1 second
            return 0.0
        return round(len(completed) / elapsed_hours, 2)

    def calculate_avg_latency(self, since: Optional[datetime] = None) -> float:
        """Average task duration in seconds across completed and failed tasks."""
        events = self._load_events(since)
        terminal = [e for e in events if e["event"] in ("task_completed", "task_failed")]
        if not terminal:
            return 0.0
        total = sum(e["duration_seconds"] for e in terminal)
        return round(total / len(terminal), 2)

    def calculate_error_rate(self, since: Optional[datetime] = None) -> float:
        """Fraction of terminal tasks that failed (0.0 – 1.0).

        Only *task_completed* and *task_failed* events are considered;
        *task_started* events are ignored.
        """
        events = self._load_events(since)
        completed = sum(1 for e in events if e["event"] == "task_completed")
        failed = sum(1 for e in events if e["event"] == "task_failed")
        total = completed + failed
        if total == 0:
            return 0.0
        return round(failed / total, 4)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_events(self, since: Optional[datetime] = None) -> list[dict]:
        """Read all events, optionally filtered by timestamp >= since."""
        if not self._log_path.exists():
            return []
        events: list[dict] = []
        with open(self._log_path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if since:
                    ts = datetime.fromisoformat(event.get("timestamp", ""))
                    if ts < since:
                        continue
                events.append(event)
        return events

    def _write(self, record: dict) -> None:
        """Stamp with timestamp and append one JSON line."""
        record["timestamp"] = datetime.now(timezone.utc).isoformat()
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._log_path, "a") as fh:
            fh.write(json.dumps(record) + "\n")

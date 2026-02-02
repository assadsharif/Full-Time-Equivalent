"""
TDD State Manager

Tracks TDD session state including current phase, target test file,
run results, and cycle history. Persists to .fte/tdd_state.json.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# Valid TDD phases
PHASES = ("idle", "red", "green", "refactor")


class TDDState:
    """Manages TDD session state with JSON persistence."""

    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path or (Path.cwd() / ".fte" / "tdd_state.json")
        self.phase: str = "idle"
        self.target_test: Optional[str] = None
        self.passed: int = 0
        self.failed: int = 0
        self.errors: int = 0
        self.cycle_history: list[dict] = []
        self._load()

    def _load(self) -> None:
        """Load state from disk if it exists."""
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text())
                self.phase = data.get("phase", "idle")
                self.target_test = data.get("target_test")
                self.passed = data.get("passed", 0)
                self.failed = data.get("failed", 0)
                self.errors = data.get("errors", 0)
                self.cycle_history = data.get("cycle_history", [])
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        """Persist state to disk."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "phase": self.phase,
            "target_test": self.target_test,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "cycle_history": self.cycle_history,
        }
        self.state_path.write_text(json.dumps(data, indent=2) + "\n")

    def set_phase(self, phase: str, target_test: Optional[str] = None) -> None:
        """Transition to a new TDD phase."""
        if phase not in PHASES:
            raise ValueError(f"Invalid phase: {phase}. Must be one of {PHASES}")
        self.phase = phase
        if target_test is not None:
            self.target_test = target_test
        self.save()

    def record_run(self, passed: int, failed: int, errors: int) -> None:
        """Record test run results."""
        self.passed = passed
        self.failed = failed
        self.errors = errors
        self.save()

    def record_cycle(self, outcome: str) -> None:
        """Append a completed cycle entry to history."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_test": self.target_test,
            "outcome": outcome,
        }
        self.cycle_history.append(entry)
        self.save()

    def reset(self) -> None:
        """Reset state to idle."""
        self.phase = "idle"
        self.target_test = None
        self.passed = 0
        self.failed = 0
        self.errors = 0
        self.save()

    def to_dict(self) -> dict:
        """Return state as a dictionary."""
        return {
            "phase": self.phase,
            "target_test": self.target_test,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "cycles_completed": len(self.cycle_history),
        }

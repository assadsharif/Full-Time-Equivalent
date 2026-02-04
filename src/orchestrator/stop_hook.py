"""
Stop Hook — file-based emergency-stop mechanism.

The orchestrator checks for a sentinel file (default: .claude_stop) in
the vault root before every iteration.  Creating the file triggers a
graceful shutdown after the current task completes.  Removing it allows
the loop to resume.

ADR-002: chosen over signal-based stopping because it is auditable
(file timestamp), cross-platform, and requires no process-signaling
complexity.
"""

from pathlib import Path


class StopHook:
    """Watches for a sentinel file that signals graceful shutdown."""

    def __init__(self, vault_path: Path, hook_filename: str = ".claude_stop"):
        self._hook_path = vault_path / hook_filename

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    @property
    def is_set(self) -> bool:
        """True when the stop-hook file exists."""
        return self._hook_path.exists()

    def set(self) -> None:
        """Create the stop-hook file (trigger shutdown)."""
        self._hook_path.touch()

    def clear(self) -> None:
        """Remove the stop-hook file (allow resumption)."""
        if self._hook_path.exists():
            self._hook_path.unlink()

    @property
    def hook_path(self) -> Path:
        return self._hook_path

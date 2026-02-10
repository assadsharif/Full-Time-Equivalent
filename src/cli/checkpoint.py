"""
CLI Checkpoint Manager

Manages persistent state for CLI operations including vault status,
watcher states, MCP server health, and command usage tracking.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from .utils import get_checkpoint_path


class WatcherCheckpoint(BaseModel):
    """Watcher state checkpoint"""

    status: str = Field(default="stopped")  # stopped, running, error
    pid: Optional[int] = Field(default=None)
    uptime: Optional[int] = Field(default=None)  # seconds
    last_start: Optional[str] = Field(default=None)  # ISO timestamp
    last_stop: Optional[str] = Field(default=None)  # ISO timestamp


class VaultCheckpoint(BaseModel):
    """Vault state checkpoint"""

    path: Optional[str] = Field(default=None)
    initialized: bool = Field(default=False)
    last_status_check: Optional[str] = Field(default=None)  # ISO timestamp


class MCPCheckpoint(BaseModel):
    """MCP servers state checkpoint"""

    registry_loaded: bool = Field(default=False)
    last_health_check: Optional[str] = Field(default=None)  # ISO timestamp
    servers: list = Field(default_factory=list)


class ApprovalsCheckpoint(BaseModel):
    """Approvals state checkpoint"""

    pending_count: int = Field(default=0)
    last_review: Optional[str] = Field(default=None)  # ISO timestamp
    last_approval: Optional[str] = Field(default=None)  # ISO timestamp
    last_rejection: Optional[str] = Field(default=None)  # ISO timestamp


class BriefingsCheckpoint(BaseModel):
    """Briefings state checkpoint"""

    last_generated: Optional[str] = Field(default=None)  # ISO timestamp
    last_viewed: Optional[str] = Field(default=None)  # ISO timestamp
    total_generated: int = Field(default=0)


class CLIUsageCheckpoint(BaseModel):
    """CLI usage state checkpoint"""

    total_commands: int = Field(default=0)
    last_command: Optional[str] = Field(default=None)
    last_command_time: Optional[str] = Field(default=None)  # ISO timestamp


class Checkpoint(BaseModel):
    """Complete CLI checkpoint state"""

    version: str = Field(default="0.1.0")
    last_updated: Optional[str] = Field(default=None)  # ISO timestamp
    vault: VaultCheckpoint = Field(default_factory=VaultCheckpoint)
    watchers: Dict[str, WatcherCheckpoint] = Field(
        default_factory=lambda: {
            "gmail": WatcherCheckpoint(),
            "whatsapp": WatcherCheckpoint(),
            "filesystem": WatcherCheckpoint(),
        }
    )
    mcp_servers: MCPCheckpoint = Field(default_factory=MCPCheckpoint)
    approvals: ApprovalsCheckpoint = Field(default_factory=ApprovalsCheckpoint)
    briefings: BriefingsCheckpoint = Field(default_factory=BriefingsCheckpoint)
    cli_usage: CLIUsageCheckpoint = Field(default_factory=CLIUsageCheckpoint)


class CheckpointManager:
    """Manages CLI checkpoint state persistence"""

    def __init__(self, checkpoint_path: Optional[Path] = None):
        """
        Initialize checkpoint manager.

        Args:
            checkpoint_path: Path to checkpoint file (defaults to .fte/cli.checkpoint.json)
        """
        self.checkpoint_path = checkpoint_path or get_checkpoint_path()
        self._checkpoint: Optional[Checkpoint] = None

    def load(self) -> Checkpoint:
        """
        Load checkpoint from file.

        Returns:
            Checkpoint instance

        Creates default checkpoint if file doesn't exist.
        """
        if not self.checkpoint_path.exists():
            # Create default checkpoint
            return Checkpoint()

        try:
            with open(self.checkpoint_path, "r") as f:
                data = json.load(f)
            self._checkpoint = Checkpoint(**data)
            return self._checkpoint
        except (json.JSONDecodeError, ValueError) as e:
            # Invalid checkpoint, return default
            return Checkpoint()

    def save(self, checkpoint: Optional[Checkpoint] = None) -> None:
        """
        Save checkpoint to file.

        Args:
            checkpoint: Checkpoint to save (uses loaded checkpoint if not provided)
        """
        if checkpoint is None:
            checkpoint = self._checkpoint or Checkpoint()

        # Update last_updated timestamp
        checkpoint.last_updated = datetime.utcnow().isoformat() + "Z"

        # Ensure directory exists
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        # Write checkpoint
        with open(self.checkpoint_path, "w") as f:
            json.dump(checkpoint.model_dump(), f, indent=2)

        self._checkpoint = checkpoint

    def get(self) -> Checkpoint:
        """
        Get loaded checkpoint (loads if not already loaded).

        Returns:
            Checkpoint instance
        """
        if self._checkpoint is None:
            self._checkpoint = self.load()
        return self._checkpoint

    def update_vault(
        self, path: Optional[str] = None, initialized: Optional[bool] = None
    ) -> None:
        """
        Update vault checkpoint.

        Args:
            path: Vault path
            initialized: Vault initialization status
        """
        checkpoint = self.get()

        if path is not None:
            checkpoint.vault.path = path
        if initialized is not None:
            checkpoint.vault.initialized = initialized

        checkpoint.vault.last_status_check = datetime.utcnow().isoformat() + "Z"
        self.save(checkpoint)

    def update_watcher(
        self,
        watcher_name: str,
        status: Optional[str] = None,
        pid: Optional[int] = None,
        uptime: Optional[int] = None,
    ) -> None:
        """
        Update watcher checkpoint.

        Args:
            watcher_name: Watcher name (gmail, whatsapp, filesystem)
            status: Watcher status (stopped, running, error)
            pid: Process ID
            uptime: Uptime in seconds
        """
        checkpoint = self.get()

        if watcher_name not in checkpoint.watchers:
            checkpoint.watchers[watcher_name] = WatcherCheckpoint()

        watcher = checkpoint.watchers[watcher_name]

        if status is not None:
            watcher.status = status
            if status == "running":
                watcher.last_start = datetime.utcnow().isoformat() + "Z"
            elif status == "stopped":
                watcher.last_stop = datetime.utcnow().isoformat() + "Z"

        if pid is not None:
            watcher.pid = pid
        if uptime is not None:
            watcher.uptime = uptime

        self.save(checkpoint)

    def update_mcp(
        self, registry_loaded: Optional[bool] = None, servers: Optional[list] = None
    ) -> None:
        """
        Update MCP servers checkpoint.

        Args:
            registry_loaded: Registry loaded status
            servers: List of server configurations
        """
        checkpoint = self.get()

        if registry_loaded is not None:
            checkpoint.mcp_servers.registry_loaded = registry_loaded
        if servers is not None:
            checkpoint.mcp_servers.servers = servers

        checkpoint.mcp_servers.last_health_check = datetime.utcnow().isoformat() + "Z"
        self.save(checkpoint)

    def update_mcp_server(self, name: str, action: str) -> None:
        """
        Update MCP server action in checkpoint.

        Args:
            name: Server name
            action: Action performed (added, tested, removed)
        """
        checkpoint = self.get()
        checkpoint.mcp_servers.last_health_check = datetime.utcnow().isoformat() + "Z"
        self.save(checkpoint)

    def update_approval(
        self,
        pending_count: Optional[int] = None,
        action: Optional[str] = None,  # "review", "approve", "reject"
    ) -> None:
        """
        Update approvals checkpoint.

        Args:
            pending_count: Number of pending approvals
            action: Action performed (review, approve, reject)
        """
        checkpoint = self.get()

        if pending_count is not None:
            checkpoint.approvals.pending_count = pending_count

        timestamp = datetime.utcnow().isoformat() + "Z"
        if action == "review":
            checkpoint.approvals.last_review = timestamp
        elif action == "approve":
            checkpoint.approvals.last_approval = timestamp
        elif action == "reject":
            checkpoint.approvals.last_rejection = timestamp

        self.save(checkpoint)

    def update_briefing(self, action: str) -> None:  # "generate", "view"
        """
        Update briefings checkpoint.

        Args:
            action: Action performed (generate, view)
        """
        checkpoint = self.get()

        timestamp = datetime.utcnow().isoformat() + "Z"
        if action == "generate":
            checkpoint.briefings.last_generated = timestamp
            checkpoint.briefings.total_generated += 1
        elif action == "view":
            checkpoint.briefings.last_viewed = timestamp

        self.save(checkpoint)

    def update_usage(self, command: str) -> None:
        """
        Update CLI usage tracking.

        Args:
            command: Command executed
        """
        checkpoint = self.get()

        checkpoint.cli_usage.total_commands += 1
        checkpoint.cli_usage.last_command = command
        checkpoint.cli_usage.last_command_time = datetime.utcnow().isoformat() + "Z"

        self.save(checkpoint)


# Global checkpoint manager instance
_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager(checkpoint_path: Optional[Path] = None) -> CheckpointManager:
    """
    Get global checkpoint manager instance.

    Args:
        checkpoint_path: Optional custom checkpoint path

    Returns:
        CheckpointManager instance
    """
    global _checkpoint_manager

    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager(checkpoint_path)

    return _checkpoint_manager

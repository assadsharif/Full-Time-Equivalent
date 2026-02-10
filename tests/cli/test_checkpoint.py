"""
Unit tests for CLI checkpoint manager.

Tests checkpoint loading, saving, and state updates.
"""

import json
from pathlib import Path

import pytest

from cli.checkpoint import (
    Checkpoint,
    CheckpointManager,
    WatcherCheckpoint,
    get_checkpoint_manager,
)


class TestCheckpoint:
    """Test Checkpoint model"""

    def test_default_checkpoint(self):
        """Test default checkpoint values"""
        checkpoint = Checkpoint()

        assert checkpoint.version == "0.1.0"
        assert checkpoint.last_updated is None
        assert checkpoint.vault.path is None
        assert checkpoint.vault.initialized is False
        assert "gmail" in checkpoint.watchers
        assert "whatsapp" in checkpoint.watchers
        assert "filesystem" in checkpoint.watchers
        assert checkpoint.watchers["gmail"].status == "stopped"
        assert checkpoint.mcp_servers.registry_loaded is False
        assert checkpoint.approvals.pending_count == 0
        assert checkpoint.briefings.total_generated == 0
        assert checkpoint.cli_usage.total_commands == 0

    def test_checkpoint_serialization(self):
        """Test checkpoint can be serialized to dict"""
        checkpoint = Checkpoint()
        data = checkpoint.model_dump()

        assert isinstance(data, dict)
        assert data["version"] == "0.1.0"
        assert "vault" in data
        assert "watchers" in data
        assert "gmail" in data["watchers"]


class TestWatcherCheckpoint:
    """Test WatcherCheckpoint model"""

    def test_default_watcher_checkpoint(self):
        """Test default watcher checkpoint values"""
        watcher = WatcherCheckpoint()

        assert watcher.status == "stopped"
        assert watcher.pid is None
        assert watcher.uptime is None
        assert watcher.last_start is None
        assert watcher.last_stop is None

    def test_watcher_checkpoint_with_values(self):
        """Test watcher checkpoint with custom values"""
        watcher = WatcherCheckpoint(
            status="running", pid=12345, uptime=3600, last_start="2026-01-28T10:00:00Z"
        )

        assert watcher.status == "running"
        assert watcher.pid == 12345
        assert watcher.uptime == 3600
        assert watcher.last_start == "2026-01-28T10:00:00Z"


class TestCheckpointManager:
    """Test CheckpointManager class"""

    def test_load_nonexistent_checkpoint(self, tmp_path):
        """Test loading checkpoint when file doesn't exist returns default"""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = CheckpointManager(checkpoint_file)

        checkpoint = manager.load()

        assert isinstance(checkpoint, Checkpoint)
        assert checkpoint.version == "0.1.0"

    def test_load_existing_checkpoint(self, tmp_path):
        """Test loading checkpoint from file"""
        checkpoint_file = tmp_path / "checkpoint.json"
        checkpoint_data = {
            "version": "0.1.0",
            "last_updated": "2026-01-28T10:00:00Z",
            "vault": {
                "path": "~/AI_Employee_Vault",
                "initialized": True,
                "last_status_check": "2026-01-28T10:00:00Z",
            },
            "watchers": {
                "gmail": {
                    "status": "running",
                    "pid": 12345,
                    "uptime": 3600,
                    "last_start": "2026-01-28T09:00:00Z",
                    "last_stop": None,
                },
                "whatsapp": {
                    "status": "stopped",
                    "pid": None,
                    "uptime": None,
                    "last_start": None,
                    "last_stop": None,
                },
                "filesystem": {
                    "status": "stopped",
                    "pid": None,
                    "uptime": None,
                    "last_start": None,
                    "last_stop": None,
                },
            },
            "mcp_servers": {
                "registry_loaded": True,
                "last_health_check": "2026-01-28T10:00:00Z",
                "servers": [],
            },
            "approvals": {
                "pending_count": 2,
                "last_review": "2026-01-28T09:30:00Z",
                "last_approval": None,
                "last_rejection": None,
            },
            "briefings": {
                "last_generated": "2026-01-27T08:00:00Z",
                "last_viewed": "2026-01-28T09:00:00Z",
                "total_generated": 5,
            },
            "cli_usage": {
                "total_commands": 42,
                "last_command": "fte status",
                "last_command_time": "2026-01-28T10:00:00Z",
            },
        }

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f)

        manager = CheckpointManager(checkpoint_file)
        checkpoint = manager.load()

        assert checkpoint.vault.path == "~/AI_Employee_Vault"
        assert checkpoint.vault.initialized is True
        assert checkpoint.watchers["gmail"].status == "running"
        assert checkpoint.watchers["gmail"].pid == 12345
        assert checkpoint.approvals.pending_count == 2
        assert checkpoint.briefings.total_generated == 5
        assert checkpoint.cli_usage.total_commands == 42

    def test_load_invalid_checkpoint(self, tmp_path):
        """Test loading invalid checkpoint returns default"""
        checkpoint_file = tmp_path / "checkpoint.json"

        with open(checkpoint_file, "w") as f:
            f.write("invalid json content")

        manager = CheckpointManager(checkpoint_file)
        checkpoint = manager.load()

        assert isinstance(checkpoint, Checkpoint)
        assert checkpoint.version == "0.1.0"

    def test_save_checkpoint(self, tmp_path):
        """Test saving checkpoint to file"""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = CheckpointManager(checkpoint_file)

        checkpoint = Checkpoint()
        checkpoint.vault.path = "~/Test"
        checkpoint.vault.initialized = True

        manager.save(checkpoint)

        assert checkpoint_file.exists()

        # Verify saved data
        with open(checkpoint_file, "r") as f:
            data = json.load(f)

        assert data["vault"]["path"] == "~/Test"
        assert data["vault"]["initialized"] is True
        assert data["last_updated"] is not None  # Timestamp added

    def test_get_cached_checkpoint(self, tmp_path):
        """Test get() returns cached checkpoint"""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = CheckpointManager(checkpoint_file)

        checkpoint1 = manager.get()
        checkpoint2 = manager.get()

        assert checkpoint1 is checkpoint2

    def test_update_vault(self, tmp_path):
        """Test updating vault checkpoint"""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = CheckpointManager(checkpoint_file)

        manager.update_vault(path="~/CustomVault", initialized=True)

        checkpoint = manager.get()
        assert checkpoint.vault.path == "~/CustomVault"
        assert checkpoint.vault.initialized is True
        assert checkpoint.vault.last_status_check is not None

    def test_update_watcher(self, tmp_path):
        """Test updating watcher checkpoint"""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = CheckpointManager(checkpoint_file)

        manager.update_watcher("gmail", status="running", pid=12345, uptime=3600)

        checkpoint = manager.get()
        assert checkpoint.watchers["gmail"].status == "running"
        assert checkpoint.watchers["gmail"].pid == 12345
        assert checkpoint.watchers["gmail"].uptime == 3600
        assert checkpoint.watchers["gmail"].last_start is not None

    def test_update_watcher_stop(self, tmp_path):
        """Test updating watcher to stopped status"""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = CheckpointManager(checkpoint_file)

        manager.update_watcher("gmail", status="stopped")

        checkpoint = manager.get()
        assert checkpoint.watchers["gmail"].status == "stopped"
        assert checkpoint.watchers["gmail"].last_stop is not None

    def test_update_mcp(self, tmp_path):
        """Test updating MCP checkpoint"""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = CheckpointManager(checkpoint_file)

        servers = [{"name": "gmail", "url": "http://localhost:3000"}]
        manager.update_mcp(registry_loaded=True, servers=servers)

        checkpoint = manager.get()
        assert checkpoint.mcp_servers.registry_loaded is True
        assert checkpoint.mcp_servers.servers == servers
        assert checkpoint.mcp_servers.last_health_check is not None

    def test_update_approval(self, tmp_path):
        """Test updating approval checkpoint"""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = CheckpointManager(checkpoint_file)

        manager.update_approval(pending_count=3, action="approve")

        checkpoint = manager.get()
        assert checkpoint.approvals.pending_count == 3
        assert checkpoint.approvals.last_approval is not None

    def test_update_approval_actions(self, tmp_path):
        """Test updating approval with different actions"""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = CheckpointManager(checkpoint_file)

        manager.update_approval(action="review")
        checkpoint = manager.get()
        assert checkpoint.approvals.last_review is not None

        manager.update_approval(action="reject")
        checkpoint = manager.get()
        assert checkpoint.approvals.last_rejection is not None

    def test_update_briefing(self, tmp_path):
        """Test updating briefing checkpoint"""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = CheckpointManager(checkpoint_file)

        manager.update_briefing(action="generate")

        checkpoint = manager.get()
        assert checkpoint.briefings.last_generated is not None
        assert checkpoint.briefings.total_generated == 1

        manager.update_briefing(action="generate")
        checkpoint = manager.get()
        assert checkpoint.briefings.total_generated == 2

    def test_update_briefing_view(self, tmp_path):
        """Test updating briefing view action"""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = CheckpointManager(checkpoint_file)

        manager.update_briefing(action="view")

        checkpoint = manager.get()
        assert checkpoint.briefings.last_viewed is not None

    def test_update_usage(self, tmp_path):
        """Test updating CLI usage tracking"""
        checkpoint_file = tmp_path / "checkpoint.json"
        manager = CheckpointManager(checkpoint_file)

        manager.update_usage("fte status")

        checkpoint = manager.get()
        assert checkpoint.cli_usage.total_commands == 1
        assert checkpoint.cli_usage.last_command == "fte status"
        assert checkpoint.cli_usage.last_command_time is not None

        manager.update_usage("fte vault init")
        checkpoint = manager.get()
        assert checkpoint.cli_usage.total_commands == 2
        assert checkpoint.cli_usage.last_command == "fte vault init"


class TestGlobalCheckpointManager:
    """Test global checkpoint manager functions"""

    def test_get_checkpoint_manager_singleton(self, tmp_path):
        """Test get_checkpoint_manager() returns singleton"""
        from src.cli import checkpoint as checkpoint_module

        # Reset global state
        checkpoint_module._checkpoint_manager = None

        checkpoint_file = tmp_path / "checkpoint.json"
        manager1 = get_checkpoint_manager(checkpoint_file)
        manager2 = get_checkpoint_manager(checkpoint_file)

        # Note: This will only be the same instance if called without arguments
        # after the first call, since we're passing checkpoint_file each time
        # Let's test the actual singleton behavior
        checkpoint_module._checkpoint_manager = None
        manager1 = get_checkpoint_manager()
        manager2 = get_checkpoint_manager()

        assert manager1 is manager2

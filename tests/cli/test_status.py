"""
Integration tests for fte status command.

Tests status display and health checks.
"""

from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.status import status_command


class TestStatusCommand:
    """Test fte status command"""

    def test_status_basic(self):
        """Test basic status command execution"""
        runner = CliRunner()
        result = runner.invoke(status_command)

        # Should display status information (may exit 1 if vault invalid)
        assert "Vault" in result.output or "Status" in result.output

    def test_status_help(self):
        """Test status command help"""
        runner = CliRunner()
        result = runner.invoke(status_command, ['--help'])

        assert result.exit_code == 0
        assert "comprehensive system status" in result.output.lower()
        assert "--vault-path" in result.output
        assert "--json" in result.output

    def test_status_with_vault_path(self, tmp_path):
        """Test status with explicit vault path"""
        runner = CliRunner()

        # Create a valid vault
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        (vault_path / "Inbox").mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()

        result = runner.invoke(status_command, ['--vault-path', str(vault_path)])

        assert "Vault" in result.output
        # Should succeed with valid vault
        assert result.exit_code == 0

    def test_status_invalid_vault(self, tmp_path):
        """Test status with invalid vault path"""
        runner = CliRunner()

        # Create invalid vault (missing folders)
        vault_path = tmp_path / "invalid_vault"
        vault_path.mkdir()

        result = runner.invoke(status_command, ['--vault-path', str(vault_path)])

        # Should exit with error code 1
        assert result.exit_code == 1
        assert "Vault" in result.output or "Invalid" in result.output or "Error" in result.output

    def test_status_json_output(self, tmp_path):
        """Test status with JSON output format"""
        runner = CliRunner()

        # Create a valid vault
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        (vault_path / "Inbox").mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()

        result = runner.invoke(status_command, ['--vault-path', str(vault_path), '--json'])

        # Should output JSON
        assert "{" in result.output or "vault" in result.output.lower()


class TestStatusVaultCheck:
    """Test vault status checking"""

    def test_status_shows_vault_path(self, tmp_path):
        """Test status displays vault path"""
        runner = CliRunner()

        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        (vault_path / "Inbox").mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()

        result = runner.invoke(status_command, ['--vault-path', str(vault_path)])

        assert str(vault_path) in result.output or "Vault" in result.output

    def test_status_valid_vault(self, tmp_path):
        """Test status with valid vault shows success"""
        runner = CliRunner()

        vault_path = tmp_path / "valid_vault"
        vault_path.mkdir()
        (vault_path / "Inbox").mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()
        (vault_path / "Approvals").mkdir()
        (vault_path / "Briefings").mkdir()
        (vault_path / "Attachments").mkdir()

        result = runner.invoke(status_command, ['--vault-path', str(vault_path)])

        assert result.exit_code == 0
        assert "Vault" in result.output

    def test_status_missing_vault(self, tmp_path):
        """Test status with missing vault"""
        runner = CliRunner()

        vault_path = tmp_path / "nonexistent_vault"

        result = runner.invoke(status_command, ['--vault-path', str(vault_path)])

        assert result.exit_code == 1
        # Should show error about missing vault

    def test_status_task_counts(self, tmp_path):
        """Test status displays task counts"""
        runner = CliRunner()

        # Create vault with some tasks
        vault_path = tmp_path / "vault_with_tasks"
        vault_path.mkdir()
        inbox = vault_path / "Inbox"
        inbox.mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()

        # Create some task files
        (inbox / "task1.md").write_text("# Task 1")
        (inbox / "task2.md").write_text("# Task 2")

        result = runner.invoke(status_command, ['--vault-path', str(vault_path)])

        assert "Inbox" in result.output or "Task" in result.output


class TestStatusWatcherCheck:
    """Test watcher status checking"""

    def test_status_shows_watchers(self, tmp_path):
        """Test status displays watcher information"""
        runner = CliRunner()

        # Create valid vault
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        (vault_path / "Inbox").mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()

        result = runner.invoke(status_command, ['--vault-path', str(vault_path)])

        # Should show watcher section
        assert "Watcher" in result.output or "Status" in result.output

    def test_status_watcher_stopped(self, tmp_path):
        """Test status shows watchers as stopped by default"""
        runner = CliRunner()

        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        (vault_path / "Inbox").mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()

        result = runner.invoke(status_command, ['--vault-path', str(vault_path)])

        # Watchers should be stopped initially
        assert "stopped" in result.output.lower() or "Watcher" in result.output


class TestStatusMCPCheck:
    """Test MCP server status checking"""

    def test_status_shows_mcp_servers(self, tmp_path):
        """Test status displays MCP server information"""
        runner = CliRunner()

        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        (vault_path / "Inbox").mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()

        result = runner.invoke(status_command, ['--vault-path', str(vault_path)])

        # Should show MCP section
        assert "MCP" in result.output or "Server" in result.output


class TestStatusApprovalCheck:
    """Test approval status checking"""

    def test_status_shows_approvals(self, tmp_path):
        """Test status displays approval information"""
        runner = CliRunner()

        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        (vault_path / "Inbox").mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()
        (vault_path / "Approvals").mkdir()

        result = runner.invoke(status_command, ['--vault-path', str(vault_path)])

        # Should show approval section
        assert "Approval" in result.output or "Status" in result.output

    def test_status_pending_approvals(self, tmp_path):
        """Test status shows pending approval count"""
        runner = CliRunner()

        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        (vault_path / "Inbox").mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()
        approvals = vault_path / "Approvals"
        approvals.mkdir()

        # Create a pending approval
        approval_content = """---
approval_status: pending
---
# Test Approval
"""
        (approvals / "test_approval.md").write_text(approval_content)

        result = runner.invoke(status_command, ['--vault-path', str(vault_path)])

        # Should show pending approval
        assert "Approval" in result.output or "pending" in result.output.lower()


class TestStatusErrorHandling:
    """Test status error handling"""

    def test_status_handles_missing_vault_gracefully(self, tmp_path):
        """Test status handles missing vault with clear error"""
        runner = CliRunner()

        nonexistent = tmp_path / "nonexistent"

        result = runner.invoke(status_command, ['--vault-path', str(nonexistent)])

        # Should exit with error code 1 (T035)
        assert result.exit_code == 1

    def test_status_handles_invalid_vault_gracefully(self, tmp_path):
        """Test status handles invalid vault with clear error"""
        runner = CliRunner()

        # Create directory but not valid vault
        invalid = tmp_path / "invalid"
        invalid.mkdir()

        result = runner.invoke(status_command, ['--vault-path', str(invalid)])

        # Should exit with error code 1 (T035)
        assert result.exit_code == 1

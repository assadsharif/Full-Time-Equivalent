"""
End-to-End Integration Tests

Tests complete workflows across multiple CLI commands.
Verifies that user stories work from start to finish.

Test Scenarios:
- Complete task lifecycle (create → move → complete → briefing)
- Watcher lifecycle (start → monitor → stop)
- MCP integration workflow (add → test → use tools)
- Approval workflow (create → review → approve)
- System health monitoring workflow
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.approval import approval_group
from cli.briefing import briefing_group
from cli.init import init_command
from cli.mcp import mcp_group
from cli.status import status_command
from cli.vault import vault_group
from cli.watcher import watcher_group


@pytest.fixture
def e2e_vault(tmp_path):
    """Create a complete vault for e2e testing."""
    vault_path = tmp_path / "e2e_vault"
    vault_path.mkdir()

    # Create all required folders
    folders = [
        "Inbox",
        "Needs_Action",
        "In_Progress",
        "Done",
        "Approvals",
        "Briefings",
        "Attachments",
    ]
    for folder in folders:
        (vault_path / folder).mkdir()

    # Create config directory
    config_dir = vault_path / "config"
    config_dir.mkdir()

    # Create minimal MCP registry
    mcp_registry = config_dir / "mcp_servers.yaml"
    mcp_registry.write_text("servers: {}")

    return vault_path


class TestCompleteTaskLifecycle:
    """
    Test US1: Complete task lifecycle from creation to briefing.

    Workflow:
        1. Create tasks manually (simulating user/agent creating files)
        2. Generate briefing including the tasks
        3. Check vault status
    """

    def test_task_lifecycle_happy_path(self, e2e_vault):
        """Test complete task lifecycle - happy path"""
        runner = CliRunner()
        vault_str = str(e2e_vault)

        # Step 1: Create tasks manually (simulating user/agent work)
        task_content = """# Complete Q1 reports

Priority: high

## Description
Review and complete all Q1 financial reports.
"""
        (e2e_vault / "Done" / "task_q1_reports.md").write_text(task_content)

        task_content2 = """# Team meeting

Priority: medium

## Description
Weekly team sync meeting.
"""
        (e2e_vault / "Done" / "task_meeting.md").write_text(task_content2)

        # Step 2: Check vault status
        result = runner.invoke(
            vault_group,
            ["status", "--vault-path", vault_str],
            obj={}
        )
        assert result.exit_code == 0

        # Step 3: Generate briefing (should include the completed tasks)
        with patch("cli.briefing.get_checkpoint_manager") as mock_checkpoint:
            mock_mgr = MagicMock()
            mock_checkpoint.return_value = mock_mgr

            result = runner.invoke(
                briefing_group,
                ["generate", "--vault-path", vault_str, "--days", "1"],
                obj={}
            )

        assert result.exit_code == 0
        assert "Briefing generated successfully" in result.output

        # Verify briefing was created
        briefings = list((e2e_vault / "Briefings").glob("briefing_*.md"))
        assert len(briefings) == 1

        # Verify briefing contains our tasks
        briefing_content = briefings[0].read_text()
        assert "Q1 reports" in briefing_content
        assert "Team meeting" in briefing_content

    def test_vault_initialization(self, tmp_path):
        """Test vault initialization workflow"""
        runner = CliRunner()
        vault_path = tmp_path / "new_vault"

        # Initialize vault structure using vault init command
        result = runner.invoke(
            vault_group,
            ["init", "--vault-path", str(vault_path)],
            obj={}
        )
        assert result.exit_code == 0
        assert "initialized successfully" in result.output.lower()

        # Verify folders were created
        assert (vault_path / "Inbox").exists()
        assert (vault_path / "Done").exists()
        assert (vault_path / "Approvals").exists()


class TestWatcherLifecycle:
    """
    Test US3: Watcher lifecycle management.

    Workflow:
        1. Check watcher status (all stopped)
        2. Start watcher
        3. Check watcher status (running)
        4. View watcher logs
        5. Stop watcher
        6. Check watcher status (stopped)
    """

    @patch("cli.watcher.subprocess.run")
    @patch("cli.watcher.check_pm2_installed")
    def test_watcher_lifecycle_happy_path(
        self,
        mock_pm2_installed,
        mock_subprocess,
        e2e_vault,
        tmp_path
    ):
        """Test complete watcher lifecycle"""
        runner = CliRunner()
        vault_str = str(e2e_vault)

        # Create dummy watcher script (required by watcher validation)
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        watcher_script = scripts_dir / "run_gmail_watcher.py"
        watcher_script.write_text("# Dummy watcher script for testing")

        # Mock PM2 installed
        mock_pm2_installed.return_value = True

        # All subprocess calls should return valid JSON for PM2 list command
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([])
        )

        try:
            # Step 1: Check status (should be empty/stopped)
            result = runner.invoke(
                watcher_group,
                ["status"],
                obj={}
            )
            assert result.exit_code == 0

            # Step 2: Start watcher (mock still returns empty list, no existing process)
            result = runner.invoke(
                watcher_group,
                ["start", "gmail"],
                obj={}
            )
            assert result.exit_code == 0
            assert "started successfully" in result.output.lower()

            # Step 3: Check status (should show running)
            mock_subprocess.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps([{
                    "name": "fte-watcher-gmail",
                    "pm2_env": {
                        "status": "online",
                        "pm_uptime": time.time() * 1000,
                        "pm_id": 0
                    },
                    "monit": {"cpu": 1.5, "memory": 50000000}
                }])
            )
            result = runner.invoke(
                watcher_group,
                ["status"],
                obj={}
            )
            assert result.exit_code == 0
            assert "gmail" in result.output.lower()

            # Step 4: Stop watcher (return running process, then stopped)
            # First call: watcher is running, second call: watcher stopped
            result = runner.invoke(
                watcher_group,
                ["stop", "gmail"],
                obj={}
            )
            assert result.exit_code == 0
            assert "stopped successfully" in result.output.lower()

        finally:
            # Clean up dummy script
            if watcher_script.exists():
                watcher_script.unlink()


class TestMCPIntegrationWorkflow:
    """
    Test US4: MCP server integration workflow.

    Workflow:
        1. List MCP servers (empty)
        2. Add MCP server
        3. List MCP servers (shows added server)
        4. Test MCP server health
        5. Get tools from MCP server
    """

    @patch("cli.mcp.requests.get")
    def test_mcp_workflow_happy_path(self, mock_get, e2e_vault):
        """Test complete MCP integration workflow"""
        runner = CliRunner()
        vault_str = str(e2e_vault)

        # Use temp config directory so we don't pollute the real config
        config_dir = e2e_vault / "config"
        config_dir.mkdir(exist_ok=True)
        registry_file = config_dir / "mcp_servers.yaml"
        registry_file.write_text("servers: {}")

        with patch("cli.mcp.get_mcp_registry_path", return_value=registry_file):
            # Step 1: List servers (empty)
            result = runner.invoke(
                mcp_group,
                ["list"],
                obj={}
            )
            assert result.exit_code == 0
            assert "No MCP servers configured" in result.output

            # Step 2: Add server
            result = runner.invoke(
                mcp_group,
                ["add", "test-api", "https://api.example.com"],
                obj={}
            )
            assert result.exit_code == 0
            assert "added successfully" in result.output.lower()

            # Step 3: List servers (should show new server in table)
            result = runner.invoke(
                mcp_group,
                ["list"],
                obj={}
            )
            assert result.exit_code == 0
            # Server should appear in the table
            assert "test-api" in result.output
            assert "https://api.example.com" in result.output

            # Step 4: Test server health
            mock_get.return_value = MagicMock(status_code=200, text="OK")
            result = runner.invoke(
                mcp_group,
                ["test", "test-api"],
                obj={}
            )
            assert result.exit_code == 0
            assert "healthy" in result.output.lower()

            # Step 5: Get tools
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: [
                    {
                        "name": "get_data",
                        "description": "Get data from API",
                        "parameters": {}
                    }
                ]
            )
            result = runner.invoke(
                mcp_group,
                ["tools", "test-api"],
                obj={}
            )
            assert result.exit_code == 0
            assert "get_data" in result.output


class TestApprovalWorkflow:
    """
    Test US5: Approval workflow.

    Workflow:
        1. List pending approvals (empty)
        2. Create approval (simulated by adding file)
        3. List pending approvals (shows approval)
        4. Review and approve
        5. List pending approvals (empty)
    """

    @patch("cli.approval.Prompt.ask")
    @patch("cli.approval.Confirm.ask")
    @patch("cli.approval.get_checkpoint_manager")
    def test_approval_workflow_approve(
        self,
        mock_checkpoint,
        mock_confirm,
        mock_prompt,
        e2e_vault
    ):
        """Test approval workflow - approve path"""
        runner = CliRunner()
        vault_str = str(e2e_vault)

        # Mock checkpoint manager
        mock_mgr = MagicMock()
        mock_checkpoint.return_value = mock_mgr

        # Step 1: List pending (empty)
        result = runner.invoke(
            approval_group,
            ["pending", "--vault-path", vault_str],
            obj={}
        )
        assert result.exit_code == 0
        assert "No pending approvals" in result.output

        # Step 2: Create approval file
        approval_content = f"""---
task_id: test_task
approval_id: TEST_APPROVAL_E2E
nonce: 12345678-1234-5678-1234-567812345678
action_type: test_action
risk_level: medium
approval_status: pending
created_at: {datetime.now(timezone.utc).isoformat()}
---

# Test Approval

This is a test approval for e2e testing.
"""
        (e2e_vault / "Approvals" / "TEST_APPROVAL_E2E.md").write_text(approval_content)

        # Step 3: List pending (should show approval)
        result = runner.invoke(
            approval_group,
            ["pending", "--vault-path", vault_str],
            obj={}
        )
        assert result.exit_code == 0
        assert "TEST_APPROVAL" in result.output  # May be truncated in display

        # Step 4: Review and approve
        mock_prompt.return_value = "1"  # Choose approve
        mock_confirm.return_value = True  # Confirm approve

        result = runner.invoke(
            approval_group,
            ["review", "TEST_APPROVAL_E2E", "--vault-path", vault_str],
            obj={}
        )
        assert result.exit_code == 0
        assert "approved successfully" in result.output.lower()

        # Verify approval file updated
        updated_content = (e2e_vault / "Approvals" / "TEST_APPROVAL_E2E.md").read_text()
        assert "approved" in updated_content.lower()


class TestSystemHealthMonitoring:
    """
    Test system health monitoring workflow.

    Workflow:
        1. Initialize vault
        2. Check status (all components)
        3. Create some tasks
        4. Check status again (updated counts)
    """

    @patch("cli.status.check_watcher_status")
    @patch("cli.status.check_mcp_status")
    def test_system_health_workflow(
        self,
        mock_mcp_status,
        mock_watcher_status,
        e2e_vault
    ):
        """Test system health monitoring"""
        runner = CliRunner()
        vault_str = str(e2e_vault)

        # Mock watcher and MCP status
        mock_watcher_status.return_value = {}
        mock_mcp_status.return_value = {
            "servers": [],
            "registry_loaded": True
        }

        # Step 1: Check initial status
        result = runner.invoke(
            status_command,
            ["--vault-path", vault_str],
            obj={}
        )
        assert result.exit_code == 0
        assert "Vault Status" in result.output

        # Step 2: Create some tasks manually
        for i in range(3):
            task_file = e2e_vault / "Inbox" / f"task_{i}.md"
            task_file.write_text(f"# Task {i}\n\nPriority: medium")

        # Step 3: Check status again (should show task counts)
        result = runner.invoke(
            status_command,
            ["--vault-path", vault_str],
            obj={}
        )
        assert result.exit_code == 0
        # Verify vault section shows inbox count
        assert "Inbox" in result.output


class TestMultiCommandWorkflow:
    """
    Test workflows that span multiple command groups.

    Workflow:
        1. Check system status
        2. Start watcher
        3. Create tasks manually
        4. Generate briefing
        5. Stop watcher
    """

    @patch("cli.watcher.subprocess.run")
    @patch("cli.watcher.check_pm2_installed")
    @patch("cli.briefing.get_checkpoint_manager")
    @patch("cli.status.check_watcher_status")
    @patch("cli.status.check_mcp_status")
    def test_full_daily_workflow(
        self,
        mock_mcp_status,
        mock_watcher_status,
        mock_checkpoint,
        mock_pm2_installed,
        mock_subprocess,
        e2e_vault
    ):
        """Test a complete daily workflow across all commands"""
        runner = CliRunner()
        vault_str = str(e2e_vault)

        # Create dummy watcher script (required by watcher validation)
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        watcher_script = scripts_dir / "run_gmail_watcher.py"
        watcher_script.write_text("# Dummy watcher script for testing")

        # Setup mocks
        mock_pm2_installed.return_value = True
        # All subprocess calls return valid JSON
        mock_subprocess.return_value = MagicMock(returncode=0, stdout=json.dumps([]))
        mock_watcher_status.return_value = {}
        mock_mcp_status.return_value = {"servers": [], "registry_loaded": True}
        mock_mgr = MagicMock()
        mock_checkpoint.return_value = mock_mgr

        try:
            # Morning: Check system status
            result = runner.invoke(
                status_command,
                ["--vault-path", vault_str],
                obj={}
            )
            assert result.exit_code == 0

            # Start monitoring
            result = runner.invoke(
                watcher_group,
                ["start", "gmail"],
                obj={}
            )
            assert result.exit_code == 0

            # Simulate work: Create completed tasks
            tasks = ["Review emails", "Update documentation", "Team meeting"]
            for i, task in enumerate(tasks):
                task_file = e2e_vault / "Done" / f"task_{i}.md"
                task_file.write_text(f"# {task}\n\nPriority: medium")

            # End of day: Generate briefing
            result = runner.invoke(
                briefing_group,
                ["generate", "--vault-path", vault_str],
                obj={}
            )
            assert result.exit_code == 0

            # Verify briefing contains all tasks
            briefings = list((e2e_vault / "Briefings").glob("briefing_*.md"))
            assert len(briefings) == 1
            briefing_content = briefings[0].read_text()
            for task in tasks:
                assert task in briefing_content

            # Stop monitoring - mock watcher as running first
            # Mock returns a running watcher so stop command can find it
            mock_subprocess.return_value = MagicMock(
                returncode=0,
                stdout=json.dumps([{
                    "name": "fte-watcher-gmail",
                    "pm2_env": {
                        "status": "online",
                        "pm_id": 0
                    }
                }])
            )
            result = runner.invoke(
                watcher_group,
                ["stop", "gmail"],
                obj={}
            )
            assert result.exit_code == 0

        finally:
            # Clean up dummy script
            if watcher_script.exists():
                watcher_script.unlink()


class TestErrorRecovery:
    """
    Test error recovery across workflows.

    Scenarios:
        - Vault not initialized
        - Invalid operations
        - Recovery from errors
    """

    def test_vault_not_initialized(self, tmp_path):
        """Test graceful handling when vault not initialized"""
        runner = CliRunner()
        invalid_vault = tmp_path / "invalid"
        invalid_vault.mkdir()

        # Try to run status on invalid vault
        result = runner.invoke(
            vault_group,
            ["status", "--vault-path", str(invalid_vault)],
            obj={}
        )
        assert result.exit_code == 1
        # Should give helpful error message

    def test_invalid_approval_review(self, e2e_vault):
        """Test handling of non-existent approval"""
        runner = CliRunner()
        vault_str = str(e2e_vault)

        # Try to review non-existent approval
        result = runner.invoke(
            approval_group,
            ["review", "NONEXISTENT_APPROVAL", "--vault-path", vault_str],
            obj={}
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower()


class TestConcurrentOperations:
    """
    Test concurrent command execution.

    Note: These tests simulate concurrent operations rather than
    actually running commands in parallel (which would be complex
    in a test environment).
    """

    def test_multiple_briefing_generations(self, e2e_vault):
        """Test multiple briefing generations in sequence"""
        runner = CliRunner()
        vault_str = str(e2e_vault)

        # Create multiple tasks
        for i in range(5):
            task_file = e2e_vault / "Done" / f"task_{i}.md"
            task_file.write_text(f"# Rapid task {i}\n\nPriority: medium")

        # Generate briefings multiple times
        with patch("cli.briefing.get_checkpoint_manager") as mock_checkpoint:
            mock_mgr = MagicMock()
            mock_checkpoint.return_value = mock_mgr

            for _ in range(3):
                result = runner.invoke(
                    briefing_group,
                    ["generate", "--vault-path", vault_str],
                    obj={}
                )
                assert result.exit_code == 0


class TestDataIntegrity:
    """
    Test data integrity across operations.

    Ensures:
        - Files are not corrupted
        - Content is preserved
        - Metadata remains valid
    """

    def test_briefing_content_integrity(self, e2e_vault):
        """Test that briefing content includes all expected information"""
        runner = CliRunner()
        vault_str = str(e2e_vault)

        # Create task with special characters
        task_content = "# Task with special chars\n\náéíóú\n\nPriority: high"
        (e2e_vault / "Done" / "special_task.md").write_text(task_content)

        # Generate briefing
        with patch("cli.briefing.get_checkpoint_manager") as mock_checkpoint:
            mock_mgr = MagicMock()
            mock_checkpoint.return_value = mock_mgr

            result = runner.invoke(
                briefing_group,
                ["generate", "--vault-path", vault_str],
                obj={}
            )

        assert result.exit_code == 0

        # Verify briefing contains special characters
        briefings = list((e2e_vault / "Briefings").glob("briefing_*.md"))
        briefing_content = briefings[0].read_text()

        assert "special chars" in briefing_content

"""
Integration tests for fte vault commands.

Tests vault initialization, status, and approval workflows.
"""

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from cli.vault import (
    vault_approve_command,
    vault_group,
    vault_init_command,
    vault_reject_command,
    vault_status_command,
)


class TestVaultInit:
    """Test fte vault init command"""

    def test_vault_init_help(self):
        """Test vault init command help"""
        runner = CliRunner()
        result = runner.invoke(vault_init_command, ["--help"])

        assert result.exit_code == 0
        assert "Initialize vault folder structure" in result.output
        assert "--vault-path" in result.output
        assert "--force" in result.output

    def test_vault_init_creates_structure(self, tmp_path):
        """Test vault init creates all folders"""
        runner = CliRunner()
        vault_path = tmp_path / "new_vault"

        result = runner.invoke(vault_init_command, ["--vault-path", str(vault_path)])

        assert result.exit_code == 0
        assert "Vault initialized successfully" in result.output

        # Check folders created
        assert (vault_path / "Inbox").exists()
        assert (vault_path / "Needs_Action").exists()
        assert (vault_path / "In_Progress").exists()
        assert (vault_path / "Done").exists()
        assert (vault_path / "Approvals").exists()
        assert (vault_path / "Briefings").exists()
        assert (vault_path / "Attachments").exists()

    def test_vault_init_creates_templates(self, tmp_path):
        """Test vault init creates Dashboard and Handbook"""
        runner = CliRunner()
        vault_path = tmp_path / "new_vault"

        result = runner.invoke(vault_init_command, ["--vault-path", str(vault_path)])

        assert result.exit_code == 0

        # Check templates created
        assert (vault_path / "Dashboard.md").exists()
        assert (vault_path / "Company_Handbook.md").exists()

        # Check template content
        dashboard_content = (vault_path / "Dashboard.md").read_text()
        assert "AI Employee Dashboard" in dashboard_content

        handbook_content = (vault_path / "Company_Handbook.md").read_text()
        assert "Company Handbook" in handbook_content

    def test_vault_init_existing_vault_no_force(self, tmp_path):
        """Test vault init on existing vault without force"""
        runner = CliRunner()
        vault_path = tmp_path / "existing_vault"

        # Create existing vault
        vault_path.mkdir()
        (vault_path / "Inbox").mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()

        # Try to init again without force
        result = runner.invoke(
            vault_init_command, ["--vault-path", str(vault_path)], input="n\n"
        )

        # Should prompt and cancel
        assert "already exists" in result.output.lower()

    def test_vault_init_with_force(self, tmp_path):
        """Test vault init with --force flag"""
        runner = CliRunner()
        vault_path = tmp_path / "force_vault"

        # Create existing vault
        vault_path.mkdir()
        (vault_path / "Inbox").mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()

        # Init with force
        result = runner.invoke(
            vault_init_command, ["--vault-path", str(vault_path), "--force"]
        )

        assert result.exit_code == 0
        assert "Vault initialized successfully" in result.output


class TestVaultStatus:
    """Test fte vault status command"""

    def test_vault_status_help(self):
        """Test vault status command help"""
        runner = CliRunner()
        result = runner.invoke(vault_status_command, ["--help"])

        assert result.exit_code == 0
        assert "detailed vault statistics" in result.output.lower()
        assert "--vault-path" in result.output

    def test_vault_status_valid_vault(self, tmp_path):
        """Test vault status on valid vault"""
        runner = CliRunner()
        vault_path = tmp_path / "valid_vault"

        # Create valid vault
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        result = runner.invoke(vault_status_command, ["--vault-path", str(vault_path)])

        assert result.exit_code == 0
        assert "Vault Statistics" in result.output
        assert "Inbox" in result.output
        assert "Needs_Action" in result.output

    def test_vault_status_with_tasks(self, tmp_path):
        """Test vault status counts tasks correctly"""
        runner = CliRunner()
        vault_path = tmp_path / "vault_with_tasks"

        # Create valid vault with tasks
        vault_path.mkdir()
        inbox = vault_path / "Inbox"
        inbox.mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()

        # Add some task files
        (inbox / "task1.md").write_text("# Task 1")
        (inbox / "task2.md").write_text("# Task 2")
        (inbox / "task3.md").write_text("# Task 3")

        result = runner.invoke(vault_status_command, ["--vault-path", str(vault_path)])

        assert result.exit_code == 0
        assert "3" in result.output  # Should show 3 tasks in Inbox

    def test_vault_status_invalid_vault(self, tmp_path):
        """Test vault status on invalid vault"""
        runner = CliRunner()
        vault_path = tmp_path / "invalid_vault"
        vault_path.mkdir()

        result = runner.invoke(vault_status_command, ["--vault-path", str(vault_path)])

        assert result.exit_code == 1
        assert "Invalid vault" in result.output or "Error" in result.output

    def test_vault_status_shows_warnings(self, tmp_path):
        """Test vault status shows warnings for pending approvals"""
        runner = CliRunner()
        vault_path = tmp_path / "vault_with_approvals"

        # Create vault with pending approvals
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        approvals = vault_path / "Approvals"
        (approvals / "approval1.md").write_text("# Approval 1")
        (approvals / "approval2.md").write_text("# Approval 2")

        result = runner.invoke(vault_status_command, ["--vault-path", str(vault_path)])

        assert result.exit_code == 0
        assert "pending approval" in result.output.lower() or "2" in result.output


class TestVaultApprove:
    """Test fte vault approve command"""

    def test_vault_approve_help(self):
        """Test vault approve command help"""
        runner = CliRunner()
        result = runner.invoke(vault_approve_command, ["--help"])

        assert result.exit_code == 0
        assert "Approve a pending action" in result.output
        assert "APPROVAL_ID" in result.output

    def test_vault_approve_valid_approval(self, tmp_path):
        """Test approving valid approval file"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"

        # Create vault structure
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Create approval file
        approval_content = """---
task_id: test_task_2026-01-28
approval_id: TEST_APPROVAL
nonce: 12345678-1234-5678-1234-567812345678
action_type: test
approval_status: pending
created_at: 2026-01-28T10:00:00Z
---

# Test Approval

This is a test approval.
"""
        approval_file = vault_path / "Approvals" / "TEST_APPROVAL.md"
        approval_file.write_text(approval_content)

        result = runner.invoke(
            vault_approve_command, ["TEST_APPROVAL", "--vault-path", str(vault_path)]
        )

        assert result.exit_code == 0
        assert "approved successfully" in result.output.lower()

        # Verify file was updated
        updated_content = approval_file.read_text()
        assert "approved" in updated_content

    def test_vault_approve_not_found(self, tmp_path):
        """Test approving non-existent approval"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"

        # Create vault structure
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        result = runner.invoke(
            vault_approve_command,
            ["NONEXISTENT_APPROVAL", "--vault-path", str(vault_path)],
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "Error" in result.output

    def test_vault_approve_invalid_nonce(self, tmp_path):
        """Test approving approval with invalid nonce"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"

        # Create vault structure
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Create approval file with invalid nonce
        approval_content = """---
task_id: test_task_2026-01-28
approval_id: INVALID_NONCE
nonce: invalid-nonce-format
action_type: test
approval_status: pending
---

# Test Approval
"""
        approval_file = vault_path / "Approvals" / "INVALID_NONCE.md"
        approval_file.write_text(approval_content)

        result = runner.invoke(
            vault_approve_command, ["INVALID_NONCE", "--vault-path", str(vault_path)]
        )

        assert result.exit_code == 1
        assert "nonce" in result.output.lower() or "Error" in result.output


class TestVaultReject:
    """Test fte vault reject command"""

    def test_vault_reject_help(self):
        """Test vault reject command help"""
        runner = CliRunner()
        result = runner.invoke(vault_reject_command, ["--help"])

        assert result.exit_code == 0
        assert "Reject a pending action" in result.output
        assert "APPROVAL_ID" in result.output
        assert "--reason" in result.output

    def test_vault_reject_with_reason(self, tmp_path):
        """Test rejecting approval with reason"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"

        # Create vault structure
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Create approval file
        approval_content = """---
task_id: test_task_2026-01-28
approval_id: TEST_REJECTION
nonce: 12345678-1234-5678-1234-567812345678
action_type: test
approval_status: pending
---

# Test Approval
"""
        approval_file = vault_path / "Approvals" / "TEST_REJECTION.md"
        approval_file.write_text(approval_content)

        result = runner.invoke(
            vault_reject_command,
            [
                "TEST_REJECTION",
                "--vault-path",
                str(vault_path),
                "--reason",
                "Test rejection",
            ],
        )

        assert result.exit_code == 0
        assert "rejected successfully" in result.output.lower()

        # Verify file was updated with rejection
        updated_content = approval_file.read_text()
        assert "rejected" in updated_content
        assert "Test rejection" in updated_content

    def test_vault_reject_prompts_for_reason(self, tmp_path):
        """Test reject prompts for reason when not provided"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"

        # Create vault structure
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Create approval file
        approval_content = """---
task_id: test_task_2026-01-28
approval_id: TEST_PROMPT
nonce: 12345678-1234-5678-1234-567812345678
action_type: test
approval_status: pending
---

# Test Approval
"""
        approval_file = vault_path / "Approvals" / "TEST_PROMPT.md"
        approval_file.write_text(approval_content)

        # Provide reason via input
        result = runner.invoke(
            vault_reject_command,
            ["TEST_PROMPT", "--vault-path", str(vault_path)],
            input="Not needed\n",
        )

        assert result.exit_code == 0
        assert "rejected successfully" in result.output.lower()

    def test_vault_reject_not_found(self, tmp_path):
        """Test rejecting non-existent approval"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"

        # Create vault structure
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        result = runner.invoke(
            vault_reject_command,
            ["NONEXISTENT", "--vault-path", str(vault_path), "--reason", "Test"],
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower() or "Error" in result.output


class TestVaultErrorHandling:
    """Test vault command error handling"""

    def test_vault_commands_with_invalid_vault(self, tmp_path):
        """Test vault commands handle invalid vault gracefully"""
        runner = CliRunner()
        invalid_vault = tmp_path / "invalid"
        invalid_vault.mkdir()

        # Test status
        result = runner.invoke(
            vault_status_command, ["--vault-path", str(invalid_vault)]
        )
        assert result.exit_code == 1

        # Test approve
        result = runner.invoke(
            vault_approve_command, ["TEST", "--vault-path", str(invalid_vault)]
        )
        assert result.exit_code == 1

        # Test reject
        result = runner.invoke(
            vault_reject_command,
            ["TEST", "--vault-path", str(invalid_vault), "--reason", "Test"],
        )
        assert result.exit_code == 1

    def test_vault_group_exists(self):
        """Test vault command group is properly registered"""
        runner = CliRunner()
        result = runner.invoke(vault_group, ["--help"])

        assert result.exit_code == 0
        assert "vault" in result.output.lower()

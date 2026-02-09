"""
Integration tests for fte approval commands.

Tests approval workflow including pending list and interactive review.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.approval import (
    approval_group,
    approval_pending_command,
    approval_review_command,
    scan_pending_approvals,
)


class TestScanPendingApprovals:
    """Test approval file scanning"""

    def test_scan_empty_approvals_folder(self, tmp_path):
        """Test scanning empty Approvals folder"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        (vault_path / "Approvals").mkdir()

        approvals = scan_pending_approvals(vault_path)

        assert approvals == []

    def test_scan_with_pending_approvals(self, tmp_path):
        """Test scanning with pending approvals"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        approvals_dir = vault_path / "Approvals"
        approvals_dir.mkdir()

        # Create pending approval
        approval_content = """---
task_id: test_task
approval_id: TEST_001
nonce: 12345678-1234-5678-1234-567812345678
action_type: payment
risk_level: high
approval_status: pending
created_at: 2026-01-29T10:00:00Z
---

# Test Approval

This is a test approval.
"""
        (approvals_dir / "TEST_001.md").write_text(approval_content)

        approvals = scan_pending_approvals(vault_path)

        assert len(approvals) == 1
        assert approvals[0]["approval_id"] == "TEST_001"
        assert approvals[0]["action_type"] == "payment"
        assert approvals[0]["risk_level"] == "high"

    def test_scan_filters_non_pending(self, tmp_path):
        """Test scanning filters out non-pending approvals"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        approvals_dir = vault_path / "Approvals"
        approvals_dir.mkdir()

        # Create approved approval
        approval_content = """---
approval_id: TEST_002
approval_status: approved
---

# Approved
"""
        (approvals_dir / "TEST_002.md").write_text(approval_content)

        approvals = scan_pending_approvals(vault_path)

        assert len(approvals) == 0

    def test_scan_filters_expired(self, tmp_path):
        """Test scanning filters out expired approvals"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        approvals_dir = vault_path / "Approvals"
        approvals_dir.mkdir()

        # Create expired approval
        expired_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        approval_content = f"""---
approval_id: TEST_003
approval_status: pending
expires_at: {expired_time}
---

# Expired
"""
        (approvals_dir / "TEST_003.md").write_text(approval_content)

        approvals = scan_pending_approvals(vault_path)

        assert len(approvals) == 0

    def test_scan_includes_non_expired(self, tmp_path):
        """Test scanning includes non-expired approvals"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        approvals_dir = vault_path / "Approvals"
        approvals_dir.mkdir()

        # Create non-expired approval
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        approval_content = f"""---
approval_id: TEST_004
approval_status: pending
expires_at: {future_time}
action_type: test
risk_level: low
created_at: 2026-01-29T10:00:00Z
nonce: 12345678-1234-5678-1234-567812345678
task_id: test_task
---

# Non-expired
"""
        (approvals_dir / "TEST_004.md").write_text(approval_content)

        approvals = scan_pending_approvals(vault_path)

        assert len(approvals) == 1
        assert approvals[0]["approval_id"] == "TEST_004"


class TestApprovalPending:
    """Test fte approval pending command"""

    def test_approval_pending_help(self):
        """Test approval pending command help"""
        runner = CliRunner()
        result = runner.invoke(approval_pending_command, ["--help"])

        assert result.exit_code == 0
        assert "List pending approvals" in result.output
        assert "--vault-path" in result.output

    def test_approval_pending_no_approvals(self, tmp_path):
        """Test pending command with no approvals"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        result = runner.invoke(
            approval_pending_command, ["--vault-path", str(vault_path)]
        )

        assert result.exit_code == 0
        assert "No pending approvals" in result.output

    def test_approval_pending_with_approvals(self, tmp_path):
        """Test pending command with approvals"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Create pending approval
        approval_content = """---
task_id: test_task
approval_id: PAYMENT_001
nonce: 12345678-1234-5678-1234-567812345678
action_type: payment
risk_level: high
approval_status: pending
created_at: 2026-01-29T10:00:00Z
---

# Payment Approval

Send $1000 to vendor.
"""
        (vault_path / "Approvals" / "PAYMENT_001.md").write_text(approval_content)

        result = runner.invoke(
            approval_pending_command, ["--vault-path", str(vault_path)]
        )

        assert result.exit_code == 0
        assert "PAYMENT_001" in result.output
        assert "payment" in result.output
        assert "HIGH" in result.output

    def test_approval_pending_invalid_vault(self, tmp_path):
        """Test pending command with invalid vault"""
        runner = CliRunner()
        invalid_vault = tmp_path / "invalid"
        invalid_vault.mkdir()

        result = runner.invoke(
            approval_pending_command, ["--vault-path", str(invalid_vault)]
        )

        assert result.exit_code == 1


class TestApprovalReview:
    """Test fte approval review command"""

    def test_approval_review_help(self):
        """Test approval review command help"""
        runner = CliRunner()
        result = runner.invoke(approval_review_command, ["--help"])

        assert result.exit_code == 0
        assert "Review and decide on approval" in result.output
        assert "APPROVAL_ID" in result.output
        assert "--vault-path" in result.output

    @patch("cli.approval.get_checkpoint_manager")
    @patch("cli.approval.Prompt.ask")
    @patch("cli.approval.Confirm.ask")
    def test_approval_review_approve(
        self, mock_confirm, mock_prompt, mock_checkpoint, tmp_path
    ):
        """Test approving an approval"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Create pending approval
        approval_content = """---
task_id: test_task
approval_id: TEST_APPROVE
nonce: 12345678-1234-5678-1234-567812345678
action_type: test
risk_level: low
approval_status: pending
created_at: 2026-01-29T10:00:00Z
---

# Test Approval

This is a test.
"""
        approval_file = vault_path / "Approvals" / "TEST_APPROVE.md"
        approval_file.write_text(approval_content)

        # Mock user selecting approve
        mock_prompt.return_value = "1"  # Choose approve
        mock_confirm.return_value = True  # Confirm approve

        # Mock checkpoint manager
        mock_mgr = MagicMock()
        mock_checkpoint.return_value = mock_mgr

        result = runner.invoke(
            approval_review_command, ["TEST_APPROVE", "--vault-path", str(vault_path)]
        )

        assert result.exit_code == 0
        assert "approved successfully" in result.output.lower()

        # Verify file was updated
        updated_content = approval_file.read_text()
        assert "approved" in updated_content.lower()

    @patch("cli.approval.get_checkpoint_manager")
    @patch("cli.approval.Prompt.ask")
    @patch("cli.approval.Confirm.ask")
    def test_approval_review_reject(
        self, mock_confirm, mock_prompt, mock_checkpoint, tmp_path
    ):
        """Test rejecting an approval"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Create pending approval
        approval_content = """---
task_id: test_task
approval_id: TEST_REJECT
nonce: 12345678-1234-5678-1234-567812345678
action_type: test
risk_level: low
approval_status: pending
created_at: 2026-01-29T10:00:00Z
---

# Test Approval

This is a test.
"""
        approval_file = vault_path / "Approvals" / "TEST_REJECT.md"
        approval_file.write_text(approval_content)

        # Mock user selecting reject
        mock_prompt.side_effect = ["2", "Not needed"]  # Choose reject, then reason
        mock_confirm.return_value = True  # Confirm reject

        # Mock checkpoint manager
        mock_mgr = MagicMock()
        mock_checkpoint.return_value = mock_mgr

        result = runner.invoke(
            approval_review_command, ["TEST_REJECT", "--vault-path", str(vault_path)]
        )

        assert result.exit_code == 0
        assert "rejected successfully" in result.output.lower()

        # Verify file was updated
        updated_content = approval_file.read_text()
        assert "rejected" in updated_content.lower()
        assert "Not needed" in updated_content

    @patch("cli.approval.Prompt.ask")
    def test_approval_review_skip(self, mock_prompt, tmp_path):
        """Test skipping an approval"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Create pending approval
        approval_content = """---
task_id: test_task
approval_id: TEST_SKIP
nonce: 12345678-1234-5678-1234-567812345678
action_type: test
risk_level: low
approval_status: pending
created_at: 2026-01-29T10:00:00Z
---

# Test Approval

This is a test.
"""
        approval_file = vault_path / "Approvals" / "TEST_SKIP.md"
        approval_file.write_text(approval_content)

        # Mock user selecting skip
        mock_prompt.return_value = "3"  # Choose skip

        result = runner.invoke(
            approval_review_command, ["TEST_SKIP", "--vault-path", str(vault_path)]
        )

        assert result.exit_code == 0
        assert "skipped" in result.output.lower()

        # Verify file was NOT updated
        updated_content = approval_file.read_text()
        assert "pending" in updated_content

    def test_approval_review_not_found(self, tmp_path):
        """Test reviewing non-existent approval"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        result = runner.invoke(
            approval_review_command, ["NONEXISTENT", "--vault-path", str(vault_path)]
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_approval_review_already_processed(self, tmp_path):
        """Test reviewing already processed approval"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Create already approved approval
        approval_content = """---
task_id: test_task
approval_id: TEST_PROCESSED
nonce: 12345678-1234-5678-1234-567812345678
action_type: test
risk_level: low
approval_status: approved
created_at: 2026-01-29T10:00:00Z
reviewed_at: 2026-01-29T11:00:00Z
---

# Test Approval

Already processed.
"""
        (vault_path / "Approvals" / "TEST_PROCESSED.md").write_text(approval_content)

        result = runner.invoke(
            approval_review_command, ["TEST_PROCESSED", "--vault-path", str(vault_path)]
        )

        assert result.exit_code == 0
        assert "already processed" in result.output.lower()

    def test_approval_review_expired(self, tmp_path):
        """Test reviewing expired approval"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Create expired approval
        expired_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        approval_content = f"""---
task_id: test_task
approval_id: TEST_EXPIRED
nonce: 12345678-1234-5678-1234-567812345678
action_type: test
risk_level: low
approval_status: pending
created_at: 2026-01-29T10:00:00Z
expires_at: {expired_time}
---

# Test Approval

This is expired.
"""
        (vault_path / "Approvals" / "TEST_EXPIRED.md").write_text(approval_content)

        result = runner.invoke(
            approval_review_command, ["TEST_EXPIRED", "--vault-path", str(vault_path)]
        )

        assert result.exit_code == 1
        assert "expired" in result.output.lower()

    def test_approval_review_invalid_nonce(self, tmp_path):
        """Test reviewing approval with invalid nonce"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Create approval with invalid nonce
        approval_content = """---
task_id: test_task
approval_id: TEST_INVALID_NONCE
nonce: invalid-nonce
action_type: test
risk_level: low
approval_status: pending
created_at: 2026-01-29T10:00:00Z
---

# Test Approval

Invalid nonce.
"""
        (vault_path / "Approvals" / "TEST_INVALID_NONCE.md").write_text(
            approval_content
        )

        result = runner.invoke(
            approval_review_command,
            ["TEST_INVALID_NONCE", "--vault-path", str(vault_path)],
        )

        assert result.exit_code == 1
        assert "nonce" in result.output.lower()


class TestApprovalGroup:
    """Test approval command group"""

    def test_approval_group_help(self):
        """Test approval group help"""
        runner = CliRunner()
        result = runner.invoke(approval_group, ["--help"])

        assert result.exit_code == 0
        assert "approval" in result.output.lower()
        assert "pending" in result.output
        assert "review" in result.output

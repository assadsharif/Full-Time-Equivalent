"""
Integration tests for fte briefing commands.

Tests briefing generation and viewing commands.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.briefing import (
    briefing_generate_command,
    briefing_group,
    briefing_view_command,
    calculate_date_range,
    check_wkhtmltopdf_installed,
    detect_markdown_viewer,
    find_latest_briefing,
    generate_briefing_content,
    save_briefing,
    scan_done_folder,
)


class TestCalculateDateRange:
    """Test date range calculation"""

    def test_calculate_date_range_default(self):
        """Test default 7 day date range"""
        start_date, end_date = calculate_date_range()

        assert isinstance(start_date, datetime)
        assert isinstance(end_date, datetime)
        assert start_date < end_date
        assert (end_date - start_date).days == 7

    def test_calculate_date_range_custom_days(self):
        """Test custom day range"""
        start_date, end_date = calculate_date_range(days=14)

        assert (end_date - start_date).days == 14

    def test_calculate_date_range_timezone(self):
        """Test dates have timezone"""
        start_date, end_date = calculate_date_range()

        assert start_date.tzinfo is not None
        assert end_date.tzinfo is not None


class TestScanDoneFolder:
    """Test scanning Done folder for completed tasks"""

    def test_scan_empty_done_folder(self, tmp_path):
        """Test scanning empty Done folder"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        (vault_path / "Done").mkdir()

        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)

        tasks = scan_done_folder(vault_path, start_date, end_date)

        assert tasks == []

    def test_scan_missing_done_folder(self, tmp_path):
        """Test scanning when Done folder doesn't exist"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)

        tasks = scan_done_folder(vault_path, start_date, end_date)

        assert tasks == []

    def test_scan_with_completed_tasks(self, tmp_path):
        """Test scanning with completed tasks"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        done_dir = vault_path / "Done"
        done_dir.mkdir()

        # Create task file
        task_content = """# Task 1

This is a completed task.
Priority: high
"""
        task_file = done_dir / "task_001.md"
        task_file.write_text(task_content)

        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc) + timedelta(days=1)

        tasks = scan_done_folder(vault_path, start_date, end_date)

        assert len(tasks) == 1
        assert tasks[0]["title"] == "Task 1"
        assert tasks[0]["priority"] == "high"

    def test_scan_filters_by_date(self, tmp_path):
        """Test scanning filters tasks by date range"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        done_dir = vault_path / "Done"
        done_dir.mkdir()

        # Create old task file
        old_task = done_dir / "old_task.md"
        old_task.write_text("# Old Task")

        # Set modification time to 30 days ago
        old_time = (datetime.now(timezone.utc) - timedelta(days=30)).timestamp()
        import os

        os.utime(old_task, (old_time, old_time))

        # Scan last 7 days
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)

        tasks = scan_done_folder(vault_path, start_date, end_date)

        assert len(tasks) == 0

    def test_scan_extracts_priority(self, tmp_path):
        """Test priority extraction from task content"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        done_dir = vault_path / "Done"
        done_dir.mkdir()

        # Test high priority
        high_task = done_dir / "high.md"
        high_task.write_text("# High Task\nPriority: High")

        # Test low priority
        low_task = done_dir / "low.md"
        low_task.write_text("# Low Task\n[Low]")

        # Test medium priority (default)
        medium_task = done_dir / "medium.md"
        medium_task.write_text("# Medium Task")

        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc) + timedelta(days=1)

        tasks = scan_done_folder(vault_path, start_date, end_date)

        assert len(tasks) == 3
        priorities = {task["title"]: task["priority"] for task in tasks}
        assert priorities["High Task"] == "high"
        assert priorities["Low Task"] == "low"
        assert priorities["Medium Task"] == "medium"


class TestGenerateBriefingContent:
    """Test briefing content generation"""

    def test_generate_content_no_tasks(self):
        """Test briefing with no tasks"""
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)

        content = generate_briefing_content([], start_date, end_date)

        assert "Weekly CEO Briefing" in content
        assert "No tasks were completed" in content
        assert "Total Tasks Completed**: 0" in content

    def test_generate_content_one_task(self):
        """Test briefing with one task"""
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)

        tasks = [
            {
                "title": "Task 1",
                "completed_at": datetime.now(timezone.utc),
                "priority": "high",
                "content": "Test task",
            }
        ]

        content = generate_briefing_content(tasks, start_date, end_date)

        assert "One task was completed" in content
        assert "Task 1" in content
        assert "🔴" in content  # High priority emoji

    def test_generate_content_multiple_tasks(self):
        """Test briefing with multiple tasks"""
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        end_date = datetime.now(timezone.utc)

        tasks = [
            {
                "title": "High Task",
                "completed_at": datetime.now(timezone.utc),
                "priority": "high",
                "content": "Test",
            },
            {
                "title": "Medium Task",
                "completed_at": datetime.now(timezone.utc),
                "priority": "medium",
                "content": "Test",
            },
            {
                "title": "Low Task",
                "completed_at": datetime.now(timezone.utc),
                "priority": "low",
                "content": "Test",
            },
        ]

        content = generate_briefing_content(tasks, start_date, end_date)

        assert "3 tasks were completed" in content
        assert "High Task" in content
        assert "Medium Task" in content
        assert "Low Task" in content
        assert "High Priority**: 1" in content
        assert "Medium Priority**: 1" in content
        assert "Low Priority**: 1" in content


class TestSaveBriefing:
    """Test briefing saving"""

    def test_save_briefing_creates_folder(self, tmp_path):
        """Test saving briefing creates Briefings folder"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        content = "# Test Briefing"
        date = datetime.now(timezone.utc)

        briefing_path = save_briefing(vault_path, content, date)

        assert briefing_path.exists()
        assert briefing_path.parent.name == "Briefings"
        assert briefing_path.read_text() == content

    def test_save_briefing_filename(self, tmp_path):
        """Test briefing filename format"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        content = "# Test Briefing"
        date = datetime(2026, 1, 29, 10, 0, 0, tzinfo=timezone.utc)

        briefing_path = save_briefing(vault_path, content, date)

        assert briefing_path.name == "briefing_2026-01-29.md"


class TestCheckWkhtmltopdfInstalled:
    """Test wkhtmltopdf availability check"""

    @patch("cli.briefing.shutil.which")
    def test_wkhtmltopdf_installed(self, mock_which):
        """Test when wkhtmltopdf is installed"""
        mock_which.return_value = "/usr/bin/wkhtmltopdf"

        result = check_wkhtmltopdf_installed()

        assert result is True
        mock_which.assert_called_once_with("wkhtmltopdf")

    @patch("cli.briefing.shutil.which")
    def test_wkhtmltopdf_not_installed(self, mock_which):
        """Test when wkhtmltopdf is not installed"""
        mock_which.return_value = None

        result = check_wkhtmltopdf_installed()

        assert result is False


class TestFindLatestBriefing:
    """Test finding latest briefing"""

    def test_find_latest_briefing_no_folder(self, tmp_path):
        """Test when Briefings folder doesn't exist"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        result = find_latest_briefing(vault_path)

        assert result is None

    def test_find_latest_briefing_empty_folder(self, tmp_path):
        """Test when Briefings folder is empty"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        (vault_path / "Briefings").mkdir()

        result = find_latest_briefing(vault_path)

        assert result is None

    def test_find_latest_briefing_with_briefings(self, tmp_path):
        """Test finding latest briefing"""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        briefings_dir = vault_path / "Briefings"
        briefings_dir.mkdir()

        # Create multiple briefings
        old_briefing = briefings_dir / "briefing_2026-01-15.md"
        old_briefing.write_text("# Old")

        new_briefing = briefings_dir / "briefing_2026-01-29.md"
        new_briefing.write_text("# New")

        # Set modification times
        import os
        import time

        old_time = time.time() - 86400  # 1 day ago
        new_time = time.time()
        os.utime(old_briefing, (old_time, old_time))
        os.utime(new_briefing, (new_time, new_time))

        result = find_latest_briefing(vault_path)

        assert result == new_briefing


class TestDetectMarkdownViewer:
    """Test markdown viewer detection"""

    @patch("cli.briefing.shutil.which")
    def test_detect_typora(self, mock_which):
        """Test detecting typora"""
        mock_which.side_effect = lambda x: "/usr/bin/typora" if x == "typora" else None

        result = detect_markdown_viewer()

        assert result == "typora"

    @patch("cli.briefing.shutil.which")
    def test_detect_cat_fallback(self, mock_which):
        """Test fallback to cat"""

        def which_side_effect(cmd):
            if cmd == "cat":
                return "/usr/bin/cat"
            return None

        mock_which.side_effect = which_side_effect

        result = detect_markdown_viewer()

        assert result == "cat"

    @patch("cli.briefing.shutil.which")
    def test_detect_no_viewer(self, mock_which):
        """Test when no viewer is available"""
        mock_which.return_value = None

        result = detect_markdown_viewer()

        assert result is None


class TestBriefingGenerate:
    """Test fte briefing generate command"""

    def test_briefing_generate_help(self):
        """Test briefing generate command help"""
        runner = CliRunner()
        result = runner.invoke(briefing_generate_command, ["--help"])

        assert result.exit_code == 0
        assert "Generate CEO briefing" in result.output
        assert "--days" in result.output
        assert "--pdf" in result.output

    @patch("cli.briefing.get_checkpoint_manager")
    def test_briefing_generate_success(self, mock_checkpoint, tmp_path):
        """Test successful briefing generation"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Create completed task
        done_dir = vault_path / "Done"
        task_file = done_dir / "task_001.md"
        task_file.write_text("# Completed Task\nPriority: high")

        # Mock checkpoint manager
        mock_mgr = MagicMock()
        mock_checkpoint.return_value = mock_mgr

        result = runner.invoke(
            briefing_generate_command, ["--vault-path", str(vault_path)]
        )

        assert result.exit_code == 0
        assert "Briefing generated successfully" in result.output

        # Verify briefing was created
        briefings_dir = vault_path / "Briefings"
        assert briefings_dir.exists()
        briefings = list(briefings_dir.glob("briefing_*.md"))
        assert len(briefings) == 1

    @patch("cli.briefing.get_checkpoint_manager")
    def test_briefing_generate_no_tasks(self, mock_checkpoint, tmp_path):
        """Test briefing generation with no completed tasks"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Mock checkpoint manager
        mock_mgr = MagicMock()
        mock_checkpoint.return_value = mock_mgr

        result = runner.invoke(
            briefing_generate_command, ["--vault-path", str(vault_path)]
        )

        assert result.exit_code == 0
        assert "No tasks completed" in result.output
        assert "Briefing generated successfully" in result.output

    @patch("cli.briefing.get_checkpoint_manager")
    def test_briefing_generate_custom_days(self, mock_checkpoint, tmp_path):
        """Test briefing generation with custom days"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Mock checkpoint manager
        mock_mgr = MagicMock()
        mock_checkpoint.return_value = mock_mgr

        result = runner.invoke(
            briefing_generate_command, ["--vault-path", str(vault_path), "--days", "14"]
        )

        assert result.exit_code == 0
        assert "Briefing generated successfully" in result.output

    @patch("cli.briefing.check_wkhtmltopdf_installed")
    @patch("cli.briefing.get_checkpoint_manager")
    def test_briefing_generate_with_pdf_not_installed(
        self, mock_checkpoint, mock_wkhtmltopdf, tmp_path
    ):
        """Test PDF generation when wkhtmltopdf not installed"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Mock checkpoint manager
        mock_mgr = MagicMock()
        mock_checkpoint.return_value = mock_mgr

        # Mock wkhtmltopdf not installed
        mock_wkhtmltopdf.return_value = False

        result = runner.invoke(
            briefing_generate_command, ["--vault-path", str(vault_path), "--pdf"]
        )

        assert result.exit_code == 0
        assert "wkhtmltopdf not installed" in result.output
        assert "Briefing generated successfully" in result.output

    def test_briefing_generate_invalid_vault(self, tmp_path):
        """Test briefing generation with invalid vault"""
        runner = CliRunner()
        invalid_vault = tmp_path / "invalid"
        invalid_vault.mkdir()

        result = runner.invoke(
            briefing_generate_command, ["--vault-path", str(invalid_vault)]
        )

        assert result.exit_code == 1


class TestBriefingView:
    """Test fte briefing view command"""

    def test_briefing_view_help(self):
        """Test briefing view command help"""
        runner = CliRunner()
        result = runner.invoke(briefing_view_command, ["--help"])

        assert result.exit_code == 0
        assert "View most recent briefing" in result.output
        assert "--vault-path" in result.output

    @patch("cli.briefing.detect_markdown_viewer")
    @patch("cli.briefing.subprocess.run")
    def test_briefing_view_success(self, mock_subprocess, mock_viewer, tmp_path):
        """Test successful briefing viewing"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Create briefing
        briefings_dir = vault_path / "Briefings"
        briefings_dir.mkdir()
        briefing_file = briefings_dir / "briefing_2026-01-29.md"
        briefing_file.write_text("# Test Briefing")

        # Mock viewer
        mock_viewer.return_value = "typora"

        result = runner.invoke(briefing_view_command, ["--vault-path", str(vault_path)])

        assert result.exit_code == 0
        assert "Briefing opened in viewer" in result.output

    @patch("cli.briefing.detect_markdown_viewer")
    @patch("cli.briefing.console.print")
    def test_briefing_view_with_cat(self, mock_print, mock_viewer, tmp_path):
        """Test briefing viewing with cat viewer"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()

        # Create briefing
        briefings_dir = vault_path / "Briefings"
        briefings_dir.mkdir()
        briefing_file = briefings_dir / "briefing_2026-01-29.md"
        briefing_file.write_text("# Test Briefing")

        # Mock cat viewer
        mock_viewer.return_value = "cat"

        result = runner.invoke(briefing_view_command, ["--vault-path", str(vault_path)])

        assert result.exit_code == 0
        # Cat displays inline, so no "opened in viewer" message
        mock_print.assert_called()

    def test_briefing_view_not_found(self, tmp_path):
        """Test viewing when no briefing exists"""
        runner = CliRunner()
        vault_path = tmp_path / "vault"
        vault_path.mkdir()
        for folder in ["Inbox", "Needs_Action", "Done", "Approvals"]:
            (vault_path / folder).mkdir()
        (vault_path / "Briefings").mkdir()

        result = runner.invoke(briefing_view_command, ["--vault-path", str(vault_path)])

        assert result.exit_code == 1
        assert "no briefings found" in result.output.lower()

    def test_briefing_view_invalid_vault(self, tmp_path):
        """Test viewing with invalid vault"""
        runner = CliRunner()
        invalid_vault = tmp_path / "invalid"
        invalid_vault.mkdir()

        result = runner.invoke(
            briefing_view_command, ["--vault-path", str(invalid_vault)]
        )

        assert result.exit_code == 1


class TestBriefingGroup:
    """Test briefing command group"""

    def test_briefing_group_help(self):
        """Test briefing group help"""
        runner = CliRunner()
        result = runner.invoke(briefing_group, ["--help"])

        assert result.exit_code == 0
        assert "briefing" in result.output.lower()
        assert "generate" in result.output
        assert "view" in result.output

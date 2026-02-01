"""
Integration tests for fte watcher commands.

Tests watcher lifecycle management including start, stop, status, and logs.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.watcher import (
    check_pm2_installed,
    format_uptime,
    validate_watcher_name,
    watcher_group,
    watcher_logs_command,
    watcher_start_command,
    watcher_status_command,
    watcher_stop_command,
)


class TestWatcherValidation:
    """Test watcher name validation"""

    def test_validate_valid_watcher_names(self):
        """Test validation passes for valid watcher names"""
        from cli.watcher import validate_watcher_name

        # Should not raise for valid names
        validate_watcher_name("gmail")
        validate_watcher_name("whatsapp")
        validate_watcher_name("filesystem")

    def test_validate_invalid_watcher_name(self):
        """Test validation fails for invalid watcher name"""
        from cli.errors import WatcherValidationError
        from cli.watcher import validate_watcher_name

        with pytest.raises(WatcherValidationError):
            validate_watcher_name("invalid")

        with pytest.raises(WatcherValidationError):
            validate_watcher_name("slack")


class TestWatcherStart:
    """Test fte watcher start command"""

    def test_watcher_start_help(self):
        """Test watcher start command help"""
        runner = CliRunner()
        result = runner.invoke(watcher_start_command, ['--help'])

        assert result.exit_code == 0
        assert "Start watcher daemon" in result.output
        assert "NAME" in result.output.upper()

    @patch('cli.watcher.check_pm2_installed')
    @patch('cli.watcher.get_watcher_process')
    @patch('cli.watcher.subprocess.run')
    @patch('cli.watcher.Path.exists')
    def test_watcher_start_success(
        self,
        mock_exists,
        mock_subprocess,
        mock_get_watcher,
        mock_pm2_check
    ):
        """Test starting a watcher successfully"""
        runner = CliRunner()

        # Mock PM2 installed
        mock_pm2_check.return_value = True

        # Mock watcher not running
        mock_get_watcher.return_value = None

        # Mock script exists
        mock_exists.return_value = True

        # Mock successful PM2 start
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )

        result = runner.invoke(watcher_start_command, ['gmail'])

        assert result.exit_code == 0
        assert "started successfully" in result.output.lower()

    @patch('cli.watcher.check_pm2_installed')
    def test_watcher_start_pm2_not_installed(self, mock_pm2_check):
        """Test start fails when PM2 not installed"""
        runner = CliRunner()

        # Mock PM2 not installed
        mock_pm2_check.return_value = False

        result = runner.invoke(watcher_start_command, ['gmail'])

        assert result.exit_code == 1
        assert "PM2 is not installed" in result.output

    def test_watcher_start_invalid_name(self):
        """Test start fails with invalid watcher name"""
        runner = CliRunner()

        result = runner.invoke(watcher_start_command, ['invalid'])

        assert result.exit_code == 1
        assert "Invalid watcher name" in result.output

    @patch('cli.watcher.check_pm2_installed')
    @patch('cli.watcher.get_watcher_process')
    def test_watcher_start_already_running(
        self,
        mock_get_watcher,
        mock_pm2_check
    ):
        """Test start when watcher is already running"""
        runner = CliRunner()

        # Mock PM2 installed
        mock_pm2_check.return_value = True

        # Mock watcher already running
        mock_get_watcher.return_value = {
            "name": "fte-watcher-gmail",
            "pm2_env": {"status": "online"}
        }

        result = runner.invoke(watcher_start_command, ['gmail'])

        assert result.exit_code == 0
        assert "already running" in result.output.lower()


class TestWatcherStop:
    """Test fte watcher stop command"""

    def test_watcher_stop_help(self):
        """Test watcher stop command help"""
        runner = CliRunner()
        result = runner.invoke(watcher_stop_command, ['--help'])

        assert result.exit_code == 0
        assert "Stop watcher daemon" in result.output

    @patch('cli.watcher.check_pm2_installed')
    @patch('cli.watcher.get_watcher_process')
    @patch('cli.watcher.subprocess.run')
    def test_watcher_stop_success(
        self,
        mock_subprocess,
        mock_get_watcher,
        mock_pm2_check
    ):
        """Test stopping a watcher successfully"""
        runner = CliRunner()

        # Mock PM2 installed
        mock_pm2_check.return_value = True

        # Mock watcher is running
        mock_get_watcher.return_value = {
            "name": "fte-watcher-gmail",
            "pm2_env": {"status": "online"}
        }

        # Mock successful PM2 stop
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )

        result = runner.invoke(watcher_stop_command, ['gmail'])

        assert result.exit_code == 0
        assert "stopped successfully" in result.output.lower()

    @patch('cli.watcher.check_pm2_installed')
    def test_watcher_stop_pm2_not_installed(self, mock_pm2_check):
        """Test stop fails when PM2 not installed"""
        runner = CliRunner()

        # Mock PM2 not installed
        mock_pm2_check.return_value = False

        result = runner.invoke(watcher_stop_command, ['gmail'])

        assert result.exit_code == 1
        assert "PM2 is not installed" in result.output

    def test_watcher_stop_invalid_name(self):
        """Test stop fails with invalid watcher name"""
        runner = CliRunner()

        result = runner.invoke(watcher_stop_command, ['invalid'])

        assert result.exit_code == 1
        assert "Invalid watcher name" in result.output

    @patch('cli.watcher.check_pm2_installed')
    @patch('cli.watcher.get_watcher_process')
    def test_watcher_stop_not_running(
        self,
        mock_get_watcher,
        mock_pm2_check
    ):
        """Test stop when watcher is not running"""
        runner = CliRunner()

        # Mock PM2 installed
        mock_pm2_check.return_value = True

        # Mock watcher not running
        mock_get_watcher.return_value = None

        result = runner.invoke(watcher_stop_command, ['gmail'])

        assert result.exit_code == 1
        assert "not running" in result.output.lower()


class TestWatcherStatus:
    """Test fte watcher status command"""

    def test_watcher_status_help(self):
        """Test watcher status command help"""
        runner = CliRunner()
        result = runner.invoke(watcher_status_command, ['--help'])

        assert result.exit_code == 0
        assert "Show watcher status" in result.output

    @patch('cli.watcher.get_pm2_list')
    def test_watcher_status_no_watchers(self, mock_get_pm2_list):
        """Test status when no watchers are running"""
        runner = CliRunner()

        # Mock empty PM2 list
        mock_get_pm2_list.return_value = []

        result = runner.invoke(watcher_status_command)

        assert result.exit_code == 0
        assert "No watchers" in result.output

    @patch('cli.watcher.get_pm2_list')
    def test_watcher_status_with_watchers(self, mock_get_pm2_list):
        """Test status with running watchers"""
        runner = CliRunner()

        # Mock PM2 list with watcher
        mock_get_pm2_list.return_value = [
            {
                "name": "fte-watcher-gmail",
                "pid": 12345,
                "pm2_env": {
                    "status": "online",
                    "pm_uptime": 3600000,  # 1 hour
                    "restart_time": 0
                },
                "monit": {
                    "cpu": 2.5,
                    "memory": 52428800  # 50MB
                }
            }
        ]

        result = runner.invoke(watcher_status_command)

        assert result.exit_code == 0
        assert "gmail" in result.output
        assert "online" in result.output.lower()

    @patch('cli.watcher.check_pm2_installed')
    def test_watcher_status_pm2_not_installed(self, mock_pm2_check):
        """Test status fails when PM2 not installed"""
        runner = CliRunner()

        # Mock PM2 not installed
        mock_pm2_check.return_value = False

        # Mock get_pm2_list to raise error
        with patch('cli.watcher.get_pm2_list') as mock_list:
            from cli.errors import PM2NotFoundError
            mock_list.side_effect = PM2NotFoundError("PM2 is not installed")

            result = runner.invoke(watcher_status_command)

            assert result.exit_code == 1
            assert "PM2 is not installed" in result.output


class TestWatcherLogs:
    """Test fte watcher logs command"""

    def test_watcher_logs_help(self):
        """Test watcher logs command help"""
        runner = CliRunner()
        result = runner.invoke(watcher_logs_command, ['--help'])

        assert result.exit_code == 0
        assert "Display watcher logs" in result.output
        assert "--tail" in result.output
        assert "--follow" in result.output

    @patch('cli.watcher.check_pm2_installed')
    @patch('cli.watcher.get_watcher_process')
    @patch('cli.watcher.subprocess.run')
    def test_watcher_logs_success(
        self,
        mock_subprocess,
        mock_get_watcher,
        mock_pm2_check
    ):
        """Test viewing watcher logs successfully"""
        runner = CliRunner()

        # Mock PM2 installed
        mock_pm2_check.return_value = True

        # Mock watcher is running
        mock_get_watcher.return_value = {
            "name": "fte-watcher-gmail",
            "pm2_env": {"status": "online"}
        }

        # Mock logs output
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="Log line 1\nLog line 2\nLog line 3",
            stderr=""
        )

        result = runner.invoke(watcher_logs_command, ['gmail', '--tail', '10'])

        assert result.exit_code == 0
        assert "Log line" in result.output

    @patch('cli.watcher.check_pm2_installed')
    @patch('cli.watcher.get_watcher_process')
    def test_watcher_logs_not_running(
        self,
        mock_get_watcher,
        mock_pm2_check
    ):
        """Test logs when watcher is not running"""
        runner = CliRunner()

        # Mock PM2 installed
        mock_pm2_check.return_value = True

        # Mock watcher not running
        mock_get_watcher.return_value = None

        result = runner.invoke(watcher_logs_command, ['gmail'])

        assert result.exit_code == 1
        assert "not running" in result.output.lower()

    def test_watcher_logs_invalid_name(self):
        """Test logs fails with invalid watcher name"""
        runner = CliRunner()

        result = runner.invoke(watcher_logs_command, ['invalid'])

        assert result.exit_code == 1
        assert "Invalid watcher name" in result.output


class TestWatcherUtilities:
    """Test watcher utility functions"""

    def test_format_uptime_seconds(self):
        """Test uptime formatting for seconds"""
        assert format_uptime(5000) == "5s"
        assert format_uptime(30000) == "30s"

    def test_format_uptime_minutes(self):
        """Test uptime formatting for minutes"""
        assert format_uptime(60000) == "1m"
        assert format_uptime(150000) == "2m"  # Seconds not shown when minutes present

    def test_format_uptime_hours(self):
        """Test uptime formatting for hours"""
        assert format_uptime(3600000) == "1h"
        assert format_uptime(7200000) == "2h"

    def test_format_uptime_days(self):
        """Test uptime formatting for days"""
        assert format_uptime(86400000) == "1d"
        assert format_uptime(90000000) == "1d 1h"

    def test_format_uptime_zero(self):
        """Test uptime formatting for zero"""
        assert format_uptime(0) == "0s"
        assert format_uptime(-100) == "0s"

    @patch('cli.watcher.subprocess.run')
    def test_check_pm2_installed_true(self, mock_subprocess):
        """Test PM2 check when installed"""
        mock_subprocess.return_value = MagicMock(returncode=0)

        result = check_pm2_installed()

        assert result is True

    @patch('cli.watcher.subprocess.run')
    def test_check_pm2_installed_false(self, mock_subprocess):
        """Test PM2 check when not installed"""
        mock_subprocess.side_effect = FileNotFoundError()

        result = check_pm2_installed()

        assert result is False


class TestWatcherGroup:
    """Test watcher command group"""

    def test_watcher_group_help(self):
        """Test watcher group help"""
        runner = CliRunner()
        result = runner.invoke(watcher_group, ['--help'])

        assert result.exit_code == 0
        assert "watcher" in result.output.lower()
        assert "start" in result.output
        assert "stop" in result.output
        assert "status" in result.output
        assert "logs" in result.output

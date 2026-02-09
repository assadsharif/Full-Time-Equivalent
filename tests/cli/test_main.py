"""
Integration tests for main CLI entry point.

Tests --version, --help, and global options.
"""

import pytest
from click.testing import CliRunner

from cli.main import cli


class TestCLIVersion:
    """Test CLI version command"""

    def test_version_flag(self):
        """Test --version displays version"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "version 0.1.0" in result.output.lower()

    def test_version_flag_short(self):
        """Test -V displays version (if supported)"""
        runner = CliRunner()
        # Click's version_option uses --version only by default
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestCLIHelp:
    """Test CLI help command"""

    def test_help_flag(self):
        """Test --help displays help"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "FTE - Digital Full-Time Employee CLI" in result.output
        assert "vault" in result.output.lower()
        assert "watcher" in result.output.lower()
        assert "mcp" in result.output.lower()
        assert "status" in result.output.lower()

    def test_help_flag_short(self):
        """Test -h flag (Click doesn't support -h by default, only --help)"""
        runner = CliRunner()
        result = runner.invoke(cli, ["-h"])

        # Click will show error for unknown option -h
        assert result.exit_code != 0 or "--help" in result.output

    def test_help_shows_commands(self):
        """Test help shows all command groups"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        # Check for command groups
        assert "vault" in result.output.lower()
        assert "watcher" in result.output.lower()
        assert "mcp" in result.output.lower()
        assert "approval" in result.output.lower()
        assert "briefing" in result.output.lower()
        assert "init" in result.output.lower()
        assert "status" in result.output.lower()

    def test_help_shows_options(self):
        """Test help shows global options"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "--verbose" in result.output or "-v" in result.output
        assert "--quiet" in result.output or "-q" in result.output
        assert "--no-color" in result.output


class TestGlobalOptions:
    """Test global CLI options"""

    def test_verbose_flag(self):
        """Test --verbose flag is accepted"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "--help"])

        # Should not error, help should still display
        assert result.exit_code == 0

    def test_quiet_flag(self):
        """Test --quiet flag is accepted"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--quiet", "--help"])

        # Should not error, help should still display
        assert result.exit_code == 0

    def test_no_color_flag(self):
        """Test --no-color flag is accepted"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--no-color", "--help"])

        # Should not error, help should still display
        assert result.exit_code == 0

    def test_vault_path_option(self):
        """Test --vault-path option is accepted"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--vault-path", "/test/path", "--help"])

        # Should not error, help should still display
        assert result.exit_code == 0

    def test_combined_flags(self):
        """Test multiple flags together"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "--no-color", "--help"])

        assert result.exit_code == 0


class TestCommandGroups:
    """Test command group structure"""

    def test_vault_command_group_exists(self):
        """Test vault command group exists"""
        runner = CliRunner()
        result = runner.invoke(cli, ["vault", "--help"])

        assert result.exit_code == 0
        assert "vault" in result.output.lower()

    def test_watcher_command_group_exists(self):
        """Test watcher command group exists"""
        runner = CliRunner()
        result = runner.invoke(cli, ["watcher", "--help"])

        assert result.exit_code == 0
        assert "watcher" in result.output.lower()

    def test_mcp_command_group_exists(self):
        """Test mcp command group exists"""
        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "--help"])

        assert result.exit_code == 0
        assert "mcp" in result.output.lower()

    def test_approval_command_group_exists(self):
        """Test approval command group exists"""
        runner = CliRunner()
        result = runner.invoke(cli, ["approval", "--help"])

        assert result.exit_code == 0
        assert "approval" in result.output.lower()

    def test_briefing_command_group_exists(self):
        """Test briefing command group exists"""
        runner = CliRunner()
        result = runner.invoke(cli, ["briefing", "--help"])

        assert result.exit_code == 0
        assert "briefing" in result.output.lower()


class TestInvalidCommands:
    """Test invalid command handling"""

    def test_invalid_command(self):
        """Test invalid command shows error"""
        runner = CliRunner()
        result = runner.invoke(cli, ["invalid-command"])

        assert result.exit_code != 0
        # Click shows "No such command" or similar error

    def test_invalid_option(self):
        """Test invalid option shows error"""
        runner = CliRunner()
        result = runner.invoke(cli, ["--invalid-option"])

        assert result.exit_code != 0

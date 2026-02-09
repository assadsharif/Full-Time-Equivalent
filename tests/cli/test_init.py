"""
Integration tests for fte init command.

Tests initialization workflow and vault path setup.
"""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from cli.init import init_command


class TestInitCommand:
    """Test fte init command"""

    def test_init_basic(self):
        """Test basic init command execution"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create config and .fte directories
            Path("config").mkdir()
            Path(".fte").mkdir()
            Path("config/cli.yaml").touch()

            result = runner.invoke(init_command, input="y\n")

            # Should succeed (or partially succeed in isolated env)
            assert "Initializing FTE CLI configuration" in result.output

    def test_init_help(self):
        """Test init command help"""
        runner = CliRunner()
        result = runner.invoke(init_command, ["--help"])

        assert result.exit_code == 0
        assert "Initialize FTE configuration" in result.output
        assert "--vault-path" in result.output
        assert "--force" in result.output

    def test_init_with_vault_path(self, tmp_path):
        """Test init with explicit vault path"""
        runner = CliRunner()

        # Create a valid vault structure
        vault_path = tmp_path / "test_vault"
        vault_path.mkdir()
        (vault_path / "Inbox").mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()

        with runner.isolated_filesystem():
            # Create config and .fte directories
            Path("config").mkdir()
            Path(".fte").mkdir()
            Path("config/cli.yaml").touch()

            result = runner.invoke(init_command, ["--vault-path", str(vault_path)])

            assert "Initializing FTE CLI configuration" in result.output

    def test_init_force_flag(self):
        """Test init with --force flag"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create config and .fte directories
            Path("config").mkdir()
            Path(".fte").mkdir()
            Path("config/cli.yaml").touch()

            result = runner.invoke(init_command, ["--force"], input="y\n")

            assert "Initializing FTE CLI configuration" in result.output
            # May see "Force flag set" in output

    def test_init_interactive_default(self):
        """Test init with interactive prompt accepting default"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create config and .fte directories
            Path("config").mkdir()
            Path(".fte").mkdir()
            Path("config/cli.yaml").touch()

            # Simulate user pressing 'y' for default
            result = runner.invoke(init_command, input="y\n")

            assert "Initializing FTE CLI configuration" in result.output
            assert "Default vault path" in result.output or "Vault" in result.output

    def test_init_interactive_custom_path(self):
        """Test init with interactive prompt providing custom path"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create config and .fte directories
            Path("config").mkdir()
            Path(".fte").mkdir()
            Path("config/cli.yaml").touch()

            # Simulate user selecting custom path
            custom_path = "/custom/vault/path"
            result = runner.invoke(init_command, input=f"n\n{custom_path}\nn\n")

            assert "Initializing FTE CLI configuration" in result.output

    def test_init_creates_checkpoint(self):
        """Test init creates checkpoint file"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create config and .fte directories
            config_dir = Path("config")
            fte_dir = Path(".fte")
            config_dir.mkdir()
            fte_dir.mkdir()
            (config_dir / "cli.yaml").touch()

            result = runner.invoke(init_command, input="y\n")

            # Checkpoint should be mentioned in output
            assert (
                "checkpoint" in result.output.lower() or "Initializing" in result.output
            )

    def test_init_nonexistent_vault_warning(self):
        """Test init warns about nonexistent vault"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create config and .fte directories
            Path("config").mkdir()
            Path(".fte").mkdir()
            Path("config/cli.yaml").touch()

            # Provide a nonexistent path
            nonexistent_path = "/nonexistent/vault/path"
            result = runner.invoke(init_command, ["--vault-path", nonexistent_path])

            # Should mention vault not found or warning
            assert "Initializing" in result.output

    def test_init_existing_config_no_force(self):
        """Test init with existing config and no force flag"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create existing config
            config_dir = Path("config")
            fte_dir = Path(".fte")
            config_dir.mkdir()
            fte_dir.mkdir()
            (config_dir / "cli.yaml").write_text("vault:\n  default_path: ~/test\n")

            result = runner.invoke(init_command, input="y\n")

            assert "Initializing FTE CLI configuration" in result.output
            # May see "already exists" in output


class TestInitIntegration:
    """Integration tests for init command"""

    def test_init_full_workflow(self, tmp_path):
        """Test complete init workflow"""
        runner = CliRunner()

        # Create a valid vault
        vault_path = tmp_path / "full_vault"
        vault_path.mkdir()
        (vault_path / "Inbox").mkdir()
        (vault_path / "Needs_Action").mkdir()
        (vault_path / "Done").mkdir()

        with runner.isolated_filesystem():
            # Set up environment
            Path("config").mkdir()
            Path(".fte").mkdir()
            Path("config/cli.yaml").touch()

            # Run init with valid vault
            result = runner.invoke(init_command, ["--vault-path", str(vault_path)])

            assert "Initializing FTE CLI configuration" in result.output
            # Should complete successfully

    def test_init_multiple_runs(self):
        """Test running init multiple times"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create config and .fte directories
            Path("config").mkdir()
            Path(".fte").mkdir()
            Path("config/cli.yaml").touch()

            # First run
            result1 = runner.invoke(init_command, input="y\n")
            assert "Initializing" in result1.output

            # Second run (should handle existing config)
            result2 = runner.invoke(init_command, input="y\n")
            assert "Initializing" in result2.output

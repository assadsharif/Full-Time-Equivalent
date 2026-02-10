"""
Unit tests for CLI config loader.

Tests configuration loading, validation, and default values.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.cli.config import (
    CLIConfig,
    ConfigLoader,
    get_config,
    reload_config,
)


class TestConfigLoader:
    """Test ConfigLoader class"""

    def test_load_default_config(self):
        """Test loading config with default values when file doesn't exist"""
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            loader = ConfigLoader(Path(tmp.name))
            config = loader.load()

            assert isinstance(config, CLIConfig)
            assert config.vault.default_path == "~/AI_Employee_Vault"
            assert config.vault.auto_detect is True
            assert config.logging.level == "INFO"
            assert config.watcher.process_manager == "pm2"

    def test_load_config_from_file(self, tmp_path):
        """Test loading config from YAML file"""
        config_file = tmp_path / "cli.yaml"
        config_data = {
            "vault": {"default_path": "~/CustomVault", "auto_detect": False},
            "logging": {"level": "DEBUG", "colored": False},
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        loader = ConfigLoader(config_file)
        config = loader.load()

        assert config.vault.default_path == "~/CustomVault"
        assert config.vault.auto_detect is False
        assert config.logging.level == "DEBUG"
        assert config.logging.colored is False

    def test_load_empty_config_file(self, tmp_path):
        """Test loading empty config file returns defaults"""
        config_file = tmp_path / "cli.yaml"
        config_file.touch()

        loader = ConfigLoader(config_file)
        config = loader.load()

        assert isinstance(config, CLIConfig)
        assert config.vault.default_path == "~/AI_Employee_Vault"

    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML raises ValueError"""
        config_file = tmp_path / "cli.yaml"
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [")

        loader = ConfigLoader(config_file)

        with pytest.raises(ValueError, match="Invalid YAML"):
            loader.load()

    def test_load_invalid_config_data(self, tmp_path):
        """Test loading config with invalid data raises ValueError"""
        config_file = tmp_path / "cli.yaml"
        config_data = {"watcher": {"poll_interval": "not_an_integer"}}  # Should be int

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        loader = ConfigLoader(config_file)

        with pytest.raises(ValueError, match="Config validation failed"):
            loader.load()

    def test_get_cached_config(self, tmp_path):
        """Test get() returns cached config"""
        config_file = tmp_path / "cli.yaml"
        config_data = {"vault": {"default_path": "~/Test"}}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        loader = ConfigLoader(config_file)
        config1 = loader.get()
        config2 = loader.get()

        assert config1 is config2  # Same instance

    def test_reload_config(self, tmp_path):
        """Test reload() loads fresh config from file"""
        config_file = tmp_path / "cli.yaml"
        config_data = {"vault": {"default_path": "~/Test1"}}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        loader = ConfigLoader(config_file)
        config1 = loader.load()
        assert config1.vault.default_path == "~/Test1"

        # Update file
        config_data["vault"]["default_path"] = "~/Test2"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config2 = loader.reload()
        assert config2.vault.default_path == "~/Test2"


class TestCLIConfig:
    """Test CLIConfig model"""

    def test_default_config(self):
        """Test default config values"""
        config = CLIConfig()

        assert config.vault.default_path == "~/AI_Employee_Vault"
        assert config.vault.auto_detect is True
        assert config.logging.level == "INFO"
        assert config.logging.colored is True
        assert config.watcher.process_manager == "pm2"
        assert config.watcher.poll_interval == 30
        assert config.mcp.health_check_timeout == 5
        assert config.approval.timeout == 43200
        assert config.briefing.default_range_days == 7
        assert config.output.format == "table"
        assert config.performance.parallel_checks is True
        assert config.telemetry.enabled is False
        assert config.features.experimental is False

    def test_partial_config(self):
        """Test partial config with defaults for missing values"""
        config = CLIConfig(
            vault={"default_path": "~/CustomVault"}, logging={"level": "DEBUG"}
        )

        assert config.vault.default_path == "~/CustomVault"
        assert config.vault.auto_detect is True  # Default
        assert config.logging.level == "DEBUG"
        assert config.logging.colored is True  # Default


class TestGlobalConfig:
    """Test global config functions"""

    def test_get_config_singleton(self, monkeypatch, tmp_path):
        """Test get_config() returns singleton instance"""
        # Create a temporary config file
        config_file = tmp_path / "cli.yaml"
        config_file.touch()

        # Mock the default config path
        monkeypatch.setattr(
            "src.cli.config.ConfigLoader.__init__",
            lambda self, path=None: setattr(self, "config_path", config_file)
            or setattr(self, "_config", None),
        )

        from src.cli import config as config_module

        # Reset global state
        config_module._config_loader = None

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_reload_config_function(self, monkeypatch, tmp_path):
        """Test reload_config() reloads from file"""
        config_file = tmp_path / "cli.yaml"
        config_data = {"vault": {"default_path": "~/Test"}}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Reset global loader
        from src.cli import config as config_module

        config_module._config_loader = ConfigLoader(config_file)

        config = reload_config()
        assert config.vault.default_path == "~/Test"

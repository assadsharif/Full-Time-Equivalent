"""
CLI Configuration Loader

Loads and validates CLI configuration from config/cli.yaml.
Provides typed access to configuration values with defaults.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError


class VaultConfig(BaseModel):
    """Vault settings configuration"""
    default_path: str = Field(default="~/AI_Employee_Vault")
    auto_detect: bool = Field(default=True)


class LoggingConfig(BaseModel):
    """Logging settings configuration"""
    level: str = Field(default="INFO")
    colored: bool = Field(default=True)
    file: Optional[str] = Field(default=None)


class WatcherConfig(BaseModel):
    """Watcher settings configuration"""
    process_manager: str = Field(default="pm2")
    poll_interval: int = Field(default=30)
    log_tail_lines: int = Field(default=50)


class MCPConfig(BaseModel):
    """MCP settings configuration"""
    registry_file: str = Field(default="config/mcp_servers.yaml")
    health_check_timeout: int = Field(default=5)
    tool_cache_ttl: int = Field(default=300)


class ApprovalConfig(BaseModel):
    """Approval settings configuration"""
    timeout: int = Field(default=43200)  # 12 hours
    auto_display_pending: bool = Field(default=True)


class BriefingConfig(BaseModel):
    """Briefing settings configuration"""
    default_range_days: int = Field(default=7)
    pdf_enabled: bool = Field(default=True)
    viewer: str = Field(default="auto")


class OutputConfig(BaseModel):
    """Output settings configuration"""
    format: str = Field(default="table")
    show_progress: bool = Field(default=True)
    pager: str = Field(default="less")


class PerformanceConfig(BaseModel):
    """Performance settings configuration"""
    parallel_checks: bool = Field(default=True)
    max_concurrent_checks: int = Field(default=5)
    startup_time_target: int = Field(default=100)


class TelemetryConfig(BaseModel):
    """Telemetry settings configuration"""
    enabled: bool = Field(default=False)
    endpoint: Optional[str] = Field(default=None)


class FeaturesConfig(BaseModel):
    """Feature flags configuration"""
    experimental: bool = Field(default=False)
    debug: bool = Field(default=False)


class CLIConfig(BaseModel):
    """Complete CLI configuration"""
    vault: VaultConfig = Field(default_factory=VaultConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    watcher: WatcherConfig = Field(default_factory=WatcherConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    approval: ApprovalConfig = Field(default_factory=ApprovalConfig)
    briefing: BriefingConfig = Field(default_factory=BriefingConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)


class ConfigLoader:
    """Loads and manages CLI configuration"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config loader.

        Args:
            config_path: Path to config file (defaults to config/cli.yaml)
        """
        if config_path is None:
            # Default to config/cli.yaml in project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "cli.yaml"

        self.config_path = Path(config_path)
        self._config: Optional[CLIConfig] = None

    def load(self) -> CLIConfig:
        """
        Load configuration from file.

        Returns:
            CLIConfig instance with loaded settings

        Raises:
            FileNotFoundError: Config file not found
            ValidationError: Config validation failed
            yaml.YAMLError: Invalid YAML syntax
        """
        if not self.config_path.exists():
            # Return default config if file doesn't exist
            return CLIConfig()

        try:
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f)

            if config_data is None:
                # Empty file, return defaults
                return CLIConfig()

            # Validate and create config
            self._config = CLIConfig(**config_data)
            return self._config

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}")
        except ValidationError as e:
            raise ValueError(f"Config validation failed: {e}")

    def get(self) -> CLIConfig:
        """
        Get loaded configuration (loads if not already loaded).

        Returns:
            CLIConfig instance
        """
        if self._config is None:
            self._config = self.load()
        return self._config

    def reload(self) -> CLIConfig:
        """
        Reload configuration from file.

        Returns:
            Reloaded CLIConfig instance
        """
        self._config = None
        return self.load()


# Global config loader instance
_config_loader: Optional[ConfigLoader] = None


def get_config(config_path: Optional[Path] = None) -> CLIConfig:
    """
    Get global CLI configuration.

    Args:
        config_path: Optional custom config path

    Returns:
        CLIConfig instance
    """
    global _config_loader

    if _config_loader is None:
        _config_loader = ConfigLoader(config_path)

    return _config_loader.get()


def reload_config() -> CLIConfig:
    """
    Reload global CLI configuration from file.

    Returns:
        Reloaded CLIConfig instance
    """
    global _config_loader

    if _config_loader is None:
        _config_loader = ConfigLoader()

    return _config_loader.reload()

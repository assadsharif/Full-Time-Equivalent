"""
Configuration loading for logging infrastructure (P2).

Supports loading from YAML files and environment variables.
Constitutional compliance: Section 3 (local-first configuration).
"""

import os
from pathlib import Path
from typing import Optional

import yaml

from .models import LoggerConfig, LogLevel


def from_file(config_path: str | Path) -> LoggerConfig:
    """
    Load logging configuration from a YAML file.

    Args:
        config_path: Path to logging.yaml configuration file

    Returns:
        LoggerConfig instance with values from file

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If config file is invalid YAML
        ValueError: If config values are invalid

    Example:
        >>> config = from_file("config/logging.yaml")
        >>> config.level
        LogLevel.INFO
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}

    # Convert string log level to enum
    level_str = data.get("level", "INFO").upper()
    level = LogLevel[level_str] if hasattr(LogLevel, level_str) else LogLevel.INFO

    # Convert module_levels dict (str -> str) to (str -> LogLevel)
    module_levels = {}
    if "module_levels" in data:
        for module, level_str in data["module_levels"].items():
            level_str = level_str.upper()
            if hasattr(LogLevel, level_str):
                module_levels[module] = LogLevel[level_str]

    # Extract secret patterns from nested structure (if present)
    secret_patterns = []
    if "secret_redaction" in data:
        secret_patterns = data["secret_redaction"].get("patterns", [])
        redaction_text = data["secret_redaction"].get("redaction_text", "***REDACTED***")
    else:
        secret_patterns = data.get("secret_patterns", [])
        redaction_text = data.get("redaction_text", "***REDACTED***")

    # Extract async writer settings (if present)
    async_enabled = data.get("async_enabled", True)
    buffer_size = data.get("buffer_size", 1000)
    flush_interval_s = data.get("flush_interval_s", 1.0)

    if "async_writer" in data:
        async_writer = data["async_writer"]
        buffer_size = async_writer.get("buffer_size", buffer_size)
        flush_interval_s = async_writer.get("flush_interval_seconds", flush_interval_s)

    # Extract retention settings (if present)
    retention_days = data.get("retention_days", 30)
    compression_enabled = data.get("compression_enabled", True)
    max_file_size_mb = data.get("max_file_size_mb", 100)

    if "retention" in data:
        retention = data["retention"]
        retention_days = retention.get("max_log_age_days", retention_days)
        max_file_size_mb = retention.get("max_archive_size_mb", max_file_size_mb)
        compression = retention.get("compression", "gzip")
        compression_enabled = compression in ["gzip", "bzip2", "xz"]

    return LoggerConfig(
        log_dir=Path(data.get("log_dir", "./Logs")),
        level=level,
        module_levels=module_levels,
        format=data.get("format", "json"),
        async_enabled=async_enabled,
        buffer_size=buffer_size,
        flush_interval_s=flush_interval_s,
        retention_days=retention_days,
        compression_enabled=compression_enabled,
        max_file_size_mb=max_file_size_mb,
        secret_patterns=secret_patterns,
        redaction_text=redaction_text,
    )


def from_env(prefix: str = "LOGGING_") -> LoggerConfig:
    """
    Load logging configuration from environment variables.

    Environment variables follow the pattern: {prefix}{FIELD_NAME}
    Example: LOGGING_LEVEL=DEBUG, LOGGING_LOG_DIR=/var/log

    Args:
        prefix: Prefix for environment variable names (default: "LOGGING_")

    Returns:
        LoggerConfig instance with values from environment (defaults for missing)

    Example:
        >>> os.environ["LOGGING_LEVEL"] = "DEBUG"
        >>> config = from_env()
        >>> config.level
        LogLevel.DEBUG
    """

    def get_env(key: str, default: str = "") -> str:
        """Get environment variable with prefix."""
        return os.environ.get(f"{prefix}{key}", default)

    # Parse log level
    level_str = get_env("LEVEL", "INFO").upper()
    level = LogLevel[level_str] if hasattr(LogLevel, level_str) else LogLevel.INFO

    # Parse module levels (format: "module1=DEBUG,module2=INFO")
    module_levels = {}
    module_levels_str = get_env("MODULE_LEVELS", "")
    if module_levels_str:
        for pair in module_levels_str.split(","):
            if "=" in pair:
                module, level_str = pair.split("=", 1)
                level_str = level_str.strip().upper()
                if hasattr(LogLevel, level_str):
                    module_levels[module.strip()] = LogLevel[level_str]

    # Parse secret patterns (format: "pattern1|pattern2|pattern3")
    secret_patterns_str = get_env("SECRET_PATTERNS", "")
    secret_patterns = [p.strip() for p in secret_patterns_str.split("|") if p.strip()]

    # Parse boolean flags
    async_enabled = get_env("ASYNC_ENABLED", "true").lower() in ["true", "1", "yes"]
    compression_enabled = get_env("COMPRESSION_ENABLED", "true").lower() in ["true", "1", "yes"]

    # Parse numeric values with defaults
    try:
        buffer_size = int(get_env("BUFFER_SIZE", "1000"))
    except ValueError:
        buffer_size = 1000

    try:
        flush_interval_s = float(get_env("FLUSH_INTERVAL_S", "1.0"))
    except ValueError:
        flush_interval_s = 1.0

    try:
        retention_days = int(get_env("RETENTION_DAYS", "30"))
    except ValueError:
        retention_days = 30

    try:
        max_file_size_mb = int(get_env("MAX_FILE_SIZE_MB", "100"))
    except ValueError:
        max_file_size_mb = 100

    return LoggerConfig(
        log_dir=Path(get_env("LOG_DIR", "./Logs")),
        level=level,
        module_levels=module_levels,
        format=get_env("FORMAT", "json"),
        async_enabled=async_enabled,
        buffer_size=buffer_size,
        flush_interval_s=flush_interval_s,
        retention_days=retention_days,
        compression_enabled=compression_enabled,
        max_file_size_mb=max_file_size_mb,
        secret_patterns=secret_patterns,
        redaction_text=get_env("REDACTION_TEXT", "***REDACTED***"),
    )

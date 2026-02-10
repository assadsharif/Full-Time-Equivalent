"""
Unit tests for logging configuration (P2).

Tests cover:
- LoggerConfig defaults
- Loading from YAML files
- Loading from environment variables
- Invalid configuration handling
"""

import os
from pathlib import Path

import pytest

from src.fte_logging.config import from_env, from_file
from src.fte_logging.models import LoggerConfig, LogLevel


class TestLoggerConfigDefaults:
    """Tests for LoggerConfig default values."""

    def test_default_config(self):
        """LoggerConfig should have sensible defaults."""
        config = LoggerConfig()

        assert config.log_dir == Path("./Logs")
        assert config.level == LogLevel.INFO
        assert config.module_levels == {}
        assert config.format == "json"
        assert config.async_enabled is True
        assert config.buffer_size == 1000
        assert config.flush_interval_s == 1.0
        assert config.retention_days == 30
        assert config.compression_enabled is True
        assert config.max_file_size_mb == 100
        assert config.secret_patterns == []
        assert config.redaction_text == "***REDACTED***"

    def test_custom_config(self):
        """LoggerConfig should accept custom values."""
        config = LoggerConfig(
            log_dir=Path("/var/log"),
            level=LogLevel.DEBUG,
            module_levels={"src.test": LogLevel.WARNING},
            async_enabled=False,
        )

        assert config.log_dir == Path("/var/log")
        assert config.level == LogLevel.DEBUG
        assert config.module_levels == {"src.test": LogLevel.WARNING}
        assert config.async_enabled is False


class TestFromFile:
    """Tests for loading configuration from YAML files."""

    def test_from_file_minimal(self, tmp_path):
        """from_file should load minimal valid config."""
        config_file = tmp_path / "logging.yaml"
        config_file.write_text("level: DEBUG\n")

        config = from_file(config_file)

        assert config.level == LogLevel.DEBUG
        assert config.log_dir == Path("./Logs")  # default

    def test_from_file_full(self, tmp_path):
        """from_file should load complete config."""
        config_file = tmp_path / "logging.yaml"
        config_content = """
log_dir: /var/log
level: WARNING
module_levels:
  src.control_plane: DEBUG
  src.mcp_servers: ERROR
format: console
async_enabled: false
buffer_size: 500
flush_interval_s: 2.0
retention_days: 60
compression_enabled: false
max_file_size_mb: 50
secret_patterns:
  - 'api_key=\\w+'
  - 'Bearer \\w+'
redaction_text: "[REDACTED]"
"""
        config_file.write_text(config_content)

        config = from_file(config_file)

        assert config.log_dir == Path("/var/log")
        assert config.level == LogLevel.WARNING
        assert config.module_levels == {
            "src.control_plane": LogLevel.DEBUG,
            "src.mcp_servers": LogLevel.ERROR,
        }
        assert config.format == "console"
        assert config.async_enabled is False
        assert config.buffer_size == 500
        assert config.flush_interval_s == 2.0
        assert config.retention_days == 60
        assert config.compression_enabled is False
        assert config.max_file_size_mb == 50
        assert config.secret_patterns == ["api_key=\\w+", "Bearer \\w+"]
        assert config.redaction_text == "[REDACTED]"

    def test_from_file_nested_structure(self, tmp_path):
        """from_file should handle nested config structure (from T008 format)."""
        config_file = tmp_path / "logging.yaml"
        config_content = """
log_dir: ./Logs
level: INFO
async_writer:
  buffer_size: 2000
  flush_interval_seconds: 0.5
secret_redaction:
  patterns:
    - 'password=\\w+'
  redaction_text: "***SECRET***"
retention:
  max_log_age_days: 90
  compression: gzip
"""
        config_file.write_text(config_content)

        config = from_file(config_file)

        assert config.buffer_size == 2000
        assert config.flush_interval_s == 0.5
        assert config.secret_patterns == ["password=\\w+"]
        assert config.redaction_text == "***SECRET***"
        assert config.retention_days == 90
        assert config.compression_enabled is True

    def test_from_file_case_insensitive_levels(self, tmp_path):
        """from_file should handle case-insensitive log level names."""
        config_file = tmp_path / "logging.yaml"
        config_content = """
level: debug
module_levels:
  src.test: Warning
  src.other: CRITICAL
"""
        config_file.write_text(config_content)

        config = from_file(config_file)

        assert config.level == LogLevel.DEBUG
        assert config.module_levels["src.test"] == LogLevel.WARNING
        assert config.module_levels["src.other"] == LogLevel.CRITICAL

    def test_from_file_empty_config(self, tmp_path):
        """from_file should handle empty config file with defaults."""
        config_file = tmp_path / "logging.yaml"
        config_file.write_text("")

        config = from_file(config_file)

        # Should use all defaults
        assert config.level == LogLevel.INFO
        assert config.log_dir == Path("./Logs")

    def test_from_file_not_found(self):
        """from_file should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            from_file("/nonexistent/path/logging.yaml")

    def test_from_file_invalid_level(self, tmp_path):
        """from_file should fall back to INFO for invalid log levels."""
        config_file = tmp_path / "logging.yaml"
        config_file.write_text("level: INVALID_LEVEL\n")

        config = from_file(config_file)

        assert config.level == LogLevel.INFO  # fallback to default


class TestFromEnv:
    """Tests for loading configuration from environment variables."""

    def test_from_env_minimal(self):
        """from_env should load with minimal environment."""
        # Clear any existing LOGGING_ variables
        for key in list(os.environ.keys()):
            if key.startswith("LOGGING_"):
                del os.environ[key]

        config = from_env()

        # Should use all defaults
        assert config.level == LogLevel.INFO
        assert config.log_dir == Path("./Logs")

    def test_from_env_full(self):
        """from_env should load all config from environment."""
        env_vars = {
            "LOGGING_LOG_DIR": "/tmp/logs",
            "LOGGING_LEVEL": "DEBUG",
            "LOGGING_MODULE_LEVELS": "src.test=WARNING,src.other=ERROR",
            "LOGGING_FORMAT": "console",
            "LOGGING_ASYNC_ENABLED": "false",
            "LOGGING_BUFFER_SIZE": "2000",
            "LOGGING_FLUSH_INTERVAL_S": "0.5",
            "LOGGING_RETENTION_DAYS": "90",
            "LOGGING_COMPRESSION_ENABLED": "no",
            "LOGGING_MAX_FILE_SIZE_MB": "200",
            "LOGGING_SECRET_PATTERNS": "api_key=\\w+|Bearer \\w+",
            "LOGGING_REDACTION_TEXT": "[HIDDEN]",
        }

        for key, value in env_vars.items():
            os.environ[key] = value

        try:
            config = from_env()

            assert config.log_dir == Path("/tmp/logs")
            assert config.level == LogLevel.DEBUG
            assert config.module_levels == {
                "src.test": LogLevel.WARNING,
                "src.other": LogLevel.ERROR,
            }
            assert config.format == "console"
            assert config.async_enabled is False
            assert config.buffer_size == 2000
            assert config.flush_interval_s == 0.5
            assert config.retention_days == 90
            assert config.compression_enabled is False
            assert config.max_file_size_mb == 200
            assert config.secret_patterns == ["api_key=\\w+", "Bearer \\w+"]
            assert config.redaction_text == "[HIDDEN]"
        finally:
            # Cleanup
            for key in env_vars:
                if key in os.environ:
                    del os.environ[key]

    def test_from_env_custom_prefix(self):
        """from_env should support custom prefix."""
        os.environ["MYAPP_LEVEL"] = "ERROR"

        try:
            config = from_env(prefix="MYAPP_")
            assert config.level == LogLevel.ERROR
        finally:
            del os.environ["MYAPP_LEVEL"]

    def test_from_env_boolean_parsing(self):
        """from_env should correctly parse boolean values."""
        test_cases = [
            ("true", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("invalid", False),  # default to False
        ]

        for value, expected in test_cases:
            os.environ["LOGGING_ASYNC_ENABLED"] = value
            try:
                config = from_env()
                assert config.async_enabled == expected, f"Failed for value: {value}"
            finally:
                del os.environ["LOGGING_ASYNC_ENABLED"]

    def test_from_env_invalid_numbers(self):
        """from_env should handle invalid numeric values gracefully."""
        os.environ["LOGGING_BUFFER_SIZE"] = "invalid"

        try:
            config = from_env()
            assert config.buffer_size == 1000  # fallback to default
        finally:
            del os.environ["LOGGING_BUFFER_SIZE"]

    def test_from_env_case_insensitive_levels(self):
        """from_env should handle case-insensitive log levels."""
        os.environ["LOGGING_LEVEL"] = "warning"

        try:
            config = from_env()
            assert config.level == LogLevel.WARNING
        finally:
            del os.environ["LOGGING_LEVEL"]

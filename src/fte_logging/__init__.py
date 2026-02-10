"""
Logging infrastructure for Digital FTE.

This module provides comprehensive structured logging with:
- Trace correlation (ULID-based trace IDs)
- Async non-blocking writes (< 5μs overhead)
- Automatic secret redaction
- High-performance SQL queries (DuckDB)
- Metrics logging and aggregation
- Log retention and archival

Constitutional compliance:
- Section 2: Logs written to disk (source of truth)
- Section 3: Local-first, secrets redacted
- Section 8: Append-only, structured logging
- Section 9: Errors never hidden, graceful degradation

Note: This is P2 (post-MVP) infrastructure. P1 control plane logging
(src.control_plane.logger.AuditLogger) remains unchanged and frozen.
"""

__version__ = "0.1.0"

from pathlib import Path
from typing import Optional

from .config import from_env, from_file
from .logger_service import LoggerService
from .models import LoggerConfig, LogLevel
from .trace import bind_trace_id, get_trace_id, new_trace_id

# Global logger instance (singleton pattern)
_global_logger: Optional[LoggerService] = None


def init_logging(
    config_path: Optional[str | Path] = None,
    *,
    log_dir: Optional[str | Path] = None,
    level: Optional[str | LogLevel] = None,
    async_enabled: bool = True,
) -> LoggerService:
    """
    Initialize global logging system.

    Args:
        config_path: Path to logging.yaml config file (optional)
        log_dir: Override log directory (default: ./Logs)
        level: Override log level (default: INFO)
        async_enabled: Enable async logging (default: True)

    Returns:
        Global LoggerService instance

    Example:
        >>> init_logging(log_dir="./Logs", level="DEBUG")
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    global _global_logger

    # Load config from file or create default
    if config_path is not None:
        config = from_file(config_path)
    else:
        config = LoggerConfig()

    # Apply overrides
    if log_dir is not None:
        config = LoggerConfig(
            log_dir=Path(log_dir),
            level=config.level,
            module_levels=config.module_levels,
            format=config.format,
            async_enabled=async_enabled,
            buffer_size=config.buffer_size,
            flush_interval_s=config.flush_interval_s,
            retention_days=config.retention_days,
            compression_enabled=config.compression_enabled,
            max_file_size_mb=config.max_file_size_mb,
            secret_patterns=config.secret_patterns,
            redaction_text=config.redaction_text,
        )

    if level is not None:
        if isinstance(level, str):
            level = LogLevel[level.upper()]
        config = LoggerConfig(
            log_dir=config.log_dir,
            level=level,
            module_levels=config.module_levels,
            format=config.format,
            async_enabled=config.async_enabled,
            buffer_size=config.buffer_size,
            flush_interval_s=config.flush_interval_s,
            retention_days=config.retention_days,
            compression_enabled=config.compression_enabled,
            max_file_size_mb=config.max_file_size_mb,
            secret_patterns=config.secret_patterns,
            redaction_text=config.redaction_text,
        )

    # Create global logger
    _global_logger = LoggerService(config, start_async=False)

    return _global_logger


def get_logger(name: Optional[str] = None) -> LoggerService:
    """
    Get logger instance.

    Args:
        name: Logger name (typically __name__). Currently unused,
              but reserved for future per-module logger support.

    Returns:
        Global LoggerService instance

    Raises:
        RuntimeError: If init_logging() not called first

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Message from module")
    """
    global _global_logger

    if _global_logger is None:
        # Auto-initialize with defaults
        _global_logger = LoggerService(LoggerConfig(), start_async=False)

    return _global_logger


# Public API
__all__ = [
    # Core functions
    "init_logging",
    "get_logger",
    # Trace ID functions
    "new_trace_id",
    "get_trace_id",
    "bind_trace_id",
    # Models
    "LogLevel",
    "LoggerConfig",
    # Services
    "LoggerService",
    # Config loaders
    "from_file",
    "from_env",
]

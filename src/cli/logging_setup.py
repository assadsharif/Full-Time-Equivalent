"""
CLI Logging Setup

Configures structured logging with Rich console integration.
Provides styled output for CLI commands with proper log levels.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import structlog
from rich.console import Console
from rich.logging import RichHandler

from cli.config import get_config


# Rich console for styled output
console = Console(stderr=True)


def setup_logging(
    level: Optional[str] = None,
    colored: Optional[bool] = None,
    log_file: Optional[Path] = None
) -> None:
    """
    Configure CLI logging with Rich integration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        colored: Enable colored output (defaults to config)
        log_file: Optional log file path (defaults to config)
    """
    # Load config
    config = get_config()

    # Use provided values or fall back to config
    log_level = level or config.logging.level
    use_color = colored if colored is not None else config.logging.colored
    file_path = log_file or (Path(config.logging.file) if config.logging.file else None)

    # Configure stdlib logging
    logging.basicConfig(
        level=log_level.upper(),
        format="%(message)s",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                show_time=False,
                show_path=False,
                markup=True,
                enable_link_path=False
            )
        ] if use_color else [logging.StreamHandler(sys.stderr)]
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Add file handler if specified
    if file_path:
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(log_level.upper())
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
        logging.getLogger().addHandler(file_handler)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def setup_quiet_mode() -> None:
    """Configure logging for quiet mode (ERROR level only)."""
    logging.getLogger().setLevel(logging.ERROR)
    for handler in logging.getLogger().handlers:
        handler.setLevel(logging.ERROR)


def setup_verbose_mode() -> None:
    """Configure logging for verbose mode (DEBUG level)."""
    logging.getLogger().setLevel(logging.DEBUG)
    for handler in logging.getLogger().handlers:
        handler.setLevel(logging.DEBUG)


def disable_colors() -> None:
    """Disable colored output (for CI/CD environments)."""
    global console
    console = Console(stderr=True, no_color=True, force_terminal=False)

    # Reconfigure logging without Rich
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
        force=True
    )

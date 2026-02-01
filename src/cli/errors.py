"""
CLI Error Handlers

Custom exception classes for CLI operations with clear error messages
and proper exit codes.
"""

import functools
import logging
import sys
import traceback
from contextlib import contextmanager
from typing import Callable, Optional

import click


class CLIError(Exception):
    """Base exception for all CLI errors"""

    def __init__(self, message: str, exit_code: int = 1):
        """
        Initialize CLI error.

        Args:
            message: Error message
            exit_code: Exit code (default: 1)
        """
        self.message = message
        self.exit_code = exit_code
        super().__init__(self.message)


class VaultNotFoundError(CLIError):
    """Vault not found or invalid"""

    def __init__(self, message: str = "Vault not found or invalid"):
        super().__init__(message, exit_code=1)


class VaultNotInitializedError(CLIError):
    """Vault not initialized"""

    def __init__(self, message: str = "Vault not initialized. Run 'fte vault init' first."):
        super().__init__(message, exit_code=1)


class ConfigError(CLIError):
    """Configuration error"""

    def __init__(self, message: str):
        super().__init__(f"Configuration error: {message}", exit_code=1)


class ConfigNotFoundError(ConfigError):
    """Configuration file not found"""

    def __init__(self, config_path: str):
        super().__init__(f"Config file not found: {config_path}")


class ConfigValidationError(ConfigError):
    """Configuration validation failed"""

    def __init__(self, details: str):
        super().__init__(f"Config validation failed: {details}")


class WatcherError(CLIError):
    """Watcher operation error"""

    def __init__(self, message: str):
        super().__init__(f"Watcher error: {message}", exit_code=1)


class WatcherNotFoundError(WatcherError):
    """Watcher not found"""

    def __init__(self, watcher_name: str):
        super().__init__(f"Watcher not found: {watcher_name}")


class WatcherAlreadyRunningError(WatcherError):
    """Watcher already running"""

    def __init__(self, watcher_name: str, pid: int):
        super().__init__(f"Watcher '{watcher_name}' is already running (PID: {pid})")


class WatcherNotRunningError(WatcherError):
    """Watcher not running"""

    def __init__(self, watcher_name: str):
        super().__init__(f"Watcher '{watcher_name}' is not running")


class ProcessManagerError(WatcherError):
    """Process manager (PM2/supervisord) error"""

    def __init__(self, message: str):
        super().__init__(f"Process manager error: {message}")


class PM2NotInstalledError(ProcessManagerError):
    """PM2 not installed"""

    def __init__(self):
        super().__init__(
            "PM2 not installed. Install with: npm install -g pm2"
        )


class MCPError(CLIError):
    """MCP server error"""

    def __init__(self, message: str):
        super().__init__(f"MCP error: {message}", exit_code=1)


class MCPServerNotFoundError(MCPError):
    """MCP server not found"""

    def __init__(self, server_name: str):
        super().__init__(f"MCP server not found: {server_name}")


class MCPHealthCheckFailedError(MCPError):
    """MCP health check failed"""

    def __init__(self, server_name: str, reason: str):
        super().__init__(f"Health check failed for '{server_name}': {reason}")


class MCPInvalidURLError(MCPError):
    """Invalid MCP server URL"""

    def __init__(self, url: str):
        super().__init__(f"Invalid MCP server URL: {url}")


class MCPRegistryError(MCPError):
    """MCP registry error"""

    def __init__(self, message: str):
        super().__init__(f"MCP registry error: {message}")


class ApprovalError(CLIError):
    """Approval workflow error"""

    def __init__(self, message: str):
        super().__init__(f"Approval error: {message}", exit_code=1)


class ApprovalNotFoundError(ApprovalError):
    """Approval not found"""

    def __init__(self, approval_id: str):
        super().__init__(f"Approval not found: {approval_id}")


class ApprovalExpiredError(ApprovalError):
    """Approval expired"""

    def __init__(self, approval_id: str, expired_at: str):
        super().__init__(f"Approval '{approval_id}' expired at {expired_at}")


class ApprovalInvalidNonceError(ApprovalError):
    """Invalid approval nonce"""

    def __init__(self, approval_id: str):
        super().__init__(f"Invalid nonce for approval '{approval_id}'")


class ApprovalIntegrityError(ApprovalError):
    """Approval file integrity check failed"""

    def __init__(self, approval_id: str):
        super().__init__(
            f"File integrity check failed for approval '{approval_id}'. "
            f"File may have been tampered with."
        )


class BriefingError(CLIError):
    """Briefing generation error"""

    def __init__(self, message: str):
        super().__init__(f"Briefing error: {message}", exit_code=1)


class BriefingNotFoundError(BriefingError):
    """Briefing not found"""

    def __init__(self):
        super().__init__("No briefings found. Generate one with 'fte briefing generate'")


class BriefingGenerationError(BriefingError):
    """Briefing generation failed"""

    def __init__(self, reason: str):
        super().__init__(f"Briefing generation failed: {reason}")


class PDFGenerationError(BriefingError):
    """PDF generation failed"""

    def __init__(self, reason: str):
        super().__init__(
            f"PDF generation failed: {reason}\n"
            f"Ensure wkhtmltopdf is installed: apt-get install wkhtmltopdf"
        )


class WatcherError(CLIError):
    """Watcher operation error"""

    def __init__(self, message: str):
        super().__init__(f"Watcher error: {message}", exit_code=1)


class WatcherNotFoundError(WatcherError):
    """Watcher not found"""

    def __init__(self, message: str):
        super().__init__(message)


class WatcherValidationError(WatcherError):
    """Watcher validation failed"""

    def __init__(self, message: str):
        super().__init__(message)


class PM2NotFoundError(WatcherError):
    """PM2 not installed"""

    def __init__(self, message: str):
        super().__init__(message)


class MCPError(CLIError):
    """MCP server operation error"""

    def __init__(self, message: str):
        super().__init__(f"MCP error: {message}", exit_code=1)


class MCPNotFoundError(MCPError):
    """MCP server not found"""

    def __init__(self, message: str):
        super().__init__(message)


class MCPInvalidURLError(MCPError):
    """Invalid MCP server URL"""

    def __init__(self, message: str):
        super().__init__(message)


class MCPRegistryError(MCPError):
    """MCP registry operation failed"""

    def __init__(self, message: str):
        super().__init__(message)


class MCPHealthCheckError(MCPError):
    """MCP health check failed"""

    def __init__(self, message: str):
        super().__init__(message)


class CheckpointError(CLIError):
    """Checkpoint operation error"""

    def __init__(self, message: str):
        super().__init__(f"Checkpoint error: {message}", exit_code=1)


class CheckpointLoadError(CheckpointError):
    """Checkpoint load failed"""

    def __init__(self, path: str, reason: str):
        super().__init__(f"Failed to load checkpoint from {path}: {reason}")


class CheckpointSaveError(CheckpointError):
    """Checkpoint save failed"""

    def __init__(self, path: str, reason: str):
        super().__init__(f"Failed to save checkpoint to {path}: {reason}")


def handle_cli_error(error: Exception, verbose: bool = False) -> int:
    """
    Handle CLI error and return appropriate exit code.

    Args:
        error: Exception to handle
        verbose: Show full traceback

    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    from cli.utils import display_error

    if isinstance(error, CLIError):
        display_error(error, verbose=verbose)
        return error.exit_code
    else:
        # Unexpected error
        display_error(error, verbose=verbose)
        return 1


# Unified Error Handling Middleware

logger = logging.getLogger(__name__)


def with_error_handling(func: Callable) -> Callable:
    """
    Decorator for unified error handling across all CLI commands.

    Usage:
        @click.command()
        @with_error_handling
        def my_command():
            ...

    Features:
        - Catches and handles all exceptions
        - Logs errors appropriately
        - Returns proper exit codes
        - Shows contextual error messages
        - Handles KeyboardInterrupt gracefully
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context(silent=True)
        verbose = ctx.obj.get("verbose", False) if ctx and ctx.obj else False

        try:
            return func(*args, **kwargs)

        except KeyboardInterrupt:
            from rich.console import Console
            console = Console()
            console.print("\n[yellow]⚠ Operation cancelled by user[/yellow]")
            logger.info("Command cancelled by user (KeyboardInterrupt)")
            sys.exit(130)  # Standard exit code for SIGINT

        except CLIError as e:
            # Known CLI errors
            logger.error(f"CLI error: {e.message}", exc_info=verbose)
            exit_code = handle_cli_error(e, verbose=verbose)
            sys.exit(exit_code)

        except click.ClickException as e:
            # Click framework errors (argument validation, etc.)
            logger.error(f"Click error: {e.format_message()}", exc_info=verbose)
            e.show()
            sys.exit(e.exit_code)

        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            exit_code = handle_cli_error(e, verbose=verbose)
            sys.exit(exit_code)

    return wrapper


@contextmanager
def error_context(operation: str, verbose: bool = False):
    """
    Context manager for error handling in specific operations.

    Usage:
        with error_context("Loading configuration"):
            config = load_config()

    Args:
        operation: Description of the operation being performed
        verbose: Show full traceback on error
    """
    try:
        yield
    except KeyboardInterrupt:
        from rich.console import Console
        console = Console()
        console.print(f"\n[yellow]⚠ {operation} cancelled by user[/yellow]")
        logger.info(f"{operation} cancelled by user")
        sys.exit(130)
    except CLIError as e:
        logger.error(f"Error during {operation}: {e.message}", exc_info=verbose)
        handle_cli_error(e, verbose=verbose)
        sys.exit(e.exit_code)
    except Exception as e:
        logger.error(f"Unexpected error during {operation}: {str(e)}", exc_info=True)
        handle_cli_error(e, verbose=verbose)
        sys.exit(1)


def safe_execute(func: Callable, *args, **kwargs) -> tuple[bool, Optional[Exception]]:
    """
    Safely execute a function and return success status and any exception.

    Usage:
        success, error = safe_execute(risky_function, arg1, arg2)
        if not success:
            handle_error(error)

    Args:
        func: Function to execute
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Tuple of (success: bool, error: Optional[Exception])
    """
    try:
        func(*args, **kwargs)
        return True, None
    except Exception as e:
        logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
        return False, e


def get_error_context(error: Exception) -> dict:
    """
    Get contextual information about an error for logging/debugging.

    Args:
        error: Exception to analyze

    Returns:
        Dictionary with error context
    """
    return {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "is_cli_error": isinstance(error, CLIError),
        "exit_code": getattr(error, "exit_code", 1),
        "traceback": traceback.format_exc(),
    }


def format_error_for_user(error: Exception) -> str:
    """
    Format an error message in a user-friendly way.

    Args:
        error: Exception to format

    Returns:
        Formatted error message
    """
    if isinstance(error, CLIError):
        return error.message
    elif isinstance(error, click.ClickException):
        return error.format_message()
    elif isinstance(error, FileNotFoundError):
        return f"File not found: {error.filename}"
    elif isinstance(error, PermissionError):
        return f"Permission denied: {error.filename}"
    elif isinstance(error, KeyboardInterrupt):
        return "Operation cancelled by user"
    else:
        return f"Unexpected error: {str(error)}"


class ErrorMetrics:
    """
    Track error metrics for telemetry and debugging.

    Usage:
        metrics = ErrorMetrics()
        metrics.record_error(error)
        stats = metrics.get_stats()
    """

    def __init__(self):
        self.errors: list[dict] = []
        self.error_counts: dict[str, int] = {}

    def record_error(self, error: Exception, command: Optional[str] = None):
        """Record an error occurrence."""
        error_type = type(error).__name__

        self.errors.append({
            "type": error_type,
            "message": str(error),
            "command": command,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })

        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

    def get_stats(self) -> dict:
        """Get error statistics."""
        return {
            "total_errors": len(self.errors),
            "error_counts": self.error_counts.copy(),
            "recent_errors": self.errors[-10:],  # Last 10 errors
        }

    def clear(self):
        """Clear all recorded errors."""
        self.errors.clear()
        self.error_counts.clear()


# Global error metrics instance
_error_metrics = ErrorMetrics()

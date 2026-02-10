"""
CLI Telemetry Collection

Anonymous usage statistics collection with opt-out support.
Helps improve the CLI by understanding how commands are used.

Privacy:
- No personal data collected
- No file contents or sensitive information
- Can be disabled with environment variable or config
- All data stays local by default
"""

import json
import logging
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .config import get_config

logger = logging.getLogger(__name__)


class TelemetryCollector:
    """
    Collects anonymous usage statistics for CLI commands.

    Features:
        - Command usage tracking
        - Performance metrics (execution time)
        - Error rate monitoring
        - Feature usage patterns
        - Opt-out support
    """

    def __init__(self, enabled: Optional[bool] = None):
        """
        Initialize telemetry collector.

        Args:
            enabled: Override telemetry setting (None = use config)
        """
        self.enabled = self._is_telemetry_enabled() if enabled is None else enabled
        self.telemetry_file = self._get_telemetry_file()
        self.session_id = self._generate_session_id()
        self.events: List[Dict] = []

    def _is_telemetry_enabled(self) -> bool:
        """
        Check if telemetry is enabled.

        Priority:
            1. FTE_TELEMETRY_DISABLED environment variable
            2. FTE_DISABLE_TELEMETRY environment variable (legacy)
            3. Config file setting
            4. Default: False (opt-in)

        Returns:
            True if telemetry is enabled
        """
        # Check environment variables for opt-out
        if os.getenv("FTE_TELEMETRY_DISABLED", "").lower() in ("1", "true", "yes"):
            return False

        if os.getenv("FTE_DISABLE_TELEMETRY", "").lower() in ("1", "true", "yes"):
            return False

        # Check config file
        try:
            config = get_config()
            return config.telemetry.enabled if hasattr(config, "telemetry") else False
        except Exception:
            # Default to disabled if config can't be loaded
            return False

    def _get_telemetry_file(self) -> Path:
        """Get path to telemetry data file."""
        try:
            config = get_config()
            vault_path = Path(config.vault.path)
        except Exception:
            vault_path = Path.home() / ".ai_employee_vault"

        telemetry_dir = vault_path / ".telemetry"
        telemetry_dir.mkdir(parents=True, exist_ok=True)

        return telemetry_dir / "usage_stats.json"

    def _generate_session_id(self) -> str:
        """Generate unique session ID for this CLI invocation."""
        import uuid

        return str(uuid.uuid4())

    def record_command(
        self,
        command: str,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error_type: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """
        Record a command execution.

        Args:
            command: Command name (e.g., "vault list")
            duration_ms: Execution time in milliseconds
            success: Whether command succeeded
            error_type: Type of error if failed
            metadata: Additional metadata (no sensitive data!)
        """
        if not self.enabled:
            return

        event = {
            "type": "command",
            "command": command,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "duration_ms": duration_ms,
            "success": success,
            "error_type": error_type,
            "metadata": metadata or {},
            "system": self._get_system_info(),
        }

        self.events.append(event)
        logger.debug(f"Telemetry: Recorded command '{command}'")

    def record_feature_use(
        self, feature: str, action: str, metadata: Optional[Dict] = None
    ):
        """
        Record feature usage.

        Args:
            feature: Feature name (e.g., "approval_workflow")
            action: Action taken (e.g., "review_approval")
            metadata: Additional metadata
        """
        if not self.enabled:
            return

        event = {
            "type": "feature",
            "feature": feature,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "metadata": metadata or {},
        }

        self.events.append(event)
        logger.debug(f"Telemetry: Recorded feature use '{feature}.{action}'")

    def record_performance(self, metric: str, value: float, unit: str = "ms"):
        """
        Record a performance metric.

        Args:
            metric: Metric name (e.g., "status_check_duration")
            value: Metric value
            unit: Unit of measurement (default: ms)
        """
        if not self.enabled:
            return

        event = {
            "type": "performance",
            "metric": metric,
            "value": value,
            "unit": unit,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
        }

        self.events.append(event)
        logger.debug(
            f"Telemetry: Recorded performance metric '{metric}': {value}{unit}"
        )

    def flush(self):
        """Write collected events to disk."""
        if not self.enabled or not self.events:
            return

        try:
            # Load existing data
            existing_data = []
            if self.telemetry_file.exists():
                try:
                    with open(self.telemetry_file, "r") as f:
                        existing_data = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Telemetry file corrupted, starting fresh")

            # Append new events
            existing_data.extend(self.events)

            # Keep only last 1000 events to prevent file from growing too large
            if len(existing_data) > 1000:
                existing_data = existing_data[-1000:]

            # Write back
            with open(self.telemetry_file, "w") as f:
                json.dump(existing_data, f, indent=2)

            logger.debug(f"Telemetry: Flushed {len(self.events)} events")
            self.events.clear()

        except Exception as e:
            logger.warning(f"Failed to flush telemetry: {e}")

    def get_stats(self) -> Dict:
        """
        Get telemetry statistics.

        Returns:
            Dictionary with usage statistics
        """
        if not self.telemetry_file.exists():
            return {
                "total_events": 0,
                "commands": {},
                "features": {},
            }

        try:
            with open(self.telemetry_file, "r") as f:
                events = json.load(f)

            # Aggregate statistics
            command_counts = {}
            feature_counts = {}

            for event in events:
                if event["type"] == "command":
                    cmd = event["command"]
                    command_counts[cmd] = command_counts.get(cmd, 0) + 1
                elif event["type"] == "feature":
                    feature = f"{event['feature']}.{event['action']}"
                    feature_counts[feature] = feature_counts.get(feature, 0) + 1

            return {
                "total_events": len(events),
                "commands": command_counts,
                "features": feature_counts,
                "file_path": str(self.telemetry_file),
            }

        except Exception as e:
            logger.warning(f"Failed to get telemetry stats: {e}")
            return {
                "total_events": 0,
                "commands": {},
                "features": {},
                "error": str(e),
            }

    def clear_data(self):
        """Delete all collected telemetry data."""
        try:
            if self.telemetry_file.exists():
                self.telemetry_file.unlink()
                logger.info("Telemetry data cleared")
        except Exception as e:
            logger.warning(f"Failed to clear telemetry data: {e}")

    def _get_system_info(self) -> Dict:
        """
        Get anonymous system information.

        Returns:
            Dictionary with system info (no personal data)
        """
        return {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "cli_version": "1.0.0",  # Would come from __version__
        }


# Global telemetry instance
_telemetry: Optional[TelemetryCollector] = None


def get_telemetry() -> TelemetryCollector:
    """
    Get global telemetry collector instance.

    Returns:
        TelemetryCollector instance
    """
    global _telemetry
    if _telemetry is None:
        _telemetry = TelemetryCollector()
    return _telemetry


def track_command(
    command: str, duration_ms: Optional[float] = None, success: bool = True
):
    """
    Convenience function to track command execution.

    Args:
        command: Command name
        duration_ms: Execution time in milliseconds
        success: Whether command succeeded
    """
    get_telemetry().record_command(command, duration_ms=duration_ms, success=success)


def track_feature(feature: str, action: str, metadata: Optional[Dict] = None):
    """
    Convenience function to track feature usage.

    Args:
        feature: Feature name
        action: Action taken
        metadata: Additional metadata
    """
    get_telemetry().record_feature_use(feature, action, metadata=metadata)


def flush_telemetry():
    """Flush telemetry data to disk."""
    get_telemetry().flush()


def disable_telemetry():
    """Disable telemetry collection (opt-out)."""
    global _telemetry
    _telemetry = TelemetryCollector(enabled=False)
    logger.info("Telemetry disabled")


def enable_telemetry():
    """Enable telemetry collection (opt-in)."""
    global _telemetry
    _telemetry = TelemetryCollector(enabled=True)
    logger.info("Telemetry enabled")


class TelemetryContext:
    """
    Context manager for timing command execution.

    Usage:
        with TelemetryContext("vault list"):
            # Command execution
            pass
    """

    def __init__(self, command: str):
        self.command = command
        self.start_time = None
        self.success = True
        self.error_type = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is not None:
            self.success = False
            self.error_type = exc_type.__name__

        get_telemetry().record_command(
            self.command,
            duration_ms=duration_ms,
            success=self.success,
            error_type=self.error_type,
        )

        # Don't suppress exceptions
        return False


# Privacy and transparency functions


def get_telemetry_status() -> Dict:
    """
    Get current telemetry status and information.

    Returns:
        Dictionary with telemetry status
    """
    telemetry = get_telemetry()

    return {
        "enabled": telemetry.enabled,
        "opt_out_methods": [
            "Set environment variable: FTE_TELEMETRY_DISABLED=1",
            "Set in config: telemetry.enabled: false",
        ],
        "data_location": str(telemetry.telemetry_file) if telemetry.enabled else None,
        "data_retention": "Last 1000 events only",
        "data_collected": [
            "Command names and execution time",
            "Success/failure status",
            "System platform and Python version",
            "Feature usage patterns",
        ],
        "data_not_collected": [
            "Personal information",
            "File contents or paths",
            "Sensitive configuration",
            "Network locations",
        ],
    }


def print_telemetry_info():
    """Print telemetry information in a user-friendly way."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
    status = get_telemetry_status()

    # Status panel
    enabled_text = (
        "[green]Enabled ✓[/green]" if status["enabled"] else "[red]Disabled ✗[/red]"
    )
    panel = Panel(
        f"Telemetry Status: {enabled_text}",
        title="[bold]FTE Telemetry[/bold]",
        border_style="blue",
    )
    console.print(panel)

    # Data collected table
    table = Table(title="Data Collection", show_header=False)
    table.add_column("Category", style="bold")
    table.add_column("Details")

    table.add_row("✓ Collected", "\n".join(status["data_collected"]))
    table.add_row("✗ Not Collected", "\n".join(status["data_not_collected"]))
    console.print(table)

    # Opt-out methods
    console.print("\n[bold]How to Disable:[/bold]")
    for method in status["opt_out_methods"]:
        console.print(f"  • {method}")

    if status["data_location"]:
        console.print(f"\n[dim]Data stored at: {status['data_location']}[/dim]")

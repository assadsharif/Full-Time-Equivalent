"""
Base Watcher abstract class.

Provides common functionality for all watchers:
- Retry logic with exponential backoff
- Checkpoint management
- Logging integration
- Filename sanitization
"""

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from src.watchers.checkpoint import CheckpointManager
from src.watchers.models import CheckpointData

# Try to import the logging module, fall back to standard logging
try:
    from src.logging import get_logger
except ImportError:
    import logging

    def get_logger(name: str):
        return logging.getLogger(name)


logger = get_logger(__name__)

T = TypeVar("T")


class PermanentError(Exception):
    """Error that should not be retried (e.g., authentication failure)."""

    pass


class TransientError(Exception):
    """Error that can be retried (e.g., network timeout)."""

    pass


class BaseWatcher(ABC):
    """
    Abstract base class for all watchers.

    Provides common functionality:
    - Exponential backoff retry logic
    - Checkpoint persistence
    - Logging integration
    - Filename sanitization

    Subclasses must implement:
    - run(): Main watcher loop
    - poll(): Fetch new items from data source
    """

    def __init__(
        self,
        vault_path: Path,
        watcher_name: str,
        poll_interval: int = 30,
        max_retries: int = 5,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ):
        """
        Initialize BaseWatcher.

        Args:
            vault_path: Path to Obsidian vault root
            watcher_name: Unique name for this watcher (used in checkpoints)
            poll_interval: Seconds between polls (default: 30)
            max_retries: Maximum retry attempts (default: 5)
            base_delay: Initial retry delay in seconds (default: 1.0)
            max_delay: Maximum retry delay in seconds (default: 60.0)
        """
        self.vault_path = Path(vault_path)
        self.watcher_name = watcher_name
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

        # Ensure vault directories exist
        self.inbox_path = self.vault_path / "Inbox"
        self.attachments_path = self.vault_path / "Attachments"
        self.inbox_path.mkdir(parents=True, exist_ok=True)
        self.attachments_path.mkdir(parents=True, exist_ok=True)

        # Initialize checkpoint manager
        self.checkpoint_manager = CheckpointManager()
        self._running = False

    @abstractmethod
    def run(self) -> None:
        """
        Main watcher loop.

        Must be implemented by subclasses. Should:
        1. Poll for new items
        2. Process each item
        3. Update checkpoint
        4. Sleep for poll_interval
        5. Handle errors with retry_with_backoff
        """
        pass

    @abstractmethod
    def poll(self) -> list[Any]:
        """
        Fetch new items from data source.

        Must be implemented by subclasses.

        Returns:
            List of new items to process
        """
        pass

    def stop(self) -> None:
        """Signal the watcher to stop."""
        self._running = False
        logger.info(f"Stop signal received for {self.watcher_name}")

    def retry_with_backoff(
        self,
        func: Callable[[], T],
        permanent_errors: tuple = (PermanentError,),
    ) -> Optional[T]:
        """
        Execute function with exponential backoff retry.

        Args:
            func: Function to retry
            permanent_errors: Exceptions that should not be retried

        Returns:
            Function result or None if all retries exhausted

        Raises:
            PermanentError: If a permanent error is encountered
        """
        for attempt in range(self.max_retries):
            try:
                return func()
            except permanent_errors as e:
                logger.error(
                    f"Permanent error in {self.watcher_name}, not retrying: {e}",
                    context={"error_type": type(e).__name__, "watcher": self.watcher_name},
                )
                raise
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Max retries exhausted in {self.watcher_name}: {e}",
                        context={
                            "error_type": type(e).__name__,
                            "watcher": self.watcher_name,
                            "attempts": self.max_retries,
                        },
                    )
                    return None

                delay = min(self.base_delay * (2**attempt), self.max_delay)
                logger.warning(
                    f"Retry {attempt + 1}/{self.max_retries} for {self.watcher_name} after {delay}s: {e}",
                    context={
                        "error_type": type(e).__name__,
                        "retry_delay": delay,
                        "attempt": attempt + 1,
                        "watcher": self.watcher_name,
                    },
                )
                time.sleep(delay)

        return None

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for cross-platform compatibility.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename safe for all platforms
        """
        # Strip leading/trailing whitespace first
        filename = filename.strip()

        # Strip spaces around the extension separator before other processing
        if "." in filename:
            name, ext = filename.rsplit(".", 1)
            filename = name.rstrip() + "." + ext.lstrip()

        # Remove invalid characters for Windows/Linux/macOS
        invalid_chars = '<>:"/\\|?*\0'
        for char in invalid_chars:
            filename = filename.replace(char, "_")

        # Replace remaining internal whitespace with underscores
        filename = filename.replace(" ", "_")

        # Remove leading/trailing dots
        filename = filename.strip(".")

        # Truncate to 255 characters (filesystem limit)
        if len(filename) > 255:
            if "." in filename:
                name, ext = filename.rsplit(".", 1)
                max_name_len = 255 - len(ext) - 1
                filename = name[:max_name_len] + "." + ext
            else:
                filename = filename[:255]

        return filename

    def load_checkpoint(self) -> CheckpointData:
        """Load checkpoint for this watcher."""
        return self.checkpoint_manager.load(self.watcher_name)

    def save_checkpoint(self, checkpoint: CheckpointData) -> None:
        """Save checkpoint for this watcher."""
        self.checkpoint_manager.save(checkpoint)

    def increment_events_processed(self, checkpoint: CheckpointData) -> CheckpointData:
        """Increment events processed counter and save checkpoint."""
        checkpoint.events_processed += 1
        self.save_checkpoint(checkpoint)
        return checkpoint

    def increment_errors(self, checkpoint: CheckpointData) -> CheckpointData:
        """Increment errors counter and save checkpoint."""
        checkpoint.errors_count += 1
        self.save_checkpoint(checkpoint)
        return checkpoint

"""
Checkpoint Manager for watcher scripts.

Persists watcher state to enable resumption after restarts
and prevent duplicate processing.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

# Try to import the logging module, fall back to standard logging
try:
    from src.logging import get_logger
except ImportError:
    import logging

    def get_logger(name: str):
        return logging.getLogger(name)


from src.watchers.models import CheckpointData

logger = get_logger(__name__)


class CheckpointManager:
    """
    Manages checkpoint persistence for watchers.

    Checkpoints track:
    - Last processed item ID (for idempotency)
    - Last poll timestamp
    - Event processing statistics

    Files are stored in .fte/watchers/<watcher_name>.checkpoint.json
    """

    def __init__(self, checkpoint_dir: Path | None = None):
        """
        Initialize CheckpointManager.

        Args:
            checkpoint_dir: Directory for checkpoint files
                           (default: .fte/watchers/)
        """
        if checkpoint_dir is None:
            # Find project root by looking for .fte directory
            current = Path.cwd()
            while current != current.parent:
                if (current / ".fte").exists():
                    checkpoint_dir = current / ".fte" / "watchers"
                    break
                current = current.parent
            else:
                # Fallback to current directory
                checkpoint_dir = Path(".fte") / "watchers"

        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _get_checkpoint_path(self, watcher_name: str) -> Path:
        """Get checkpoint file path for a watcher."""
        safe_name = watcher_name.replace("/", "_").replace("\\", "_")
        return self.checkpoint_dir / f"{safe_name}.checkpoint.json"

    def load(self, watcher_name: str) -> CheckpointData:
        """
        Load checkpoint for a watcher.

        Args:
            watcher_name: Name of the watcher

        Returns:
            CheckpointData (new checkpoint if file doesn't exist)
        """
        checkpoint_path = self._get_checkpoint_path(watcher_name)

        if not checkpoint_path.exists():
            logger.info(f"No checkpoint found for {watcher_name}, creating new")
            return CheckpointData(watcher_name=watcher_name)

        try:
            data = json.loads(checkpoint_path.read_text(encoding="utf-8"))

            # Parse datetime strings back to datetime objects
            if "last_poll_time" in data and isinstance(data["last_poll_time"], str):
                data["last_poll_time"] = datetime.fromisoformat(
                    data["last_poll_time"].replace("Z", "+00:00")
                )

            checkpoint = CheckpointData(**data)
            logger.debug(
                f"Loaded checkpoint for {watcher_name}",
                extra={
                    "last_processed_id": checkpoint.last_processed_id,
                    "events_processed": checkpoint.events_processed,
                },
            )
            return checkpoint

        except json.JSONDecodeError as e:
            logger.warning(
                f"Corrupt checkpoint for {watcher_name}, creating new: {e}"
            )
            return CheckpointData(watcher_name=watcher_name)
        except Exception as e:
            logger.error(f"Error loading checkpoint for {watcher_name}: {e}")
            return CheckpointData(watcher_name=watcher_name)

    def save(self, checkpoint: CheckpointData) -> None:
        """
        Save checkpoint for a watcher.

        Args:
            checkpoint: CheckpointData to save
        """
        checkpoint_path = self._get_checkpoint_path(checkpoint.watcher_name)

        # Update last poll time
        checkpoint.last_poll_time = datetime.now(timezone.utc)

        # Convert to dict and handle datetime serialization
        data = checkpoint.model_dump()
        if isinstance(data.get("last_poll_time"), datetime):
            data["last_poll_time"] = data["last_poll_time"].isoformat()

        # Write atomically
        temp_path = checkpoint_path.with_suffix(".tmp")
        try:
            temp_path.write_text(
                json.dumps(data, indent=2, default=str),
                encoding="utf-8",
            )
            temp_path.rename(checkpoint_path)
            logger.debug(
                f"Saved checkpoint for {checkpoint.watcher_name}",
                extra={"events_processed": checkpoint.events_processed},
            )
        except Exception as e:
            logger.error(f"Error saving checkpoint for {checkpoint.watcher_name}: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise

    def delete(self, watcher_name: str) -> bool:
        """
        Delete checkpoint for a watcher.

        Args:
            watcher_name: Name of the watcher

        Returns:
            True if checkpoint was deleted, False if it didn't exist
        """
        checkpoint_path = self._get_checkpoint_path(watcher_name)

        if checkpoint_path.exists():
            checkpoint_path.unlink()
            logger.info(f"Deleted checkpoint for {watcher_name}")
            return True

        return False

    def list_checkpoints(self) -> list[str]:
        """
        List all watchers with checkpoints.

        Returns:
            List of watcher names
        """
        checkpoints = []
        for path in self.checkpoint_dir.glob("*.checkpoint.json"):
            watcher_name = path.stem.replace(".checkpoint", "")
            checkpoints.append(watcher_name)
        return checkpoints

    def get_stats(self, watcher_name: str) -> dict:
        """
        Get statistics for a watcher from its checkpoint.

        Args:
            watcher_name: Name of the watcher

        Returns:
            Dictionary with stats (events_processed, errors_count, etc.)
        """
        checkpoint = self.load(watcher_name)
        return {
            "watcher_name": checkpoint.watcher_name,
            "last_processed_id": checkpoint.last_processed_id,
            "last_poll_time": checkpoint.last_poll_time.isoformat()
            if checkpoint.last_poll_time
            else None,
            "events_processed": checkpoint.events_processed,
            "errors_count": checkpoint.errors_count,
            "error_rate": (
                checkpoint.errors_count / checkpoint.events_processed * 100
                if checkpoint.events_processed > 0
                else 0
            ),
        }

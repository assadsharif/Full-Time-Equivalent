"""
File System Watcher.

Monitors directories for new files and creates Markdown tasks in the vault.
Uses watchdog library for cross-platform file system events.

Constitutional Compliance:
- Section 2: Writes to vault (source of truth)
- Section 4: Additive only (no control plane modifications)
- Section 8: All events logged
"""

import hashlib
import mimetypes
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import pathspec
except ImportError:
    pathspec = None

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent
except ImportError:
    Observer = None
    FileSystemEventHandler = object
    FileCreatedEvent = None

# Try to import the logging module, fall back to standard logging
try:
    from src.fte_logging import get_logger
except ImportError:
    import logging

    def get_logger(name: str):
        return logging.getLogger(name)


from .base_watcher import BaseWatcher
from .markdown_formatter import MarkdownFormatter
from .models import FileEvent

logger = get_logger(__name__)


class FileSystemWatcher(BaseWatcher, FileSystemEventHandler):
    """
    File System Watcher that monitors directories for new files.

    Uses watchdog library for efficient event-driven file monitoring
    (inotify on Linux, FSEvents on macOS, ReadDirectoryChangesW on Windows).

    Example:
        watcher = FileSystemWatcher(
            vault_path=Path("./vault"),
            watch_path=Path("./Input_Documents"),
        )
        watcher.run()
    """

    def __init__(
        self,
        vault_path: Path,
        watch_path: Path,
        recursive: bool = True,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        max_hash_size: int = 1073741824,  # 1GB
        **kwargs,
    ):
        """
        Initialize FileSystemWatcher.

        Args:
            vault_path: Path to Obsidian vault root
            watch_path: Directory to monitor for new files
            recursive: Monitor subdirectories recursively
            include_patterns: Glob patterns for files to include (None = all)
            exclude_patterns: Glob patterns for files to exclude
            max_hash_size: Skip hash for files larger than this (bytes)
            **kwargs: Additional arguments for BaseWatcher
        """
        super().__init__(vault_path, watcher_name="filesystem", **kwargs)

        self.watch_path = Path(watch_path)
        self.recursive = recursive
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or [
            "*.tmp",
            "*.swp",
            "*.bak",
            "~*",
            ".DS_Store",
            "Thumbs.db",
        ]
        self.max_hash_size = max_hash_size

        # Initialize formatter
        self.formatter = MarkdownFormatter()

        # Load .gitignore patterns
        self._gitignore_spec = self._load_gitignore()

        # Track processed files to avoid duplicates
        self._processed_files: set[str] = set()

        # Observer instance (set in run())
        self._observer: Optional[Observer] = None

    def _load_gitignore(self) -> Optional["pathspec.PathSpec"]:
        """Load .gitignore patterns from watch directory."""
        if pathspec is None:
            logger.warning(
                "pathspec library not installed, .gitignore patterns disabled"
            )
            return None

        gitignore_path = self.watch_path / ".gitignore"
        if not gitignore_path.exists():
            return None

        try:
            patterns = gitignore_path.read_text().splitlines()
            # Filter out empty lines and comments
            patterns = [p for p in patterns if p.strip() and not p.startswith("#")]
            spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
            logger.info(f"Loaded {len(patterns)} .gitignore patterns")
            return spec
        except Exception as e:
            logger.warning(f"Failed to load .gitignore: {e}")
            return None

    def _should_ignore(self, file_path: Path) -> bool:
        """
        Check if file should be ignored based on patterns.

        Args:
            file_path: Path to check

        Returns:
            True if file should be ignored
        """
        filename = file_path.name
        relative_path = str(file_path.relative_to(self.watch_path))

        # Check exclude patterns
        for pattern in self.exclude_patterns:
            if file_path.match(pattern):
                logger.debug(f"Ignoring {filename}: matches exclude pattern {pattern}")
                return True

        # Check .gitignore patterns
        if self._gitignore_spec and self._gitignore_spec.match_file(relative_path):
            logger.debug(f"Ignoring {filename}: matches .gitignore pattern")
            return True

        # Check include patterns (if specified)
        if self.include_patterns:
            matched = any(file_path.match(p) for p in self.include_patterns)
            if not matched:
                logger.debug(f"Ignoring {filename}: doesn't match include patterns")
                return True

        return False

    def _compute_hash(self, file_path: Path) -> str:
        """
        Compute SHA256 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hash as hex string, or empty string if skipped
        """
        try:
            file_size = file_path.stat().st_size

            # Skip hash for large files
            if self.max_hash_size > 0 and file_size > self.max_hash_size:
                logger.warning(
                    f"Skipping hash for large file: {file_path.name} ({file_size} bytes)"
                )
                return ""

            sha256 = hashlib.sha256()
            with file_path.open("rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256.update(chunk)

            return sha256.hexdigest()

        except Exception as e:
            logger.error(f"Error computing hash for {file_path}: {e}")
            return ""

    def _detect_mime_type(self, file_path: Path) -> str:
        """
        Detect MIME type of file.

        Args:
            file_path: Path to file

        Returns:
            MIME type string
        """
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "application/octet-stream"

    def on_created(self, event) -> None:
        """
        Handle file creation event.

        Called by watchdog when a new file is detected.
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check if should be ignored
        if self._should_ignore(file_path):
            return

        # Avoid duplicate processing
        file_key = str(file_path.resolve())
        if file_key in self._processed_files:
            logger.debug(f"Skipping already processed file: {file_path.name}")
            return

        logger.info(f"New file detected: {file_path.name}")

        try:
            # Wait briefly for file to be fully written
            time.sleep(0.5)

            # Get file metadata
            stat = file_path.stat()
            file_size = stat.st_size
            file_type = self._detect_mime_type(file_path)
            file_hash = self._compute_hash(file_path)

            # Create FileEvent
            event_model = FileEvent(
                id="",  # Will be generated
                file_path=file_path,
                file_name=file_path.name,
                file_size=file_size,
                file_type=file_type,
                file_hash=file_hash,
                event_type="created",
            )
            event_model.id = event_model.generate_id()

            # Format as Markdown
            markdown_content = self.formatter.format_file_event(event_model)

            # Write to vault
            output_filename = self._sanitize_filename(f"file_{event_model.id}.md")
            output_path = self.inbox_path / output_filename
            self.formatter.write_to_file(markdown_content, output_path)

            # Mark as processed
            self._processed_files.add(file_key)

            # Update checkpoint
            checkpoint = self.load_checkpoint()
            checkpoint.last_processed_id = event_model.id
            self.increment_events_processed(checkpoint)

            logger.info(
                f"Created task for file: {file_path.name}",
                context={
                    "file_size": file_size,
                    "file_type": file_type,
                    "task_id": event_model.id,
                },
            )

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            checkpoint = self.load_checkpoint()
            self.increment_errors(checkpoint)

    def poll(self) -> list:
        """
        Poll is not used for filesystem watcher (event-driven).

        Returns empty list as events are handled by on_created().
        """
        return []

    def run(self) -> None:
        """
        Start file system observer.

        Runs until stop() is called or KeyboardInterrupt.
        """
        if Observer is None:
            raise ImportError(
                "watchdog library required for FileSystemWatcher. "
                "Install with: pip install watchdog"
            )

        # Ensure watch path exists
        if not self.watch_path.exists():
            logger.warning(f"Watch path does not exist, creating: {self.watch_path}")
            self.watch_path.mkdir(parents=True, exist_ok=True)

        self._running = True
        self._observer = Observer()
        self._observer.schedule(self, str(self.watch_path), recursive=self.recursive)
        self._observer.start()

        logger.info(
            f"FileSystem watcher started",
            context={
                "watch_path": str(self.watch_path),
                "recursive": self.recursive,
                "vault_path": str(self.vault_path),
            },
        )

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("FileSystem watcher interrupted")
        finally:
            self._observer.stop()
            self._observer.join()
            logger.info("FileSystem watcher stopped")

    def stop(self) -> None:
        """Stop the file system observer."""
        super().stop()
        if self._observer:
            self._observer.stop()


def main():
    """Entry point for filesystem watcher."""
    import argparse

    parser = argparse.ArgumentParser(description="FileSystem Watcher for Digital FTE")
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=Path("./vault"),
        help="Path to Obsidian vault",
    )
    parser.add_argument(
        "--watch-path",
        type=Path,
        default=Path("./Input_Documents"),
        help="Directory to monitor",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="Monitor subdirectories recursively",
    )

    args = parser.parse_args()

    watcher = FileSystemWatcher(
        vault_path=args.vault_path,
        watch_path=args.watch_path,
        recursive=args.recursive,
    )
    watcher.run()


if __name__ == "__main__":
    main()

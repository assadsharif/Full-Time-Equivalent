"""
Atomic file operation wrappers for File-Driven Control Plane

Constitutional compliance:
- Section 2 (Source of Truth): File operations maintain filesystem as truth
- Section 4 (File-Driven Control Plane): Atomic moves ensure state integrity
- Section 9 (Error Handling): Explicit error handling, no silent failures
"""

from pathlib import Path
from typing import Optional

from src.control_plane.errors import FileOperationError


def atomic_move(source: Path, destination: Path) -> None:
    """
    Atomically move a file from source to destination.

    Uses pathlib.Path.rename() which is atomic on POSIX systems.
    Constitutional requirement (Section 4): File moves must be atomic.

    Args:
        source: Source file path
        destination: Destination file path

    Raises:
        FileOperationError: If move fails (disk full, permissions, etc.)
    """
    try:
        source.rename(destination)
    except OSError as e:
        raise FileOperationError(
            f"Failed to move {source} to {destination}: {e}"
        ) from e


def safe_read(file_path: Path) -> str:
    """
    Safely read file contents with error handling.

    Args:
        file_path: Path to file to read

    Returns:
        File contents as string

    Raises:
        FileOperationError: If read fails (not found, permissions, etc.)
    """
    try:
        return file_path.read_text(encoding="utf-8")
    except OSError as e:
        raise FileOperationError(
            f"Failed to read {file_path}: {e}"
        ) from e


def safe_write(file_path: Path, content: str) -> None:
    """
    Safely write content to file with error handling.

    Args:
        file_path: Path to file to write
        content: Content to write

    Raises:
        FileOperationError: If write fails (disk full, permissions, etc.)
    """
    try:
        file_path.write_text(content, encoding="utf-8")
    except OSError as e:
        raise FileOperationError(
            f"Failed to write {file_path}: {e}"
        ) from e

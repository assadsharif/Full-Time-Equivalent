"""
Integrity Checker — SHA256 tamper detection for approval files.

The body (everything after the closing ``---`` of YAML frontmatter) is
hashed at creation time and the digest stored *inside* the frontmatter.
Before an approval is acted on, the body is re-hashed and compared.
Any mismatch means the file was edited after creation.
"""

import hashlib
from pathlib import Path
from typing import Optional


class IntegrityChecker:
    """Static helpers — no instance state required."""

    # ------------------------------------------------------------------
    # Hash helpers
    # ------------------------------------------------------------------

    @staticmethod
    def compute_hash(content: str) -> str:
        """SHA256 hex-digest of *content*."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def verify(content: str, expected_hash: str) -> bool:
        """True when the live hash of *content* matches *expected_hash*."""
        return IntegrityChecker.compute_hash(content) == expected_hash

    # ------------------------------------------------------------------
    # File-level helpers
    # ------------------------------------------------------------------

    @staticmethod
    def body_content(file_path: Path) -> str:
        """Return everything after the frontmatter closing ``---``."""
        text = file_path.read_text()
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                return text[end + 3:].lstrip("\n")
        return text

    @staticmethod
    def extract_hash(file_path: Path) -> Optional[str]:
        """Pull the ``integrity_hash`` value out of YAML frontmatter."""
        for line in file_path.read_text().splitlines():
            if line.startswith("integrity_hash:"):
                value = line.split(":", 1)[1].strip()
                return value if value else None
        return None

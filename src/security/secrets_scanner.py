"""
Secrets Scanner — detect exposed credentials in files and text (spec 004 Bronze).

Uses ``detect_secrets`` when available (primary backend).  Falls back to a
curated set of regex patterns that catch common credential formats.  Findings
never include the actual secret value — only a redacted context line.
"""

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from detect_secrets import SecretsCollection
    from detect_secrets.settings import default_settings

    _DETECT_SECRETS_AVAILABLE = True
except ImportError:
    _DETECT_SECRETS_AVAILABLE = False

# ---------------------------------------------------------------------------
# Fallback regex patterns
# ---------------------------------------------------------------------------

_FALLBACK_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("AWS Access Key", re.compile(r"AKIA[A-Z0-9]{16}")),
    ("API Key", re.compile(r'(?i)api[_-]?key\s*[=:]\s*["\']?([A-Za-z0-9_-]{20,})')),
    ("Password", re.compile(r'(?i)password\s*[=:]\s*["\']?([^\s"\']{8,})')),
    (
        "Secret Key",
        re.compile(r'(?i)secret[_-]?key\s*[=:]\s*["\']?([A-Za-z0-9_-]{20,})'),
    ),
    ("Token", re.compile(r'(?i)token\s*[=:]\s*["\']?([A-Za-z0-9_./-]{30,})')),
]


@dataclass
class ScanFinding:
    """A single secrets-scan finding (secret value is never stored)."""

    file_path: Optional[str]
    line_number: Optional[int]
    secret_type: str
    redacted_context: str


class SecretsScanner:
    """Scan files or text for exposed credentials."""

    def scan_text(self, text: str, source: str = "<text>") -> list[ScanFinding]:
        """Scan a string for secrets.

        When detect_secrets is available the text is written to a temporary
        file so that its file-based scanner can be used.  Otherwise the
        regex fallback is used directly.
        """
        if _DETECT_SECRETS_AVAILABLE:
            return self._scan_text_via_tempfile(text, source)
        return self._scan_with_fallback(text, source)

    def scan_file(self, path: Path) -> list[ScanFinding]:
        """Scan a single file for secrets."""
        if not path.exists():
            return []
        if _DETECT_SECRETS_AVAILABLE:
            return self._scan_file_detect_secrets(path)
        text = path.read_text(encoding="utf-8", errors="replace")
        return self._scan_with_fallback(text, source=str(path))

    def scan_directory(
        self, directory: Path, glob: str = "**/*.md"
    ) -> list[ScanFinding]:
        """Scan all matching files in a directory tree."""
        findings: list[ScanFinding] = []
        for path in sorted(directory.glob(glob)):
            if path.is_file():
                findings.extend(self.scan_file(path))
        return findings

    # ------------------------------------------------------------------
    # detect_secrets backend
    # ------------------------------------------------------------------

    def _scan_file_detect_secrets(self, path: Path) -> list[ScanFinding]:
        findings: list[ScanFinding] = []
        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
        with default_settings():
            sc = SecretsCollection()
            sc.scan_file(str(path))
            for _fname, secrets in sc.data.items():
                for secret in secrets:
                    context = (
                        lines[secret.line_number - 1]
                        if secret.line_number <= len(lines)
                        else ""
                    )
                    findings.append(
                        ScanFinding(
                            file_path=str(path),
                            line_number=secret.line_number,
                            secret_type=secret.type,
                            redacted_context=_redact(context),
                        )
                    )
        return findings

    def _scan_text_via_tempfile(self, text: str, source: str) -> list[ScanFinding]:
        fd, tmp_path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(text)
            raw = self._scan_file_detect_secrets(Path(tmp_path))
            # Replace the temp path with the original source label
            return [
                ScanFinding(
                    file_path=source,
                    line_number=f.line_number,
                    secret_type=f.secret_type,
                    redacted_context=f.redacted_context,
                )
                for f in raw
            ]
        finally:
            os.unlink(tmp_path)

    # ------------------------------------------------------------------
    # Regex fallback backend
    # ------------------------------------------------------------------

    def _scan_with_fallback(self, text: str, source: str) -> list[ScanFinding]:
        findings: list[ScanFinding] = []
        seen: set[tuple[int, str]] = set()  # deduplicate per (line, type)
        for line_num, line in enumerate(text.split("\n"), start=1):
            for secret_type, pattern in _FALLBACK_PATTERNS:
                if pattern.search(line) and (line_num, secret_type) not in seen:
                    seen.add((line_num, secret_type))
                    findings.append(
                        ScanFinding(
                            file_path=source,
                            line_number=line_num,
                            secret_type=secret_type,
                            redacted_context=_redact(line),
                        )
                    )
        return findings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _redact(line: str) -> str:
    """Replace credential-like values with [REDACTED] and truncate."""
    redacted = re.sub(
        r'([=:]\s*["\']?)([A-Za-z0-9_/+=.-]{20,})',
        r"\1[REDACTED]",
        line,
    )
    return redacted[:120]

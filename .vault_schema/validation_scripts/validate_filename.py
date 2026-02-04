#!/usr/bin/env python3
"""
Filename Validation and Sanitization

Validates that vault files follow the naming conventions defined in
naming_conventions.md.  Also provides a sanitize() helper that converts
arbitrary strings into convention-compliant filenames.
"""

import re
import sys
import unicodedata
from pathlib import Path
from typing import List, Tuple


# --- Compiled regex patterns for each folder context ---

TASK_PATTERN = re.compile(r"^TASK-\d{8}-\d{3}\.md$")
APPROVAL_PATTERN = re.compile(r"^APR-\d{8}-\d{3}\.md$")
BRIEFING_PATTERN = re.compile(r"^BRIEF-\d{8}\.md$")
GENERAL_MD_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*\.md$")
ATTACHMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*\.\w+$")

# Map folder names (lowercase) to their expected pattern
FOLDER_PATTERNS: dict[str, re.Pattern] = {
    "inbox":          TASK_PATTERN,
    "needs_action":   TASK_PATTERN,
    "in_progress":    TASK_PATTERN,
    "done":           TASK_PATTERN,
    "approvals":      APPROVAL_PATTERN,
    "briefings":      BRIEFING_PATTERN,
    "attachments":    ATTACHMENT_PATTERN,
    "templates":      GENERAL_MD_PATTERN,
}

MAX_STEM_LENGTH = 200


# ---------------------------------------------------------------------------
# Sanitization
# ---------------------------------------------------------------------------


def sanitize(name: str, max_length: int = MAX_STEM_LENGTH) -> str:
    """
    Convert an arbitrary string into a convention-safe filename stem.

    Steps:
      1. NFKD-normalise and drop non-ASCII combining marks
      2. Replace runs of whitespace/special chars with a single hyphen
      3. Strip leading/trailing hyphens and underscores
      4. Truncate to max_length
      5. If empty after sanitization, return 'untitled'

    Args:
        name: Raw input string
        max_length: Maximum character length for the stem

    Returns:
        Sanitized filename stem (no extension)
    """
    # Normalise unicode → ASCII-safe approximation
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")

    # Replace anything that isn't alphanumeric, hyphen, or underscore
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", ascii_only)

    # Collapse multiple hyphens
    cleaned = re.sub(r"-+", "-", cleaned)

    # Strip leading/trailing hyphens and underscores
    cleaned = cleaned.strip("-_")

    # Truncate
    cleaned = cleaned[:max_length]

    return cleaned or "untitled"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class FilenameValidationWarning:
    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message

    def __str__(self):
        return f"  ⚠️  {self.path}: {self.message}"


class FilenameValidationError:
    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message

    def __str__(self):
        return f"  ❌ {self.path}: {self.message}"


def validate_filename(filename: str, folder: str) -> Tuple[List[FilenameValidationError], List[FilenameValidationWarning]]:
    """
    Validate a single filename against the rules for its folder.

    Args:
        filename: The filename (basename, no directory)
        folder: The folder it resides in

    Returns:
        Tuple of (errors, warnings)
    """
    errors: List[FilenameValidationError] = []
    warnings: List[FilenameValidationWarning] = []
    rel = f"{folder}/{filename}"

    # Skip hidden files and .gitkeep
    if filename.startswith(".") or filename == ".gitkeep":
        return errors, warnings

    # Check stem length
    stem = Path(filename).stem
    if len(stem) > MAX_STEM_LENGTH:
        errors.append(FilenameValidationError(rel, f"stem length {len(stem)} exceeds {MAX_STEM_LENGTH}"))

    # Look up pattern for this folder
    pattern = FOLDER_PATTERNS.get(folder.lower())
    if pattern is None:
        # Unknown folder — just check general safety
        if not GENERAL_MD_PATTERN.match(filename) and not ATTACHMENT_PATTERN.match(filename):
            warnings.append(FilenameValidationWarning(rel, "does not match general naming rules"))
        return errors, warnings

    if not pattern.match(filename):
        # For attachments, only warn
        if folder.lower() == "attachments":
            warnings.append(FilenameValidationWarning(rel, f"does not match attachment pattern (expected: [A-Za-z0-9_-]+.ext)"))
        else:
            errors.append(FilenameValidationError(rel, f"does not match expected pattern for {folder}/"))

    return errors, warnings


def validate_vault_filenames(vault_path: Path) -> Tuple[List[FilenameValidationError], List[FilenameValidationWarning], int]:
    """
    Walk all vault folders and validate filenames.

    Returns:
        Tuple of (errors, warnings, files_checked)
    """
    all_errors: List[FilenameValidationError] = []
    all_warnings: List[FilenameValidationWarning] = []
    checked = 0

    for folder_name in FOLDER_PATTERNS:
        # Map convention folder name to actual directory name
        dir_name = {
            "inbox": "Inbox",
            "needs_action": "Needs_Action",
            "in_progress": "In_Progress",
            "done": "Done",
            "approvals": "Approvals",
            "briefings": "Briefings",
            "attachments": "Attachments",
            "templates": "Templates",
        }.get(folder_name, folder_name)

        folder_path = vault_path / dir_name
        if not folder_path.is_dir():
            continue

        for f in folder_path.iterdir():
            if f.is_file():
                errs, warns = validate_filename(f.name, folder_name)
                all_errors.extend(errs)
                all_warnings.extend(warns)
                checked += 1

    return all_errors, all_warnings, checked


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_filename.py <vault_path>")
        sys.exit(1)

    vault_path = Path(sys.argv[1]).expanduser().resolve()
    if not vault_path.is_dir():
        print(f"❌ Path is not a directory: {vault_path}")
        sys.exit(1)

    print(f"🔍 Validating filenames in: {vault_path}\n")
    errors, warnings, checked = validate_vault_filenames(vault_path)

    print(f"   Checked {checked} file(s)")

    if warnings:
        print(f"\n⚠️  {len(warnings)} warning(s):")
        for w in warnings:
            print(w)

    if errors:
        print(f"\n🚨 {len(errors)} naming violation(s):")
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print("\n✅ All filenames valid")
        sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
package_skill.py — Bundle a skill directory into a portable .skill.tar.gz

Usage:
    python scripts/package_skill.py <skill-dir> [--output <path>]

The script:
  1. Validates SKILL.md exists and passes syntax-level validation.
  2. Collects SKILL.md + optional sub-directories (references/, scripts/).
  3. Writes a tar.gz archive named <slug>.skill.tar.gz.
  4. Prints a manifest of the included files.

Exit codes:
  0 — packaged successfully
  1 — validation failure or missing SKILL.md
  2 — I/O error
"""

import argparse
import json
import sys
import tarfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Validation (inline subset — avoids importing the full validate_skill module
# to keep this script self-contained)
# ---------------------------------------------------------------------------

def _extract_frontmatter(content: str) -> dict | None:
    """Return parsed YAML frontmatter or None if malformed."""
    try:
        import yaml
    except ImportError:
        # Fallback: just check the fences exist
        if content.startswith("---\n") and "\n---\n" in content[4:]:
            return {"_raw": True}
        return None

    if not content.startswith("---\n"):
        return None
    end = content.index("\n---\n", 4) if "\n---\n" in content[4:] else -1
    if end == -1:
        return None
    raw_yaml = content[4:end]
    try:
        return yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError:
        return None


REQUIRED_FIELDS = [
    "name", "version", "description", "triggers", "command",
    "category", "tags", "safety_level", "author", "created",
]


def _validate_syntax(skill_md: Path) -> list[str]:
    """Return a list of error strings; empty list means PASS."""
    errors: list[str] = []
    content = skill_md.read_text(encoding="utf-8")
    fm = _extract_frontmatter(content)
    if fm is None:
        errors.append("SKILL.md: could not parse YAML frontmatter")
        return errors
    for field in REQUIRED_FIELDS:
        if field not in fm:
            errors.append(f"Missing required frontmatter field: {field}")
    return errors


# ---------------------------------------------------------------------------
# Packaging
# ---------------------------------------------------------------------------

# Sub-directories that are eligible for inclusion in the archive
INCLUDABLE_SUBDIRS = {"references", "scripts", "assets"}


def _collect_files(skill_dir: Path) -> list[Path]:
    """Return all files to include, relative paths."""
    files: list[Path] = []
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        files.append(skill_md)
    for subdir_name in INCLUDABLE_SUBDIRS:
        subdir = skill_dir / subdir_name
        if subdir.is_dir():
            files.extend(subdir.rglob("*"))
    # Filter to regular files only
    return [f for f in files if f.is_file()]


def package(skill_dir: Path, output: Path | None = None) -> tuple[Path, list[str]]:
    """
    Validate and package a skill directory.

    Returns:
        (archive_path, manifest_lines)

    Raises:
        SystemExit on validation failure.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"❌ SKILL.md not found in {skill_dir}", file=sys.stderr)
        sys.exit(1)

    # --- validate ---
    errors = _validate_syntax(skill_md)
    if errors:
        print("❌ Validation failed:", file=sys.stderr)
        for e in errors:
            print(f"   • {e}", file=sys.stderr)
        sys.exit(1)

    # --- collect ---
    files = _collect_files(skill_dir)
    if not files:
        print("❌ No files to package", file=sys.stderr)
        sys.exit(1)

    # --- determine archive path ---
    slug = skill_dir.resolve().name  # e.g. "fte-vault-init"
    if output is None:
        output = skill_dir.parent / f"{slug}.skill.tar.gz"
    output.parent.mkdir(parents=True, exist_ok=True)

    # --- write archive ---
    manifest: list[str] = []
    with tarfile.open(output, "w:gz") as tar:
        for filepath in files:
            arcname = filepath.relative_to(skill_dir)
            tar.add(filepath, arcname=str(arcname))
            manifest.append(str(arcname))

    return output, manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Package a skill directory into a .skill.tar.gz archive."
    )
    parser.add_argument(
        "skill_dir",
        type=Path,
        help="Path to the skill directory containing SKILL.md",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output archive path (default: <skill-dir>/../<slug>.skill.tar.gz)",
    )
    args = parser.parse_args()

    skill_dir = args.skill_dir.resolve()
    if not skill_dir.is_dir():
        print(f"❌ Not a directory: {skill_dir}", file=sys.stderr)
        sys.exit(2)

    try:
        archive_path, manifest = package(skill_dir, args.output)
    except OSError as exc:
        print(f"❌ I/O error: {exc}", file=sys.stderr)
        sys.exit(2)

    # --- report ---
    print(f"✅ Packaged: {archive_path}")
    print(f"   Size: {archive_path.stat().st_size} bytes")
    print(f"   Files ({len(manifest)}):")
    for entry in manifest:
        print(f"     - {entry}")


if __name__ == "__main__":
    main()

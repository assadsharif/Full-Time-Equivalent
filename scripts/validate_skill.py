#!/usr/bin/env python3
"""
validate_skill.py — Validate an Agent Skill against the schema.

Usage:
    python scripts/validate_skill.py <skill_dir_or_name> [--level syntax|complete|quality]

Levels (cumulative):
    syntax   — YAML frontmatter parses; required fields present
    complete — All required body sections present (default)
    quality  — Completeness + ≥2 examples, ≥3 steps, error-handling section

Exit codes:
    0 = valid at requested level
    1 = validation errors
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List

import yaml


# ---------------------------------------------------------------------------
# Required frontmatter fields (syntax level)
# ---------------------------------------------------------------------------
REQUIRED_FIELDS = [
    "name", "version", "description", "triggers", "command",
    "category", "tags", "safety_level", "approval_required",
    "destructive", "author", "created", "last_updated",
]

VALID_SAFETY_LEVELS = {"low", "medium", "high"}

VALID_CATEGORIES = {
    "task", "query", "config", "diagnostic", "workflow", "git",
    "vault", "briefing", "watcher", "orchestrator", "security", "approval",
}

# Required body section headings (complete level)
REQUIRED_SECTIONS = ["Overview", "Instructions", "Examples", "Validation"]

# Leftover placeholder markers that must not survive to commit
PLACEHOLDER_PATTERNS = [
    re.compile(r"<[A-Za-z_|]+>"),                 # <placeholder>
    re.compile(r"\bYYYY-MM-DD\b"),                # literal date placeholder
    re.compile(r"trigger phrase \d"),             # unfilled trigger
    re.compile(r"tag\d"),                         # unfilled tags
]


# ---------------------------------------------------------------------------
# Result accumulator
# ---------------------------------------------------------------------------
class Report:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def error(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def note(self, msg: str):
        self.info.append(msg)

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    def print(self):
        if self.info:
            for m in self.info:
                print(f"  ℹ️  {m}")
        if self.warnings:
            print()
            for m in self.warnings:
                print(f"  ⚠️  {m}")
        if self.errors:
            print()
            for m in self.errors:
                print(f"  ❌ {m}")
        print()
        if self.valid:
            print("✅ Skill validation PASSED")
        else:
            print(f"❌ Skill validation FAILED ({len(self.errors)} error(s))")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def extract_frontmatter(content: str):
    """Return (frontmatter_dict, body_text) or raise ValueError."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not match:
        raise ValueError("No YAML frontmatter (--- delimiters) found")
    fm = yaml.safe_load(match.group(1))
    if not isinstance(fm, dict):
        raise ValueError("Frontmatter did not parse as a YAML mapping")
    return fm, match.group(2)


def find_sections(body: str) -> List[str]:
    """Return list of H2 heading titles found in body."""
    return [m.group(1).strip() for m in re.finditer(r"^##\s+(.+)", body, re.MULTILINE)]


def count_examples(body: str) -> int:
    """Count ### headings under an ## Examples section."""
    in_examples = False
    count = 0
    for line in body.splitlines():
        if re.match(r"^##\s+Examples", line):
            in_examples = True
            continue
        if re.match(r"^##\s+", line) and in_examples:
            break
        if in_examples and re.match(r"^###\s+", line):
            count += 1
    return count


def count_instruction_steps(body: str) -> int:
    """Count ### headings inside the Instructions section."""
    in_instructions = False
    count = 0
    for line in body.splitlines():
        if re.match(r"^##\s+Instructions", line):
            in_instructions = True
            continue
        if re.match(r"^##\s+", line) and in_instructions:
            break
        if in_instructions and re.match(r"^###\s+", line):
            count += 1
    return count


def has_error_handling(body: str) -> bool:
    """True if an 'Error Handling' sub-section exists anywhere in body."""
    return bool(re.search(r"^###\s+Error\s+Handling", body, re.MULTILINE))


# ---------------------------------------------------------------------------
# Validation passes
# ---------------------------------------------------------------------------
def _is_fte_skill(fm: dict) -> bool:
    """FTE-domain skills (fte.* or sp.*) get the full schema check.
    Third-party / minimal skills (name+description only) get warnings."""
    name = str(fm.get("name", ""))
    return name.startswith("fte.") or name.startswith("sp.")


def validate_syntax(fm: dict, report: Report):
    """Check frontmatter fields exist and have valid values."""
    strict = _is_fte_skill(fm)
    if not strict:
        report.note("Third-party skill detected — missing fields are warnings only")
    for field in REQUIRED_FIELDS:
        if field not in fm:
            if strict:
                report.error(f"Missing required frontmatter field: '{field}'")
            else:
                report.warn(f"Missing field (not enforced for third-party): '{field}'")

    if "safety_level" in fm and fm["safety_level"] not in VALID_SAFETY_LEVELS:
        report.error(f"safety_level '{fm['safety_level']}' not in {sorted(VALID_SAFETY_LEVELS)}")

    if "category" in fm and fm["category"] not in VALID_CATEGORIES:
        report.warn(f"category '{fm['category']}' not in known set — may be a custom category")

    if "triggers" in fm:
        if not isinstance(fm["triggers"], list) or len(fm["triggers"]) < 2:
            report.error("'triggers' must be a list with ≥ 2 entries")

    if "tags" in fm:
        if not isinstance(fm["tags"], list) or len(fm["tags"]) < 1:
            report.error("'tags' must be a list with ≥ 1 entry")

    if "version" in fm:
        if not re.match(r"^\d+\.\d+\.\d+$", str(fm["version"])):
            report.error(f"version '{fm['version']}' does not match semver (X.Y.Z)")

    report.note("Syntax check complete")


def validate_complete(body: str, report: Report):
    """Check all required body sections are present."""
    sections = find_sections(body)
    for req in REQUIRED_SECTIONS:
        # Partial match: "Validation Criteria" satisfies "Validation"
        if not any(req.lower() in s.lower() for s in sections):
            report.error(f"Missing required body section: '## {req}'")
        else:
            report.note(f"Section found: {req}")


def validate_quality(body: str, report: Report):
    """Check examples count, step count, error handling, placeholders."""
    examples = count_examples(body)
    if examples < 2:
        report.error(f"Quality: need ≥ 2 examples, found {examples}")
    else:
        report.note(f"Examples: {examples}")

    steps = count_instruction_steps(body)
    if steps < 3:
        report.error(f"Quality: need ≥ 3 instruction steps (### headings), found {steps}")
    else:
        report.note(f"Instruction steps: {steps}")

    if not has_error_handling(body):
        report.error("Quality: missing '### Error Handling' sub-section in Instructions")
    else:
        report.note("Error Handling section present")

    # Placeholder scan
    for pattern in PLACEHOLDER_PATTERNS:
        hits = pattern.findall(body)
        if hits:
            report.warn(f"Possible unfilled placeholder: {hits[0]}")


# ---------------------------------------------------------------------------
# Resolve skill directory
# ---------------------------------------------------------------------------
def resolve_skill_dir(arg: str) -> Path:
    """Accept a path or a skill name and return the directory containing SKILL.md."""
    p = Path(arg)
    if p.is_dir() and (p / "SKILL.md").exists():
        return p

    # Try as a slug under .claude/skills/
    # Walk up to find repo root
    candidate = Path.cwd()
    for _ in range(5):
        skills_dir = candidate / ".claude" / "skills"
        if skills_dir.is_dir():
            # Try exact slug
            slug = arg.replace(".", "-")
            candidate_skill = skills_dir / slug
            if candidate_skill.is_dir() and (candidate_skill / "SKILL.md").exists():
                return candidate_skill
            # Try arg as-is (might already be a slug)
            candidate_skill2 = skills_dir / arg
            if candidate_skill2.is_dir() and (candidate_skill2 / "SKILL.md").exists():
                return candidate_skill2
            break
        candidate = candidate.parent

    raise FileNotFoundError(
        f"Cannot find skill '{arg}'. Provide a directory path or a skill name/slug."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Validate an Agent Skill against the schema."
    )
    parser.add_argument(
        "skill",
        help="Path to skill directory OR skill name (e.g. fte-vault-init or fte.vault.init)",
    )
    parser.add_argument(
        "--level",
        choices=["syntax", "complete", "quality"],
        default="complete",
        help="Validation depth (default: complete)",
    )
    args = parser.parse_args()

    # --- Resolve ---
    try:
        skill_dir = resolve_skill_dir(args.skill)
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    skill_file = skill_dir / "SKILL.md"
    print(f"🔍 Validating: {skill_file}\n")

    # --- Parse ---
    content = skill_file.read_text()
    report = Report()

    try:
        fm, body = extract_frontmatter(content)
    except ValueError as e:
        report.error(str(e))
        report.print()
        sys.exit(1)

    report.note(f"Parsed frontmatter ({len(fm)} fields) + body ({len(body)} chars)")

    # --- Syntax (always run) ---
    validate_syntax(fm, report)

    # --- Complete ---
    if args.level in ("complete", "quality"):
        validate_complete(body, report)

    # --- Quality ---
    if args.level == "quality":
        validate_quality(body, report)

    # --- Report ---
    report.print()
    sys.exit(0 if report.valid else 1)


if __name__ == "__main__":
    main()

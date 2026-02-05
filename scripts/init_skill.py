#!/usr/bin/env python3
"""
init_skill.py — Scaffold a new Agent Skill from the canonical template.

Usage:
    python scripts/init_skill.py <name> --category <category> [--dry-run]

Examples:
    python scripts/init_skill.py fte.vault.status --category vault
    python scripts/init_skill.py sp.git.find_commit --category git --dry-run
"""

import argparse
import sys
from datetime import date
from pathlib import Path


VALID_CATEGORIES = {
    # Abstract
    "task", "query", "config", "diagnostic", "workflow", "git",
    # FTE domain
    "vault", "briefing", "watcher", "orchestrator", "security", "approval",
}


def find_repo_root() -> Path:
    """Walk up from this script's location to find the repo root."""
    candidate = Path(__file__).resolve().parent
    for _ in range(5):
        if (candidate / ".specify").is_dir():
            return candidate
        candidate = candidate.parent
    raise FileNotFoundError("Cannot locate repo root (expected .specify/ to exist)")


def name_to_slug(name: str) -> str:
    """Convert dot-separated skill name to directory slug.

    fte.vault.init  →  fte-vault-init
    """
    return name.replace(".", "-")


def validate_name(name: str) -> None:
    """Ensure name follows namespace.category.action pattern."""
    parts = name.split(".")
    if len(parts) < 2 or len(parts) > 4:
        raise ValueError(
            f"Skill name must have 2-4 dot-separated segments, got {len(parts)}: '{name}'"
        )
    for part in parts:
        if not part.isalnum() or not part[0].isalpha():
            raise ValueError(
                f"Each segment must start with a letter and contain only alphanumerics: '{part}'"
            )


def render_template(template_path: Path, name: str, category: str) -> str:
    """Read skill-template.md and replace placeholders."""
    raw = template_path.read_text()
    today = date.today().isoformat()
    slug = name_to_slug(name)

    replacements = {
        "<namespace>.<category>.<action>": name,
        "/<namespace>.<category>.<action>": f"/{name}",
        "<task|query|config|diagnostic|workflow|git|vault|briefing|watcher|orchestrator|security|approval>": category,
        "YYYY-MM-DD": today,
        # Leave section placeholders as-is so the developer fills them
    }

    output = raw
    for old, new in replacements.items():
        output = output.replace(old, new)

    return output


def main():
    parser = argparse.ArgumentParser(
        description="Scaffold a new Agent Skill from the canonical template."
    )
    parser.add_argument("name", help="Dot-separated skill name (e.g. fte.vault.status)")
    parser.add_argument(
        "--category",
        required=True,
        choices=sorted(VALID_CATEGORIES),
        help="Primary skill category",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print rendered template to stdout without writing files",
    )
    args = parser.parse_args()

    # --- Validate ---
    try:
        validate_name(args.name)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    # --- Locate template ---
    try:
        repo_root = find_repo_root()
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    template_path = repo_root / ".specify" / "templates" / "skill-template.md"
    if not template_path.exists():
        print(f"❌ Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    # --- Render ---
    rendered = render_template(template_path, args.name, args.category)

    # --- Output ---
    if args.dry_run:
        print(rendered)
        print(f"\n# ← would write to .claude/skills/{name_to_slug(args.name)}/SKILL.md")
        sys.exit(0)

    # --- Write ---
    slug = name_to_slug(args.name)
    skill_dir = repo_root / ".claude" / "skills" / slug
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_file = skill_dir / "SKILL.md"
    if skill_file.exists():
        print(f"❌ Skill already exists: {skill_file}", file=sys.stderr)
        print("   Edit it directly or delete it first.", file=sys.stderr)
        sys.exit(1)

    skill_file.write_text(rendered)
    print(f"✅ Scaffolded: {skill_file.relative_to(repo_root)}")
    print(f"   Name:     {args.name}")
    print(f"   Category: {args.category}")
    print(f"   Next:     fill in the placeholder sections, then run:")
    print(f"             python scripts/validate_skill.py .claude/skills/{slug}")


if __name__ == "__main__":
    main()

"""
Skill Registry — discover and index agent skills from disk (spec 009).

Scans one or more directories for ``*.skill.md`` files, parses their YAML
frontmatter, and exposes a queryable index.  Call ``refresh()`` to pick up
new or edited skills without restarting.
"""

from pathlib import Path
from typing import Optional

import yaml

from .models import SkillMetadata


class SkillRegistry:
    """Discover and index skills from a list of search paths."""

    def __init__(self, search_paths: list[Path]):
        self._search_paths = search_paths
        self._skills: dict[str, SkillMetadata] = {}
        self.refresh()

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Re-scan all search paths and rebuild the index."""
        self._skills.clear()
        for root in self._search_paths:
            if not root.exists():
                continue
            for skill_file in sorted(root.glob("**/*.skill.md")):
                meta = _parse_skill_file(skill_file)
                if meta:
                    self._skills[meta.name] = meta

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, name: str) -> Optional[SkillMetadata]:
        """Look up a single skill by its canonical name."""
        return self._skills.get(name)

    def list_all(self) -> list[SkillMetadata]:
        """Return every indexed skill, sorted alphabetically by name."""
        return sorted(self._skills.values(), key=lambda s: s.name)

    def search_by_tag(self, tag: str) -> list[SkillMetadata]:
        """Return skills that carry a specific tag (case-insensitive)."""
        tag_lower = tag.lower()
        return [
            s for s in self._skills.values() if tag_lower in [t.lower() for t in s.tags]
        ]

    def search_by_category(self, category: str) -> list[SkillMetadata]:
        """Return skills in a given category (case-insensitive)."""
        cat_lower = category.lower()
        return [s for s in self._skills.values() if s.category.lower() == cat_lower]


# ---------------------------------------------------------------------------
# Parser helper
# ---------------------------------------------------------------------------


def _parse_skill_file(path: Path) -> Optional[SkillMetadata]:
    """Extract SkillMetadata from a skill file's YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    try:
        fm = yaml.safe_load(text[3:end]) or {}
    except yaml.YAMLError:
        return None
    if "name" not in fm:
        return None
    return SkillMetadata(
        name=fm["name"],
        version=str(fm.get("version", "")),
        description=str(fm.get("description", "")),
        triggers=fm.get("triggers", []),
        command=fm.get("command"),
        category=fm.get("category", "general"),
        tags=fm.get("tags", []),
        safety_level=fm.get("safety_level", "low"),
        approval_required=bool(fm.get("approval_required", False)),
        destructive=bool(fm.get("destructive", False)),
        file_path=path,
    )

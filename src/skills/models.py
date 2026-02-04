"""Skill data models (spec 009)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SkillMetadata:
    """Parsed metadata from a skill's YAML frontmatter."""

    name: str
    version: str = ""
    description: str = ""
    triggers: list[str] = field(default_factory=list)
    command: Optional[str] = None
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    safety_level: str = "low"  # low | medium | high
    approval_required: bool = False
    destructive: bool = False
    file_path: Optional[Path] = None

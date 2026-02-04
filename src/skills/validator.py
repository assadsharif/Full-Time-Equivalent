"""
Skill Validator — 3-level validation for agent skill files (spec 009).

Level 1 – Syntax:       YAML frontmatter parses; required fields present;
                         safety_level is a valid enum value.
Level 2 – Completeness: All four required sections exist in the body
                         (Overview, Instructions, Examples, Validation).
Level 3 – Quality:      Instructions have ≥ 2 sub-steps; at least one
                         named example; error-handling documentation present;
                         high-safety skills declare approval_required.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from src.skills.models import SkillMetadata

_VALID_SAFETY_LEVELS = {"low", "medium", "high"}
_REQUIRED_FM_FIELDS = ["name", "description", "category"]
_REQUIRED_SECTIONS = ["Overview", "Instructions", "Examples", "Validation"]


@dataclass
class ValidationIssue:
    level: str       # syntax | completeness | quality
    severity: str    # error | warning
    message: str


@dataclass
class SkillValidationResult:
    path: Path
    metadata: Optional[SkillMetadata] = None
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]


class SkillValidator:
    """Validate a skill file across syntax, completeness, and quality."""

    def validate(self, path: Path) -> SkillValidationResult:
        result = SkillValidationResult(path=path)
        text = path.read_text(encoding="utf-8")

        # ---------- Level 1: Syntax ----------
        fm, body = _parse_frontmatter(text)
        if fm is None:
            result.issues.append(ValidationIssue("syntax", "error", "missing or unparseable YAML frontmatter"))
            return result

        for fld in _REQUIRED_FM_FIELDS:
            if fld not in fm or not fm[fld]:
                result.issues.append(ValidationIssue("syntax", "error", f"missing required frontmatter field '{fld}'"))

        safety = fm.get("safety_level", "low")
        if safety not in _VALID_SAFETY_LEVELS:
            result.issues.append(ValidationIssue("syntax", "error", f"invalid safety_level '{safety}' (expected one of {sorted(_VALID_SAFETY_LEVELS)})"))

        # Build metadata (best-effort even if there are syntax errors)
        result.metadata = SkillMetadata(
            name=fm.get("name", ""),
            version=str(fm.get("version", "")),
            description=str(fm.get("description", "")),
            triggers=fm.get("triggers", []),
            command=fm.get("command"),
            category=fm.get("category", "general"),
            tags=fm.get("tags", []),
            safety_level=safety,
            approval_required=bool(fm.get("approval_required", False)),
            destructive=bool(fm.get("destructive", False)),
            file_path=path,
        )

        # ---------- Level 2: Completeness ----------
        for section in _REQUIRED_SECTIONS:
            if not re.search(rf"^##\s+{section}", body, re.MULTILINE | re.IGNORECASE):
                result.issues.append(ValidationIssue("completeness", "error", f"missing required section '## {section}'"))

        if not fm.get("triggers"):
            result.issues.append(ValidationIssue("completeness", "warning", "no triggers defined — skill won't be auto-discovered"))

        if not fm.get("version"):
            result.issues.append(ValidationIssue("completeness", "warning", "version not specified"))

        # ---------- Level 3: Quality ----------
        # Instructions need ≥ 2 sub-steps (### headers inside the Instructions section)
        instructions_body = _extract_section(body, "Instructions")
        if instructions_body:
            sub_steps = re.findall(r"^###\s+", instructions_body, re.MULTILINE)
            if len(sub_steps) < 2:
                result.issues.append(ValidationIssue("quality", "warning", "instructions have fewer than 2 sub-steps"))

        # Examples need at least one ### Example sub-section
        examples_body = _extract_section(body, "Examples")
        if examples_body:
            example_headers = re.findall(r"^###\s+Example", examples_body, re.MULTILINE)
            if len(example_headers) < 1:
                result.issues.append(ValidationIssue("quality", "warning", "no '### Example' sub-section in Examples"))

        # Error handling documentation
        if "error" not in body.lower():
            result.issues.append(ValidationIssue("quality", "warning", "no error-handling documentation detected"))

        # High-safety skills must require approval
        if safety == "high" and not fm.get("approval_required"):
            result.issues.append(ValidationIssue("quality", "error", "safety_level=high requires approval_required=true"))

        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_frontmatter(text: str) -> tuple[Optional[dict], str]:
    """Split YAML frontmatter from body.  Returns (None, text) on failure."""
    if not text.startswith("---"):
        return None, text
    end = text.find("---", 3)
    if end == -1:
        return None, text
    try:
        fm = yaml.safe_load(text[3:end]) or {}
        return fm, text[end + 3:]
    except yaml.YAMLError:
        return None, text


def _extract_section(body: str, section_name: str) -> Optional[str]:
    """Extract everything between one ## heading and the next (or EOF)."""
    pattern = rf"^##\s+{section_name}[^\n]*\n(.*?)(?=^##\s|\Z)"
    match = re.search(pattern, body, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else None

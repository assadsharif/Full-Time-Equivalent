"""
Vault Schema Validator (spec 008).

Validates task, approval, and briefing Markdown files against the
expected field requirements.  Each folder in the vault has its own
validator; ``VaultValidator`` is the top-level driver.

Exit semantics (when used as ``python -m src.vault.validator <vault>``):
  0 — all files valid
  1 — one or more validation errors
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Per-file validation outcome."""

    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


# ---------------------------------------------------------------------------
# Per-type validators
# ---------------------------------------------------------------------------


class TaskValidator:
    """Validate task files in Inbox / Needs_Action / In_Progress / Done."""

    REQUIRED_FIELDS = ["Priority", "From"]

    def validate(self, path: Path) -> ValidationResult:
        text = path.read_text(encoding="utf-8")
        errors: list[str] = []

        for fld in self.REQUIRED_FIELDS:
            if f"**{fld}**:" not in text:
                errors.append(f"missing required field '**{fld}**:'")

        return ValidationResult(path=path, errors=errors)


class ApprovalValidator:
    """Validate approval request files — must have structured frontmatter."""

    REQUIRED_FM_KEYS = [
        "approval_id", "nonce", "approval_status",
        "created_at", "expires_at",
    ]
    VALID_STATUSES = {"pending", "approved", "rejected", "timeout"}

    def validate(self, path: Path) -> ValidationResult:
        text = path.read_text(encoding="utf-8")
        errors: list[str] = []

        if not text.startswith("---"):
            return ValidationResult(path=path, errors=["missing YAML frontmatter"])

        end = text.find("---", 3)
        if end == -1:
            return ValidationResult(path=path, errors=["unclosed YAML frontmatter"])

        fm = yaml.safe_load(text[3:end]) or {}

        for key in self.REQUIRED_FM_KEYS:
            if key not in fm:
                errors.append(f"missing frontmatter key '{key}'")

        status = fm.get("approval_status", "")
        if status not in self.VALID_STATUSES:
            errors.append(f"invalid approval_status '{status}' (expected one of {sorted(self.VALID_STATUSES)})")

        return ValidationResult(path=path, errors=errors)


class BriefingValidator:
    """Validate briefing report files."""

    REQUIRED_FM_KEYS = ["report_type", "total_tasks", "generated_at"]

    def validate(self, path: Path) -> ValidationResult:
        text = path.read_text(encoding="utf-8")
        errors: list[str] = []

        if not text.startswith("---"):
            return ValidationResult(path=path, errors=["missing YAML frontmatter"])

        end = text.find("---", 3)
        if end == -1:
            return ValidationResult(path=path, errors=["unclosed YAML frontmatter"])

        fm = yaml.safe_load(text[3:end]) or {}
        for key in self.REQUIRED_FM_KEYS:
            if key not in fm:
                errors.append(f"missing frontmatter key '{key}'")

        return ValidationResult(path=path, errors=errors)


# ---------------------------------------------------------------------------
# Top-level vault scanner
# ---------------------------------------------------------------------------

_TASK_FOLDERS = ("Inbox", "Needs_Action", "In_Progress", "Done")


class VaultValidator:
    """
    Scan an entire vault and validate every .md file by folder type.

    Returns ``folder_name → [ValidationResult, ...]``.
    """

    def __init__(self, vault_path: Path):
        self.vault = vault_path
        self._task = TaskValidator()
        self._approval = ApprovalValidator()
        self._briefing = BriefingValidator()

    def validate_all(self) -> dict[str, list[ValidationResult]]:
        results: dict[str, list[ValidationResult]] = {}

        for folder in _TASK_FOLDERS:
            folder_path = self.vault / folder
            if folder_path.exists():
                results[folder] = [
                    self._task.validate(md)
                    for md in sorted(folder_path.glob("*.md"))
                ]

        approvals = self.vault / "Approvals"
        if approvals.exists():
            results["Approvals"] = [
                self._approval.validate(md) for md in sorted(approvals.glob("*.md"))
            ]

        briefings = self.vault / "Briefings"
        if briefings.exists():
            results["Briefings"] = [
                self._briefing.validate(md) for md in sorted(briefings.glob("*.md"))
            ]

        return results

    # Convenience queries

    @property
    def total_errors(self) -> int:
        return sum(
            len(r.errors)
            for folder_results in self.validate_all().values()
            for r in folder_results
        )

    @property
    def is_valid(self) -> bool:
        return self.total_errors == 0

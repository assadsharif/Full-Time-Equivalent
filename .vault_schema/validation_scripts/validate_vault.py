#!/usr/bin/env python3
"""
Vault Validation Script

Validates Obsidian vault structure, YAML frontmatter, and file naming conventions.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
import yaml
import re
from datetime import datetime


class ValidationResult:
    """Stores validation results."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def add_error(self, msg: str):
        self.errors.append(f"❌ ERROR: {msg}")

    def add_warning(self, msg: str):
        self.warnings.append(f"⚠️  WARNING: {msg}")

    def add_info(self, msg: str):
        self.info.append(f"ℹ️  INFO: {msg}")

    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def print_results(self):
        """Print all validation results."""
        if self.errors:
            print("\n🚨 ERRORS:")
            for error in self.errors:
                print(f"  {error}")

        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")

        if self.info:
            print("\nℹ️  INFO:")
            for info in self.info:
                print(f"  {info}")

        if self.is_valid():
            print("\n✅ Vault validation PASSED")
        else:
            print(f"\n❌ Vault validation FAILED ({len(self.errors)} errors)")


class VaultValidator:
    """Validates Obsidian vault structure and content."""

    # Required folders
    REQUIRED_FOLDERS = [
        "Inbox",
        "Needs_Action",
        "In_Progress",
        "Done",
        "Approvals",
        "Briefings",
        "Attachments",
        "Templates",
    ]

    # Required root files
    REQUIRED_FILES = [
        "Dashboard.md",
        "Company_Handbook.md",
    ]

    # Valid states for tasks
    VALID_STATES = [
        "inbox",
        "needs_action",
        "in_progress",
        "pending_approval",
        "done",
        "rejected",
        "error_queue",
        "failed",
    ]

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.result = ValidationResult()
        self.schema_path = Path(__file__).parent.parent / "frontmatter_schemas"
        self._load_schemas()

    def _load_schemas(self):
        """Load YAML schemas for validation."""
        try:
            self.task_schema = yaml.safe_load((self.schema_path / "task.yaml").read_text())
            self.approval_schema = yaml.safe_load((self.schema_path / "approval.yaml").read_text())
            self.briefing_schema = yaml.safe_load((self.schema_path / "briefing.yaml").read_text())
            self.result.add_info(f"Loaded schemas from {self.schema_path}")
        except Exception as e:
            self.result.add_warning(f"Could not load schemas: {e}")
            self.task_schema = {}
            self.approval_schema = {}
            self.briefing_schema = {}

    def validate(self) -> ValidationResult:
        """Run all validation checks."""
        print(f"🔍 Validating vault: {self.vault_path}\n")

        self._validate_structure()
        self._validate_root_files()
        self._validate_obsidian_config()
        self._validate_tasks()
        self._validate_approvals()
        self._validate_briefings()

        return self.result

    def _validate_structure(self):
        """Validate vault folder structure."""
        if not self.vault_path.exists():
            self.result.add_error(f"Vault path does not exist: {self.vault_path}")
            return

        if not self.vault_path.is_dir():
            self.result.add_error(f"Vault path is not a directory: {self.vault_path}")
            return

        self.result.add_info(f"Vault exists at {self.vault_path}")

        # Check required folders
        for folder in self.REQUIRED_FOLDERS:
            folder_path = self.vault_path / folder
            if not folder_path.exists():
                self.result.add_error(f"Required folder missing: {folder}")
            elif not folder_path.is_dir():
                self.result.add_error(f"Required folder is not a directory: {folder}")
            else:
                self.result.add_info(f"Folder exists: {folder}")

    def _validate_root_files(self):
        """Validate required root files."""
        for file in self.REQUIRED_FILES:
            file_path = self.vault_path / file
            if not file_path.exists():
                self.result.add_error(f"Required file missing: {file}")
            elif not file_path.is_file():
                self.result.add_error(f"Required file is not a file: {file}")
            else:
                self.result.add_info(f"File exists: {file}")

    def _validate_obsidian_config(self):
        """Validate Obsidian configuration."""
        obsidian_dir = self.vault_path / ".obsidian"
        if not obsidian_dir.exists():
            self.result.add_warning("Obsidian config directory missing (.obsidian)")
            return

        # Check for essential config files
        required_configs = ["app.json", "core-plugins.json"]
        for config in required_configs:
            config_path = obsidian_dir / config
            if not config_path.exists():
                self.result.add_warning(f"Obsidian config missing: .obsidian/{config}")
            else:
                self.result.add_info(f"Obsidian config exists: {config}")

    def _validate_tasks(self):
        """Validate task files in workflow folders."""
        task_folders = ["Inbox", "Needs_Action", "In_Progress", "Done"]

        for folder in task_folders:
            folder_path = self.vault_path / folder
            if not folder_path.exists():
                continue

            for task_file in folder_path.glob("*.md"):
                self._validate_task_file(task_file, folder.lower().replace("_", ""))

    def _validate_task_file(self, task_file: Path, expected_state: str):
        """Validate individual task file."""
        try:
            content = task_file.read_text()

            # Extract YAML frontmatter
            if not content.startswith("---"):
                self.result.add_warning(f"Task missing frontmatter: {task_file.name}")
                return

            end = content.find("---", 3)
            if end == -1:
                self.result.add_warning(f"Task has malformed frontmatter: {task_file.name}")
                return

            frontmatter = yaml.safe_load(content[3:end])

            # Validate state
            if "state" in frontmatter:
                state = frontmatter["state"]
                if state not in self.VALID_STATES:
                    self.result.add_error(f"Invalid state '{state}' in {task_file.name}")
                elif expected_state == "needs_action" and state != "needs_action":
                    self.result.add_warning(
                        f"Task in {expected_state} folder has state '{state}': {task_file.name}"
                    )
            else:
                self.result.add_warning(f"Task missing 'state' field: {task_file.name}")

            # Validate required fields
            required_fields = ["task_id", "title", "source", "created_at"]
            for field in required_fields:
                if field not in frontmatter:
                    self.result.add_warning(f"Task missing '{field}' field: {task_file.name}")

        except Exception as e:
            self.result.add_error(f"Error validating task {task_file.name}: {e}")

    def _validate_approvals(self):
        """Validate approval files."""
        approvals_path = self.vault_path / "Approvals"
        if not approvals_path.exists():
            return

        for approval_file in approvals_path.glob("APR-*.md"):
            self._validate_approval_file(approval_file)

    def _validate_approval_file(self, approval_file: Path):
        """Validate individual approval file."""
        try:
            content = approval_file.read_text()

            if not content.startswith("---"):
                self.result.add_warning(f"Approval missing frontmatter: {approval_file.name}")
                return

            end = content.find("---", 3)
            if end == -1:
                self.result.add_warning(f"Approval has malformed frontmatter: {approval_file.name}")
                return

            frontmatter = yaml.safe_load(content[3:end])

            # Validate required fields
            required_fields = ["approval_id", "task_id", "status", "nonce", "created_at", "expires_at"]
            for field in required_fields:
                if field not in frontmatter:
                    self.result.add_warning(f"Approval missing '{field}' field: {approval_file.name}")

            # Validate status
            if "status" in frontmatter:
                status = frontmatter["status"]
                valid_statuses = ["pending", "approved", "rejected", "expired"]
                if status not in valid_statuses:
                    self.result.add_error(f"Invalid approval status '{status}' in {approval_file.name}")

        except Exception as e:
            self.result.add_error(f"Error validating approval {approval_file.name}: {e}")

    def _validate_briefings(self):
        """Validate briefing files."""
        briefings_path = self.vault_path / "Briefings"
        if not briefings_path.exists():
            return

        for briefing_file in briefings_path.glob("BRIEF-*.md"):
            self._validate_briefing_file(briefing_file)

    def _validate_briefing_file(self, briefing_file: Path):
        """Validate individual briefing file."""
        try:
            content = briefing_file.read_text()

            if not content.startswith("---"):
                self.result.add_warning(f"Briefing missing frontmatter: {briefing_file.name}")
                return

            end = content.find("---", 3)
            if end == -1:
                self.result.add_warning(f"Briefing has malformed frontmatter: {briefing_file.name}")
                return

            frontmatter = yaml.safe_load(content[3:end])

            # Validate required fields
            required_fields = ["briefing_id", "title", "week_start", "week_end", "generated_at"]
            for field in required_fields:
                if field not in frontmatter:
                    self.result.add_warning(f"Briefing missing '{field}' field: {briefing_file.name}")

        except Exception as e:
            self.result.add_error(f"Error validating briefing {briefing_file.name}: {e}")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: validate_vault.py <vault_path>")
        sys.exit(1)

    vault_path = Path(sys.argv[1]).expanduser().resolve()

    validator = VaultValidator(vault_path)
    result = validator.validate()

    result.print_results()

    sys.exit(0 if result.is_valid() else 1)


if __name__ == "__main__":
    main()

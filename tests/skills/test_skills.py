"""
Agent Skills framework tests (spec 009).

Coverage map:
  TestSkillValidator   — valid skill, missing frontmatter, missing name,
                         missing sections, invalid safety_level, high-safety
                         without approval, warnings (triggers, version,
                         error handling, few steps, no examples)
  TestSkillRegistry    — discover skills, tag search, category search,
                         empty dir, refresh picks up new files, malformed
                         files skipped, get by name
"""

import shutil
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

_VALID_SKILL = """\
---
name: fte.vault.status
version: 1.0.0
description: Show vault status
triggers:
  - vault status
  - check vault
command: /fte.vault.status
category: vault
tags: [vault, status]
safety_level: low
approval_required: false
destructive: false
---

## Overview

Displays a summary of the vault.

## Instructions for Claude

### Step 1: Count tasks
Count files in each vault folder.

### Step 2: Format output
Produce a nicely formatted summary.

### Error Handling
- **Vault missing:** Inform user that no vault exists at the expected path.

## Examples

### Example 1: Normal run
**User Input:**
```
User: "vault status"
```

**Output:**
```
Inbox: 2  Needs_Action: 1  Done: 42
```

## Validation Criteria

### Success Criteria
- [ ] Counts are accurate
- [ ] Output is formatted
"""


@pytest.fixture
def tmp_dir():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _write_skill(directory: Path, name: str, content: str) -> Path:
    p = directory / name
    p.write_text(content)
    return p


# ===========================================================================
# SkillValidator
# ===========================================================================


class TestSkillValidator:
    def _validator(self):
        from src.skills.validator import SkillValidator

        return SkillValidator()

    def test_valid_skill_passes(self, tmp_dir):
        path = _write_skill(tmp_dir, "good.skill.md", _VALID_SKILL)
        result = self._validator().validate(path)
        assert result.is_valid
        assert result.errors == []
        assert result.metadata.name == "fte.vault.status"
        assert result.metadata.category == "vault"

    def test_missing_frontmatter(self, tmp_dir):
        path = _write_skill(tmp_dir, "no-fm.skill.md", "# No frontmatter here\n")
        result = self._validator().validate(path)
        assert not result.is_valid
        assert any("frontmatter" in i.message for i in result.errors)

    def test_unclosed_frontmatter(self, tmp_dir):
        content = "---\nname: test\n# no closing delimiter\n"
        path = _write_skill(tmp_dir, "unclosed.skill.md", content)
        result = self._validator().validate(path)
        assert not result.is_valid

    def test_missing_name_field(self, tmp_dir):
        content = "---\ndescription: Oops\ncategory: vault\n---\n\n## Overview\n\n## Instructions\n\n## Examples\n\n## Validation\n"
        path = _write_skill(tmp_dir, "no-name.skill.md", content)
        result = self._validator().validate(path)
        assert not result.is_valid
        assert any("name" in i.message for i in result.errors)

    def test_missing_description_field(self, tmp_dir):
        content = "---\nname: x\ncategory: vault\n---\n\n## Overview\n\n## Instructions\n\n## Examples\n\n## Validation\n"
        path = _write_skill(tmp_dir, "no-desc.skill.md", content)
        result = self._validator().validate(path)
        assert not result.is_valid
        assert any("description" in i.message for i in result.errors)

    def test_missing_overview_section(self, tmp_dir):
        # Has all FM fields but body is missing Overview
        content = (
            "---\nname: x\ndescription: d\ncategory: c\n---\n\n"
            "## Instructions\n\n### Step 1: Do it\n### Step 2: Verify\n\n"
            "## Examples\n\n### Example 1: One\n\n"
            "## Validation\n"
        )
        path = _write_skill(tmp_dir, "no-overview.skill.md", content)
        result = self._validator().validate(path)
        assert not result.is_valid
        assert any("Overview" in i.message for i in result.errors)

    def test_missing_instructions_section(self, tmp_dir):
        content = (
            "---\nname: x\ndescription: d\ncategory: c\n---\n\n"
            "## Overview\nSomething.\n\n"
            "## Examples\n\n### Example 1: One\n\n"
            "## Validation\n"
        )
        path = _write_skill(tmp_dir, "no-instr.skill.md", content)
        result = self._validator().validate(path)
        assert not result.is_valid
        assert any("Instructions" in i.message for i in result.errors)

    def test_invalid_safety_level(self, tmp_dir):
        content = (
            "---\nname: x\ndescription: d\ncategory: c\nsafety_level: extreme\n---\n\n"
            "## Overview\n## Instructions\n### Step 1: A\n### Step 2: B\n"
            "## Examples\n### Example 1: E\n## Validation\n"
        )
        path = _write_skill(tmp_dir, "bad-safety.skill.md", content)
        result = self._validator().validate(path)
        assert not result.is_valid
        assert any("safety_level" in i.message for i in result.errors)

    def test_high_safety_without_approval_is_error(self, tmp_dir):
        content = (
            "---\nname: x\ndescription: d\ncategory: c\n"
            "safety_level: high\napproval_required: false\n---\n\n"
            "## Overview\nRisky.\n\n"
            "## Instructions\n### Step 1: Do risky thing\n### Step 2: Verify\n"
            "### Error Handling\n- **Fail:** Stop.\n\n"
            "## Examples\n### Example 1: Boom\n\n"
            "## Validation\n"
        )
        path = _write_skill(tmp_dir, "unsafe.skill.md", content)
        result = self._validator().validate(path)
        assert not result.is_valid
        assert any("approval_required" in i.message for i in result.errors)

    def test_high_safety_with_approval_is_valid(self, tmp_dir):
        content = (
            "---\nname: x\ndescription: d\ncategory: c\n"
            "safety_level: high\napproval_required: true\n"
            "triggers: [run]\nversion: 1.0.0\n---\n\n"
            "## Overview\nRisky.\n\n"
            "## Instructions\n### Step 1: Check approval\n### Step 2: Execute\n"
            "### Error Handling\n- **Fail:** Alert user.\n\n"
            "## Examples\n### Example 1: With approval\n\n"
            "## Validation\n"
        )
        path = _write_skill(tmp_dir, "safe-high.skill.md", content)
        result = self._validator().validate(path)
        assert result.is_valid

    def test_warning_no_triggers(self, tmp_dir):
        # Valid skill but no triggers — should be a warning, not error
        content = (
            "---\nname: x\ndescription: d\ncategory: c\nversion: '1.0'\n---\n\n"
            "## Overview\nStuff.\n\n"
            "## Instructions\n### Step 1: A\n### Step 2: B\n"
            "### Error Handling\n- **Err:** Handle.\n\n"
            "## Examples\n### Example 1: One\n\n"
            "## Validation\n"
        )
        path = _write_skill(tmp_dir, "no-triggers.skill.md", content)
        result = self._validator().validate(path)
        assert result.is_valid  # warnings don't make it invalid
        assert any("triggers" in i.message for i in result.warnings)

    def test_warning_few_steps(self, tmp_dir):
        # Only 1 ### step in Instructions
        content = (
            "---\nname: x\ndescription: d\ncategory: c\ntriggers: [go]\nversion: '1'\n---\n\n"
            "## Overview\nStuff.\n\n"
            "## Instructions\n### Step 1: Only one step\n\n"
            "## Examples\n### Example 1: One\n\n"
            "## Validation\n"
        )
        path = _write_skill(tmp_dir, "few-steps.skill.md", content)
        result = self._validator().validate(path)
        assert any("fewer than 2" in i.message for i in result.warnings)


# ===========================================================================
# SkillRegistry
# ===========================================================================


class TestSkillRegistry:
    def _registry(self, *paths):
        from src.skills.registry import SkillRegistry

        return SkillRegistry(search_paths=list(paths))

    def test_discovers_skills(self, tmp_dir):
        skills_dir = tmp_dir / "skills"
        skills_dir.mkdir()
        _write_skill(skills_dir, "fte.vault.status.skill.md", _VALID_SKILL)
        reg = self._registry(skills_dir)
        assert len(reg.list_all()) == 1
        assert reg.list_all()[0].name == "fte.vault.status"

    def test_get_by_name(self, tmp_dir):
        skills_dir = tmp_dir / "skills"
        skills_dir.mkdir()
        _write_skill(skills_dir, "fte.vault.status.skill.md", _VALID_SKILL)
        reg = self._registry(skills_dir)
        skill = reg.get("fte.vault.status")
        assert skill is not None
        assert skill.category == "vault"

    def test_get_unknown_returns_none(self, tmp_dir):
        reg = self._registry(tmp_dir)
        assert reg.get("no.such.skill") is None

    def test_search_by_tag(self, tmp_dir):
        skills_dir = tmp_dir / "skills"
        skills_dir.mkdir()
        _write_skill(skills_dir, "a.skill.md", _VALID_SKILL)  # tags: [vault, status]
        # A skill with different tags
        other = (
            "---\nname: git.commit\ndescription: Commit\ncategory: git\n"
            "tags: [git, commit]\nsafety_level: low\n---\n\n"
        )
        _write_skill(skills_dir, "b.skill.md", other)
        reg = self._registry(skills_dir)
        vault_skills = reg.search_by_tag("vault")
        assert len(vault_skills) == 1
        assert vault_skills[0].name == "fte.vault.status"

    def test_search_by_category(self, tmp_dir):
        skills_dir = tmp_dir / "skills"
        skills_dir.mkdir()
        _write_skill(skills_dir, "a.skill.md", _VALID_SKILL)
        reg = self._registry(skills_dir)
        vault_skills = reg.search_by_category("vault")
        assert len(vault_skills) == 1

    def test_empty_directory(self, tmp_dir):
        reg = self._registry(tmp_dir)
        assert reg.list_all() == []

    def test_nonexistent_path_ignored(self, tmp_dir):
        reg = self._registry(tmp_dir / "no_such_dir")
        assert reg.list_all() == []

    def test_refresh_picks_up_new_skill(self, tmp_dir):
        skills_dir = tmp_dir / "skills"
        skills_dir.mkdir()
        reg = self._registry(skills_dir)
        assert reg.list_all() == []

        # Add a skill after initial scan
        _write_skill(skills_dir, "new.skill.md", _VALID_SKILL)
        reg.refresh()
        assert len(reg.list_all()) == 1

    def test_malformed_skill_file_skipped(self, tmp_dir):
        skills_dir = tmp_dir / "skills"
        skills_dir.mkdir()
        _write_skill(skills_dir, "bad.skill.md", "not a skill at all\n")
        _write_skill(skills_dir, "good.skill.md", _VALID_SKILL)
        reg = self._registry(skills_dir)
        assert len(reg.list_all()) == 1

    def test_multiple_search_paths(self, tmp_dir):
        dir_a = tmp_dir / "a"
        dir_b = tmp_dir / "b"
        dir_a.mkdir()
        dir_b.mkdir()
        _write_skill(dir_a, "a.skill.md", _VALID_SKILL)
        other = (
            "---\nname: other.skill\ndescription: Another\ncategory: other\n"
            "tags: [other]\nsafety_level: low\n---\n\n"
        )
        _write_skill(dir_b, "b.skill.md", other)
        reg = self._registry(dir_a, dir_b)
        assert len(reg.list_all()) == 2

"""
Cross-module integration tests.

Each class pins together two or more modules that were developed
independently to verify they compose correctly end-to-end.

  TestVaultInitThenValidate   — initializer output passes all validators
  TestBriefingPipeline        — aggregate → Markdown + PDF in one vault
  TestSkillDiscoveryInVault   — skills placed in an initialized vault are
                                discovered by the registry
  TestSecurityAuditRoundTrip  — MCP guard logs events that the audit logger
                                can query back
"""

import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_vault():
    """Return an empty directory; caller decides whether to initialise it."""
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ===========================================================================
# Vault Init → Validate
# ===========================================================================


class TestVaultInitThenValidate:
    """Freshly initialised vault should pass every validator without errors."""

    def test_empty_vault_is_structurally_valid(self, tmp_vault):
        from src.vault.initializer import VaultInitializer
        from src.vault.validator import VaultValidator

        VaultInitializer(tmp_vault).initialize()

        # No .md files yet in workflow folders → zero errors
        v = VaultValidator(tmp_vault)
        assert v.is_valid
        assert v.total_errors == 0

    def test_task_in_done_validates_after_init(self, tmp_vault):
        from src.vault.initializer import VaultInitializer
        from src.vault.validator import TaskValidator

        VaultInitializer(tmp_vault).initialize()

        # Drop a well-formed task into Done
        task = (
            "# deploy-prod\n\n"
            "**Priority**: High\n"
            "**From**: ops@company.com\n\n"
            "---\n\nDone.\n"
        )
        (tmp_vault / "Done" / "deploy-prod.md").write_text(task)

        result = TaskValidator().validate(tmp_vault / "Done" / "deploy-prod.md")
        assert result.is_valid

    def test_check_structure_clean_after_init(self, tmp_vault):
        from src.vault.initializer import VaultInitializer

        VaultInitializer(tmp_vault).initialize()
        missing = VaultInitializer(tmp_vault).check_structure()
        assert missing == {"folders": [], "schemas": [], "files": []}


# ===========================================================================
# Briefing Pipeline (aggregate → Markdown + PDF)
# ===========================================================================


class TestBriefingPipeline:
    """Populate /Done, aggregate, render both Markdown and PDF."""

    def _populate_done(self, vault: Path) -> None:
        done = vault / "Done"
        done.mkdir(exist_ok=True)
        tasks = [
            (
                "deploy-prod.md",
                "# deploy-prod\n\n**Priority**: \U0001f534 Urgent\n**From**: ops@co.com\n\n---\n\nProduction v3 deployed.\n",
            ),
            (
                "client-deck.md",
                "# client-deck\n\n**Priority**: \U0001f7e0 High\n**From**: sales@co.com\n\n---\n\nDeck sent to Acme.\n",
            ),
            (
                "newsletter.md",
                "# newsletter\n\n**Priority**: \U0001f7e2 Low\n**From**: marketing@co.com\n\n---\n\nNewsletter out.\n",
            ),
        ]
        for name, content in tasks:
            (done / name).write_text(content)

    def test_markdown_and_pdf_both_created(self, tmp_vault):
        from src.briefing.aggregator import BriefingAggregator
        from src.briefing.template_renderer import TemplateRenderer
        from src.briefing.pdf_generator import generate_pdf_to_file

        project_root = Path(__file__).resolve().parents[2]
        template_dir = project_root / "templates" / "briefing"

        self._populate_done(tmp_vault)
        (tmp_vault / "Briefings").mkdir(exist_ok=True)

        # Aggregate
        data = BriefingAggregator(tmp_vault / "Done").aggregate()
        assert data.total_tasks == 3

        # Markdown
        md_path = tmp_vault / "Briefings" / "weekly.md"
        TemplateRenderer(template_dir).render_to_file(
            "executive_summary.md.j2", data, md_path
        )
        assert md_path.exists()
        md_text = md_path.read_text()
        assert "ops@co.com" in md_text

        # PDF
        pdf_path = tmp_vault / "Briefings" / "weekly.pdf"
        generate_pdf_to_file(data, pdf_path)
        assert pdf_path.exists()
        assert pdf_path.read_bytes()[:5] == b"%PDF-"
        assert pdf_path.stat().st_size < 1_000_000

    def test_empty_done_produces_valid_outputs(self, tmp_vault):
        from src.briefing.aggregator import BriefingAggregator
        from src.briefing.template_renderer import TemplateRenderer
        from src.briefing.pdf_generator import generate_pdf_to_file

        project_root = Path(__file__).resolve().parents[2]
        template_dir = project_root / "templates" / "briefing"

        (tmp_vault / "Done").mkdir()
        (tmp_vault / "Briefings").mkdir()

        data = BriefingAggregator(tmp_vault / "Done").aggregate()
        assert data.total_tasks == 0

        md_path = tmp_vault / "Briefings" / "empty.md"
        TemplateRenderer(template_dir).render_to_file(
            "executive_summary.md.j2", data, md_path
        )
        assert md_path.exists()

        pdf_path = tmp_vault / "Briefings" / "empty.pdf"
        generate_pdf_to_file(data, pdf_path)
        assert pdf_path.read_bytes()[:5] == b"%PDF-"


# ===========================================================================
# Skill Discovery in an Initialized Vault
# ===========================================================================


class TestSkillDiscoveryInVault:
    """Skills dropped into Templates/ of an init'd vault are indexed."""

    _SKILL = """\
---
name: fte.deploy.rollback
version: 1.0.0
description: Roll back the latest deployment
triggers:
  - rollback
  - undo deploy
command: /fte.deploy.rollback
category: deploy
tags: [deploy, rollback]
safety_level: high
approval_required: true
destructive: true
---

## Overview

Rolls back the most recent production deployment to the previous stable version.

## Instructions for Claude

### Step 1: Identify current version
Check the deployment log to find the active version.

### Step 2: Trigger rollback
Execute the rollback command with the target version.

### Error Handling
- **No previous version:** Abort and alert the operator.

## Examples

### Example 1: Standard rollback
**User Input:**
```
User: "rollback"
```

**Output:**
```
Rolling back from v3.1 to v3.0 ...
Rollback complete.
```

## Validation Criteria

### Success Criteria
- [ ] Previous version is restored
- [ ] Health check passes after rollback
"""

    def test_registry_finds_skill_in_templates(self, tmp_vault):
        from src.vault.initializer import VaultInitializer
        from src.skills.registry import SkillRegistry

        VaultInitializer(tmp_vault).initialize()

        # Write skill into Templates/
        (tmp_vault / "Templates" / "fte.deploy.rollback.skill.md").write_text(
            self._SKILL
        )

        reg = SkillRegistry(search_paths=[tmp_vault / "Templates"])
        assert len(reg.list_all()) == 1
        skill = reg.get("fte.deploy.rollback")
        assert skill is not None
        assert skill.category == "deploy"
        assert "rollback" in skill.tags

    def test_validator_accepts_skill(self, tmp_vault):
        from src.vault.initializer import VaultInitializer
        from src.skills.validator import SkillValidator

        VaultInitializer(tmp_vault).initialize()
        path = tmp_vault / "Templates" / "fte.deploy.rollback.skill.md"
        path.write_text(self._SKILL)

        result = SkillValidator().validate(path)
        assert result.is_valid, [i.message for i in result.errors]


# ===========================================================================
# Security Audit Round-Trip
# ===========================================================================


class TestSecurityAuditRoundTrip:
    """Events produced by MCP guard are queryable via audit logger."""

    def test_guard_success_logged(self, tmp_vault):
        from src.security.audit_logger import SecurityAuditLogger
        from src.security.mcp_guard import MCPGuard
        from src.security.rate_limiter import RateLimiter

        audit_log = tmp_vault / "security_audit.jsonl"
        logger = SecurityAuditLogger(audit_log)

        rate_state = tmp_vault / "rate_state.json"
        rate_limiter = RateLimiter(state_path=rate_state)

        guard = MCPGuard(
            rate_limiter=rate_limiter,
            audit_logger=logger,
        )

        # Execute a no-op function through the guard
        result = guard.call(
            server="test-mcp",
            action_type="read_data",
            fn=lambda: "ok",
        )
        assert result == "ok"

        # Audit log should contain the event
        recent = logger.query_recent(limit=5)
        assert len(recent) >= 1
        event = recent[-1]
        assert event["mcp_server"] == "test-mcp"
        assert event["action"] == "read_data"
        assert event["result"] == "success"

    def test_guard_rate_limit_logged(self, tmp_vault):
        from src.security.audit_logger import SecurityAuditLogger
        from src.security.mcp_guard import MCPGuard
        from src.security.rate_limiter import RateLimiter, RateLimitExceededError

        audit_log = tmp_vault / "security_audit.jsonl"
        logger = SecurityAuditLogger(audit_log)

        rate_state = tmp_vault / "rate_state.json"
        # Tight limit: 1 token max, action type "do_thing"
        rate_limiter = RateLimiter(
            state_path=rate_state,
            default_limits={"do_thing": {"per_minute": 1, "per_hour": 1}},
        )

        guard = MCPGuard(
            rate_limiter=rate_limiter,
            audit_logger=logger,
        )

        # First call should succeed (consumes the 1 token)
        guard.call(server="tight-mcp", action_type="do_thing", fn=lambda: "ok")

        # Second call should be rate-limited
        with pytest.raises(RateLimitExceededError):
            guard.call(server="tight-mcp", action_type="do_thing", fn=lambda: "ok")

        recent = logger.query_recent(limit=10)
        results = [e["result"] for e in recent]
        assert "success" in results
        assert "rate_limit_exceeded" in results

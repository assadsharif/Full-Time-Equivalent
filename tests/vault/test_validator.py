"""
Vault Schema Validator tests (spec 008).

Coverage map:
  TestTaskValidator       — valid task, missing Priority, missing From, both missing
  TestApprovalValidator   — valid approval, missing frontmatter, unclosed frontmatter,
                            missing nonce, invalid status
  TestBriefingValidator   — valid briefing, missing frontmatter, missing generated_at
  TestVaultValidator      — empty vault, mixed good/bad across folders, is_valid flag,
                            total_errors count
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from vault.validator import (
    ApprovalValidator,
    BriefingValidator,
    TaskValidator,
    VaultValidator,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vault_dir():
    d = Path(tempfile.mkdtemp())
    for folder in (
        "Inbox",
        "Needs_Action",
        "In_Progress",
        "Done",
        "Approvals",
        "Briefings",
    ):
        (d / folder).mkdir()
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ===========================================================================
# TaskValidator
# ===========================================================================


class TestTaskValidator:
    def _file(self, vault: Path, name: str, content: str) -> Path:
        p = vault / "Done" / name
        p.write_text(content)
        return p

    def test_valid_task(self, vault_dir):
        p = self._file(
            vault_dir,
            "good.md",
            "# good.md\n\n**Priority**: High\n**From**: alice@x.com\n\n---\n\nDone.\n",
        )
        result = TaskValidator().validate(p)
        assert result.is_valid
        assert result.errors == []

    def test_missing_priority(self, vault_dir):
        p = self._file(
            vault_dir, "no-pri.md", "# t\n\n**From**: a@b.com\n\n---\nBody\n"
        )
        result = TaskValidator().validate(p)
        assert not result.is_valid
        assert any("Priority" in e for e in result.errors)

    def test_missing_from(self, vault_dir):
        p = self._file(
            vault_dir, "no-from.md", "# t\n\n**Priority**: Low\n\n---\nBody\n"
        )
        result = TaskValidator().validate(p)
        assert not result.is_valid
        assert any("From" in e for e in result.errors)

    def test_missing_both(self, vault_dir):
        p = self._file(vault_dir, "bare.md", "# bare\n\nJust text.\n")
        result = TaskValidator().validate(p)
        assert len(result.errors) == 2


# ===========================================================================
# ApprovalValidator
# ===========================================================================


class TestApprovalValidator:
    def _file(self, vault: Path, name: str, content: str) -> Path:
        p = vault / "Approvals" / name
        p.write_text(content)
        return p

    def _valid_fm(self) -> str:
        return (
            "---\n"
            "approval_id: APR-test-202602\n"
            "nonce: abc-123-def\n"
            "approval_status: pending\n"
            "created_at: '2026-02-04T10:00:00+00:00'\n"
            "expires_at: '2026-02-04T22:00:00+00:00'\n"
            "---\n\n"
            "# Approval Request\n"
        )

    def test_valid_approval(self, vault_dir):
        p = self._file(vault_dir, "good-apr.md", self._valid_fm())
        result = ApprovalValidator().validate(p)
        assert result.is_valid

    def test_missing_frontmatter(self, vault_dir):
        p = self._file(vault_dir, "no-fm.md", "# Plain markdown\n")
        result = ApprovalValidator().validate(p)
        assert not result.is_valid
        assert "missing YAML frontmatter" in result.errors[0]

    def test_unclosed_frontmatter(self, vault_dir):
        p = self._file(
            vault_dir, "unclosed.md", "---\napproval_id: x\n# Oops no closing\n"
        )
        result = ApprovalValidator().validate(p)
        assert not result.is_valid
        assert "unclosed" in result.errors[0]

    def test_missing_nonce(self, vault_dir):
        fm = (
            "---\n"
            "approval_id: APR-x\n"
            "approval_status: pending\n"
            "created_at: '2026-01-01T00:00:00+00:00'\n"
            "expires_at: '2026-01-02T00:00:00+00:00'\n"
            "---\n\n# Body\n"
        )
        p = self._file(vault_dir, "no-nonce.md", fm)
        result = ApprovalValidator().validate(p)
        assert not result.is_valid
        assert any("nonce" in e for e in result.errors)

    def test_invalid_status_value(self, vault_dir):
        fm = (
            "---\n"
            "approval_id: APR-y\n"
            "nonce: n1\n"
            "approval_status: maybe\n"
            "created_at: '2026-01-01T00:00:00+00:00'\n"
            "expires_at: '2026-01-02T00:00:00+00:00'\n"
            "---\n\n# Body\n"
        )
        p = self._file(vault_dir, "bad-status.md", fm)
        result = ApprovalValidator().validate(p)
        assert not result.is_valid
        assert any("invalid approval_status" in e for e in result.errors)

    def test_all_valid_statuses_accepted(self, vault_dir):
        for status in ("pending", "approved", "rejected", "timeout"):
            fm = (
                "---\n"
                f"approval_id: APR-{status}\n"
                "nonce: n\n"
                f"approval_status: {status}\n"
                "created_at: '2026-01-01T00:00:00+00:00'\n"
                "expires_at: '2026-01-02T00:00:00+00:00'\n"
                "---\n\n# Body\n"
            )
            p = self._file(vault_dir, f"status-{status}.md", fm)
            assert (
                ApprovalValidator().validate(p).is_valid
            ), f"status={status} should be valid"


# ===========================================================================
# BriefingValidator
# ===========================================================================


class TestBriefingValidator:
    def _file(self, vault: Path, name: str, content: str) -> Path:
        p = vault / "Briefings" / name
        p.write_text(content)
        return p

    def test_valid_briefing(self, vault_dir):
        content = (
            "---\n"
            "report_type: executive_summary\n"
            "total_tasks: 5\n"
            "generated_at: '2026-02-04T12:00:00+00:00'\n"
            "---\n\n"
            "# Briefing\n"
        )
        p = self._file(vault_dir, "good-brief.md", content)
        assert BriefingValidator().validate(p).is_valid

    def test_missing_frontmatter(self, vault_dir):
        p = self._file(vault_dir, "no-fm.md", "# Just a heading\n")
        result = BriefingValidator().validate(p)
        assert not result.is_valid

    def test_missing_generated_at(self, vault_dir):
        content = (
            "---\n"
            "report_type: executive_summary\n"
            "total_tasks: 3\n"
            "---\n\n# Brief\n"
        )
        p = self._file(vault_dir, "no-gen.md", content)
        result = BriefingValidator().validate(p)
        assert not result.is_valid
        assert any("generated_at" in e for e in result.errors)

    def test_missing_report_type(self, vault_dir):
        content = (
            "---\n"
            "total_tasks: 3\n"
            "generated_at: '2026-02-04T00:00:00+00:00'\n"
            "---\n\n# Brief\n"
        )
        p = self._file(vault_dir, "no-type.md", content)
        result = BriefingValidator().validate(p)
        assert not result.is_valid
        assert any("report_type" in e for e in result.errors)


# ===========================================================================
# VaultValidator — full-vault scanning
# ===========================================================================


class TestVaultValidator:
    def test_empty_vault_is_valid(self, vault_dir):
        v = VaultValidator(vault_dir)
        assert v.is_valid
        assert v.total_errors == 0

    def test_single_valid_task(self, vault_dir):
        (vault_dir / "Done" / "task.md").write_text(
            "# task.md\n\n**Priority**: High\n**From**: x@y.com\n\n---\nBody\n"
        )
        assert VaultValidator(vault_dir).is_valid

    def test_invalid_task_detected(self, vault_dir):
        (vault_dir / "Needs_Action" / "bad.md").write_text("# bad\n\nNo fields.\n")
        v = VaultValidator(vault_dir)
        assert not v.is_valid
        assert v.total_errors == 2  # missing Priority + From

    def test_mixed_good_and_bad_across_folders(self, vault_dir):
        # Good task in Done
        (vault_dir / "Done" / "good.md").write_text(
            "# good\n\n**Priority**: Low\n**From**: a@b.com\n\n---\nDone\n"
        )
        # Bad task in Inbox
        (vault_dir / "Inbox" / "bad.md").write_text("# bad\n\nNothing.\n")
        # Valid approval
        (vault_dir / "Approvals" / "apr.md").write_text(
            "---\n"
            "approval_id: APR-1\nnonce: n\napproval_status: pending\n"
            "created_at: '2026-01-01T00:00:00+00:00'\n"
            "expires_at: '2026-01-02T00:00:00+00:00'\n"
            "---\n\n# Approval\n"
        )
        v = VaultValidator(vault_dir)
        results = v.validate_all()

        assert results["Done"][0].is_valid
        assert not results["Inbox"][0].is_valid
        assert results["Approvals"][0].is_valid
        assert v.total_errors == 2  # only the bad Inbox task

    def test_validate_all_returns_per_folder(self, vault_dir):
        (vault_dir / "In_Progress" / "wip.md").write_text(
            "# wip\n\n**Priority**: Medium\n**From**: dev@co.com\n\n---\nWorking\n"
        )
        (vault_dir / "Briefings" / "brief.md").write_text(
            "---\nreport_type: executive_summary\ntotal_tasks: 1\n"
            "generated_at: '2026-02-01T00:00:00+00:00'\n---\n\n# Brief\n"
        )
        results = VaultValidator(vault_dir).validate_all()
        assert "In_Progress" in results
        assert "Briefings" in results
        assert results["In_Progress"][0].is_valid
        assert results["Briefings"][0].is_valid

    def test_nonexistent_vault_is_valid(self):
        """A vault path that doesn't exist has no files → no errors."""
        v = VaultValidator(Path("/nonexistent/vault"))
        assert v.is_valid
        assert v.total_errors == 0

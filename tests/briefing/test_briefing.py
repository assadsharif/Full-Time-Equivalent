"""
CEO Briefing tests (spec 007 — Bronze Tier).

Coverage map:
  TestTaskParsing          — plain markdown, YAML-frontmatter + persistence_loop,
                             priority emoji mapping, missing fields
  TestBriefingAggregator   — empty /Done, single task, multiple tasks,
                             stats computation (by_priority, by_sender, top_senders)
  TestTemplateRenderer     — render returns string, render_to_file creates file,
                             template placeholders fully resolved
  TestBriefingEndToEnd     — vault layout simulation: populate /Done → aggregate
                             → render → verify output in /Briefings
"""

import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.briefing.aggregator import BriefingAggregator
from src.briefing.models import BriefingData, TaskSummary
from src.briefing.template_renderer import TemplateRenderer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = PROJECT_ROOT / "templates" / "briefing"


@pytest.fixture
def vault_dir():
    d = Path(tempfile.mkdtemp())
    (d / "Done").mkdir()
    (d / "Briefings").mkdir()
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _done_file(vault: Path, name: str, content: str) -> Path:
    p = vault / "Done" / name
    p.write_text(content)
    return p


# ===========================================================================
# Task file parsing
# ===========================================================================


class TestTaskParsing:
    def test_plain_markdown_task(self, vault_dir):
        _done_file(
            vault_dir,
            "review-docs.md",
            "# review-docs.md\n\n"
            "\u0001\u0001Priority**: \U0001f7e0 High\n"
            "**Status**: Done\n"
            "**From**: alice@example.com\n\n"
            "---\n\n"
            "All docs reviewed and approved.\n",
        )
        agg = BriefingAggregator(vault_dir / "Done")
        summary = agg._parse_task_file(vault_dir / "Done" / "review-docs.md")

        assert summary.name == "review-docs"
        assert summary.sender == "alice@example.com"
        assert "reviewed" in summary.body
        assert summary.persistence_iterations == 0

    def test_task_with_persistence_frontmatter(self, vault_dir):
        _done_file(
            vault_dir,
            "deploy-staging.md",
            "---\n"
            "persistence_loop:\n"
            "  iteration: 3\n"
            "  consecutive_retries: 0\n"
            "---\n"
            "# deploy-staging.md\n\n"
            "**Priority**: \U0001f534 Urgent\n"
            "**From**: ci@company.com\n\n"
            "---\n\n"
            "Staging deploy completed.\n",
        )
        summary = BriefingAggregator._parse_task_file(
            vault_dir / "Done" / "deploy-staging.md"
        )
        assert summary.persistence_iterations == 3
        assert summary.priority == "urgent"
        assert summary.sender == "ci@company.com"

    def test_priority_emoji_mapping(self, vault_dir):
        cases = [
            ("\U0001f534 Urgent", "urgent"),
            ("\U0001f7e0 High", "high"),
            ("\U0001f7e1 Medium", "medium"),
            ("\U0001f7e2 Low", "low"),
            ("Normal", "normal"),
        ]
        for i, (raw, expected) in enumerate(cases):
            _done_file(
                vault_dir,
                f"task-{i}.md",
                f"# task-{i}.md\n\n**Priority**: {raw}\n**From**: x@x.com\n\n---\n\nBody.\n",
            )
            summary = BriefingAggregator._parse_task_file(
                vault_dir / "Done" / f"task-{i}.md"
            )
            assert summary.priority == expected, f"Failed for raw={raw!r}"

    def test_missing_fields_use_defaults(self, vault_dir):
        _done_file(vault_dir, "bare.md", "# bare.md\n\nJust some text.\n")
        summary = BriefingAggregator._parse_task_file(vault_dir / "Done" / "bare.md")
        assert summary.sender == "unknown"
        assert summary.priority == "normal"
        assert summary.persistence_iterations == 0


# ===========================================================================
# BriefingAggregator
# ===========================================================================


class TestBriefingAggregator:
    def test_empty_done_folder(self, vault_dir):
        agg = BriefingAggregator(vault_dir / "Done")
        data = agg.aggregate()
        assert data.total_tasks == 0
        assert data.tasks == []
        assert data.by_priority == {}

    def test_single_task(self, vault_dir):
        _done_file(
            vault_dir,
            "one.md",
            "# one.md\n\n**Priority**: \U0001f7e0 High\n**From**: bob@test.com\n\n---\n\nDone.\n",
        )
        data = BriefingAggregator(vault_dir / "Done").aggregate()
        assert data.total_tasks == 1
        assert data.tasks[0].name == "one"
        assert data.by_priority == {"high": 1}
        assert data.by_sender == {"bob@test.com": 1}

    def test_multiple_tasks_stats(self, vault_dir):
        _done_file(
            vault_dir, "a.md",
            "# a.md\n\n**Priority**: \U0001f534 Urgent\n**From**: ceo@co.com\n\n---\n\nA.\n",
        )
        _done_file(
            vault_dir, "b.md",
            "# b.md\n\n**Priority**: \U0001f7e0 High\n**From**: ceo@co.com\n\n---\n\nB.\n",
        )
        _done_file(
            vault_dir, "c.md",
            "# c.md\n\n**Priority**: \U0001f7e0 High\n**From**: dev@co.com\n\n---\n\nC.\n",
        )
        data = BriefingAggregator(vault_dir / "Done").aggregate()

        assert data.total_tasks == 3
        assert data.by_priority == {"high": 2, "urgent": 1}
        assert data.by_sender == {"ceo@co.com": 2, "dev@co.com": 1}
        assert data.top_senders[0] == ("ceo@co.com", 2)

    def test_avg_iterations_computed(self, vault_dir):
        _done_file(
            vault_dir, "iter1.md",
            "---\npersistence_loop:\n  iteration: 2\n---\n"
            "# iter1.md\n\n**From**: x@x.com\n\n---\n\nBody.\n",
        )
        _done_file(
            vault_dir, "iter2.md",
            "---\npersistence_loop:\n  iteration: 4\n---\n"
            "# iter2.md\n\n**From**: x@x.com\n\n---\n\nBody.\n",
        )
        data = BriefingAggregator(vault_dir / "Done").aggregate()
        assert data.avg_iterations == 3.0

    def test_nonexistent_done_folder(self):
        """Aggregator handles a missing /Done gracefully."""
        agg = BriefingAggregator(Path("/nonexistent/Done"))
        data = agg.aggregate()
        assert data.total_tasks == 0


# ===========================================================================
# TemplateRenderer
# ===========================================================================


class TestTemplateRenderer:
    def _sample_data(self) -> BriefingData:
        now = datetime.now(timezone.utc)
        return BriefingData(
            period_start=now.replace(day=now.day - 1) if now.day > 1 else now,
            period_end=now,
            generated_at=now,
            tasks=[
                TaskSummary(
                    name="review-docs",
                    priority="high",
                    sender="alice@example.com",
                    body="All reviewed.",
                    persistence_iterations=1,
                ),
                TaskSummary(
                    name="fix-bug-42",
                    priority="urgent",
                    sender="bob@example.com",
                    body="Bug squashed.",
                    persistence_iterations=3,
                ),
            ],
            total_tasks=2,
            by_priority={"high": 1, "urgent": 1},
            by_sender={"alice@example.com": 1, "bob@example.com": 1},
            avg_iterations=2.0,
            top_senders=[("alice@example.com", 1), ("bob@example.com", 1)],
        )

    def test_render_returns_string(self):
        renderer = TemplateRenderer(TEMPLATE_DIR)
        output = renderer.render("executive_summary.md.j2", self._sample_data())
        assert isinstance(output, str)
        assert len(output) > 0

    def test_render_contains_task_names(self):
        renderer = TemplateRenderer(TEMPLATE_DIR)
        output = renderer.render("executive_summary.md.j2", self._sample_data())
        assert "Review Docs" in output or "review-docs" in output
        assert "Fix Bug 42" in output or "fix-bug-42" in output

    def test_render_contains_senders(self):
        renderer = TemplateRenderer(TEMPLATE_DIR)
        output = renderer.render("executive_summary.md.j2", self._sample_data())
        assert "alice@example.com" in output
        assert "bob@example.com" in output

    def test_render_contains_stats(self):
        renderer = TemplateRenderer(TEMPLATE_DIR)
        output = renderer.render("executive_summary.md.j2", self._sample_data())
        assert "2" in output          # total_tasks
        assert "2.0" in output        # avg_iterations

    def test_render_no_unresolved_placeholders(self):
        renderer = TemplateRenderer(TEMPLATE_DIR)
        output = renderer.render("executive_summary.md.j2", self._sample_data())
        assert "{{" not in output
        assert "}}" not in output

    def test_render_to_file(self, vault_dir):
        renderer = TemplateRenderer(TEMPLATE_DIR)
        target = vault_dir / "Briefings" / "briefing-2026-02-04.md"
        renderer.render_to_file("executive_summary.md.j2", self._sample_data(), target)
        assert target.exists()
        assert "Executive Briefing" in target.read_text()


# ===========================================================================
# End-to-end: vault layout → aggregate → render → Briefings
# ===========================================================================


class TestBriefingEndToEnd:
    def test_full_pipeline(self, vault_dir):
        """Populate /Done, aggregate, render, verify /Briefings output."""
        # --- populate /Done with realistic files ---
        _done_file(
            vault_dir, "deploy-prod.md",
            "---\npersistence_loop:\n  iteration: 2\n---\n"
            "# deploy-prod.md\n\n"
            "**Priority**: \U0001f534 Urgent\n"
            "**Status**: Done\n"
            "**From**: ops@company.com\n\n"
            "---\n\n"
            "Production deployment v2.1 rolled out successfully.\n",
        )
        _done_file(
            vault_dir, "client-report.md",
            "# client-report.md\n\n"
            "**Priority**: \U0001f7e0 High\n"
            "**Status**: Done\n"
            "**From**: sales@company.com\n\n"
            "---\n\n"
            "Q4 client report delivered to Acme Corp.\n",
        )
        _done_file(
            vault_dir, "newsletter-draft.md",
            "# newsletter-draft.md\n\n"
            "**Priority**: \U0001f7e2 Low\n"
            "**Status**: Done\n"
            "**From**: marketing@company.com\n\n"
            "---\n\n"
            "January newsletter draft reviewed.\n",
        )

        # --- aggregate ---
        data = BriefingAggregator(vault_dir / "Done").aggregate()
        assert data.total_tasks == 3
        assert data.by_priority["urgent"] == 1
        assert data.by_priority["high"] == 1

        # --- render ---
        renderer = TemplateRenderer(TEMPLATE_DIR)
        output_path = vault_dir / "Briefings" / "weekly-briefing.md"
        renderer.render_to_file("executive_summary.md.j2", data, output_path)

        # --- verify ---
        assert output_path.exists()
        report = output_path.read_text()
        assert "Executive Briefing" in report
        assert "3" in report                       # total_tasks
        assert "ops@company.com" in report
        assert "sales@company.com" in report
        assert "marketing@company.com" in report
        assert "Production deployment" in report
        assert "{{" not in report                  # no unresolved placeholders

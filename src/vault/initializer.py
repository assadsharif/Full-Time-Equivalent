"""
Vault Initializer — create and verify the standard Obsidian vault layout (spec 008).

Creates the 7 core workflow folders, YAML frontmatter schema files,
and seed documents (Dashboard.md, Company_Handbook.md, task template)
that form the memory layer for the AI Employee system.

Idempotent: running ``initialize()`` on an existing vault only fills gaps;
it never overwrites files that are already present.
"""

from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CORE_FOLDERS = [
    "Inbox",
    "Needs_Action",
    "In_Progress",
    "Done",
    "Approvals",
    "Briefings",
    "Attachments",
    "Templates",
]

_SCHEMA_DIR = Path(".vault_schema") / "frontmatter_schemas"

# --- frontmatter schemas ----------------------------------------------------

_TASK_SCHEMA = """\
# Task frontmatter schema (spec 008)
# Files in Inbox / Needs_Action / In_Progress / Done must satisfy this schema.
required_fields:
  - Priority   # High | Medium | Low
  - From       # sender address (email or phone)
optional_fields:
  - Subject    # short summary
  - Tags       # list of labels
  - Deadline   # ISO-8601 date
  - Source     # gmail | whatsapp | manual
"""

_APPROVAL_SCHEMA = """\
# Approval frontmatter schema (spec 008 / spec 010)
# Files in Approvals/ must satisfy this schema.
required_fields:
  - approval_id      # unique identifier (APR-...)
  - nonce            # replay-protection token
  - approval_status  # pending | approved | rejected | timeout
  - created_at       # ISO-8601 timestamp
  - expires_at       # ISO-8601 timestamp
optional_fields:
  - action_type      # payment | email | deletion | ...
  - risk_level       # low | medium | high
  - action           # structured action payload
"""

_BRIEFING_SCHEMA = """\
# Briefing frontmatter schema (spec 008 / spec 007)
# Files in Briefings/ must satisfy this schema.
required_fields:
  - report_type    # executive_summary | detailed
  - total_tasks    # integer count
  - generated_at   # ISO-8601 timestamp
optional_fields:
  - period_start   # ISO-8601 date
  - period_end     # ISO-8601 date
  - top_senders    # list of top contributors
"""

_SCHEMAS: dict[str, str] = {
    "task.yaml": _TASK_SCHEMA,
    "approval.yaml": _APPROVAL_SCHEMA,
    "briefing.yaml": _BRIEFING_SCHEMA,
}

# --- seed documents ----------------------------------------------------------

_TASK_TEMPLATE = """\
# {subject}

**Priority**: Medium
**From**: {sender}

---

## Description

Describe the task here.

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
"""

_COMPANY_HANDBOOK = """\
# Company Handbook — AI Employee Context

## About This Document

This handbook provides the authoritative context and policies for the
AI Employee system.  The orchestrator reads it on every sweep to stay
aligned with operational rules.

## Core Principles

1. **File-Driven** — All state lives in the vault.  The vault IS the
   single source of truth (Constitution §2).
2. **Human-in-the-Loop** — Payments, outbound emails, and destructive
   actions require explicit approval before execution (Constitution §6-7).
3. **Auditability** — Every action is logged and traceable
   (Constitution §8).
4. **Local-First** — No data leaves the system without explicit
   approval (Constitution §3).
5. **Fail-Safe** — When in doubt, stop and surface the decision to a
   human (Constitution §9).

## Task Lifecycle

```
Inbox  →  Needs_Action  →  In_Progress  →  Done
                  ↓
           Approvals (if required by risk level)
```

## Folder Reference

| Folder          | Purpose                                          |
|-----------------|--------------------------------------------------|
| Inbox           | New tasks arriving from watchers                 |
| Needs_Action    | Tasks ready for orchestrator pick-up             |
| In_Progress     | Tasks currently being processed                  |
| Done            | Completed tasks — permanent audit trail          |
| Approvals       | Pending human-approval requests                  |
| Briefings       | Generated executive briefing reports             |
| Attachments     | Binary files, images, documents                  |
| Templates       | Seed templates for new tasks / approvals         |

## Emergency Procedures

1. **Stop the AI Employee** — Create a `.claude_stop` file in the vault
   root.  The orchestrator finishes its current task then halts.
2. **Review pending approvals** — Open any file in `Approvals/`.
3. **Check logs** — Look in the `/Logs` directory for recent activity.
"""


def _render_dashboard(vault_path: Path) -> str:
    """Render Dashboard.md with current folder counts."""
    rows = []
    for folder in CORE_FOLDERS:
        count = (
            sum(1 for _ in (vault_path / folder).glob("*.md"))
            if (vault_path / folder).exists()
            else 0
        )
        rows.append(f"| {folder:<16} | {count} |")

    return (
        "# AI Employee Dashboard\n\n"
        f"*Last updated: {date.today().isoformat()}*\n\n"
        "## Vault Status\n\n"
        "| Folder           | Files |\n"
        "|------------------|-------|\n" + "\n".join(rows) + "\n\n"
        "## Recent Activity\n\n"
        "*No activity recorded yet.*\n\n"
        "## Pending Approvals\n\n"
        "*None.*\n\n"
        "## Quick Reference\n\n"
        "- **Add a task** — drop a Markdown file into `Inbox/`\n"
        "- **Approve an action** — edit the file in `Approvals/` and set\n"
        "  `approval_status: approved`\n"
        "- **Emergency stop** — create `.claude_stop` in the vault root\n"
        "- **View logs** — check the `/Logs` directory\n"
    )


# ---------------------------------------------------------------------------
# VaultInitializer
# ---------------------------------------------------------------------------


class VaultInitializer:
    """Create or verify the standard AI Employee vault layout.

    All operations are idempotent — existing files and directories are
    never overwritten.
    """

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize(self) -> list[str]:
        """Create the full vault structure.

        Returns a list of ``category:name`` strings for every item that
        was actually created (items that already existed are skipped).
        """
        self.vault_path.mkdir(parents=True, exist_ok=True)
        created: list[str] = []

        # 1. Core workflow folders
        for folder in CORE_FOLDERS:
            p = self.vault_path / folder
            if not p.exists():
                p.mkdir()
                created.append(f"folder:{folder}")

        # 2. Schema directory + files
        schema_dir = self.vault_path / _SCHEMA_DIR
        schema_dir.mkdir(parents=True, exist_ok=True)
        for name, content in _SCHEMAS.items():
            sp = schema_dir / name
            if not sp.exists():
                sp.write_text(content, encoding="utf-8")
                created.append(f"schema:{name}")

        # 3. Seed documents
        for filename, content in [
            ("Dashboard.md", _render_dashboard(self.vault_path)),
            ("Company_Handbook.md", _COMPANY_HANDBOOK),
        ]:
            p = self.vault_path / filename
            if not p.exists():
                p.write_text(content, encoding="utf-8")
                created.append(f"file:{filename}")

        # 4. Task template inside Templates/
        task_tmpl = self.vault_path / "Templates" / "task_template.md"
        if not task_tmpl.exists():
            task_tmpl.write_text(_TASK_TEMPLATE, encoding="utf-8")
            created.append("file:Templates/task_template.md")

        return created

    def check_structure(self) -> dict[str, list[str]]:
        """Report what is missing from the expected vault layout.

        Returns a dict with keys ``folders``, ``schemas``, ``files``,
        each mapping to a (possibly empty) list of missing item names.
        """
        missing: dict[str, list[str]] = {"folders": [], "schemas": [], "files": []}

        for folder in CORE_FOLDERS:
            if not (self.vault_path / folder).exists():
                missing["folders"].append(folder)

        schema_dir = self.vault_path / _SCHEMA_DIR
        for schema_name in _SCHEMAS:
            if not (schema_dir / schema_name).exists():
                missing["schemas"].append(schema_name)

        for filename in ("Dashboard.md", "Company_Handbook.md"):
            if not (self.vault_path / filename).exists():
                missing["files"].append(filename)

        return missing

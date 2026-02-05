# Core FTE Skills — Index

This document is the single-page reference for every skill shipped with the
Digital FTE system.  Each entry lists what the skill does, when to invoke it,
and a one-line invocation example.

---

## Quick-Reference Table

| # | Skill Name | Command | Category | Safety | What It Does | Invoke When… |
|---|-----------|---------|----------|--------|--------------|--------------|
| 1 | `fte.vault.init` | `/fte.vault.init` | vault | medium | Creates the canonical 8-folder Obsidian vault from `.vault_templates/` | You need a fresh vault or want to reset the scaffold |
| 2 | `fte.vault.status` | `/fte.vault.status` | vault | low | Shows task counts per folder, pending-approval alerts, backlog warnings | You want a live snapshot of vault activity |
| 3 | `fte.vault.validate` | `/fte.vault.validate` | vault | low | Runs structure + state-transition + filename validators | You want to confirm the vault is consistent before acting |
| 4 | `fte.approval.review` | `/fte.approval.review` | approval | high | Lists pending approvals and captures approve/reject decisions | You see a pending-approval alert and want to clear the queue |
| 5 | `fte.briefing.generate` | `/fte.briefing.generate` | briefing | medium | Aggregates Done-folder tasks into a CEO briefing Markdown file | It is time for a weekly or monthly executive summary |
| 6 | `fte.watcher.status` | `/fte.watcher.status` | watcher | low | Reads watcher checkpoints and surfaces last-seen, errors, health per watcher | You want to know if Gmail / WhatsApp watchers are polling |
| 7 | `fte.task.triage` | `/fte.task.triage` | task | medium | Classifies Inbox tasks by priority/source and moves them to Needs_Action | New tasks have arrived and you want to route them into the active queue |
| 8 | `fte.orchestrator.status` | `/fte.orchestrator.status` | orchestrator | low | Shows scheduler liveness, queue depth, and 24 h throughput/error metrics | You want to know if the orchestrator is running and healthy |
| 9 | `fte.security.scan` | `/fte.security.scan` | security | low | Scans vault `.md` files for secrets, tokens, and PII patterns | You want to verify no secrets leaked into task files before a push |
| 10 | `fte.health.check` | `/fte.health.check` | diagnostic | low | Runs vault-validate + watcher + orchestrator + security and aggregates into one report | You want a single system-wide confidence check |

---

## Skill Groups

### Vault Management
Skills 1-3 cover the full vault lifecycle.  Start with `/fte.vault.status`
for a quick read; use `/fte.vault.validate` before any bulk operations.

### Workflow Automation
Skills 4 (approvals) and 7 (triage) handle the two main decision gates in the
task pipeline.  Approvals require human sign-off (`safety_level: high`); triage
is safe to run unattended.

### Reporting
Skills 5 (briefing) and 8 (orchestrator status) produce human-readable
summaries.  Briefing is the formal CEO deliverable; orchestrator status is the
ops dashboard.

### Monitoring & Security
Skills 6 (watchers), 9 (security), and 10 (health check) are the observability
layer.  `/fte.health.check` is the one-stop entry point; the others can be
invoked individually for targeted investigation.

---

## Invocation Examples

```bash
# Quick system check
/fte.health.check

# See what's in the vault right now
/fte.vault.status

# Route new messages into the active queue
/fte.task.triage

# Preview triage without moving files
/fte.task.triage --dry-run

# Generate this week's CEO briefing
/fte.briefing.generate

# Generate a monthly briefing
/fte.briefing.generate --period month

# Review and action pending approvals
/fte.approval.review

# Check watcher health (single watcher)
/fte.watcher.status --watcher gmail

# Scan for leaked secrets (high+ only)
/fte.security.scan --severity high

# Orchestrator metrics for the last 7 days
/fte.orchestrator.status --since 7d

# Validate vault structure
/fte.vault.validate
```

---

## Adding a New Core Skill

1. Scaffold: `python scripts/init_skill.py fte.<category>.<action> --category <cat>`
2. Fill the SKILL.md sections (see `docs/skills/skill-creation-guide.md`)
3. Validate: `python scripts/validate_skill.py .claude/skills/<slug> --level quality`
4. Add a row to the table above
5. Commit and push

---

*Last updated: 2026-02-05 — generated during 009-agent-skills-guide Phase 5.*

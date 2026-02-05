# Vault Structure

This document describes the Obsidian vault layout used by the Digital
FTE system, how it maps to the orchestrator's workflow, and what each
folder and file is for.

## Overview

The vault is a standard Obsidian vault directory that doubles as the
primary task-management surface for the AI Employee.  Folder placement
encodes task state; YAML frontmatter encodes metadata.

## Directory Layout

```
vault/
├── Inbox/                  Task files just received (state: inbox)
├── Needs_Action/           Triaged tasks waiting for action
│                           (state: needs_action | error_queue)
├── In_Progress/            Actively processing (state: in_progress)
├── Done/                   Terminal states (done | rejected | failed)
├── Approvals/              Pending human sign-off (state: pending_approval)
├── Briefings/              Weekly CEO briefing drafts
├── Attachments/            Binary / media attachments
├── Templates/              Reusable .md templates
│   ├── task_template.md
│   ├── approval_template.md
│   └── naming_examples.md
├── Dashboard.md            Live system-status dashboard
├── Company_Handbook.md     Company policies & AI instructions
├── README.md               Human-readable vault overview
├── .obsidian/              Obsidian application configuration
│   ├── app.json
│   ├── appearance.json
│   └── core-plugins.json
└── .gitignore              VCS exclusions (workspace, cache, secrets)
```

## Canonical Template Source

All vault scaffolding originates from the repo's `.vault_templates/`
directory.  `fte vault init` copies this tree into the target vault path
and then generates `Dashboard.md` and `Company_Handbook.md` with live
timestamps.

## Schemas and Validation

YAML frontmatter schemas live in `.vault_schema/frontmatter_schemas/`:

| File | Controls |
|------|----------|
| `task.yaml` | Task metadata, state, history |
| `approval.yaml` | Approval requests, nonces, risk levels |
| `briefing.yaml` | Weekly CEO briefing metadata |

Validation scripts live in `.vault_schema/validation_scripts/`:

| Script | What it checks |
|--------|----------------|
| `validate_vault.py` | Full structure + frontmatter |
| `validate_state.py` | State transitions and history |
| `validate_filename.py` | Filename patterns and sanitisation |

Run all validators at once: `fte vault validate --vault-path <path>`

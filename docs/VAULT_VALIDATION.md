# Vault Validation Guide

This guide explains how to run and interpret validation results for the
AI Employee vault.

## Quick Start

```bash
# Full validation (recommended)
fte vault validate --vault-path /path/to/vault

# Structure + frontmatter only
python .vault_schema/validation_scripts/validate_vault.py /path/to/vault

# State transitions only
python .vault_schema/validation_scripts/validate_state.py /path/to/vault

# Filename patterns only
python .vault_schema/validation_scripts/validate_filename.py /path/to/vault
```

## What Each Validator Checks

### validate_vault.py (Full Structure)

| Check | Severity |
|-------|----------|
| Vault directory exists | Error |
| All 8 required folders present | Error |
| `Dashboard.md` and `Company_Handbook.md` present | Error |
| `.obsidian/app.json` and `core-plugins.json` present | Warning |
| Task files have valid frontmatter (task_id, title, source, state, created_at) | Warning |
| Approval files have required fields (approval_id, nonce, status, etc.) | Warning |
| Briefing files have required fields | Warning |

### validate_state.py (State Transitions)

| Check | Severity |
|-------|----------|
| Task `state` matches its folder | Error |
| `state_history` timestamps are chronological | Error |
| All transitions in history are in the allowed set | Error |
| Last `state_history` entry matches current `state` | Error |
| `failed` tasks have `retry_count >= 3` | Error |

Allowed transitions are defined in `.vault_schema/state_transitions.md`.

### validate_filename.py (Naming Patterns)

| Check | Severity |
|-------|----------|
| Task files match `TASK-YYYYMMDD-NNN.md` | Error |
| Approval files match `APR-YYYYMMDD-NNN.md` | Error |
| Briefing files match `BRIEF-YYYYMMDD.md` | Error |
| Attachment files are ASCII-safe | Warning |
| Stem length ≤ 200 characters | Error |

## Reading the Output

```
🔍 Validating vault: /path/to/vault

   Checked 12 task file(s)

⚠️  2 warning(s):
  ⚠️  Approvals/old-file.md: does not match expected pattern for approvals/
  ⚠️  Attachments/my file.pdf: does not match attachment pattern

🚨 1 naming violation(s):
  ❌ Inbox/bad.md: does not match expected pattern for inbox/

✅ All state transitions valid      ← state validator passed
❌ Vault validation FAILED (1 errors) ← structure validator failed
```

- `✅` = that validator passed
- `❌` = errors that must be fixed
- `⚠️` = warnings that should be addressed but don't block

## Fixing Common Issues

| Error message | Fix |
|---------------|-----|
| `Required folder missing: X` | `mkdir vault/X` |
| `state 'Y' invalid in folder 'Z'` | Move file to the correct folder |
| `does not match expected pattern` | Rename using the pattern in `naming_conventions.md` |
| `state_history timestamps not in order` | Sort `state_history` by timestamp |
| `state 'failed' but retry_count < 3` | Update `retry_count` or change state to `error_queue` |

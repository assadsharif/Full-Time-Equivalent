# Vault Migration Guide

Use this guide when migrating an existing vault to the current
canonical layout, or when upgrading a vault created by an earlier
version of the FTE system.

---

## When to Migrate

- Your vault was created before `.vault_templates/` was introduced and
  lacks `.obsidian/` config, `.gitignore`, or the `Templates/` folder.
- You have task files that do not follow the `TASK-YYYYMMDD-NNN.md`
  naming convention.
- `fte vault validate` reports missing folders or invalid filenames.

---

## Step 1: Back Up

Before making any changes, copy your vault to a safe location:

```bash
cp -r /path/to/vault /path/to/vault-backup-$(date +%Y%m%d)
```

---

## Step 2: Re-initialise Structure

Run vault init with `--force`.  This re-creates all folders and
regenerates `Dashboard.md` and `Company_Handbook.md` (with today's
date).  Existing task files in present folders are **not** deleted.

```bash
fte vault init --vault-path /path/to/vault --force
```

**What changes:**
- Missing folders are created.
- `.obsidian/` config is (re-)written.
- `.gitignore` is (re-)written.
- `Templates/` is populated with current templates.
- `Dashboard.md` and `Company_Handbook.md` are regenerated.

**What stays:**
- Existing `.md` files in `Inbox/`, `Needs_Action/`, etc.
- Files in `Attachments/`.
- Any custom content you added to `Company_Handbook.md` (overwritten —
  restore from backup if needed and re-apply customisations).

---

## Step 3: Rename Task Files

If your existing task files do not match `TASK-YYYYMMDD-NNN.md`, rename
them:

```bash
# Example: rename "my-task.md" created on 2026-02-05
mv Inbox/my-task.md Inbox/TASK-20260205-001.md
```

Use `validate_filename.py` to find all non-conforming files:

```bash
python .vault_schema/validation_scripts/validate_filename.py /path/to/vault
```

---

## Step 4: Add / Fix Frontmatter

Each task file needs at minimum:

```yaml
---
task_id: TASK-YYYYMMDD-NNN
title: <descriptive title>
source: <gmail|whatsapp|file|manual|scheduled>
state: <inbox|needs_action|in_progress|done|...>
created_at: "YYYY-MM-DDTHH:MM:SSZ"
state_history:
  - state: <initial state>
    timestamp: "YYYY-MM-DDTHH:MM:SSZ"
    moved_by: <migrated>
---
```

Set `state` to match the folder the file is currently in:

| Folder | state value |
|--------|-------------|
| `Inbox/` | `inbox` |
| `Needs_Action/` | `needs_action` |
| `In_Progress/` | `in_progress` |
| `Done/` | `done` |

If migrating files that were previously completed, set `state: done`
and place them in `Done/`.

---

## Step 5: Validate

Run the full validator suite and fix any remaining issues:

```bash
fte vault validate --vault-path /path/to/vault
```

Repeat until exit code is `0`.

---

## Step 6: Verify in Obsidian

1. Open the vault in Obsidian.
2. Confirm `Dashboard.md` renders correctly.
3. Browse each folder to ensure files appear.
4. Check that `Company_Handbook.md` still has your custom policies
   (restore from backup if needed).

---

## Rollback

If something went wrong, restore from the backup created in Step 1:

```bash
rm -rf /path/to/vault
cp -r /path/to/vault-backup-YYYYMMDD /path/to/vault
```

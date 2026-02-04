# File Naming Conventions

All files in the vault MUST follow these naming rules.  The filename
validator (`validate_filename.py`) enforces them automatically.

## General Rules

1. Use only ASCII letters, digits, hyphens (`-`), and underscores (`_`).
2. No spaces.  Replace spaces with hyphens.
3. No leading or trailing hyphens or underscores.
4. Maximum filename length: 200 characters (excluding extension).
5. Extension must be `.md` for all vault content files.

## Task Files

**Pattern**: `TASK-YYYYMMDD-NNN.md`

| Part | Format | Example |
|------|--------|---------|
| Prefix | `TASK` | `TASK` |
| Date | `YYYYMMDD` | `20260205` |
| Sequence | 3-digit zero-padded | `001` |
| Extension | `.md` | `.md` |

**Examples**:
- ✅ `TASK-20260205-001.md`
- ✅ `TASK-20260210-042.md`
- ❌ `task-2026-02-05-1.md` (wrong date format, no zero-padding)
- ❌ `My Task.md` (spaces, no prefix)

## Approval Files

**Pattern**: `APR-YYYYMMDD-NNN.md`

| Part | Format | Example |
|------|--------|---------|
| Prefix | `APR` | `APR` |
| Date | `YYYYMMDD` | `20260205` |
| Sequence | 3-digit zero-padded | `001` |
| Extension | `.md` | `.md` |

**Examples**:
- ✅ `APR-20260205-001.md`
- ❌ `approval-jan-5.md`

## Briefing Files

**Pattern**: `BRIEF-YYYYMMDD.md`

| Part | Format | Example |
|------|--------|---------|
| Prefix | `BRIEF` | `BRIEF` |
| Date | `YYYYMMDD` (week start) | `20260202` |
| Extension | `.md` | `.md` |

**Examples**:
- ✅ `BRIEF-20260202.md`
- ❌ `briefing_feb_2.md`

## Attachment Files

Attachments in `Attachments/` may retain their original filename but
must satisfy the general rules (no spaces; ASCII-safe characters only).
The validator will warn — not error — on attachment filenames.

## Summary Table

| Folder | Pattern | Regex |
|--------|---------|-------|
| Inbox / Needs_Action / In_Progress / Done | `TASK-YYYYMMDD-NNN.md` | `^TASK-\d{8}-\d{3}\.md$` |
| Approvals | `APR-YYYYMMDD-NNN.md` | `^APR-\d{8}-\d{3}\.md$` |
| Briefings | `BRIEF-YYYYMMDD.md` | `^BRIEF-\d{8}\.md$` |
| Attachments | General rules only | `^[A-Za-z0-9_-]+\.\w+$` |
| Templates | Any `.md` | `^[A-Za-z0-9_-]+\.md$` |

# Naming Convention Examples

Quick reference for how to name files in each vault folder.

## Task Files (`Inbox/`, `Needs_Action/`, `In_Progress/`, `Done/`)

```
TASK-20260205-001.md    ← first task created on 2026-02-05
TASK-20260205-002.md    ← second task, same day
TASK-20260210-001.md    ← first task on 2026-02-10
```

## Approval Files (`Approvals/`)

```
APR-20260205-001.md     ← first approval request on 2026-02-05
APR-20260207-003.md     ← third approval request on 2026-02-07
```

## Briefing Files (`Briefings/`)

```
BRIEF-20260202.md       ← briefing for week starting 2026-02-02
BRIEF-20260209.md       ← briefing for week starting 2026-02-09
```

## Attachments (`Attachments/`)

Retain original name but must be ASCII-safe with no spaces:

```
invoice-vendor-a.pdf
screenshot-2026-02-05.png
contract_renewal.docx
```

## Common Mistakes

| Wrong | Correct | Why |
|-------|---------|-----|
| `My Task.md` | `TASK-20260205-001.md` | Tasks must use TASK prefix |
| `task-2026-02-05.md` | `TASK-20260205-001.md` | Date must be YYYYMMDD, prefix uppercase |
| `APR_001.md` | `APR-20260205-001.md` | Use hyphens, include date |
| `Report Feb.pdf` | `report-feb.pdf` | No spaces in filenames |

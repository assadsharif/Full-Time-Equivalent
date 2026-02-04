# Task State Transition Rules

This document defines the allowed state transitions for tasks moving
between vault folders.  The orchestrator and watchers MUST enforce these
rules before moving any task file.

## States

| State | Folder | Description |
|-------|--------|-------------|
| `inbox` | `Inbox/` | Newly received, not yet triaged |
| `needs_action` | `Needs_Action/` | Triaged — requires a concrete action |
| `in_progress` | `In_Progress/` | Actively being worked on |
| `pending_approval` | `Approvals/` | Waiting for human sign-off |
| `done` | `Done/` | Completed successfully |
| `rejected` | `Done/` | Explicitly rejected (terminal) |
| `error_queue` | `Needs_Action/` | Hit an error; retryable |
| `failed` | `Done/` | Exhausted retries or unrecoverable (terminal) |

## Allowed Transitions

```
inbox              → needs_action
inbox              → pending_approval      (requires_approval == true)
needs_action       → in_progress
needs_action       → pending_approval
needs_action       → error_queue           (processing error)
in_progress        → done
in_progress        → pending_approval
in_progress        → error_queue           (processing error)
pending_approval   → in_progress           (approved)
pending_approval   → rejected              (rejected — terminal)
error_queue        → needs_action          (retry)
error_queue        → failed                (max retries exhausted — terminal)
```

## Terminal States

`done`, `rejected`, and `failed` are terminal.  No transitions out of
these states are permitted.

## Retry Budget

- Default max retries: **3**
- Each retry increments `retry_count` in frontmatter
- When `retry_count >= max_retries`, transition `error_queue → failed`

## State History

Every transition MUST append an entry to the `state_history` array in
the task frontmatter before the file is moved:

```yaml
state_history:
  - state: inbox
    timestamp: "2026-02-05T10:00:00Z"
    moved_by: "watcher-gmail"
  - state: needs_action
    timestamp: "2026-02-05T10:05:00Z"
    moved_by: "orchestrator"
```

## Folder ↔ State Mapping

A task's `state` field MUST match the folder it resides in according to
the table above.  `validate_state.py` enforces this at validation time.

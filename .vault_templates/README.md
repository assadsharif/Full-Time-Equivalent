# AI Employee Vault

This is the canonical Obsidian vault for the Digital FTE system.

## Folder Layout

```
vault/
├── Inbox/              ← New tasks arrive here
├── Needs_Action/       ← Triaged; ready for action (also: error_queue)
├── In_Progress/        ← Actively being worked on
├── Done/               ← Completed, rejected, or failed tasks
├── Approvals/          ← Tasks awaiting human sign-off
├── Briefings/          ← Weekly CEO briefing drafts
├── Attachments/        ← Binary/media attachments
├── Templates/          ← Reusable task & approval templates
├── Dashboard.md        ← Live system status
├── Company_Handbook.md ← Policies & AI instructions
├── .obsidian/          ← Obsidian app configuration
└── .gitignore          ← VCS exclusions
```

## Task State Flow

```
                    ┌──────────┐
          ──────►   │  inbox   │
                    └────┬─────┘
                         │
                         ▼
                 ┌───────────────┐      ┌───────────────────┐
          ──────►│ needs_action  │─────►│ pending_approval  │
          │      └──────┬────────┘      └────────┬──────────┘
          │             │                        │
          │  (retry)    ▼                        │ (approved)
          │      ┌─────────────┐                 │
          └──────│ error_queue │                 ▼
                 └──────┬──────┘         ┌─────────────┐
                        │                │ in_progress │──────►  done  ✓
                        │ (max retries)  └──────┬──────┘
                        ▼                       │
                     failed  ✗                  │ (error)
                                                ▼
                                          error_queue
                                                │ (rejected)
                                                ▼
                                            rejected  ✗
```

### Terminal States

- **done** — task completed successfully
- **rejected** — task explicitly rejected by human
- **failed** — retries exhausted; requires manual intervention

### Key Rules

1. Every state change appends an entry to `state_history` in frontmatter.
2. A task's `state` field must match the folder it lives in.
3. Terminal states (`done`, `rejected`, `failed`) have no outgoing transitions.
4. `error_queue` → `failed` only when `retry_count >= 3`.

See `.vault_schema/state_transitions.md` for the full specification.

## Validation

```bash
# Full vault structure validation
python .vault_schema/validation_scripts/validate_vault.py <vault_path>

# State-transition-only validation
python .vault_schema/validation_scripts/validate_state.py <vault_path>

# Via CLI
fte vault validate --vault-path <vault_path>
```

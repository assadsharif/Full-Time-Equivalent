# Vault CLI Reference

All vault commands are under the `fte vault` group.

## Commands

### `fte vault init`

Initialize a new vault with the canonical folder layout, Obsidian
config, templates, and generated Dashboard / Handbook files.

```bash
fte vault init                          # Use path from config
fte vault init --vault-path ~/my-vault  # Explicit path
fte vault init --force                  # Overwrite an existing vault
```

**What it creates:**
- 8 core folders (`Inbox`, `Needs_Action`, `In_Progress`, `Done`, `Approvals`, `Briefings`, `Attachments`, `Templates`)
- `.obsidian/` with `app.json`, `appearance.json`, `core-plugins.json`
- `.gitignore`
- `Templates/` with `task_template.md`, `approval_template.md`, `naming_examples.md`
- `Dashboard.md` (date-stamped)
- `Company_Handbook.md` (date-stamped)

---

### `fte vault status`

Display a table of task counts per folder and highlight alerts
(pending approvals, large Needs_Action backlogs).

```bash
fte vault status
fte vault status --vault-path ~/my-vault
```

---

### `fte vault validate`

Run all structural, state-transition, and filename validators against
the vault.

```bash
fte vault validate                          # Full validation
fte vault validate --vault-path ~/my-vault  # Explicit path
fte vault validate --state-only             # State transitions only
```

**Validators executed:**
1. `validate_vault.py` — folder presence, required files, Obsidian config, frontmatter fields
2. `validate_state.py` — folder↔state consistency, history ordering, transition legality
3. `validate_filename.py` — TASK-/APR-/BRIEF- patterns, general naming rules

Exit code `0` = all passed; `1` = one or more validators failed.

---

### `fte vault approve <APPROVAL_ID>`

Approve a pending action.  Validates the nonce and integrity hash
before updating the approval status to `approved`.

```bash
fte vault approve APR-20260205-001
```

---

### `fte vault reject <APPROVAL_ID>`

Reject a pending action.  Prompts for a reason if `--reason` is not
provided.

```bash
fte vault reject APR-20260205-001
fte vault reject APR-20260205-001 --reason "Amount exceeds budget"
```

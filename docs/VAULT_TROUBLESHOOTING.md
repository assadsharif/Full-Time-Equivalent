# Vault Troubleshooting Guide

Common issues and how to resolve them.

---

## Vault initialization fails

**Symptom**: `fte vault init` exits with an error.

**Causes & fixes**:
1. **Permission denied** — Ensure the target directory (or its parent)
   is writable.  `chmod 755 <parent>` or choose a different path.
2. **`.vault_templates/` not found** — The script walks up from
   `src/cli/vault.py` looking for `.vault_templates/`.  If you moved the
   repo or are running from an unexpected working directory, set
   `--vault-path` explicitly and ensure you are inside the repo tree.

---

## Validation reports missing folders

**Symptom**: `fte vault validate` shows `Required folder missing`.

**Fix**: The vault was either partially initialised or folders were
deleted manually.  Re-run `fte vault init --force` to recreate the
full layout (existing files in present folders are not deleted).

---

## Tasks stuck in wrong folder

**Symptom**: `validate_state.py` reports `state 'X' invalid in folder 'Y'`.

**Explanation**: The task's `state` frontmatter field does not match the
folder it is currently in.

**Fix**:
- Move the file to the folder that corresponds to its `state`, **or**
- Update the `state` field in frontmatter to match where the file is.
- Append a corrective entry to `state_history`.

Reference: see the folder↔state mapping in `.vault_schema/state_transitions.md`.

---

## Approval nonce validation fails

**Symptom**: `fte vault approve` reports an invalid nonce.

**Causes**:
1. The nonce in the approval file does not match UUID format
   (`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).
2. The approval file was manually edited and the nonce was corrupted.

**Fix**: Regenerate the approval file from the template
(`.vault_templates/Templates/approval_template.md`) with a fresh nonce.

---

## Filename validation errors on existing files

**Symptom**: `validate_filename.py` flags files that were created before
the naming conventions were adopted.

**Fix**: Rename files to match the expected patterns:
- Tasks: `TASK-YYYYMMDD-NNN.md`
- Approvals: `APR-YYYYMMDD-NNN.md`
- Briefings: `BRIEF-YYYYMMDD.md`

Use the `sanitize()` function from `validate_filename.py` to generate
safe stems for attachment files:

```python
from validate_filename import sanitize
print(sanitize("My Messy File Name!"))  # → My-Messy-File-Name
```

---

## Dashboard shows stale counts

**Symptom**: The Quick Stats in `Dashboard.md` do not reflect the
current folder contents.

**Explanation**: Dashboard counts are populated once at `vault init`
time (all zeros).  They are intended to be updated by the orchestrator
watchers at runtime.

**Workaround**: Run `fte vault status` for live counts.  The watchers
will keep the dashboard current once they are running (`fte watcher
start <name>`).

---

## Validation script import errors

**Symptom**: Running `validate_vault.py` directly fails with
`ModuleNotFoundError: No module named 'yaml'`.

**Fix**: Install PyYAML if missing:
```bash
pip install pyyaml
```
The validation scripts require only the Python standard library plus
`pyyaml`.

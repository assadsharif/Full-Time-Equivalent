# Skill Naming Conventions

Consistent naming makes skills discoverable and avoids conflicts.

---

## Skill Name

**Pattern:** `<namespace>.<category>.<action>`

Each segment is lowercase alphanumeric, starting with a letter.
2 to 4 segments are allowed.

| Segment | Purpose | Examples |
|---------|---------|----------|
| Namespace | Owning system | `fte` (FTE system), `sp` (SpecKit Plus) |
| Category | Functional area | `vault`, `git`, `briefing`, `security` |
| Action | What it does | `init`, `status`, `validate`, `generate` |
| Sub-action | (optional) variant | `commit_pr`, `find_commit` |

**Examples:**
- `fte.vault.init` — FTE system, vault area, initialise action
- `sp.git.commit_pr` — SpecKit Plus, git area, commit-and-PR action
- `fte.briefing.generate` — FTE system, briefing area, generate action

### Anti-patterns

| Wrong | Why | Fix |
|-------|-----|-----|
| `do_task` | Too generic | Pick a specific action |
| `FTE.Vault.Init` | Mixed case | All lowercase |
| `fte-vault-init` | Hyphens | Use dots for name; hyphens are for the directory slug only |
| `init` | No namespace | Always qualify with at least 2 segments |

---

## Directory Slug

Derive from the skill name by replacing every dot with a hyphen.

| Skill Name | Slug |
|------------|------|
| `fte.vault.init` | `fte-vault-init` |
| `sp.git.commit_pr` | `sp-git-commit-pr` |
| `fte.briefing.generate` | `fte-briefing-generate` |

The slug is the directory name under `.claude/skills/`.

---

## Categories

| Category | Description | When to use |
|----------|-------------|-------------|
| `task` | Executes a concrete action | Committing code, generating a report |
| `query` | Retrieves information | Searching the vault, listing watchers |
| `config` | Manages configuration | Setting thresholds, updating env |
| `diagnostic` | Diagnoses issues | Health checks, error analysis |
| `workflow` | Multi-step orchestrated flow | Plan → tasks → implement |
| `git` | Version-control operations | Commit, PR, branch management |

---

## Slash Commands

The `command` field is `/` followed by the skill name:

```
/fte.vault.init
/sp.git.commit_pr
```

`aliases` are optional short-hands:

```yaml
command: /sp.git.commit_pr
aliases: [/commit, /git-commit]
```

Aliases must not collide across skills.  The validator warns on
duplicates detected across the installed skill set.

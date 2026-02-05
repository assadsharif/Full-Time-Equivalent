# Skill Registry

How skills are discovered, stored, and managed at runtime.

---

## Discovery

Skills are discovered by scanning `.claude/skills/`.  Every
sub-directory that contains a `SKILL.md` file is treated as an
installed skill.  No manifest file or index is needed — the directory
IS the registry.

```
.claude/skills/
├── fte-vault-init/
│   └── SKILL.md        ← discovered automatically
├── skill-validator/
│   └── SKILL.md
└── ...
```

Claude Code and `fte skill list` both walk this tree at invocation
time.  There is no caching layer — changes take effect immediately
after a file is written.

---

## Installing a Skill

1. Create the skill directory and write `SKILL.md`:
   ```bash
   python scripts/init_skill.py fte.vault.status --category vault
   # → .claude/skills/fte-vault-status/SKILL.md
   ```

2. Fill the template sections and validate:
   ```bash
   python scripts/validate_skill.py .claude/skills/fte-vault-status --level quality
   ```

3. Commit:
   ```bash
   git add .claude/skills/fte-vault-status/
   git commit -m "feat(skills): add fte.vault.status query skill"
   ```

The skill is now live.

---

## Removing a Skill

Delete the directory:

```bash
rm -rf .claude/skills/fte-vault-status
git add -u
git commit -m "chore(skills): remove deprecated fte.vault.status"
```

---

## CLI Commands

| Command | What it does |
|---------|--------------|
| `fte skill list` | Print all installed skills grouped by category |
| `fte skill show <name>` | Print full metadata for one skill |
| `fte skill search --tag <t>` | Filter by tag |
| `fte skill search --category <c>` | Filter by category |
| `fte skill validate <name>` | Run `validate_skill.py` against a skill |
| `fte skill validate <name> --level quality` | Full quality check |

`<name>` accepts either dot notation (`fte.vault.init`) or the
directory slug (`fte-vault-init`).

---

## Relationship to Claude Code Skill Invocation

When a user types `/fte.vault.init`, Claude Code looks for a matching
`command` field in the installed skills.  The `triggers` list is used
for natural-language routing (e.g. "init the vault" → routes to
`fte.vault.init`).

`aliases` provide short-hands (e.g. `/vault-init` → `fte.vault.init`).

---

## Versioning

Skills use semver in frontmatter (`version: 1.0.0`).  Git history
is the authoritative version trail — no separate changelog is
required.  Bump `version` and `last_updated` in frontmatter on every
meaningful change.

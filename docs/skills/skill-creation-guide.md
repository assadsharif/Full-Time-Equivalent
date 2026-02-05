# Skill Creation Guide

End-to-end walkthrough: from idea to a validated, committed skill.

---

## Step 1: Pick a Task Worth Automating

A good candidate skill is:
- **Repeatable** — you do it more than once.
- **Documented** — the steps can be written down unambiguously.
- **Reasoning-heavy** — it requires judgment, not just shell commands.

Good first skills: initialise a project, generate a report, triage
incoming tasks, check system health.

Avoid for a first skill: OAuth flows, multi-service orchestration,
anything with dozens of edge cases.

---

## Step 2: Write Down the Manual Steps

Before touching any code, write out exactly how you would do this
task today — step by step, as if handing it to a new team member.

```
Task: Check vault health

1. Open vault directory
2. List all folders — are the 8 required ones present?
3. Open Dashboard.md — does it have a date?
4. Check Approvals/ — are there pending items older than 24 h?
5. Report findings to user
```

This becomes the **Instructions** section of your skill.

---

## Step 3: Scaffold the Skill

```bash
python scripts/init_skill.py fte.health.check --category diagnostic
```

This creates `.claude/skills/fte-health-check/SKILL.md` with:
- Frontmatter pre-filled (name, category, today's date).
- All required sections as headings with placeholder text.

Use `--dry-run` to preview without writing:

```bash
python scripts/init_skill.py fte.health.check --category diagnostic --dry-run
```

---

## Step 4: Fill the Sections

Open `.claude/skills/fte-health-check/SKILL.md` and fill each section:

| Section | What to write |
|---------|---------------|
| **Frontmatter** | Add triggers (≥2), tags, safety_level, any parameters |
| **Overview** | 2-3 sentences: what, when to use, when NOT to |
| **Instructions** | Your manual steps from Step 2, refined into imperative form |
| **Examples** | ≥2: one happy path, one error/edge case |
| **Validation Criteria** | ≥3 checkboxes: how someone would know it worked |

Reference `.specify/templates/skill-template.md` for the exact
structure, and `docs/skills/skill-anatomy.md` for field-level
constraints.

---

## Step 5: Validate

```bash
python scripts/validate_skill.py .claude/skills/fte-health-check
```

Fix any errors reported before moving on.  For a thorough check:

```bash
python scripts/validate_skill.py .claude/skills/fte-health-check --level quality
```

---

## Step 6: Commit and Ship

```bash
git add .claude/skills/fte-health-check/
git commit -m "feat(skills): add fte.health.check diagnostic skill"
```

The skill is now discoverable via `fte skill list` and invocable
by Claude Code.

---

## Naming Quick-Reference

| Component | Rule | Example |
|-----------|------|---------|
| Skill name | `namespace.category.action` | `fte.vault.init` |
| Directory slug | Replace dots with hyphens | `fte-vault-init` |
| File | Always `SKILL.md` | `SKILL.md` |
| Command | `/` + name | `/fte.vault.init` |

See `docs/skills/naming-conventions.md` for the full taxonomy.

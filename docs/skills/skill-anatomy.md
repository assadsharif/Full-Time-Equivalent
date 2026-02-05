# Skill Anatomy

Every skill in the FTE system is a single **Markdown file** (`SKILL.md`)
inside its own directory under `.claude/skills/<slug>/`.  This document
defines exactly what that file must contain and why.

---

## File Location

```
.claude/skills/
└── <slug>/
    └── SKILL.md          ← required; everything else is optional
        references/       ← optional: linked reference docs
        scripts/          ← optional: helper scripts the skill invokes
        assets/           ← optional: templates, configs, static data
```

The `<slug>` is the directory name.  Derive it from the skill `name`
by replacing dots with hyphens: `fte.vault.init` → `fte-vault-init`.

---

## YAML Frontmatter

The frontmatter sits between the opening and closing `---` fences at
the top of `SKILL.md`.  The authoritative field list and constraints
live in `.specify/templates/skill-schema.yaml`.  Quick reference:

| Field | Required | Purpose |
|-------|----------|---------|
| `name` | yes | Dot-separated identifier (`namespace.category.action`) |
| `version` | yes | Semver (`1.0.0`) |
| `description` | yes | 1-2 sentence summary |
| `triggers` | yes | ≥2 natural-language phrases that route here |
| `command` | yes | The slash-command (`/fte.vault.init`) |
| `aliases` | no | Short alternate commands |
| `category` | yes | One of: task, query, config, diagnostic, workflow, git |
| `tags` | yes | ≥1 searchable keyword |
| `requires` | no | tools / skills / env dependencies |
| `parameters` | no | Typed, documented inputs |
| `safety_level` | yes | `low` / `medium` / `high` |
| `approval_required` | yes | Boolean |
| `destructive` | yes | Boolean |
| `constitutional_compliance` | no | Constitution section numbers |
| `author` | yes | Name or team |
| `created` | yes | YYYY-MM-DD |
| `last_updated` | yes | YYYY-MM-DD |

### Safety Level Semantics

| Level | Side Effects | Approval Gate |
|-------|-------------|---------------|
| `low` | None (read-only) | Never |
| `medium` | Local writes, non-destructive | Never |
| `high` | Destructive or externally visible | Always |

---

## Body Sections

### 1. Overview (required)

**What to include:**
- What the skill does in plain language.
- When a user should invoke it.
- When they should NOT (and what alternative exists).

**Constraints:** ≤ 10 sentences.

### 2. Instructions (required)

**What to include:**
- A numbered step list in imperative mood ("Run …", "Check …", "If …").
- A **Prerequisites** sub-section listing anything that must be true before Step 1.
- An **Error Handling** sub-section mapping each foreseeable failure to a concrete recovery action.

**Constraints:**
- ≥ 3 steps.
- Every step must be actionable without external context.
- No "think about" or "consider" — only concrete actions.

### 3. Examples (required)

**What to include:**
- ≥ 2 examples.  One happy-path, one edge-case or error scenario.
- Each example has: User Input → Execution (commands) → Output.

**Constraints:**
- Commands must be copy-pasteable (no pseudo-code in bash blocks).
- Output must show exactly what the user would see.

### 4. Validation Criteria (required)

**What to include:**
- **Success Criteria** — checkbox list of observable outcomes.
- **Safety Checks** — checkbox list verifying no policy violations.

**Constraints:**
- ≥ 3 success criteria.
- High-safety skills must include approval-gate and audit-log checks.

---

## Size Constraints

| Metric | Limit | Reason |
|--------|-------|--------|
| SKILL.md line count | ≤ 500 | Context window is shared; keep it tight |
| Skill file size | ≤ 100 KB | Loading latency |
| Example count | ≥ 2, ≤ 5 | Few-shot sweet spot |
| Step count | ≥ 3 | Anything fewer is a one-liner, not a skill |

Put long reference material in `references/` and link to it — don't
inline it in SKILL.md.

---

## Relationship to Existing Skills

The 36 skills already installed under `.claude/skills/` use a minimal
frontmatter (`name` + `description` only).  New FTE-domain skills
MUST use the full schema.  Existing third-party skills are not
retroactively required to conform, but `validate_skill.py` will warn
on missing fields.

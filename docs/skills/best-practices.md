# Skill Best Practices

Rules that separate good skills from ones that break or confuse.

---

## DO

### Write instructions in imperative mood

Every step tells Claude what to **do**, not what to think about.

```markdown
### Step 1: Check for uncommitted changes
Run `git status` and parse the output.  If the working tree is clean,
inform the user and exit.
```

Not: *"You should consider checking whether there are changes."*

### Provide ≥ 2 examples

One happy-path example and one error or edge-case example.  Each must
show the full loop: user input → commands run → output displayed.

### Include an Error Handling sub-section

Map every foreseeable failure to a concrete action.  "Show error"
is not a plan.

```markdown
### Error Handling
- **No changes:** Print "Nothing to commit" and exit 0.
- **Push rejected:** Show the git error verbatim; suggest `git pull --rebase`.
- **Missing tool:** Print which tool is missing and the install command.
```

### Declare safety_level honestly

If the skill writes files, set `medium`.  If it deletes, sends emails,
or touches production, set `high` and `approval_required: true`.

### Keep SKILL.md under 500 lines

Put long reference material in a `references/` sub-directory and link
to it.  Context is a shared resource.

---

## DON'T

### Don't make skills too generic

A skill named `do_task` that "does any task" will never be invoked
reliably.  Skills should be **focused and specific**.

### Don't hardcode values

Wrong:
```markdown
Commit with message "Updated code"
```

Right:
```markdown
Analyze the diff, draft a commit message following the conventions
shown in the last 10 commits (`git log --oneline -10`).
```

### Don't skip safety checks

If a skill is `safety_level: high`, the Instructions MUST include a
step that verifies approval before executing.  The validator will flag
this, but the developer must wire it correctly.

### Don't duplicate an existing skill

Before creating a new skill, run:

```bash
fte skill search --tag <relevant-tag>
```

If a skill already covers the same ground, extend or compose it
rather than duplicating.

### Don't leave placeholder text

Every `<placeholder>` and `TODO` in the template must be replaced
before committing.  `validate_skill.py` checks for common leftover
markers.

---

## Composition Pattern

Skills can invoke other skills.  Declare dependencies in frontmatter:

```yaml
requires:
  skills: [fte.vault.validate, fte.health.check]
```

Then in Instructions:

```markdown
### Step 2: Validate vault
Invoke `/fte.vault.validate` and wait for its output.
If it reports errors, surface them to the user before continuing.
```

This keeps each skill small and testable while enabling powerful
multi-step workflows.

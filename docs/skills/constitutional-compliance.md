# Constitutional Compliance — Skills

Every skill in the FTE system must declare which sections of the project
constitution it touches and honour the constraints those sections impose.
This document maps each relevant constitution section to the concrete
requirements it places on skill authors.

---

## Section → Skill Requirements

### Section 2 — Source of Truth

**Principle:** Files are facts; never invent data from memory.

**Skill requirement:** Any skill that reads vault state (task counts,
checkpoint data, watcher status) must fetch that data at runtime — never
cache or hard-code values.  Declare `section: 2` in
`constitutional_compliance`.

**Applies to:** fte.vault.status, fte.vault.validate, fte.watcher.status,
fte.orchestrator.status, fte.briefing.generate, fte.health.check,
fte.security.scan.

---

### Section 4 — Frozen Control Plane

**Principle:** Source code under `src/` is not modified at runtime.

**Skill requirement:** Skills must never write to `src/` or modify CLI
modules during execution.  If a skill needs a new behaviour, it should be
proposed as a code change (PR), not patched inline.

**Applies to:** All skills (implicit constraint).

---

### Section 5 — Human-in-the-Loop (HITL)

**Principle:** Destructive or high-risk actions require explicit human
approval before execution.

**Skill requirement:**
- Any skill with `safety_level: high` **must** set `approval_required: true`.
- The skill instructions **must** include a step that presents the proposed
  action to the user and waits for an explicit approve / reject response
  before proceeding.
- If the user rejects, the skill **must** log the rejection and stop.

**Applies to:** fte.approval.review, fte.task.triage (when moving files —
medium safety, no approval gate, but the dry-run flag honours the spirit).

---

### Section 8 — Auditability

**Principle:** Every action taken by the system must be traceable.

**Skill requirement:**
- Skills that modify state (move files, update frontmatter, send messages)
  **must** append an entry to `state_history` or an equivalent audit log.
- Skills that read-only are exempt from write-side auditing but should still
  be invocable via the skill registry (discoverable = auditable path).

**Applies to:** fte.task.triage (appends `state_history`),
fte.approval.review (approval decisions logged via CLI audit trail),
fte.briefing.generate (output file is the audit artifact).

---

### Section 9 — Error Recovery

**Principle:** Failures must degrade gracefully; never leave the system in
an inconsistent state.

**Skill requirement:**
- Every skill **must** include an `### Error Handling` section in its
  Instructions body.
- Error handling must cover at minimum: (a) the "nothing to do" case,
  (b) malformed input, (c) missing files or services.
- Skills must not leave partial writes: if a file move fails mid-way, the
  original file must remain at its source.

**Applies to:** All skills (enforced by `validate_skill.py --level quality`).

---

## Compliance Declaration Cheat-Sheet

| Skill | Sec 2 | Sec 4 | Sec 5 | Sec 8 | Sec 9 |
|-------|:-----:|:-----:|:-----:|:-----:|:-----:|
| fte.vault.init | ✓ | — | — | ✓ | ✓ |
| fte.vault.status | ✓ | — | — | — | ✓ |
| fte.vault.validate | ✓ | — | — | — | ✓ |
| fte.approval.review | — | — | ✓ | ✓ | ✓ |
| fte.briefing.generate | ✓ | — | — | ✓ | ✓ |
| fte.watcher.status | ✓ | — | — | — | ✓ |
| fte.task.triage | ✓ | — | ✓ | ✓ | ✓ |
| fte.orchestrator.status | ✓ | — | — | — | ✓ |
| fte.security.scan | ✓ | ✓ | — | ✓ | ✓ |
| fte.health.check | ✓ | — | — | ✓ | ✓ |

---

## Enforcement

- **At author time:** The skill template includes a
  `constitutional_compliance` YAML list.  Authors must populate it
  honestly.
- **At validation time:** `validate_skill.py` checks that FTE-namespaced
  skills (`fte.*`) declare at least sections 2 and 8.  Skills with
  `safety_level: high` that do not declare section 5 produce an error.
- **At review time:** PRs that add or modify skills are expected to have
  the compliance list reviewed against this document.

---

*Last updated: 2026-02-05 — generated during 009-agent-skills-guide Phase 6.*

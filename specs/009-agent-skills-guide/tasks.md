---
description: "Task list for Agent Skills Guide implementation"
---

# Tasks: Agent Skills Guide

**Input**: Design documents from `/specs/009-agent-skills-guide/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Not explicitly requested — focus on implementation and validation scripts.

**Organization**: Tasks grouped by user story mapped from plan.md phases.
Phase 1 → US1 (Skill Framework), Phase 2 → US2 (Skill Tooling), Phase 3 → US3 (Core Skills).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to
- Include exact file paths in descriptions

## Path Conventions

```
.specify/templates/         ← skill-template.md lives here
scripts/                    ← Python tooling scripts
.claude/skills/             ← installed skill directories (36 already exist)
docs/skills/                ← user-facing skill documentation
src/cli/skill.py            ← CLI group for `fte skill` commands
```

---

## Phase 1: Setup

**Purpose**: Establish directories and baseline schema before any skills or tooling.

- [ ] T001 Create `docs/skills/` directory for skill documentation
- [ ] T002 Create `scripts/` entry point — confirm existing `scripts/` is reusable (no new dir needed)

**Checkpoint**: Directories ready; existing `.claude/skills/` layout understood as the installed-skill convention.

---

## Phase 2: Foundational (Skill Schema & Template)

**Purpose**: Define the authoritative skill structure that all tooling and core skills conform to.  Blocks US2 and US3.

- [ ] T003 Define skill YAML frontmatter schema in `.specify/templates/skill-schema.yaml` (name, version, description, triggers, command, category, tags, requires, parameters, safety_level, approval_required, destructive, constitutional_compliance, author, created, last_updated)
- [ ] T004 [P] Create skill template in `.specify/templates/skill-template.md` — full skeleton with all required sections (Overview, Instructions, Examples ×2, Validation Criteria, Error Handling) and YAML frontmatter populated from schema
- [ ] T005 [P] Document the skill anatomy and section contracts in `docs/skills/skill-anatomy.md` — what each frontmatter field means, what each body section must contain, min/max constraints

**Checkpoint**: Schema + template + anatomy doc in place.  `validate_skill.py` (US2) can now be built against them.

---

## Phase 3: User Story 1 — Skill Creation Workflow (Bronze Tier) 🎯 MVP

**Goal**: A developer can scaffold, fill, and commit a new skill end-to-end using `scripts/init_skill.py` and the template.

**Independent Test**: Run `python scripts/init_skill.py fte.vault.status --category vault` → verify scaffold appears in `.claude/skills/vault-status/SKILL.md` with all required sections and valid frontmatter.

### Scaffolding Script

- [ ] T006 [US1] Implement `scripts/init_skill.py` — CLI script that accepts `<name> --category <cat>` and renders `skill-template.md` into `.claude/skills/<slug>/SKILL.md` with placeholders filled (name, category, date, empty triggers/tags/parameters)
- [ ] T007 [US1] Add `--dry-run` flag to `init_skill.py` — print rendered template to stdout without writing files

### Creation Guide

- [ ] T008 [P] [US1] Write `docs/skills/skill-creation-guide.md` — step-by-step walkthrough: choose a task → document steps → scaffold → fill sections → validate → commit
- [ ] T009 [P] [US1] Write `docs/skills/best-practices.md` — DO/DON'T rules extracted from spec (clear instructions, provide ≥2 examples, include error handling, no hardcoded values, declare safety level, no overly generic skills)

### Naming & Categories

- [ ] T010 [US1] Document naming conventions and category taxonomy in `docs/skills/naming-conventions.md` — namespace.category.action pattern, approved categories (task, query, config, diagnostic, workflow), slug derivation rules for directory names

**Checkpoint**: `init_skill.py` + docs in place.  A developer can create a conforming skill without reading the spec.

---

## Phase 4: User Story 2 — Skill Validation & Registry (Silver Tier)

**Goal**: `validate_skill.py` checks any skill against the schema; `fte skill` CLI commands let users list, show, search, and validate skills.

**Independent Test**: Run `python scripts/validate_skill.py .claude/skills/skill-validator` → exits 0 with structured report.  Run `fte skill list` → prints all 36+ installed skills grouped by category.

### Validation Script

- [ ] T011 [US2] Implement `scripts/validate_skill.py` — accepts a skill directory path; checks: (1) SKILL.md exists, (2) YAML frontmatter parses and has all required fields, (3) required body sections present (Overview, Instructions, Examples, Validation Criteria), (4) ≥2 examples, (5) safety_level is one of low/medium/high.  Outputs structured report (errors / warnings / info) and exits 1 on any error.
- [ ] T012 [US2] Add `--level` flag (`syntax` | `complete` | `quality`) to `validate_skill.py` — syntax checks frontmatter only; complete adds section presence; quality adds example count, error-handling section, step count ≥ 3

### Registry & CLI

- [ ] T013 [US2] Implement `src/cli/skill.py` — Click group `skill` with sub-commands: `list`, `show`, `search`, `validate`
- [ ] T014 [US2] `fte skill list` — scan `.claude/skills/`, parse each SKILL.md frontmatter, group by category, print table (name, description, safety_level)
- [ ] T015 [P] [US2] `fte skill show <name>` — print full metadata for a single skill (all frontmatter fields + section headers found)
- [ ] T016 [P] [US2] `fte skill search --tag <tag> | --category <cat>` — filter skill list by tag or category
- [ ] T017 [US2] `fte skill validate <name>` — invoke `validate_skill.py` against the named skill and print its report
- [ ] T018 [US2] Register `skill` group in `src/cli/main.py` via `cli.add_command(skill_group)`

### Registry Docs

- [ ] T019 [US2] Write `docs/skills/skill-registry.md` — how discovery works (`.claude/skills/` scan), how to install/uninstall a skill manually, how CLI commands map to registry queries

**Checkpoint**: Every existing skill is discoverable and validatable via CLI.

---

## Phase 5: User Story 3 — Core Skills Library (Gold Tier)

**Goal**: Ship 10 FTE-domain skills that cover the main system workflows.  Each skill conforms to the schema, passes `validate_skill.py --level quality`, and is documented in the registry.

**Independent Test**: Run `fte skill list` → ≥10 FTE skills present.  Run `fte skill validate <each>` → all pass quality level.

### FTE Domain Skills

- [ ] T020 [P] [US3] Create `.claude/skills/fte-vault-init/SKILL.md` — vault initialisation skill (wraps `fte vault init` logic, includes pre-checks and post-verification steps)
- [ ] T021 [P] [US3] Create `.claude/skills/fte-vault-status/SKILL.md` — vault status query skill (wraps `fte vault status`, formats output)
- [ ] T022 [P] [US3] Create `.claude/skills/fte-vault-validate/SKILL.md` — vault validation skill (wraps `fte vault validate`, interprets results)
- [ ] T023 [P] [US3] Create `.claude/skills/fte-approval-review/SKILL.md` — approval review workflow (find pending approvals, present to user, approve/reject with reason)
- [ ] T024 [P] [US3] Create `.claude/skills/fte-briefing-generate/SKILL.md` — briefing generation skill (parameterised: period, format; aggregates Done tasks, renders briefing)
- [ ] T025 [P] [US3] Create `.claude/skills/fte-watcher-status/SKILL.md` — watcher health-check skill (lists active watchers, last-seen timestamps, error counts)
- [ ] T026 [P] [US3] Create `.claude/skills/fte-task-triage/SKILL.md` — task triage skill (read Inbox tasks, classify by priority/source, move to Needs_Action with updated frontmatter)
- [ ] T027 [P] [US3] Create `.claude/skills/fte-orchestrator-status/SKILL.md` — orchestrator status skill (reads checkpoint, last-run metrics, current queue depth)
- [ ] T028 [P] [US3] Create `.claude/skills/fte-security-scan/SKILL.md` — security scan skill (runs secrets scanner on vault, reports findings)
- [ ] T029 [P] [US3] Create `.claude/skills/fte-health-check/SKILL.md` — full system health check (runs vault validate + watcher status + orchestrator status, aggregates into single report)

### Core Skill Docs

- [ ] T030 [US3] Write `docs/skills/core-skills-index.md` — table of all 10 core FTE skills with: name, category, what it does, when to invoke, example invocation

**Checkpoint**: 10 core skills shipped, all passing quality validation, all documented.

---

## Phase 6: Polish & Cross-Cutting

**Purpose**: Final validation pass, packaging script, and constitutional compliance sign-off.

- [ ] T031 [P] Implement `scripts/package_skill.py` — takes a skill directory, validates it, bundles SKILL.md + any `references/` or `scripts/` sub-dirs into a single `.skill.tar.gz`, prints manifest
- [ ] T032 [P] Run `validate_skill.py --level quality` against all 10 core FTE skills — fix any failures
- [ ] T033 [P] Write `docs/skills/constitutional-compliance.md` — maps each constitution section to skill requirements (safety_level declarations, approval gating, audit logging)
- [ ] T034 Verify `fte skill list` returns all FTE skills correctly grouped; `fte skill search --category vault` returns vault skills
- [ ] T035 Update memory (`MEMORY.md` or equivalent) with skill-framework patterns for future sessions

**Checkpoint**: All skills valid, packaged, documented, constitution-compliant.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies
- **Phase 2 (Foundational)**: Depends on Phase 1
- **Phase 3 (US1)**: Depends on Phase 2 (needs schema + template)
- **Phase 4 (US2)**: Depends on Phase 2 (validator reads schema); benefits from Phase 3 (init_skill exists)
- **Phase 5 (US3)**: Depends on Phase 2 (skills must conform) and Phase 4 (validate each skill)
- **Phase 6 (Polish)**: Depends on Phase 5

### Within Each User Story

**US1 (Creation Workflow)**:
1. T006 init_skill.py (needs template from Phase 2)
2. T007 --dry-run flag (depends on T006)
3. T008, T009, T010 docs (parallel, depend only on Phase 2)

**US2 (Validation & Registry)**:
1. T011 validate_skill.py (needs schema from Phase 2)
2. T012 --level flag (depends on T011)
3. T013 skill CLI group
4. T014-T017 sub-commands (T015, T016 parallel after T013)
5. T018 register in main.py (depends on T013)
6. T019 docs

**US3 (Core Skills)**:
1. T020-T029 all parallel (each is an independent skill file)
2. T030 index doc (after all skills written)

---

## Parallel Execution Opportunities

- **Phase 2**: T004 + T005 parallel (template and anatomy doc are independent)
- **US1 Docs**: T008 + T009 + T010 all parallel
- **US2 CLI**: T015 + T016 parallel after T013 creates the group
- **US3 Skills**: T020-T029 fully parallel (10 independent files)
- **Phase 6**: T031 + T032 + T033 parallel

---

## Implementation Strategy

### Bronze Tier MVP (Phases 1-3, T001-T010)
- Skill schema, template, and scaffolding script
- Creation guide and best practices
- Deliverable: `python scripts/init_skill.py` works end-to-end

### Silver Tier (Phase 4, T011-T019)
- Validator and CLI registry
- Deliverable: `fte skill list/show/search/validate` all functional

### Gold Tier (Phase 5, T020-T030)
- 10 core FTE skills + index doc
- Deliverable: full skill library discoverable and validated

### Polish (Phase 6, T031-T035)
- Packaging, final validation pass, constitution sign-off

---

## Summary

**Total Tasks**: 35
- Phase 1 (Setup): 2 tasks
- Phase 2 (Foundational): 3 tasks
- Phase 3 (US1 — Creation Workflow): 5 tasks
- Phase 4 (US2 — Validation & Registry): 9 tasks
- Phase 5 (US3 — Core Skills): 11 tasks
- Phase 6 (Polish): 5 tasks

**Parallel Opportunities**: 22+ tasks can run in parallel

**MVP Scope** (Bronze Tier): Phases 1-3 (10 tasks) — schema + template + init script + docs

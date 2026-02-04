---
description: "Task list for Obsidian Vault Structure implementation"
---

# Tasks: Obsidian Vault Structure

**Input**: Design documents from `/specs/008-obsidian-vault-structure/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**Tests**: Not explicitly requested in specification - focus on implementation and validation scripts

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

This feature creates vault structure and CLI commands:
- Vault templates: `.vault_templates/`
- CLI commands: `src/cli/vault.py`
- Validation scripts: `.vault_schema/validation_scripts/`
- Schema definitions: `.vault_schema/frontmatter_schemas/`

---

## Phase 1: Setup (Infrastructure)

**Purpose**: Project structure for vault initialization and validation

- [ ] T001 Create `.vault_templates/` directory for vault structure templates
- [ ] T002 Create `.vault_schema/` directory for YAML schemas and validation scripts
- [ ] T003 [P] Create `.vault_schema/frontmatter_schemas/` directory for YAML frontmatter definitions

**Checkpoint**: Template directories ready for content

---

## Phase 2: Foundational (Core Schemas & Validation)

**Purpose**: Define schemas and validation framework that all user stories depend on

**⚠️ CRITICAL**: These schemas define the structure for all vault files

- [ ] T004 Create task YAML frontmatter schema in `.vault_schema/frontmatter_schemas/task.yaml`
- [ ] T005 [P] Create approval YAML frontmatter schema in `.vault_schema/frontmatter_schemas/approval.yaml`
- [ ] T006 [P] Create briefing YAML frontmatter schema in `.vault_schema/frontmatter_schemas/briefing.yaml`
- [ ] T007 Create vault validation script in `.vault_schema/validation_scripts/validate_vault.py`

**Checkpoint**: Schemas defined - vault template creation can begin

---

## Phase 3: User Story 1 - Initialize Vault Structure (Priority: Bronze Tier) 🎯 MVP

**Goal**: Create standardized Obsidian vault with all required folders and core files

**Independent Test**: Run `fte vault init --path /tmp/test_vault` and verify all folders/files created

### Folder Structure

- [ ] T008 [P] [US1] Create Inbox folder template in `.vault_templates/folders/Inbox/.gitkeep`
- [ ] T009 [P] [US1] Create Needs_Action folder template in `.vault_templates/folders/Needs_Action/.gitkeep`
- [ ] T010 [P] [US1] Create In_Progress folder template in `.vault_templates/folders/In_Progress/.gitkeep`
- [ ] T011 [P] [US1] Create Done folder template in `.vault_templates/folders/Done/.gitkeep`
- [ ] T012 [P] [US1] Create Approvals folder template in `.vault_templates/folders/Approvals/.gitkeep`
- [ ] T013 [P] [US1] Create Briefings folder template in `.vault_templates/folders/Briefings/.gitkeep`
- [ ] T014 [P] [US1] Create Attachments folder template in `.vault_templates/folders/Attachments/.gitkeep`
- [ ] T015 [P] [US1] Create Templates folder template in `.vault_templates/folders/Templates/.gitkeep`

### Core Templates

- [ ] T016 [P] [US1] Create task template in `.vault_templates/Templates/task_template.md`
- [ ] T017 [P] [US1] Create approval template in `.vault_templates/Templates/approval_template.md`

### Obsidian Configuration

- [ ] T018 [US1] Create Obsidian app settings in `.vault_templates/.obsidian/app.json`
- [ ] T019 [P] [US1] Create Obsidian appearance settings in `.vault_templates/.obsidian/appearance.json`
- [ ] T020 [P] [US1] Create Obsidian core plugins config in `.vault_templates/.obsidian/core-plugins.json`

### Git Configuration

- [ ] T021 [US1] Create .gitignore template in `.vault_templates/.gitignore`

### CLI Implementation

- [ ] T022 [US1] Implement `vault init` command in `src/cli/vault.py`
- [ ] T023 [US1] Add vault initialization logic (copy templates, create folders) in `src/cli/vault.py`
- [ ] T024 [US1] Add `vault status` command for health checks in `src/cli/vault.py`
- [ ] T025 [US1] Integrate vault commands with main CLI in `src/cli/main.py`

**Checkpoint**: Vault initialization complete - can create vaults with `fte vault init`

---

## Phase 4: User Story 2 - Dashboard Monitoring (Priority: Bronze Tier)

**Goal**: Create Dashboard.md template that provides system status visibility

**Independent Test**: Open Dashboard.md in Obsidian and verify all sections render correctly

- [ ] T026 [P] [US2] Create Dashboard.md template header in `.vault_templates/Dashboard.md`
- [ ] T027 [P] [US2] Add Task Summary section to Dashboard.md template
- [ ] T028 [P] [US2] Add System Health section to Dashboard.md template
- [ ] T029 [P] [US2] Add Recent Activity section to Dashboard.md template
- [ ] T030 [P] [US2] Add Pending Approvals section to Dashboard.md template
- [ ] T031 [P] [US2] Add Quick Actions section to Dashboard.md template
- [ ] T032 [US2] Add dashboard update logic to vault init command in `src/cli/vault.py`

**Checkpoint**: Dashboard template ready with monitoring sections

---

## Phase 5: User Story 3 - Company Handbook (Priority: Bronze Tier)

**Goal**: Create Company_Handbook.md template with AI context and policies

**Independent Test**: Open Company_Handbook.md in Obsidian and verify all policy sections are present

- [ ] T033 [P] [US3] Create Company_Handbook.md template header in `.vault_templates/Company_Handbook.md`
- [ ] T034 [P] [US3] Add Mission & Vision section to Company_Handbook.md
- [ ] T035 [P] [US3] Add Communication Guidelines section to Company_Handbook.md
- [ ] T036 [P] [US3] Add Task Prioritization Rules section to Company_Handbook.md
- [ ] T037 [P] [US3] Add Approval Requirements section to Company_Handbook.md
- [ ] T038 [P] [US3] Add Security & Privacy Policies section to Company_Handbook.md
- [ ] T039 [P] [US3] Add Working Hours & Availability section to Company_Handbook.md
- [ ] T040 [US3] Add handbook generation to vault init command in `src/cli/vault.py`

**Checkpoint**: Company Handbook template complete with all policy sections

---

## Phase 6: User Story 4 - Task State Flow (Priority: Silver Tier)

**Goal**: Define and validate task state transitions between folders

**Independent Test**: Move a task through state flow and verify frontmatter updates correctly

- [ ] T041 [US4] Document state transition rules in `.vault_schema/state_transitions.md`
- [ ] T042 [P] [US4] Create state validation function in `.vault_schema/validation_scripts/validate_state.py`
- [ ] T043 [P] [US4] Add state history tracking to task YAML schema in `.vault_schema/frontmatter_schemas/task.yaml`
- [ ] T044 [US4] Implement `vault validate` command in `src/cli/vault.py`
- [ ] T045 [US4] Add state flow diagram to vault documentation in `.vault_templates/README.md`

**Checkpoint**: State flow rules defined and validation available

---

## Phase 7: User Story 5 - File Naming Conventions (Priority: Silver Tier)

**Goal**: Define and enforce standardized file naming patterns

**Independent Test**: Create files with naming convention and verify validation passes

- [ ] T046 [P] [US5] Document file naming conventions in `.vault_schema/naming_conventions.md`
- [ ] T047 [P] [US5] Create filename validation regex patterns in `.vault_schema/validation_scripts/validate_filename.py`
- [ ] T048 [P] [US5] Add filename sanitization function in `.vault_schema/validation_scripts/validate_filename.py`
- [ ] T049 [US5] Add filename validation to `vault validate` command in `src/cli/vault.py`
- [ ] T050 [US5] Create filename examples in Templates folder in `.vault_templates/Templates/naming_examples.md`

**Checkpoint**: File naming conventions documented and validated

---

## Phase 8: Polish & Documentation

**Purpose**: Final documentation, validation, and operational guides

- [ ] T051 [P] Create vault structure documentation in `docs/VAULT_STRUCTURE.md`
- [ ] T052 [P] Create vault CLI guide in `docs/VAULT_CLI.md`
- [ ] T053 [P] Add vault structure diagram to documentation
- [ ] T054 [P] Create validation examples in `docs/VAULT_VALIDATION.md`
- [ ] T055 [P] Add troubleshooting guide for common vault issues in `docs/VAULT_TROUBLESHOOTING.md`
- [ ] T056 Run full vault validation on example vault
- [ ] T057 Create vault migration guide for existing installations in `docs/VAULT_MIGRATION.md`

**Checkpoint**: Documentation complete - vault structure fully specified

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - start here
- **Phase 2 (Foundational)**: Depends on Phase 1 complete
- **Phase 3 (US1)**: Depends on Phase 2 complete ⚠️ BLOCKS all other stories
- **Phase 4 (US2)**: Depends on Phase 3 complete
- **Phase 5 (US3)**: Depends on Phase 3 complete
- **Phase 6 (US4)**: Depends on Phase 3 complete, benefits from Phase 2 schemas
- **Phase 7 (US5)**: Depends on Phase 3 complete
- **Phase 8 (Polish)**: Can run in parallel with user stories, depends on Phase 3

### User Story Dependencies

- **US1 (Initialize Vault)**: No dependencies - foundational story
- **US2 (Dashboard)**: Depends on US1 - needs vault structure
- **US3 (Handbook)**: Depends on US1 - needs vault structure
- **US4 (State Flow)**: Depends on US1 - needs folders to define flow between
- **US5 (Naming Conventions)**: Depends on US1 - needs vault to apply conventions to

### Within Each User Story

**US1 (Initialize Vault)**:
1. Create folder templates (T008-T015) - parallel
2. Create core templates (T016-T017) - parallel
3. Create Obsidian config (T018-T020) - sequential (app.json first)
4. Create Git config (T021)
5. Implement CLI (T022-T025) - sequential

**US2 (Dashboard)**:
1. Create dashboard sections (T026-T031) - parallel
2. Integrate with CLI (T032)

**US3 (Handbook)**:
1. Create handbook sections (T033-T039) - parallel
2. Integrate with CLI (T040)

**US4 (State Flow)**:
1. Document rules (T041)
2. Implement validation (T042-T043) - parallel
3. Add CLI command (T044)
4. Add diagram (T045)

**US5 (Naming Conventions)**:
1. Document conventions (T046)
2. Implement validation (T047-T048) - parallel
3. Integrate with CLI (T049)
4. Create examples (T050)

---

## Parallel Execution Opportunities

### Highly Parallel Phases
- **Phase 1 (Setup)**: All 3 tasks can run in parallel
- **US1 Folder Creation**: T008-T015 (8 tasks) - completely independent
- **US2 Dashboard Sections**: T026-T031 (6 tasks) - all parallel
- **US3 Handbook Sections**: T033-T039 (7 tasks) - all parallel
- **Phase 8 (Polish)**: T051-T055 (5 tasks) - all documentation, fully parallel

### Sequential Bottlenecks
- **Phase 2**: T004 must complete before vault templates use schemas
- **US1 CLI**: T022 → T023 → T024 → T025 (sequential implementation)
- **US4 State Flow**: T041 (document) → T042 (validate) → T044 (CLI)

---

## Implementation Strategy

### MVP Scope (Bronze Tier - US1, US2, US3)
1. **Week 1: Core Vault Structure (US1)**
   - Days 1-2: Folder templates and Obsidian config
   - Days 3-4: CLI implementation
   - Day 5: Testing and validation

2. **Week 2: Monitoring & Context (US2, US3)**
   - Days 1-2: Dashboard.md template
   - Days 3-4: Company_Handbook.md template
   - Day 5: Integration and polish

**Delivery**: Functional vault initialization with monitoring dashboard

### Post-MVP Features (Silver Tier - US4, US5)
3. **Week 3: Advanced Features**
   - Days 1-3: State flow validation (US4)
   - Days 4-5: Naming conventions (US5)

**Delivery**: Complete vault structure with validation

### Incremental Delivery Plan
- **Sprint 1**: US1 (Initialize Vault) - Deliverable: `fte vault init` works
- **Sprint 2**: US2 + US3 (Dashboard + Handbook) - Deliverable: Complete vault template
- **Sprint 3**: US4 + US5 (State Flow + Naming) - Deliverable: Validation framework

---

## Testing Strategy

### Manual Validation Tests
1. **Vault Initialization**:
   ```bash
   fte vault init --path /tmp/test_vault
   ls /tmp/test_vault  # Verify all folders
   open /tmp/test_vault  # Open in Obsidian
   ```

2. **Dashboard Rendering**:
   - Open Dashboard.md in Obsidian
   - Verify all sections render
   - Check tables format correctly

3. **Handbook Content**:
   - Open Company_Handbook.md in Obsidian
   - Verify all policy sections present
   - Check links work

4. **State Validation**:
   ```bash
   fte vault validate --path /tmp/test_vault
   # Should pass validation
   ```

5. **Filename Validation**:
   - Create test files with valid/invalid names
   - Run validation
   - Verify correct pass/fail

### Automated Validation
- `.vault_schema/validation_scripts/validate_vault.py` - Full vault validation
- `.vault_schema/validation_scripts/validate_state.py` - State transition validation
- `.vault_schema/validation_scripts/validate_filename.py` - Filename pattern validation

---

## Summary

**Total Tasks**: 57
- Phase 1 (Setup): 3 tasks
- Phase 2 (Foundational): 4 tasks
- Phase 3 (US1 - Initialize Vault): 18 tasks
- Phase 4 (US2 - Dashboard): 7 tasks
- Phase 5 (US3 - Handbook): 8 tasks
- Phase 6 (US4 - State Flow): 5 tasks
- Phase 7 (US5 - Naming): 5 tasks
- Phase 8 (Polish): 7 tasks

**Parallel Opportunities**: 35+ tasks can run in parallel (folder creation, templates, documentation)

**MVP Scope** (Bronze Tier): Phases 1-5 (40 tasks) - Core vault with dashboard and handbook

**Format Validation**: ✅ All tasks follow checklist format with checkboxes, IDs, [P] markers where applicable, [Story] labels for user story tasks, and file paths

**Next Steps**: Begin with Phase 1 (Setup) to create template directory structure, then move to Phase 2 (Foundational) to define schemas before implementing US1 vault initialization.

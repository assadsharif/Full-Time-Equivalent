# Tasks: File-Driven Control Plane

**Input**: Design documents from `/specs/001-file-control-plane/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are included per feature requirements (pytest-based unit and integration tests)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project structure with:
- `src/control_plane/` - Core library modules
- `src/cli/` - CLI interface
- `src/utils/` - Utility modules
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests
- `tests/fixtures/` - Test fixtures and sample data

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create src/control_plane/ directory structure with __init__.py
- [ ] T002 [P] Create src/cli/ directory with __init__.py
- [ ] T003 [P] Create src/utils/ directory with __init__.py
- [ ] T004 [P] Create tests/unit/ directory structure
- [ ] T005 [P] Create tests/integration/ directory structure
- [ ] T006 [P] Create tests/fixtures/ directory with conftest.py for pytest fixtures
- [ ] T007 Initialize Python project with pyproject.toml (Python 3.11+, dependencies: watchdog, PyYAML, structlog, pytest, pytest-cov)
- [ ] T008 [P] Configure pytest in pyproject.toml with coverage settings
- [ ] T009 [P] Create .gitignore for Python project (__pycache__, *.pyc, venv/, .pytest_cache/, .coverage)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T010 Implement WorkflowState enum in src/control_plane/models.py with 7 states (INBOX, NEEDS_ACTION, PLANS, PENDING_APPROVAL, APPROVED, REJECTED, DONE)
- [ ] T011 [P] Implement custom exception classes in src/control_plane/errors.py (ControlPlaneError, InvalidTransitionError, ApprovalRequiredError, StateInconsistencyError, LogWriteError, FileOperationError)
- [ ] T012 [P] Implement atomic file operation wrappers in src/utils/file_ops.py (atomic_move, safe_read, safe_write with error handling)
- [ ] T013 [P] Implement configuration loader in src/utils/config.py (load YAML config from .specify/config/)
- [ ] T014 Configure structlog in src/control_plane/logger.py (JSON output, timestamp processor, log level processor)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Task Lifecycle Management (Priority: P1) 🎯 MVP

**Goal**: Automatically manage task files through their lifecycle with atomic state transitions and complete audit trail

**Independent Test**: Create a task file in /Inbox, verify it moves through states to /Done with all transitions logged

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T015 [P] [US1] Create test fixture for isolated file system (tmpdir with 8 workflow folders) in tests/fixtures/conftest.py
- [ ] T016 [P] [US1] Unit test for WorkflowState enum in tests/unit/test_models.py (verify all 7 states, folder name mapping)
- [ ] T017 [P] [US1] Unit test for TaskFile entity in tests/unit/test_models.py (from_file, to_file, derive_state_from_location, YAML parsing)
- [ ] T018 [P] [US1] Unit test for StateTransition entity in tests/unit/test_models.py (all fields, validation)
- [ ] T019 [P] [US1] Unit test for state transition matrix validation in tests/unit/test_state_machine.py (valid transitions, forbidden transitions)
- [ ] T020 [P] [US1] Unit test for atomic file move operation in tests/unit/test_state_machine.py (success, disk full, permission error)
- [ ] T021 [P] [US1] Unit test for AuditLogger in tests/unit/test_logger.py (log_transition, JSON format, append-only)
- [ ] T022 [US1] Integration test for complete workflow in tests/integration/test_workflow.py (Inbox → Needs_Action → Plans → Pending_Approval → Approved → Done)

### Implementation for User Story 1

- [ ] T023 [P] [US1] Implement TaskFile dataclass in src/control_plane/models.py (id, state, priority, created_at, modified_at, metadata, file_path, content fields)
- [ ] T024 [P] [US1] Implement TaskFile.from_file() classmethod in src/control_plane/models.py (read file, parse YAML frontmatter, parse markdown content)
- [ ] T025 [P] [US1] Implement TaskFile.to_file() method in src/control_plane/models.py (write YAML frontmatter + markdown to file)
- [ ] T026 [P] [US1] Implement TaskFile.derive_state_from_location() method in src/control_plane/models.py (map parent folder to WorkflowState)
- [ ] T027 [P] [US1] Implement StateTransition dataclass in src/control_plane/models.py (transition_id, task_id, from_state, to_state, timestamp, reason, actor, logged, error fields)
- [ ] T028 [US1] Implement transition matrix in src/control_plane/state_machine.py (dictionary of valid from_state → to_state transitions)
- [ ] T029 [US1] Implement StateMachine class in src/control_plane/state_machine.py with __init__ (validate workflow folders exist)
- [ ] T030 [US1] Implement StateMachine.validate_transition() in src/control_plane/state_machine.py (check transition matrix, return bool)
- [ ] T031 [US1] Implement StateMachine.execute_transition() in src/control_plane/state_machine.py (validate, atomic file move, update metadata, log, verify)
- [ ] T032 [US1] Implement StateMachine.get_current_state() in src/control_plane/state_machine.py (find task file in workflow folders, derive state)
- [ ] T033 [US1] Implement StateMachine.list_tasks_in_state() in src/control_plane/state_machine.py (glob *.md files in folder, load TaskFiles)
- [ ] T034 [P] [US1] Implement LogEntry dataclass in src/control_plane/models.py (timestamp, level, action, task_id, from_state, to_state, result, approval_status, error, context fields)
- [ ] T035 [US1] Implement AuditLogger class in src/control_plane/logger.py with structlog configuration
- [ ] T036 [US1] Implement AuditLogger.log_transition() in src/control_plane/logger.py (append JSON entry to /Logs/YYYY-MM-DD.log)
- [ ] T037 [US1] Implement AuditLogger.log_error() in src/control_plane/logger.py (log exceptions with context, stack traces)
- [ ] T038 [US1] Add error handling in StateMachine.execute_transition() for disk full (OSError errno 28, keep task in original state, log CRITICAL)
- [ ] T039 [US1] Add error handling in StateMachine.execute_transition() for permission errors (PermissionError, move to /Rejected with error metadata)
- [ ] T040 [US1] Add retry logic in StateMachine.execute_transition() for transient failures (max 3 attempts, exponential backoff)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently (task lifecycle with logging)

---

## Phase 4: User Story 2 - Sensitive Action Approval (Priority: P1)

**Goal**: Explicitly require human approval for sensitive actions before execution, enforcing Constitutional Section 6-7

**Independent Test**: Create task requiring sensitive action, verify it waits in /Pending_Approval until manually moved to /Approved

### Tests for User Story 2

- [ ] T041 [P] [US2] Unit test for SensitiveActionDetector in tests/unit/test_approval.py (detect_patterns for send_message, make_payment, post_public, delete_data)
- [ ] T042 [P] [US2] Unit test for ApprovalChecker.is_sensitive_action() in tests/unit/test_approval.py (various task content patterns)
- [ ] T043 [P] [US2] Unit test for ApprovalChecker.requires_approval() in tests/unit/test_approval.py (sensitive content, high risk, explicit metadata)
- [ ] T044 [P] [US2] Unit test for ApprovalChecker.is_approved() in tests/unit/test_approval.py (file location check, approval_request.decision check)
- [ ] T045 [P] [US2] Unit test for ApprovalChecker.block_unapproved_action() in tests/unit/test_approval.py (raises ApprovalRequiredError, logs CRITICAL)
- [ ] T046 [US2] Integration test for approval workflow in tests/integration/test_workflow.py (Plans → Pending_Approval → manual move to Approved → Done)
- [ ] T047 [US2] Integration test for rejection workflow in tests/integration/test_workflow.py (Pending_Approval → manual move to Rejected → blocked execution)

### Implementation for User Story 2

- [ ] T048 [P] [US2] Implement ApprovalRequest dataclass in src/control_plane/models.py (task_id, action_type, risk_level, justification, requested_at, approved_at, approved_by, decision fields)
- [ ] T049 [US2] Implement SensitiveActionDetector class in src/control_plane/approval.py with sensitive action patterns (send_message, make_payment, post_public, delete_data)
- [ ] T050 [US2] Implement SensitiveActionDetector.detect_patterns() in src/control_plane/approval.py (regex patterns for each action type)
- [ ] T051 [US2] Implement SensitiveActionDetector.classify_risk_level() in src/control_plane/approval.py (low/medium/high based on action types)
- [ ] T052 [US2] Implement ApprovalChecker class in src/control_plane/approval.py with __init__
- [ ] T053 [US2] Implement ApprovalChecker.is_sensitive_action() in src/control_plane/approval.py (use SensitiveActionDetector on task content)
- [ ] T054 [US2] Implement ApprovalChecker.requires_approval() in src/control_plane/approval.py (check content, metadata, risk level)
- [ ] T055 [US2] Implement ApprovalChecker.is_approved() in src/control_plane/approval.py (check file location == /Approved and approval_request.decision == "approved")
- [ ] T056 [US2] Implement ApprovalChecker.block_unapproved_action() in src/control_plane/approval.py (raise ApprovalRequiredError if not approved)
- [ ] T057 [US2] Implement ApprovalChecker.create_approval_request() in src/control_plane/approval.py (create ApprovalRequest, add to task metadata, move to /Pending_Approval, log)
- [ ] T058 [US2] Implement AuditLogger.log_approval_request() in src/control_plane/logger.py (log approval request with context)
- [ ] T059 [US2] Integrate ApprovalChecker into StateMachine.execute_transition() (check for sensitive actions when moving from Plans, auto-move to Pending_Approval)
- [ ] T060 [US2] Add approval check before execution in StateMachine.execute_transition() (block if transitioning from Approved and not approved)
- [ ] T061 [US2] Add constitutional violation logging in ApprovalChecker.block_unapproved_action() (log CRITICAL with "approval_bypass_attempt" flag)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently (task lifecycle + approval enforcement)

---

## Phase 5: User Story 3 - State Verification & Recovery (Priority: P2)

**Goal**: Verify task state and recover from failures, ensuring system can be audited and failures handled gracefully

**Independent Test**: Simulate failure scenarios, verify state is consistent and recovery is possible

### Tests for User Story 3

- [ ] T062 [P] [US3] Unit test for StateVerifier.verify_state_consistency() in tests/unit/test_verifier.py (file location matches metadata state)
- [ ] T063 [P] [US3] Unit test for StateVerifier.verify_completion() in tests/unit/test_verifier.py (all Section 13 criteria: files exist, correct folders, logs written, disk verifiable)
- [ ] T064 [P] [US3] Unit test for AuditLogger.verify_log_integrity() in tests/unit/test_logger.py (hash chain verification, no tampering)
- [ ] T065 [P] [US3] Unit test for AuditLogger.query_logs() in tests/unit/test_logger.py (date range filter, task_id filter)
- [ ] T066 [US3] Integration test for error handling in tests/integration/test_error_handling.py (disk full, permission error, concurrent modification)
- [ ] T067 [US3] Integration test for state recovery in tests/integration/test_error_handling.py (reconstruct state from disk, orphaned task detection)
- [ ] T068 [US3] Integration test for retry logic in tests/integration/test_error_handling.py (transient failure → retry with backoff → success or max attempts)

### Implementation for User Story 3

- [ ] T069 [US3] Implement StateVerifier class in src/control_plane/verifier.py with __init__
- [ ] T070 [US3] Implement StateVerifier.verify_state_consistency() in src/control_plane/verifier.py (compare file location to metadata state, trust file location if mismatch)
- [ ] T071 [US3] Implement StateVerifier.verify_completion() in src/control_plane/verifier.py (check 4 criteria: file in /Done, metadata matches, log entry exists, disk consistent)
- [ ] T072 [US3] Implement StateVerifier.verify_all_tasks() in src/control_plane/verifier.py (scan all workflow folders, verify each task, report inconsistencies)
- [ ] T073 [US3] Implement AuditLogger.query_logs() in src/control_plane/logger.py (read log files, parse JSON, filter by date/task_id, return List[LogEntry])
- [ ] T074 [US3] Implement log integrity hash chain in AuditLogger.log_transition() (compute hash of previous entry + current entry, store in log)
- [ ] T075 [US3] Implement AuditLogger.verify_log_integrity() in src/control_plane/logger.py (verify hash chain, detect tampering, return bool)
- [ ] T076 [US3] Implement ErrorHandler class in src/control_plane/errors.py with handle_file_operation_error() (classify error, determine retry vs fail)
- [ ] T077 [US3] Implement ErrorHandler.handle_state_inconsistency() in src/control_plane/errors.py (trust file location, update metadata, log StateInconsistencyError)
- [ ] T078 [US3] Implement ErrorHandler.handle_log_write_failure() in src/control_plane/errors.py (write to stderr, add "unlogged_transition" flag to task metadata, alert human)
- [ ] T079 [US3] Add state inconsistency detection to StateMachine.get_current_state() (compare file location to metadata, call ErrorHandler if mismatch)
- [ ] T080 [US3] Add log integrity check on StateMachine.__init__ (verify logs on startup, halt if tampering detected per Section 8)
- [ ] T081 [US3] Implement recovery mode in StateMachine with recover_from_disk() method (scan all folders, reconstruct state, verify consistency, return report)

**Checkpoint**: All user stories should now be independently functional (task lifecycle + approval + verification/recovery)

---

## Phase 6: CLI Interface

**Purpose**: Command-line interface for manual operations and testing

- [ ] T082 [P] Implement CLI argument parser in src/cli/control_plane_cli.py (commands: create, transition, list, logs, verify)
- [ ] T083 [P] Implement 'create' command in src/cli/control_plane_cli.py (create task file in /Inbox with YAML frontmatter)
- [ ] T084 [P] Implement 'transition' command in src/cli/control_plane_cli.py (move task to specified state via StateMachine.execute_transition)
- [ ] T085 [P] Implement 'list' command in src/cli/control_plane_cli.py (list tasks in specified state via StateMachine.list_tasks_in_state)
- [ ] T086 [P] Implement 'logs' command in src/cli/control_plane_cli.py (query logs via AuditLogger.query_logs, pretty-print JSON)
- [ ] T087 [P] Implement 'verify' command in src/cli/control_plane_cli.py (verify all tasks via StateVerifier.verify_all_tasks, report inconsistencies)
- [ ] T088 Add CLI entry point in pyproject.toml (control-plane command → src.cli.control_plane_cli:main)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T089 [P] Add type hints to all functions and classes (use Python 3.11+ syntax with | for unions)
- [ ] T090 [P] Add docstrings to all public classes and methods (Google-style docstrings with Args, Returns, Raises)
- [ ] T091 [P] Create sample task files in tests/fixtures/sample_tasks/ (valid task, sensitive action task, malformed YAML)
- [ ] T092 [P] Add logging for all state machine operations (INFO level for normal ops, WARNING for retries, ERROR for failures)
- [ ] T093 [P] Add performance instrumentation (measure and log latencies for transitions, log writes, state queries)
- [ ] T094 [P] Create README.md with quickstart instructions (installation, basic usage, example workflows)
- [ ] T095 Validate against quickstart.md (follow all setup steps, run all examples, verify outputs)
- [ ] T096 Run complete test suite with coverage (pytest tests/ -v --cov=src/control_plane --cov-report=term-missing, target: 90%+ coverage)
- [ ] T097 Verify all performance targets (state transitions <100ms, logs <50ms, queries <10ms at p95)
- [ ] T098 Verify all constitutional requirements (run constitution compliance checklist from plan.md)
- [ ] T099 Create example workflow documentation in docs/examples/ (basic task lifecycle, approval workflow, error recovery)
- [ ] T100 Security audit (verify file permissions, no secrets in files, log sanitization, approval enforcement)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User Story 1 (Phase 3): Core task lifecycle - NO dependencies on other stories
  - User Story 2 (Phase 4): Approval system - Integrates with US1 but independently testable
  - User Story 3 (Phase 5): Verification - Uses US1/US2 but independently testable
- **CLI (Phase 6)**: Depends on all user stories (uses StateMachine, ApprovalChecker, StateVerifier)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - Integrates with US1 state machine but maintains independent approval logic
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Uses US1/US2 components but adds independent verification layer

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services/logic (entities → state machine → logger)
- Core functionality before integration
- Error handling after core functionality
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002-T009)
- All Foundational tasks marked [P] can run in parallel (T011-T014)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for User Story 1 marked [P] can run in parallel (T015-T021)
- All models for User Story 1 marked [P] can run in parallel (T023-T027, T034)
- All tests for User Story 2 marked [P] can run in parallel (T041-T045)
- All tests for User Story 3 marked [P] can run in parallel (T062-T065)
- All CLI commands marked [P] can run in parallel (T082-T087)
- All Polish tasks marked [P] can run in parallel (T089-T094, T099-T100)

---

## Parallel Example: User Story 1

```bash
# Launch all unit tests for User Story 1 together:
Task T016: "Unit test for WorkflowState enum in tests/unit/test_models.py"
Task T017: "Unit test for TaskFile entity in tests/unit/test_models.py"
Task T018: "Unit test for StateTransition entity in tests/unit/test_models.py"
Task T019: "Unit test for state transition matrix validation in tests/unit/test_state_machine.py"
Task T020: "Unit test for atomic file move operation in tests/unit/test_state_machine.py"
Task T021: "Unit test for AuditLogger in tests/unit/test_logger.py"

# Launch all model implementations for User Story 1 together:
Task T023: "Implement TaskFile dataclass in src/control_plane/models.py"
Task T024: "Implement TaskFile.from_file() classmethod in src/control_plane/models.py"
Task T025: "Implement TaskFile.to_file() method in src/control_plane/models.py"
Task T026: "Implement TaskFile.derive_state_from_location() method in src/control_plane/models.py"
Task T027: "Implement StateTransition dataclass in src/control_plane/models.py"
Task T034: "Implement LogEntry dataclass in src/control_plane/models.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T009)
2. Complete Phase 2: Foundational (T010-T014) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (T015-T040) - Core task lifecycle
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Create task in /Inbox
   - Validate it moves to /Needs_Action
   - Move through workflow to /Done
   - Verify all transitions logged
   - Verify state queries work
   - Test error scenarios (disk full, permissions)
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational (T001-T014) → Foundation ready
2. Add User Story 1 (T015-T040) → Test independently → Deploy/Demo (MVP!)
   - **Delivers**: Basic task lifecycle with logging
3. Add User Story 2 (T041-T061) → Test independently → Deploy/Demo
   - **Delivers**: Approval enforcement for sensitive actions
4. Add User Story 3 (T062-T081) → Test independently → Deploy/Demo
   - **Delivers**: State verification and error recovery
5. Add CLI (T082-T088) → Test independently → Deploy/Demo
   - **Delivers**: Command-line interface for operations
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (T001-T014)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (T015-T040) - Task lifecycle
   - **Developer B**: User Story 2 (T041-T061) - Approval system
   - **Developer C**: User Story 3 (T062-T081) - Verification
3. Stories complete and integrate independently
4. Team collaborates on CLI (T082-T088)
5. Team collaborates on Polish (T089-T100)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail (RED) before implementing (TDD approach)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- File paths are absolute from repository root
- All tasks follow Constitutional requirements (see plan.md Section: Constitution Check)
- Performance targets: State transitions <100ms, logs <50ms, queries <10ms (p95)
- Test coverage target: 90%+ for src/control_plane/

---

## Task Count Summary

- **Total Tasks**: 100
- **Phase 1 (Setup)**: 9 tasks
- **Phase 2 (Foundational)**: 5 tasks (BLOCKS all user stories)
- **Phase 3 (User Story 1 - Task Lifecycle)**: 26 tasks (8 tests + 18 implementation)
- **Phase 4 (User Story 2 - Approval)**: 21 tasks (7 tests + 14 implementation)
- **Phase 5 (User Story 3 - Verification)**: 13 tasks (7 tests + 6 implementation)
- **Phase 6 (CLI)**: 7 tasks
- **Phase 7 (Polish)**: 12 tasks
- **Parallel Opportunities**: 42 tasks marked [P] (42% of total)

---

## MVP Scope Recommendation

**Minimum Viable Product**: Phases 1-3 (T001-T040)
- Setup (9 tasks)
- Foundational (5 tasks)
- User Story 1: Task Lifecycle Management (26 tasks)

**Total MVP Tasks**: 40 tasks

**MVP Delivers**:
- Complete task lifecycle management (Inbox → Done)
- Atomic state transitions with audit trail
- Error handling and retry logic
- Full logging infrastructure
- Constitutional compliance for core workflow

**Post-MVP** (optional enhancements):
- User Story 2: Approval system (21 tasks)
- User Story 3: Verification & recovery (13 tasks)
- CLI interface (7 tasks)
- Polish & documentation (12 tasks)

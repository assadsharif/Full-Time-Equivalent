# Tasks: HITL Approval Workflows

**Input**: Design documents from `/specs/010-hitl-approval-workflows/`
**Prerequisites**: plan.md ✅, spec.md ✅

**Status**: Bronze ✅ DONE | Silver ✅ DONE | Gold ⚠️ IN PROGRESS

**Completed Work**:
- ✅ Bronze/Silver Tier: ApprovalManager (create, approve, reject, timeout), NonceGenerator (replay protection), IntegrityChecker (tamper detection)
- ✅ Test Coverage: 47 tests passing (nonce, integrity, lifecycle, timeout, orchestrator integration)
- ✅ CLI Integration: `fte approval list/show/approve/reject` commands implemented

**This Document**: Tasks for remaining Gold tier features (audit trail integration, file watch, authorized approvers, timeout escalation)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (No additional setup needed)

**Bronze/Silver infrastructure complete**. Existing structure:

```
src/approval/
├── __init__.py           ✅ Exports ApprovalManager, ApprovalRequest, ApprovalStatus
├── approval_manager.py   ✅ Full lifecycle (create, approve, reject, timeout)
├── nonce_generator.py    ✅ Replay protection
├── integrity_checker.py  ✅ Tamper detection (SHA256)
└── models.py             ✅ ApprovalRequest, ApprovalStatus enums

tests/approval/
├── test_approval_workflows.py  ✅ 47 tests passing
└── tests/cli/test_approval.py  ✅ CLI command tests

src/cli/approval.py       ✅ list/show/approve/reject commands
```

---

## Phase 2: Foundational (No blocking prerequisites)

**All foundational work complete**. Bronze/Silver tiers provide:
- Approval request creation with nonce
- File integrity verification
- Approve/reject state machine
- Timeout detection
- CLI interface

**Checkpoint**: Foundation ready - Gold tier enhancements can now be added

---

## Phase 3: User Story 3 - Timeout Escalation (Priority: P4 - Gold Tier)

**Goal**: Automatically escalate timed-out approvals to `/Needs_Human_Review` and send notifications

**Independent Test**: Create approval with 1-second timeout, wait, verify moved to `/Needs_Human_Review` with notification logged

### Implementation for User Story 3

- [ ] T001 [P] [US3] Create timeout checker service in src/approval/timeout_checker.py
- [ ] T002 [US3] Implement check_timeouts method to scan all pending approvals in src/approval/timeout_checker.py
- [ ] T003 [US3] Add move_to_needs_human_review method in src/approval/timeout_checker.py
- [ ] T004 [US3] Create notification generator for timeout events in src/approval/timeout_checker.py
- [ ] T005 [US3] Add timeout escalation to orchestrator approval checking loop in src/orchestrator/approval_checker.py
- [ ] T006 [US3] Create /Needs_Human_Review folder if not exists in vault initializer in src/vault/initializer.py
- [ ] T007 [P] [US3] Add tests for timeout escalation in tests/approval/test_timeout_escalation.py
- [ ] T008 [US3] Add timeout check to orchestrator main loop in src/orchestrator/scheduler.py

**Checkpoint**: Timeout escalation working - Expired approvals auto-moved with notifications

---

## Phase 4: User Story 4 - Audit Trail Integration (Priority: P4 - Gold Tier)

**Goal**: All approval events logged via P2 infrastructure with queryable audit trail

**Independent Test**: Create, approve, reject approvals and verify all events queryable via P2 logging service

### Implementation for User Story 4

- [ ] T009 [P] [US4] Add approval event logging to create method in src/approval/approval_manager.py
- [ ] T010 [P] [US4] Add approval event logging to approve method in src/approval/approval_manager.py
- [ ] T011 [P] [US4] Add approval event logging to reject method in src/approval/approval_manager.py
- [ ] T012 [P] [US4] Add timeout event logging to timeout checker in src/approval/timeout_checker.py
- [ ] T013 [US4] Create approval audit query service in src/approval/audit_query.py
- [ ] T014 [US4] Add query_approval_events method (filter by task_id, approval_id, status) in src/approval/audit_query.py
- [ ] T015 [US4] Add query_approver_history method (all approvals by user) in src/approval/audit_query.py
- [ ] T016 [US4] Add query_approval_stats method (approval rate, avg response time) in src/approval/audit_query.py
- [ ] T017 [US4] Add --audit flag to fte approval CLI to show audit trail in src/cli/approval.py
- [ ] T018 [P] [US4] Add tests for audit logging and queries in tests/approval/test_audit_trail.py

**Checkpoint**: Audit trail complete - All approval events logged and queryable

---

## Phase 5: User Story 5 - File Watch for Obsidian Edits (Priority: P4 - Gold Tier)

**Goal**: Detect manual approval file edits in Obsidian within 5 seconds

**Independent Test**: Manually edit approval file in vault, verify orchestrator detects change within 5 seconds

### Implementation for User Story 5

- [ ] T019 [P] [US5] Create ApprovalFileWatcher class in src/watchers/approval_watcher.py
- [ ] T020 [US5] Implement watch method using inotify/watchdog in src/watchers/approval_watcher.py
- [ ] T021 [US5] Add on_approval_file_modified callback in src/watchers/approval_watcher.py
- [ ] T022 [US5] Add approval file change detection to orchestrator in src/orchestrator/scheduler.py
- [ ] T023 [US5] Integrate ApprovalFileWatcher with orchestrator main loop in src/orchestrator/scheduler.py
- [ ] T024 [US5] Add debouncing to prevent multiple triggers (wait 2s after last change) in src/watchers/approval_watcher.py
- [ ] T025 [P] [US5] Add tests for file watch detection in tests/watchers/test_approval_watcher.py
- [ ] T026 [US5] Add latency logging for approval detection (<5s target) in src/watchers/approval_watcher.py

**Checkpoint**: File watch operational - Manual Obsidian edits detected within 5 seconds

---

## Phase 6: User Story 6 - Authorized Approvers (Priority: P4 - Gold Tier)

**Goal**: Enforce authorized approvers list per action type

**Independent Test**: Configure authorized approvers, attempt approval as unauthorized user, verify rejection

### Implementation for User Story 6

- [ ] T027 [P] [US6] Create AuthorizedApprovers class in src/approval/authorized_approvers.py
- [ ] T028 [P] [US6] Add load_config method to read from config/approval.yaml in src/approval/authorized_approvers.py
- [ ] T029 [P] [US6] Implement is_authorized method (check user against action type) in src/approval/authorized_approvers.py
- [ ] T030 [US6] Add authorization check to approve method in src/approval/approval_manager.py
- [ ] T031 [US6] Create approval configuration file template in config/approval.yaml
- [ ] T032 [US6] Add approver validation to CLI approve command in src/cli/approval.py
- [ ] T033 [US6] Add --approver flag to CLI for testing with different users in src/cli/approval.py
- [ ] T034 [P] [US6] Add tests for authorized approvers in tests/approval/test_authorized_approvers.py
- [ ] T035 [US6] Add authorization errors to audit log in src/approval/approval_manager.py

**Checkpoint**: Authorized approvers enforced - Unauthorized users cannot approve

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, testing, and operational improvements

- [ ] T036 [P] Create approval dashboard CLI command (fte approval dashboard) in src/cli/approval.py
- [ ] T037 [P] Add approval metrics (pending count, avg response time, approval rate) to dashboard in src/cli/approval.py
- [ ] T038 [P] Add --dry-run flag to approval commands for testing in src/cli/approval.py
- [ ] T039 [P] Create end-to-end approval workflow test (create → timeout → escalate) in tests/integration/test_approval_e2e.py
- [ ] T040 [P] Add approval workflow documentation in docs/APPROVAL_WORKFLOWS.md
- [ ] T041 [P] Add approval configuration examples in config/approval.yaml
- [ ] T042 [P] Add performance tests for approval operations (<100ms target) in tests/performance/test_approval_performance.py
- [ ] T043 [P] Create approval troubleshooting guide in docs/APPROVAL_TROUBLESHOOTING.md
- [ ] T044 [P] Add approval webhook support for external notifications in src/approval/webhooks.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1-2**: Complete ✅
- **Phase 3-6**: User Stories can proceed in parallel (all independent)
  - US3 (Timeout Escalation): No dependencies
  - US4 (Audit Trail): No dependencies
  - US5 (File Watch): No dependencies
  - US6 (Authorized Approvers): No dependencies
- **Phase 7**: Can start anytime, runs in parallel with user stories

### User Story Dependencies

- **User Story 3 (Timeout Escalation)**: Can start immediately - No dependencies
- **User Story 4 (Audit Trail)**: Can start immediately - No dependencies
- **User Story 5 (File Watch)**: Can start immediately - No dependencies
- **User Story 6 (Authorized Approvers)**: Can start immediately - No dependencies

### Within Each User Story

- US3: Timeout checker → orchestrator integration → tests
- US4: Event logging → query service → CLI integration → tests
- US5: File watcher → orchestrator integration → debouncing → tests
- US6: AuthorizedApprovers class → config file → approval manager integration → tests

### Parallel Opportunities

- **Phase 3-6**: All four user stories (US3, US4, US5, US6) can be developed in parallel by different team members
- Within US4: Tasks T009-T012 (logging to all methods) can run in parallel
- Within US6: Tasks T027-T029 (AuthorizedApprovers class) can run in parallel
- Polish tasks (T036-T044) can all run in parallel

---

## Parallel Example: User Story 4 (Audit Trail)

```bash
# Launch all logging additions in parallel:
Task T009: "Add approval event logging to create method in src/approval/approval_manager.py"
Task T010: "Add approval event logging to approve method in src/approval/approval_manager.py"
Task T011: "Add approval event logging to reject method in src/approval/approval_manager.py"
Task T012: "Add timeout event logging in src/approval/timeout_checker.py"

# Then create query service:
Task T013: "Create approval audit query service in src/approval/audit_query.py"

# Then CLI integration:
Task T017: "Add --audit flag to fte approval CLI in src/cli/approval.py"
```

---

## Implementation Strategy

### Recommended Order (Sequential)

1. **US4 (Audit Trail)** - Highest value, foundational for compliance
   - Tasks T009-T018 (10 tasks)
   - Enables compliance reporting

2. **US3 (Timeout Escalation)** - Critical for operational flow
   - Tasks T001-T008 (8 tasks)
   - Prevents approvals from blocking indefinitely

3. **US6 (Authorized Approvers)** - Security enhancement
   - Tasks T027-T035 (9 tasks)
   - Enforces authorization policy

4. **US5 (File Watch)** - UX improvement for Obsidian users
   - Tasks T019-T026 (8 tasks)
   - Enables sub-5s detection

5. **Polish (Phase 7)** - Final hardening
   - Tasks T036-T044 (9 tasks)
   - Dashboard, docs, performance

### Parallel Team Strategy

With 4 developers:

1. Complete existing Bronze/Silver validation together
2. Then split:
   - Developer A: US4 (Audit Trail) → Polish (Dashboard, Docs)
   - Developer B: US3 (Timeout Escalation) → Polish (Performance Tests)
   - Developer C: US6 (Authorized Approvers) → Polish (Webhooks)
   - Developer D: US5 (File Watch) → Polish (E2E Tests)
3. All features integrate via existing ApprovalManager interface

### MVP Definition

**Current State (Bronze + Silver)** is already MVP for Silver tier:
- ✅ Create approval requests
- ✅ Approve/reject via CLI
- ✅ Nonce-based replay protection
- ✅ File integrity verification
- ✅ Timeout detection

**Next MVP (Gold Core)**: US4 + US3
- Add audit trail compliance
- Add timeout escalation
- Low risk, high regulatory value

**Full Gold**: US3 + US4 + US5 + US6
- Complete compliance + UX + security

---

## Notes

- Bronze/Silver implementation uses UUID-based nonces (src/approval/nonce_generator.py)
- File integrity uses SHA256 hashing (src/approval/integrity_checker.py)
- Approval files are YAML frontmatter + Markdown body in `/Approvals`
- Timeout default is 12 hours (configurable via DEFAULT_TIMEOUT_HOURS)
- File watch should use `watchdog` library (cross-platform) not raw inotify
- Authorized approvers config should support wildcards (e.g., "*@company.com")
- Audit logging should use P2 logger with context: approval_id, action_type, approver, timestamp
- Timeout notifications should integrate with existing notification system (if available)
- Dashboard should show: pending count, avg response time, approval rate, recent activity
- All user story implementations should maintain zero-bypass guarantee

---

## Test Coverage Goals

- **Unit Tests**: 90%+ coverage for new modules (timeout_checker, audit_query, authorized_approvers, approval_watcher)
- **Integration Tests**: End-to-end approval workflow (create → approve → execute)
- **Performance Tests**: Approval operations <100ms, file watch detection <5s
- **Security Tests**: Authorization checks, nonce replay protection, integrity verification

---

## Success Metrics

- [ ] Timeout escalation operational (expired approvals → /Needs_Human_Review)
- [ ] Audit trail complete (all events logged and queryable)
- [ ] File watch functional (<5s detection latency for Obsidian edits)
- [ ] Authorized approvers enforced (unauthorized users blocked)
- [ ] Zero approval bypasses (100% enforcement maintained)
- [ ] All tests passing (unit, integration, e2e, performance)
- [ ] Dashboard operational (pending count, metrics, history)
- [ ] Documentation complete (workflows, config, troubleshooting)

---

**Total Tasks**: 44
- User Story 3 (Timeout Escalation): 8 tasks
- User Story 4 (Audit Trail): 10 tasks
- User Story 5 (File Watch): 8 tasks
- User Story 6 (Authorized Approvers): 9 tasks
- Polish: 9 tasks

**Estimated Effort**:
- US4: 6-8 hours (audit logging + query service + CLI)
- US3: 4-6 hours (timeout checker + escalation + notifications)
- US6: 4-6 hours (authorized approvers + config + enforcement)
- US5: 6-8 hours (file watcher + inotify/watchdog + orchestrator integration)
- Polish: 4-6 hours (dashboard + docs + performance tests)
- **Total**: 24-34 hours (3-4 days of focused work)

---

## Configuration Example

```yaml
# config/approval.yaml

# Default timeout for all approval requests
default_timeout_hours: 12

# Timeout per action type (overrides default)
timeout_by_action_type:
  payment: 24        # Payments get 24 hours
  wire: 24
  email: 6           # Emails get 6 hours
  delete: 12         # Deletions get 12 hours
  deploy: 4          # Deployments get 4 hours

# Authorized approvers per action type
authorized_approvers:
  payment:
    - ceo@company.com
    - cfo@company.com
    - "*@finance.company.com"   # Wildcard: all finance team

  wire:
    - ceo@company.com
    - cfo@company.com

  email:
    - ceo@company.com
    - "*@company.com"           # Any company employee

  delete:
    - cto@company.com
    - "*@engineering.company.com"

  deploy:
    - cto@company.com
    - lead-engineer@company.com

# Notification settings
notifications:
  timeout:
    enabled: true
    channels: ["email", "slack"]
    recipients:
      - ops@company.com

  approval_request:
    enabled: true
    channels: ["email"]
    recipients:
      - ceo@company.com
      - cfo@company.com

# Audit trail settings
audit:
  enabled: true
  log_level: info
  retention_days: 365  # Keep audit logs for 1 year
```

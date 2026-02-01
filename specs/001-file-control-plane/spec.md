# Feature Specification: File-Driven Control Plane

**Created**: 2026-01-27
**Status**: Planning
**Priority**: P1 - Critical (Foundation)
**Constitutional Requirements**: Sections 2, 4, 5

---

## Overview

Implement the file-driven state machine that manages task workflow through folder-based state transitions. This is the foundational control plane for the Digital FTE, ensuring all work is represented as files and state changes are explicit, auditable, and constitutional.

---

## User Scenarios & Testing

### User Story 1 - Task Lifecycle Management (Priority: P1)

**As a** Digital FTE system
**I want** to automatically manage task files through their lifecycle
**So that** every task follows a consistent, auditable workflow

**Why this priority**: Core infrastructure - all other features depend on this

**Independent Test**: Create a task file in /Inbox, verify it moves through states to /Done with all transitions logged

**Acceptance Scenarios**:

1. **Given** a new task file in /Inbox, **When** system validates it, **Then** file moves to /Needs_Action and transition is logged
2. **Given** a task in /Plans, **When** planning completes, **Then** file moves to /Pending_Approval with plan attached
3. **Given** a task in /Approved, **When** execution succeeds, **Then** file moves to /Done with completion metadata
4. **Given** any state transition, **When** it occurs, **Then** append-only log entry is created with timestamp, action, and status

---

### User Story 2 - Sensitive Action Approval (Priority: P1)

**As a** human owner
**I want** to explicitly approve sensitive actions before execution
**So that** the system never performs irreversible operations without my consent

**Why this priority**: Critical safety mechanism per Constitution Section 6-7

**Independent Test**: Create task requiring sensitive action, verify it waits in /Pending_Approval until manually moved to /Approved

**Acceptance Scenarios**:

1. **Given** a task involving "send message", **When** planning completes, **Then** task moves to /Pending_Approval with approval request
2. **Given** a task in /Pending_Approval, **When** human moves to /Approved, **Then** system executes action
3. **Given** a task in /Pending_Approval, **When** human moves to /Rejected, **Then** system does NOT execute action
4. **Given** a sensitive action task, **When** no approval exists, **Then** system blocks execution and logs warning

---

### User Story 3 - State Verification & Recovery (Priority: P2)

**As a** system administrator
**I want** to verify task state and recover from failures
**So that** the system can be audited and failures can be handled gracefully

**Why this priority**: Operational reliability and debugging capability

**Independent Test**: Simulate failure scenarios, verify state is consistent and recovery is possible

**Acceptance Scenarios**:

1. **Given** any task file, **When** querying its state, **Then** system returns current folder location and last transition
2. **Given** a task execution failure, **When** failure occurs, **Then** task moves to /Rejected with error details logged
3. **Given** a task in /Rejected, **When** human decides to retry, **Then** task can be moved back to /Inbox with revised approach
4. **Given** workflow folders, **When** inspecting disk, **Then** system state is fully reconstructable from files alone

---

### Edge Cases

- What happens when a file move operation fails (disk full, permissions)?
- How does system handle concurrent modifications to the same task file?
- What if a task file is manually deleted while in-progress?
- How does system detect and handle orphaned tasks stuck in folders?

---

## Requirements

### Functional Requirements

**FR-001**: System MUST maintain exactly 8 workflow folders: Inbox, Needs_Action, Plans, Pending_Approval, Approved, Rejected, Done, Logs

**FR-002**: System MUST treat file moves between folders as atomic state transitions

**FR-003**: System MUST validate sensitive actions against Constitution Section 6 list (sending messages, making payments, posting publicly, deleting data)

**FR-004**: System MUST block execution of sensitive actions unless task file is in /Approved folder

**FR-005**: System MUST create append-only log entry for every state transition with: timestamp, action type, triggering file, result, approval status

**FR-006**: System MUST support querying current state of any task by file path

**FR-007**: System MUST implement file-based approval mechanism (manual file move to /Approved)

**FR-008**: System MUST detect and log constitution violations (attempts to bypass approval)

**FR-009**: System MUST support state recovery from disk inspection (no hidden state)

**FR-010**: System MUST implement bounded retry logic for failed operations (max 3 attempts)

### Key Entities

- **TaskFile**: Represents a unit of work with metadata (ID, description, priority, state, created, modified)
- **WorkflowState**: Enum of valid states (Inbox, Needs_Action, Plans, Pending_Approval, Approved, Rejected, Done)
- **StateTransition**: Record of state change (from_state, to_state, timestamp, reason, logged)
- **ApprovalRequest**: Request for human approval (task_id, action_type, risk_level, justification)
- **LogEntry**: Audit record (timestamp, level, action, task_id, result, approval_status)

---

## Success Criteria

### Measurable Outcomes

**SC-001**: 100% of state transitions are logged to /Logs (verified via audit)

**SC-002**: 0 sensitive actions execute without approval (verified via constitution checks)

**SC-003**: System state is fully reconstructable from disk files alone (verified via recovery tests)

**SC-004**: State transitions complete in < 100ms (p95)

**SC-005**: Log entries are append-only and never modified (verified via integrity checks)

**SC-006**: Failed operations result in clean state (task in /Rejected with error details)

---

## Assumptions

- File system is reliable and supports atomic operations
- Single process access (no concurrent writes to same file)
- File system has sufficient permissions for folder operations
- Disk space monitoring handled separately
- Task file format is markdown with YAML frontmatter

---

## Out of Scope

- Multi-user concurrent access (Phase 2)
- Distributed file system support (Phase 2)
- Real-time notifications (Phase 2)
- Web UI for state visualization (Phase 3)
- Automatic state recovery from crashes (Phase 2)

---

## Non-Functional Requirements

**Performance:**
- State transitions: < 100ms (p95)
- Log writes: < 50ms (p95)
- State queries: < 10ms (p95)

**Reliability:**
- No data loss on state transitions
- Atomic file operations
- Graceful degradation on disk errors

**Security:**
- File permissions enforced (owner-only access)
- No secrets in task files
- Audit trail immutability

**Maintainability:**
- Clear error messages
- Comprehensive logging
- Simple file-based debugging

---

## Dependencies

- File system with atomic move operations
- YAML parser for task file metadata
- Logging library for structured logs
- File watcher for state change detection (optional)

---

## Constitutional Compliance

This feature directly implements:
- **Section 2**: Source of Truth - Files are facts, memory is derived
- **Section 4**: File-Driven Control Plane - Folder state defines workflow state
- **Section 5**: Reasoning Discipline - Read → Think → Plan → Act → Write → Verify
- **Section 6-7**: Autonomy Boundaries and HITL - Approval for sensitive actions
- **Section 8**: Auditability & Logging - Every action logged
- **Section 9**: Error Handling - Errors never hidden, partial completion preferred

---

*This feature is the foundation of the Digital FTE's trustworthy, auditable behavior.*

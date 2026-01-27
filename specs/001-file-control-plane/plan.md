# Implementation Plan: File-Driven Control Plane

**Branch**: `001-file-control-plane` | **Date**: 2026-01-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-file-control-plane/spec.md`

**Note**: This plan implements the foundational file-driven state machine for the Digital FTE.

## Summary

Implement a folder-based state machine that manages task workflow through atomic file transitions across 8 workflow folders (Inbox, Needs_Action, Plans, Pending_Approval, Approved, Rejected, Done, Logs). The system ensures all work is file-represented, state changes are auditable, and sensitive actions require explicit human approval. Uses Python with pathlib for atomic file operations, watchdog for file monitoring, PyYAML for task metadata parsing, and structlog for append-only logging.

## Technical Context

**Language/Version**: Python 3.11+ (for pathlib atomic operations, match statements, type hints)
**Primary Dependencies**:
- pathlib (stdlib) - atomic file operations and path management
- watchdog - file system event monitoring
- PyYAML - task file metadata parsing (YAML frontmatter)
- structlog - structured, append-only logging

**Storage**: File system (local disk) - task files in workflow folders, logs in /Logs directory
**Testing**: pytest with fixtures for isolated file system operations
**Target Platform**: Linux/macOS/Windows (cross-platform file operations)
**Project Type**: Single library + CLI (file-driven control plane)
**Performance Goals**:
- State transitions: < 100ms (p95)
- Log writes: < 50ms (p95)
- State queries: < 10ms (p95)

**Constraints**:
- Atomic file operations (no partial states)
- Single process access (no concurrent file writes)
- Append-only logs (immutability requirement)
- Owner-only file permissions (security requirement)

**Scale/Scope**:
- 8 workflow folders (fixed per Constitution Section 4)
- Support 100s of concurrent task files
- Log retention: 90 days default
- Max 3 retry attempts on transient failures

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Section 2: Source of Truth ✅
**Requirement**: Files are facts. Memory is derived. No hidden state.
**Compliance**: All task state stored in file location and YAML frontmatter. State fully reconstructable from disk.
**Implementation**: TaskFile class reads state from folder location + file metadata. No in-memory caches.

### Section 4: File-Driven Control Plane ✅
**Requirement**: 8 workflow folders fixed. File moves = state transitions.
**Compliance**: Exactly 8 folders enforced in WorkflowState enum. File moves via atomic `pathlib.Path.rename()`.
**Implementation**: StateMachine class validates folder existence, enforces valid transitions, uses atomic operations.

### Section 5: Reasoning Discipline ✅
**Requirement**: Read → Think → Plan → Act → Write → Verify loop.
**Compliance**: Each state transition follows: read task file → validate state → plan transition → execute move → write log → verify new state.
**Implementation**: StateTransition class encapsulates loop with mandatory verification step.

### Section 6-7: Autonomy & HITL ✅
**Requirement**: Sensitive actions require approval. No action without file in /Approved.
**Compliance**: SensitiveActionDetector checks task content against Constitution Section 6 list. Blocks execution unless in /Approved folder.
**Implementation**: ApprovalChecker validates folder location before sensitive action execution. Logs violations.

### Section 8: Auditability & Logging ✅
**Requirement**: Every action logged with timestamp, action type, file, result, approval status.
**Compliance**: structlog configured for append-only JSON logs with all required fields.
**Implementation**: AuditLogger wraps all state transitions. Log rotation daily. Integrity hashes computed.

### Section 9: Error Handling ✅
**Requirement**: Errors never hidden. Partial completion preferred. Bounded retry.
**Compliance**: All exceptions logged with full context. Failed tasks move to /Rejected with error details. Max 3 retry attempts.
**Implementation**: ErrorHandler catches exceptions, logs details, moves task to /Rejected with metadata.

### Section 10: Persistence Loop 🔄
**Requirement**: Ralph Wiggum rule (not in this feature - deferred to persistence-loop feature)
**Status**: Not applicable - this feature provides state machine foundation. Persistence loop implemented separately.

### Section 11: No Spec Drift ✅
**Requirement**: No invented requirements. All changes via SDD workflow.
**Compliance**: Implementation follows spec exactly. No additional features.
**Verification**: Every requirement in spec.md mapped to implementation component.

### Section 13: Completion Definition ✅
**Requirement**: Task complete only if: output files exist, files in correct folders, logs written, verifiable via disk.
**Compliance**: StateVerifier checks all 4 criteria before marking task in /Done.
**Implementation**: Completion gate validates file existence, folder location, log entry, and disk consistency.

**GATE STATUS**: ✅ **PASS** - All applicable constitutional requirements satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (/sp.plan command)
├── data-model.md        # Phase 1 output (/sp.plan command)
├── quickstart.md        # Phase 1 output (/sp.plan command)
├── contracts/           # Phase 1 output (/sp.plan command)
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created by /sp.plan)
```

### Source Code (repository root)

```text
src/
├── control_plane/
│   ├── __init__.py
│   ├── models.py              # TaskFile, WorkflowState, StateTransition entities
│   ├── state_machine.py       # StateMachine class - core state transition logic
│   ├── approval.py            # ApprovalChecker, SensitiveActionDetector
│   ├── logger.py              # AuditLogger with structlog configuration
│   ├── verifier.py            # StateVerifier for completion checks
│   └── errors.py              # ErrorHandler, custom exceptions
├── cli/
│   └── control_plane_cli.py   # CLI interface for manual operations
└── utils/
    ├── file_ops.py            # Atomic file operation wrappers
    └── config.py              # Configuration loader

tests/
├── unit/
│   ├── test_models.py         # Entity unit tests
│   ├── test_state_machine.py # State machine logic tests
│   ├── test_approval.py       # Approval checking tests
│   └── test_logger.py         # Logging tests
├── integration/
│   ├── test_workflow.py       # End-to-end workflow tests
│   └── test_error_handling.py # Error scenario tests
└── fixtures/
    ├── sample_tasks/          # Test task files
    └── conftest.py            # pytest fixtures for isolated file systems

Inbox/.gitkeep                 # Workflow folders (already exist)
Needs_Action/.gitkeep
Plans/.gitkeep
Pending_Approval/.gitkeep
Approved/.gitkeep
Rejected/.gitkeep
Done/.gitkeep
Logs/.gitkeep
```

**Structure Decision**: Single project structure (Option 1) selected. The file-driven control plane is a foundational library with CLI tooling. No frontend/backend split needed - this is infrastructure code that other features will use. Workflow folders already exist at repository root per Constitution Section 4.

## Complexity Tracking

> **No constitutional violations requiring justification.**

All design choices align with constitutional requirements. No unnecessary complexity introduced.

## Phase 0: Research & Technology Decisions

### Python 3.11+ Selection

**Decision**: Use Python 3.11+ as implementation language.

**Rationale**:
- Native atomic file operations via pathlib.Path.rename() (POSIX-compliant, constitutional requirement)
- Structural pattern matching (match statements) for clean state machine logic
- Improved type hints for better IDE support and early error detection
- Cross-platform compatibility (Linux/macOS/Windows) for workflow folder operations
- Rich standard library reduces external dependencies

**Alternatives Considered**:
- Go: Excellent performance but adds build complexity, harder to iterate for spec-driven development
- Rust: Maximum safety but steeper learning curve, overkill for file operations
- TypeScript/Node.js: Good for async, but weaker file system atomicity guarantees

**Constitutional Mapping**: Section 2 (Source of Truth) requires file system as single source of truth. Python pathlib provides reliable atomic operations.

---

### pathlib vs os Module

**Decision**: Use pathlib (stdlib) for all file operations.

**Rationale**:
- Path.rename() provides atomic move operations (required for state transitions per Section 4)
- Object-oriented API reduces path manipulation errors
- Cross-platform path handling (handles Windows vs Unix paths transparently)
- Composable paths reduce string concatenation bugs
- Better readability: `path.parent / "new_folder"` vs `os.path.join(os.path.dirname(path), "new_folder")`

**Alternatives Considered**:
- os module: Lower-level, more verbose, harder to ensure atomic operations
- shutil: Non-atomic by default, risk of partial state during errors

**Constitutional Mapping**: Section 4 (File-Driven Control Plane) requires atomic state transitions. pathlib.Path.rename() ensures atomicity.

---

### watchdog for File System Monitoring

**Decision**: Use watchdog library for file system event detection.

**Rationale**:
- Cross-platform (Linux inotify, macOS FSEvents, Windows ReadDirectoryChangesW)
- Event-driven architecture reduces polling overhead
- Detects file moves, creates, modifies, deletes in real-time
- Well-maintained library (10+ years, 6k+ stars)
- Enables reactive state machine (respond to file moves immediately)

**Alternatives Considered**:
- Polling with os.listdir(): High CPU overhead, introduces latency
- Platform-specific APIs (inotify, FSEvents): Not cross-platform, increases maintenance
- No monitoring: Requires explicit API calls, misses manual file moves by human

**Constitutional Mapping**: Section 5 (Reasoning Discipline) requires continuous Read → Verify loop. Watchdog enables real-time state observation.

---

### PyYAML for Task Metadata

**Decision**: Use PyYAML for parsing task file frontmatter.

**Rationale**:
- YAML frontmatter is human-readable (important for file-first design per Section 2)
- Standard format for markdown files with metadata (Jekyll, Hugo, Obsidian convention)
- Supports complex nested structures (checkpoints, approval requests)
- safe_load() prevents code execution (security requirement)
- Wide adoption in Python ecosystem (well-tested)

**Alternatives Considered**:
- JSON frontmatter: Less human-readable, requires strict quoting
- TOML frontmatter: Less common, adds dependency
- No frontmatter: Pure markdown less structured, harder to query state

**Constitutional Mapping**: Section 2 (Source of Truth) requires files as facts. YAML frontmatter makes metadata explicit and queryable.

---

### structlog for Append-Only Logging

**Decision**: Use structlog for structured, append-only audit logging.

**Rationale**:
- Structured logging (JSON output) enables programmatic log analysis (required for Section 8)
- Append-only design prevents log tampering (constitutional requirement)
- Context binding (task_id, state) automatically added to all log entries
- Fast performance (< 50ms for log writes)
- Integrates with standard logging library (compatible with existing tools)

**Alternatives Considered**:
- Standard logging: Unstructured text, harder to query, no context binding
- Custom logging: Reinventing wheel, likely less robust
- Database logging: Adds dependency, violates file-first design (Section 2)

**Constitutional Mapping**: Section 8 (Auditability & Logging) requires "timestamp, action type, triggering file, result, approval status" - structlog provides all fields as structured JSON.

---

### pytest for Testing

**Decision**: Use pytest with fixtures for isolated file system testing.

**Rationale**:
- Fixtures enable isolated test environments (tmpdir, tmp_path)
- Parametrized tests reduce duplication for state transition matrix
- Rich assertion introspection (detailed failure messages)
- Plugin ecosystem (pytest-cov for coverage, pytest-xdist for parallel)
- Industry standard for Python testing

**Alternatives Considered**:
- unittest: More verbose, requires classes, weaker fixtures
- nose2: Less maintained, smaller ecosystem
- Custom test framework: Unnecessary complexity

**Constitutional Mapping**: Section 13 (Completion Definition) requires verification. pytest fixtures enable reproducible verification.

---

## Phase 1: Design & Contracts

### Data Model

See [data-model.md](./data-model.md) for complete entity definitions.

**Core Entities**:

1. **TaskFile**: Represents a unit of work
   - Fields: id, description, priority, state, created_at, modified_at, metadata
   - Derived from: File location (determines state) + YAML frontmatter (metadata)
   - Validation: ID must be unique, state must match folder location

2. **WorkflowState**: Enum of valid states
   - Values: Inbox, Needs_Action, Plans, Pending_Approval, Approved, Rejected, Done
   - Immutable: Fixed set per Constitution Section 4
   - Validation: No custom states allowed

3. **StateTransition**: Record of state change
   - Fields: from_state, to_state, timestamp, reason, task_id, logged
   - Validation: Transition must be in allowed transition matrix
   - Persistence: Logged to /Logs immediately after transition

4. **ApprovalRequest**: Request for human approval
   - Fields: task_id, action_type, risk_level, justification, requested_at
   - Triggers: Sensitive actions per Constitution Section 6 list
   - Resolution: Human moves file from /Pending_Approval to /Approved or /Rejected

5. **LogEntry**: Audit record
   - Fields: timestamp, level, action, task_id, from_state, to_state, result, approval_status, error
   - Format: JSON (structured logging via structlog)
   - Storage: /Logs/YYYY-MM-DD.log (daily rotation)

### State Transition Matrix

Valid transitions (enforced by StateMachine class):

```
Inbox → Needs_Action             # Validation complete
Needs_Action → Plans             # Planning started
Plans → Pending_Approval         # Plan complete, approval needed
Plans → Needs_Action             # Planning identified clarifications needed
Pending_Approval → Approved      # Human approved (manual file move)
Pending_Approval → Rejected      # Human rejected (manual file move)
Approved → Done                  # Execution succeeded
Approved → Rejected              # Execution failed (hard failure)
Rejected → Inbox                 # Human requests retry with revised approach
```

Invalid transitions (blocked by StateMachine):
- Any transition skipping approval (e.g., Plans → Approved)
- Any transition to Approved without manual human file move
- Any backwards transition except Rejected → Inbox
- Any transition from Done (terminal state)

### API Contracts

See [contracts/](./contracts/) for OpenAPI specifications.

**Core APIs** (Python library interface):

```python
# State Machine API
class StateMachine:
    def validate_transition(from_state: WorkflowState, to_state: WorkflowState) -> bool
    def execute_transition(task_file: TaskFile, to_state: WorkflowState) -> StateTransition
    def get_current_state(task_id: str) -> WorkflowState
    def list_tasks_in_state(state: WorkflowState) -> List[TaskFile]

# Approval API
class ApprovalChecker:
    def is_sensitive_action(task_content: str) -> bool
    def requires_approval(task_file: TaskFile) -> bool
    def is_approved(task_file: TaskFile) -> bool
    def block_unapproved_action(task_file: TaskFile) -> None  # Raises exception if not approved

# Logging API
class AuditLogger:
    def log_transition(transition: StateTransition) -> None
    def log_approval_request(request: ApprovalRequest) -> None
    def log_error(task_id: str, error: Exception, context: dict) -> None
    def query_logs(start_date: date, end_date: date, task_id: Optional[str]) -> List[LogEntry]

# Verification API
class StateVerifier:
    def verify_state_consistency(task_file: TaskFile) -> bool  # File location matches metadata state
    def verify_completion(task_file: TaskFile) -> bool  # All Section 13 criteria met
    def verify_log_integrity(log_file: Path) -> bool  # Append-only, no tampering
```

**Error Taxonomy**:

```python
# errors.py
class ControlPlaneError(Exception): pass

class InvalidTransitionError(ControlPlaneError): pass  # Transition not in allowed matrix
class ApprovalRequiredError(ControlPlaneError): pass  # Sensitive action without approval
class StateInconsistencyError(ControlPlaneError): pass  # File location != metadata state
class LogWriteError(ControlPlaneError): pass  # Failed to write to /Logs
class FileOperationError(ControlPlaneError): pass  # Atomic file operation failed
```

### Quickstart Guide

See [quickstart.md](./quickstart.md) for complete setup instructions.

**Development Environment Setup**:

```bash
# 1. Clone repository and checkout feature branch
git checkout 001-file-control-plane

# 2. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -e ".[dev]"  # Installs: watchdog, PyYAML, structlog, pytest, pytest-cov

# 4. Verify workflow folders exist
ls -la {Inbox,Needs_Action,Plans,Pending_Approval,Approved,Rejected,Done,Logs}

# 5. Run tests
pytest tests/ -v --cov=src/control_plane
```

**Example Usage**:

```python
from control_plane import StateMachine, TaskFile, WorkflowState

# Initialize state machine
sm = StateMachine()

# Create task in /Inbox
task = TaskFile.create(
    id="task-001",
    description="Implement feature X",
    priority="P1"
)

# Validate task → move to /Needs_Action
transition = sm.execute_transition(task, WorkflowState.NEEDS_ACTION)
# Result: File moved from /Inbox/task-001.md to /Needs_Action/task-001.md
# Log entry created in /Logs/2026-01-27.log

# Query current state
state = sm.get_current_state("task-001")
assert state == WorkflowState.NEEDS_ACTION
```

---

## Explicit Failure Modes

### File System Failures

**Failure Mode 1: Disk Full During State Transition**
- **Trigger**: pathlib.Path.rename() fails with OSError (errno 28: No space left on device)
- **Impact**: Task stuck in intermediate state (file not moved)
- **Detection**: Exception caught in StateMachine.execute_transition()
- **Handling**:
  1. Log error with full context (task_id, from_state, to_state, disk_usage)
  2. Do NOT modify task file (partial state prevented)
  3. Alert human via log entry (level: CRITICAL)
  4. Task remains in original state (atomic guarantee)
- **Recovery**: Human frees disk space, manually retries transition via CLI
- **Constitutional Mapping**: Section 9 (Error Handling) - "partial completion preferred" (task not lost, state consistent)

**Failure Mode 2: File Permission Error on Move**
- **Trigger**: pathlib.Path.rename() fails with PermissionError
- **Impact**: State transition blocked
- **Detection**: Exception caught in StateMachine.execute_transition()
- **Handling**:
  1. Log error with file path and permission bits
  2. Check file ownership (expected: current user only per security requirement)
  3. Move task to /Rejected with error metadata
  4. Alert human (requires permission fix)
- **Recovery**: Human fixes permissions (chmod 600), moves file from /Rejected to /Inbox
- **Constitutional Mapping**: Section 9 - "errors never hidden" (explicit rejection with details)

**Failure Mode 3: Concurrent File Modification**
- **Trigger**: Task file modified by external process while state machine reads it
- **Impact**: Race condition - state inconsistency possible
- **Detection**: File mtime changed between read and write operations
- **Handling**:
  1. Read file with timestamp check
  2. If mtime changed during operation, abort and log warning
  3. Retry with exponential backoff (max 3 attempts per Section 9)
  4. If retries exhausted, move to /Rejected with concurrency error
- **Recovery**: Human ensures single-process access (constitutional constraint)
- **Constitutional Mapping**: Section 2 (Source of Truth) - maintains file consistency

---

### Logging Failures

**Failure Mode 4: Log Write Failure**
- **Trigger**: structlog append fails (disk full, permissions, log file locked)
- **Impact**: State transition succeeded but not auditable
- **Detection**: Exception in AuditLogger.log_transition()
- **Handling**:
  1. Write emergency log to stderr (console output)
  2. Mark task file metadata with "unlogged_transition" flag
  3. Attempt log write on next state change (recover lost entry)
  4. Alert human via console (CRITICAL: audit trail incomplete)
- **Recovery**: Human checks /Logs directory, manually reconstructs entry from task metadata
- **Constitutional Mapping**: Section 8 (Auditability) - "every action logged" (best-effort recovery, transparent failure)

**Failure Mode 5: Log Integrity Violation**
- **Trigger**: Log file modified (not append-only)
- **Impact**: Audit trail compromised
- **Detection**: Integrity hash mismatch (computed vs stored)
- **Handling**:
  1. Halt all operations immediately (constitutional override per Section 14)
  2. Log CRITICAL alert to separate integrity violation log
  3. Do NOT allow any further state transitions
  4. Alert human: "STOP → WARN → DO NOT PROCEED" protocol
- **Recovery**: Human investigates tampering, restores logs from backup, restarts system
- **Constitutional Mapping**: Section 8 - "append-only, never modified" (non-negotiable requirement)

---

### State Machine Failures

**Failure Mode 6: Invalid State Transition Attempted**
- **Trigger**: Code attempts transition not in allowed matrix (e.g., Plans → Approved skipping approval)
- **Impact**: Constitutional violation (Section 6-7: HITL requirement)
- **Detection**: StateMachine.validate_transition() returns False
- **Handling**:
  1. Raise InvalidTransitionError immediately (block execution)
  2. Log violation with full context (task_id, attempted transition, stack trace)
  3. Do NOT move file (state unchanged)
  4. Alert human (potential bug or malicious code)
- **Recovery**: Human reviews code, identifies bug, fixes transition logic
- **Constitutional Mapping**: Section 11 (No Spec Drift) - enforces valid transitions per spec

**Failure Mode 7: Sensitive Action Without Approval**
- **Trigger**: Code attempts to execute sensitive action (send message, delete data) on task in non-/Approved folder
- **Impact**: Constitutional violation (Section 6: Autonomy Boundaries)
- **Detection**: ApprovalChecker.is_approved() returns False
- **Handling**:
  1. Raise ApprovalRequiredError immediately (block execution)
  2. Log attempted bypass with full context (task_id, action_type, current_state)
  3. Move task to /Rejected with "approval_bypass_attempt" flag
  4. Alert human (CRITICAL: constitutional violation)
- **Recovery**: Human reviews task, moves to /Pending_Approval if legitimate, investigates code if malicious
- **Constitutional Mapping**: Section 6-7 (Autonomy & HITL) - "no action without file in /Approved"

**Failure Mode 8: State Inconsistency (File Location ≠ Metadata)**
- **Trigger**: Task file in /Plans folder but metadata says state=Approved
- **Impact**: Source of truth violated (Section 2)
- **Detection**: StateVerifier.verify_state_consistency() returns False
- **Handling**:
  1. Log StateInconsistencyError with both values (file location, metadata state)
  2. Trust file location as authoritative (per Section 2: "files are facts")
  3. Overwrite metadata state to match file location
  4. Alert human (potential bug in state machine)
- **Recovery**: Human reviews state machine code, identifies bug, adds regression test
- **Constitutional Mapping**: Section 2 (Source of Truth) - "files are facts, memory is derived"

---

### External Dependency Failures

**Failure Mode 9: YAML Parsing Error**
- **Trigger**: Task file frontmatter is malformed YAML
- **Impact**: Cannot read task metadata
- **Detection**: PyYAML.safe_load() raises YAMLError
- **Handling**:
  1. Log parsing error with file path and YAML excerpt
  2. Move file to /Rejected with "malformed_yaml" flag
  3. Create error report file in /Rejected with parser output
  4. Alert human (manual fix required)
- **Recovery**: Human edits task file to fix YAML syntax, moves from /Rejected to /Inbox
- **Constitutional Mapping**: Section 9 (Error Handling) - "errors never hidden" (explicit error report)

**Failure Mode 10: Watchdog Monitoring Failure**
- **Trigger**: File system monitor crashes or stops emitting events
- **Impact**: State changes not detected in real-time
- **Detection**: Watchdog thread death detected by health check
- **Handling**:
  1. Log watchdog failure with exception details
  2. Restart watchdog observer (auto-recovery attempt)
  3. If restart fails 3 times, fall back to polling mode (scan folders every 5 seconds)
  4. Alert human (degraded performance)
- **Recovery**: Automatic (restart observer) or human intervention (investigate system issues)
- **Constitutional Mapping**: Section 9 (Error Handling) - "partial completion preferred" (fall back to polling vs halt)

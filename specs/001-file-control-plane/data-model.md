# Data Model: File-Driven Control Plane

**Feature**: File-Driven Control Plane
**Branch**: `001-file-control-plane`
**Created**: 2026-01-27

---

## Overview

This document defines the core entities for the file-driven control plane. All entities are designed to be file-backed per Constitution Section 2 (Source of Truth).

---

## Core Entities

### 1. TaskFile

**Description**: Represents a unit of work with metadata stored in YAML frontmatter.

**Source of Truth**: File system location (folder determines state) + YAML frontmatter (metadata)

**File Format**:
```markdown
---
id: task-001
state: Needs_Action
priority: P1
created_at: 2026-01-27T10:00:00Z
modified_at: 2026-01-27T10:30:00Z
metadata:
  assigned_to: null
  tags: [feature, backend]
  estimated_hours: 8
---

# Task: Implement feature X

## Description
Detailed task description here...

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| id | str | Yes | Unique, alphanumeric+hyphens | Unique task identifier |
| state | WorkflowState | Yes | Must match file location folder | Current workflow state (derived from folder) |
| priority | str | Yes | P0, P1, P2, P3 | Task priority |
| created_at | datetime | Yes | ISO 8601 format | Task creation timestamp |
| modified_at | datetime | Yes | ISO 8601 format, >= created_at | Last modification timestamp |
| metadata | dict | No | Free-form key-value pairs | Additional task-specific metadata |

**Relationships**:
- 1 TaskFile → Many StateTransition (audit trail)
- 1 TaskFile → 0..1 ApprovalRequest (if sensitive action detected)

**Validation Rules**:
- `id` must be unique across all workflow folders
- `state` must match the folder the file is in (enforced by StateVerifier)
- `modified_at` must be >= `created_at`
- File must be valid Markdown with YAML frontmatter

**Python Representation**:
```python
@dataclass
class TaskFile:
    id: str
    state: WorkflowState
    priority: str
    created_at: datetime
    modified_at: datetime
    metadata: dict[str, Any]
    file_path: Path  # Actual file system path
    content: str  # Markdown content (without frontmatter)

    @classmethod
    def from_file(cls, path: Path) -> 'TaskFile':
        """Load TaskFile from disk."""
        pass

    def to_file(self, path: Path) -> None:
        """Write TaskFile to disk."""
        pass

    def derive_state_from_location(self) -> WorkflowState:
        """Derive state from parent folder name."""
        pass
```

---

### 2. WorkflowState

**Description**: Enum of valid workflow states. Fixed set per Constitution Section 4.

**Values**:
```python
class WorkflowState(Enum):
    INBOX = "Inbox"
    NEEDS_ACTION = "Needs_Action"
    PLANS = "Plans"
    PENDING_APPROVAL = "Pending_Approval"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    DONE = "Done"
```

**Constraints**:
- Immutable: No custom states can be added
- Folder names must exactly match enum values
- Case-sensitive matching

**Folder Mapping**:
```
/Inbox            → WorkflowState.INBOX
/Needs_Action     → WorkflowState.NEEDS_ACTION
/Plans            → WorkflowState.PLANS
/Pending_Approval → WorkflowState.PENDING_APPROVAL
/Approved         → WorkflowState.APPROVED
/Rejected         → WorkflowState.REJECTED
/Done             → WorkflowState.DONE
```

---

### 3. StateTransition

**Description**: Record of a state change. Logged to `/Logs` for audit trail.

**Source of Truth**: Log file (`/Logs/YYYY-MM-DD.log`)

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| transition_id | str | Yes | Unique transition identifier |
| task_id | str | Yes | ID of task that transitioned |
| from_state | WorkflowState | Yes | Previous state |
| to_state | WorkflowState | Yes | New state |
| timestamp | datetime | Yes | When transition occurred (ISO 8601) |
| reason | str | No | Human-readable reason for transition |
| actor | str | Yes | "system" or "human" |
| logged | bool | Yes | Whether transition was logged (always True) |
| error | str | No | Error message if transition failed |

**Validation Rules**:
- `(from_state, to_state)` must be in allowed transition matrix
- `timestamp` must be >= task.created_at
- `actor` must be "system" or "human"
- If `to_state == APPROVED` or `to_state == REJECTED` from `PENDING_APPROVAL`, actor must be "human"

**Log Format** (JSON via structlog):
```json
{
  "transition_id": "trans-001",
  "task_id": "task-001",
  "from_state": "Plans",
  "to_state": "Pending_Approval",
  "timestamp": "2026-01-27T10:30:00Z",
  "reason": "Planning complete, sensitive action detected",
  "actor": "system",
  "logged": true,
  "error": null
}
```

**Python Representation**:
```python
@dataclass
class StateTransition:
    transition_id: str
    task_id: str
    from_state: WorkflowState
    to_state: WorkflowState
    timestamp: datetime
    reason: str
    actor: str  # "system" or "human"
    logged: bool = True
    error: Optional[str] = None
```

---

### 4. ApprovalRequest

**Description**: Request for human approval for sensitive actions (Constitution Section 6).

**Triggers**: When SensitiveActionDetector identifies:
- Sending messages (email, Slack, SMS)
- Making payments or financial transactions
- Posting publicly (social media, blog)
- Deleting data (files, records)

**Source of Truth**: Task file metadata + file location in `/Pending_Approval`

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| task_id | str | Yes | ID of task requiring approval |
| action_type | str | Yes | Type of sensitive action (send_message, make_payment, post_public, delete_data) |
| risk_level | str | Yes | low, medium, high |
| justification | str | Yes | Why this action is needed |
| requested_at | datetime | Yes | When approval was requested |
| approved_at | datetime | No | When human approved (null if pending) |
| approved_by | str | No | Who approved (null if pending) |
| decision | str | No | approved, rejected, pending |

**Validation Rules**:
- `action_type` must be in Constitution Section 6 list
- `risk_level` must be low/medium/high
- Task must be in `/Pending_Approval` folder
- If `decision == "approved"`, task must be in `/Approved` folder
- If `decision == "rejected"`, task must be in `/Rejected` folder

**YAML Representation** (in task file):
```yaml
---
id: task-001
state: Pending_Approval
approval_request:
  action_type: send_message
  risk_level: medium
  justification: "Send project update email to stakeholders"
  requested_at: 2026-01-27T10:30:00Z
  approved_at: null
  approved_by: null
  decision: pending
---
```

**Python Representation**:
```python
@dataclass
class ApprovalRequest:
    task_id: str
    action_type: str
    risk_level: str
    justification: str
    requested_at: datetime
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    decision: str = "pending"
```

---

### 5. LogEntry

**Description**: Audit record for all system actions (Constitution Section 8).

**Source of Truth**: Log file (`/Logs/YYYY-MM-DD.log`)

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| timestamp | datetime | Yes | When action occurred (ISO 8601) |
| level | str | Yes | INFO, WARNING, ERROR, CRITICAL |
| action | str | Yes | Action type (transition, approval, error, etc.) |
| task_id | str | No | Associated task ID (if applicable) |
| from_state | WorkflowState | No | Previous state (for transitions) |
| to_state | WorkflowState | No | New state (for transitions) |
| result | str | Yes | success, failure, pending |
| approval_status | str | No | approved, rejected, pending, not_required |
| error | str | No | Error message if result=failure |
| context | dict | No | Additional context (free-form) |

**Log Format** (JSON via structlog):
```json
{
  "timestamp": "2026-01-27T10:30:00Z",
  "level": "INFO",
  "action": "state_transition",
  "task_id": "task-001",
  "from_state": "Plans",
  "to_state": "Pending_Approval",
  "result": "success",
  "approval_status": "pending",
  "error": null,
  "context": {
    "reason": "Planning complete, sensitive action detected",
    "actor": "system"
  }
}
```

**Python Representation**:
```python
@dataclass
class LogEntry:
    timestamp: datetime
    level: str
    action: str
    result: str
    task_id: Optional[str] = None
    from_state: Optional[WorkflowState] = None
    to_state: Optional[WorkflowState] = None
    approval_status: Optional[str] = None
    error: Optional[str] = None
    context: Optional[dict] = None
```

---

## State Transition Matrix

Valid state transitions (enforced by StateMachine):

```
┌──────────────────┐
│      Inbox       │ (Entry point)
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│  Needs_Action    │ (Validated, ready for planning)
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│      Plans       │ ←─────────────┐ (Planning)
└────────┬─────────┘                │
         │                          │
         ↓                          │
┌──────────────────┐                │
│Pending_Approval  │                │ (Human decision required)
└────┬─────────┬───┘                │
     │         │                    │
     ↓         ↓                    │
┌─────────┐ ┌─────────┐            │
│Approved │ │Rejected │────────────┘ (Retry with revised approach)
└────┬────┘ └─────────┘
     │
     ↓
┌──────────────────┐
│       Done       │ (Terminal state)
└──────────────────┘
```

**Transition Rules**:
- Any state → Same state: Allowed (update metadata only, no file move)
- Inbox → Needs_Action: System validates task
- Needs_Action → Plans: System starts planning
- Plans → Pending_Approval: Sensitive action detected
- Plans → Needs_Action: Planning identified missing requirements
- Pending_Approval → Approved: **Human only** (manual file move)
- Pending_Approval → Rejected: **Human only** (manual file move)
- Approved → Done: System execution succeeded
- Approved → Rejected: System execution failed (hard failure)
- Rejected → Inbox: **Human only** (retry with revised approach)
- Done → *: **Forbidden** (terminal state, no exits)

**Forbidden Transitions** (raise InvalidTransitionError):
- Any state → Approved (except from Pending_Approval via human)
- Plans → Done (skips approval)
- Inbox → Approved (skips planning + approval)
- Any state → Done (except from Approved after execution)

---

## Entity Relationships

```
TaskFile ──(1)──(many)─→ StateTransition
    │
    └──(1)──(0..1)──→ ApprovalRequest

StateTransition ──(many)──→ LogEntry (logged)
ApprovalRequest ──(many)──→ LogEntry (logged)
ErrorEvent ──(many)──────→ LogEntry (logged)
```

**Cardinalities**:
- 1 TaskFile can have many StateTransitions (audit history)
- 1 TaskFile can have 0 or 1 ApprovalRequest (only if sensitive action detected)
- All StateTransitions are logged as LogEntries (1:1 correspondence)
- All ApprovalRequests are logged as LogEntries (1:many for request, decision, execution)

---

## Persistence Strategy

### File System Layout

```
/Inbox/task-001.md          → TaskFile (state=Inbox)
/Needs_Action/task-002.md   → TaskFile (state=Needs_Action)
/Plans/task-003.md          → TaskFile (state=Plans)
/Pending_Approval/task-004.md → TaskFile (state=Pending_Approval, approval_request in frontmatter)
/Approved/task-005.md       → TaskFile (state=Approved)
/Rejected/task-006.md       → TaskFile (state=Rejected, error in frontmatter)
/Done/task-007.md           → TaskFile (state=Done)

/Logs/2026-01-27.log        → LogEntry (daily rotation, append-only)
/Logs/2026-01-28.log        → LogEntry
```

### Atomic Operations

All state transitions use `pathlib.Path.rename()` for atomicity:

```python
# Atomic state transition
old_path = Path("/Needs_Action/task-001.md")
new_path = Path("/Plans/task-001.md")
old_path.rename(new_path)  # Atomic on POSIX systems
```

**Guarantees**:
- Either the file moves completely or not at all (no partial state)
- File contents remain intact during move
- No other process sees intermediate state

---

## Query Patterns

### Get Current State
```python
task = TaskFile.from_file(Path("/Plans/task-001.md"))
state = task.derive_state_from_location()  # Returns WorkflowState.PLANS
```

### List Tasks by State
```python
tasks_in_plans = list(Path("/Plans").glob("*.md"))
task_files = [TaskFile.from_file(p) for p in tasks_in_plans]
```

### Audit History for Task
```python
# Read logs, filter by task_id
with open("/Logs/2026-01-27.log") as f:
    entries = [json.loads(line) for line in f if '"task_id": "task-001"' in line]
    transitions = [LogEntry(**e) for e in entries if e['action'] == 'state_transition']
```

### Check Approval Status
```python
task = TaskFile.from_file(Path("/Pending_Approval/task-001.md"))
if task.state == WorkflowState.PENDING_APPROVAL:
    approval = task.metadata.get('approval_request', {})
    decision = approval.get('decision', 'pending')
```

---

## Constitutional Compliance

**Section 2 (Source of Truth)**: All entities derive from files. No hidden state.
- TaskFile: File location + YAML frontmatter
- StateTransition: Log file entries
- ApprovalRequest: Task file metadata
- LogEntry: Append-only log files

**Section 4 (File-Driven Control Plane)**: File moves = state transitions.
- WorkflowState enum matches folder names exactly
- pathlib.Path.rename() ensures atomic transitions

**Section 8 (Auditability)**: Every action logged.
- All StateTransitions → LogEntry
- All ApprovalRequests → LogEntry
- All errors → LogEntry

**Section 13 (Completion Definition)**: Task complete only if verifiable.
- TaskFile in /Done folder (file exists)
- State metadata matches folder (files in correct folders)
- Transition logged (logs written)
- State verifiable from disk (reconstructable)

---

*All entities designed for file-first, auditable, constitutional compliance.*

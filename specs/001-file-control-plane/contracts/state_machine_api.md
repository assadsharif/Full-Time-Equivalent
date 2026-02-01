# State Machine API Contract

**Feature**: File-Driven Control Plane
**Module**: `src/control_plane/state_machine.py`
**Created**: 2026-01-27

---

## Overview

The State Machine API provides core functionality for managing task workflow state transitions. All operations follow Constitutional Section 4 requirements (atomic file operations, valid transitions).

---

## StateMachine Class

### `validate_transition(from_state: WorkflowState, to_state: WorkflowState) -> bool`

Validates whether a state transition is allowed per the transition matrix.

**Parameters**:
- `from_state` (WorkflowState): Current state
- `to_state` (WorkflowState): Desired state

**Returns**: `bool`
- `True` if transition is allowed
- `False` if transition is forbidden

**Raises**: None (returns False for invalid transitions)

**Example**:
```python
sm = StateMachine()
is_valid = sm.validate_transition(WorkflowState.PLANS, WorkflowState.PENDING_APPROVAL)
# Returns: True (valid transition)

is_valid = sm.validate_transition(WorkflowState.PLANS, WorkflowState.APPROVED)
# Returns: False (skips approval requirement)
```

**Constitutional Mapping**: Section 4 (File-Driven Control Plane) - enforces valid transitions

---

### `execute_transition(task_file: TaskFile, to_state: WorkflowState) -> StateTransition`

Executes an atomic state transition by moving task file to new folder.

**Parameters**:
- `task_file` (TaskFile): Task to transition
- `to_state` (WorkflowState): Target state

**Returns**: `StateTransition`
- Contains: transition_id, task_id, from_state, to_state, timestamp, reason, actor, logged

**Raises**:
- `InvalidTransitionError`: If transition not allowed (e.g., Plans → Approved)
- `FileOperationError`: If file move fails (disk full, permissions)
- `ApprovalRequiredError`: If attempting to execute sensitive action without approval

**Side Effects**:
1. Moves task file from current folder to target folder (atomic)
2. Updates task file metadata (state, modified_at)
3. Writes log entry to `/Logs/YYYY-MM-DD.log`
4. Verifies state consistency (file location matches metadata)

**Example**:
```python
task = TaskFile.from_file(Path("/Inbox/task-001.md"))
transition = sm.execute_transition(task, WorkflowState.NEEDS_ACTION)

print(transition.from_state)  # WorkflowState.INBOX
print(transition.to_state)    # WorkflowState.NEEDS_ACTION
print(transition.logged)      # True
# File now at: /Needs_Action/task-001.md
```

**Performance**: < 100ms (p95) per Constitutional requirement

**Constitutional Mapping**:
- Section 2 (Source of Truth): File location determines state
- Section 4 (File-Driven Control Plane): Atomic file move
- Section 5 (Reasoning Discipline): Read → Plan → Act → Write → Verify loop
- Section 8 (Auditability): Transition logged

---

### `get_current_state(task_id: str) -> WorkflowState`

Queries current state of a task by finding its file location.

**Parameters**:
- `task_id` (str): Unique task identifier

**Returns**: `WorkflowState`
- Current state derived from file location

**Raises**:
- `FileNotFoundError`: If task file not found in any workflow folder

**Example**:
```python
state = sm.get_current_state("task-001")
print(state)  # WorkflowState.NEEDS_ACTION
```

**Performance**: < 10ms (p95) per Constitutional requirement

**Constitutional Mapping**: Section 2 (Source of Truth) - state derived from file location

---

### `list_tasks_in_state(state: WorkflowState) -> List[TaskFile]`

Lists all tasks in a specific workflow state.

**Parameters**:
- `state` (WorkflowState): State to query

**Returns**: `List[TaskFile]`
- All tasks currently in the specified state

**Example**:
```python
pending = sm.list_tasks_in_state(WorkflowState.PENDING_APPROVAL)
print(f"Tasks awaiting approval: {len(pending)}")
for task in pending:
    print(f"  - {task.id}")
```

**Performance**: < 100ms for 100s of tasks

**Constitutional Mapping**: Section 2 (Source of Truth) - query from file system

---

## Transition Matrix

### Valid Transitions

| From State | To State | Actor | Condition |
|------------|----------|-------|-----------|
| Inbox | Needs_Action | System | Task validated |
| Needs_Action | Plans | System | Planning started |
| Plans | Pending_Approval | System | Sensitive action detected |
| Plans | Needs_Action | System | Clarifications needed |
| Pending_Approval | Approved | **Human** | Manual file move |
| Pending_Approval | Rejected | **Human** | Manual file move |
| Approved | Done | System | Execution succeeded |
| Approved | Rejected | System | Execution failed |
| Rejected | Inbox | **Human** | Retry with revised approach |

### Forbidden Transitions

| From State | To State | Reason |
|------------|----------|--------|
| Plans | Approved | Skips approval requirement (Constitutional violation) |
| Inbox | Approved | Skips planning + approval (Constitutional violation) |
| Plans | Done | Skips approval + execution (Constitutional violation) |
| Any | Approved | Only human can approve (except from Pending_Approval) |
| Done | Any | Terminal state (no exits allowed) |

---

## Error Responses

### `InvalidTransitionError`

**Trigger**: Attempted transition not in allowed matrix

**Fields**:
- `from_state` (WorkflowState): Current state
- `to_state` (WorkflowState): Attempted target state
- `message` (str): Human-readable error message

**Example**:
```python
try:
    sm.execute_transition(task, WorkflowState.APPROVED)
except InvalidTransitionError as e:
    print(e.message)
    # "Invalid transition: Plans → Approved (skips approval requirement)"
```

**Logged**: Yes (level: ERROR)

---

### `ApprovalRequiredError`

**Trigger**: Attempted to execute sensitive action without approval

**Fields**:
- `task_id` (str): Task that requires approval
- `action_type` (str): Type of sensitive action
- `current_state` (WorkflowState): Current state (not Approved)
- `message` (str): Human-readable error message

**Example**:
```python
try:
    sm.execute_transition(task, WorkflowState.DONE)
except ApprovalRequiredError as e:
    print(e.message)
    # "Task task-001 requires approval (action: send_message, state: Plans)"
```

**Logged**: Yes (level: CRITICAL - constitutional violation)

---

### `FileOperationError`

**Trigger**: File system operation failed (disk full, permissions, etc.)

**Fields**:
- `task_id` (str): Task that failed to move
- `from_path` (Path): Source file path
- `to_path` (Path): Destination file path
- `os_error` (OSError): Original OS-level error
- `message` (str): Human-readable error message

**Example**:
```python
try:
    sm.execute_transition(task, WorkflowState.NEEDS_ACTION)
except FileOperationError as e:
    print(e.message)
    # "Failed to move task-001: [Errno 28] No space left on device"
```

**Logged**: Yes (level: ERROR)
**Recovery**: Task remains in original state (atomic guarantee)

---

## Concurrency Model

**Constraint**: Single-process access (Constitutional requirement)

**Guarantees**:
- No concurrent writes to same task file
- pathlib.Path.rename() is atomic (POSIX)
- File either moves completely or not at all

**Limitations**:
- No multi-process support in Phase 1
- Manual file moves by human may race with system

**Future Work** (Phase 2):
- File locking for multi-process access
- Optimistic concurrency with mtime checks

---

## Performance Guarantees

Per Constitutional requirements:

| Operation | Performance Target (p95) |
|-----------|--------------------------|
| `validate_transition()` | < 1ms |
| `execute_transition()` | < 100ms |
| `get_current_state()` | < 10ms |
| `list_tasks_in_state()` | < 100ms (for 100s of tasks) |

---

## Constitutional Compliance

**Section 2 (Source of Truth)**:
- State derived from file location
- No hidden in-memory state
- Fully reconstructable from disk

**Section 4 (File-Driven Control Plane)**:
- 8 workflow folders enforced
- File moves = state transitions
- Atomic operations (pathlib.Path.rename)

**Section 5 (Reasoning Discipline)**:
- Read task file
- Validate transition
- Plan file move
- Execute move
- Write log
- Verify state

**Section 8 (Auditability)**:
- All transitions logged
- Log entries contain: timestamp, action, task_id, from_state, to_state, result

**Section 9 (Error Handling)**:
- All exceptions logged
- Partial completion preferred (task not lost on error)
- Bounded retry (max 3 attempts)

---

*API designed for constitutional compliance and operational reliability.*

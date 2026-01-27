# Logger API Contract

**Feature**: File-Driven Control Plane
**Module**: `src/control_plane/logger.py`
**Created**: 2026-01-27

---

## Overview

The Logger API implements Constitutional Section 8 requirements (Auditability & Logging). It provides structured, append-only logging for all system actions.

---

## AuditLogger Class

### `log_transition(transition: StateTransition) -> None`

Logs a state transition to the append-only audit trail.

**Parameters**:
- `transition` (StateTransition): Transition to log

**Returns**: None

**Side Effects**:
- Appends JSON entry to `/Logs/YYYY-MM-DD.log`
- Never modifies existing log entries (append-only)

**Log Entry Format**:
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
    "reason": "Sensitive action detected",
    "actor": "system"
  }
}
```

**Example**:
```python
logger = AuditLogger()
transition = StateTransition(
    transition_id="trans-001",
    task_id="task-001",
    from_state=WorkflowState.PLANS,
    to_state=WorkflowState.PENDING_APPROVAL,
    timestamp=datetime.now(),
    reason="Sensitive action detected",
    actor="system"
)
logger.log_transition(transition)
# Entry appended to /Logs/2026-01-27.log
```

**Performance**: < 50ms (p95) per Constitutional requirement

**Constitutional Mapping**: Section 8 (Auditability) - "every action logged"

---

### `log_approval_request(request: ApprovalRequest) -> None`

Logs an approval request to the audit trail.

**Parameters**:
- `request` (ApprovalRequest): Approval request to log

**Returns**: None

**Log Entry Format**:
```json
{
  "timestamp": "2026-01-27T10:30:00Z",
  "level": "INFO",
  "action": "approval_request",
  "task_id": "task-001",
  "result": "pending",
  "approval_status": "pending",
  "context": {
    "action_type": "send_message",
    "risk_level": "medium",
    "justification": "Send project update email to stakeholders"
  }
}
```

**Example**:
```python
request = ApprovalRequest(
    task_id="task-001",
    action_type="send_message",
    risk_level="medium",
    justification="Send project update email",
    requested_at=datetime.now()
)
logger.log_approval_request(request)
```

**Constitutional Mapping**: Section 7 (HITL) - "file-based approval system must log all requests"

---

### `log_error(task_id: str, error: Exception, context: dict) -> None`

Logs an error with full context to the audit trail.

**Parameters**:
- `task_id` (str): Task that encountered error
- `error` (Exception): Exception object
- `context` (dict): Additional context (from_state, to_state, etc.)

**Returns**: None

**Log Entry Format**:
```json
{
  "timestamp": "2026-01-27T10:30:00Z",
  "level": "ERROR",
  "action": "error",
  "task_id": "task-001",
  "result": "failure",
  "error": "InvalidTransitionError: Plans → Approved (skips approval)",
  "context": {
    "from_state": "Plans",
    "to_state": "Approved",
    "exception_type": "InvalidTransitionError",
    "stack_trace": "..."
  }
}
```

**Example**:
```python
try:
    sm.execute_transition(task, WorkflowState.APPROVED)
except InvalidTransitionError as e:
    logger.log_error(
        task_id="task-001",
        error=e,
        context={
            "from_state": "Plans",
            "to_state": "Approved"
        }
    )
```

**Constitutional Mapping**: Section 9 (Error Handling) - "errors never hidden"

---

### `query_logs(start_date: date, end_date: date, task_id: Optional[str] = None) -> List[LogEntry]`

Queries audit logs for a date range, optionally filtered by task.

**Parameters**:
- `start_date` (date): Start of date range (inclusive)
- `end_date` (date): End of date range (inclusive)
- `task_id` (str, optional): Filter by specific task

**Returns**: `List[LogEntry]`
- All log entries matching criteria

**Example**:
```python
from datetime import date

# Get all logs for task-001 on 2026-01-27
entries = logger.query_logs(
    start_date=date(2026, 1, 27),
    end_date=date(2026, 1, 27),
    task_id="task-001"
)

for entry in entries:
    print(f"{entry.timestamp} - {entry.action}: {entry.result}")
```

**Performance**: < 1 second for 10k entries

**Constitutional Mapping**: Section 8 (Auditability) - enables audit trail inspection

---

### `verify_log_integrity() -> bool`

Verifies that logs have not been tampered with (append-only requirement).

**Parameters**: None

**Returns**: `bool`
- `True` if logs are intact (append-only, no modifications)
- `False` if tampering detected

**Verification Method**:
1. Compute hash of each log entry
2. Compare with stored integrity hashes
3. Verify entries are in chronological order
4. Verify no entries deleted (sequence numbers intact)

**Example**:
```python
is_valid = logger.verify_log_integrity()
if not is_valid:
    # CRITICAL: Log tampering detected
    # Halt all operations per Constitutional override (Section 14)
    raise LogIntegrityViolation("Append-only logs have been modified")
```

**Constitutional Mapping**: Section 8 (Auditability) - "append-only, never modified"

---

## Log Entry Format

### Standard Fields

All log entries contain these fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| timestamp | datetime | Yes | When action occurred (ISO 8601) |
| level | str | Yes | INFO, WARNING, ERROR, CRITICAL |
| action | str | Yes | Action type (state_transition, approval_request, error, etc.) |
| task_id | str | No | Associated task ID (if applicable) |
| result | str | Yes | success, failure, pending |
| error | str | No | Error message if result=failure |
| context | dict | No | Additional context (free-form) |

### Action-Specific Fields

**State Transition**:
```json
{
  "action": "state_transition",
  "from_state": "Plans",
  "to_state": "Pending_Approval",
  "approval_status": "pending"
}
```

**Approval Request**:
```json
{
  "action": "approval_request",
  "approval_status": "pending",
  "context": {
    "action_type": "send_message",
    "risk_level": "medium",
    "justification": "..."
  }
}
```

**Approval Decision**:
```json
{
  "action": "approval_decision",
  "approval_status": "approved",
  "context": {
    "approved_by": "human",
    "approved_at": "2026-01-27T11:00:00Z"
  }
}
```

**Error**:
```json
{
  "action": "error",
  "result": "failure",
  "error": "FileOperationError: Disk full",
  "context": {
    "exception_type": "FileOperationError",
    "from_state": "Plans",
    "to_state": "Pending_Approval"
  }
}
```

---

## Log Levels

### INFO

Normal operations that require auditing:
- State transitions
- Approval requests
- Task creation
- Task completion

### WARNING

Recoverable issues that require attention:
- Retry attempts
- Approaching resource limits
- Deprecated feature usage

### ERROR

Failures that prevent operation completion:
- Invalid transitions
- File operation errors
- YAML parsing errors
- State inconsistencies

### CRITICAL

Constitutional violations and system integrity issues:
- Attempted approval bypass
- Log tampering detected
- Constitutional override invoked

---

## Log Storage

### File Organization

```
/Logs/
├── 2026-01-27.log    # Daily rotation
├── 2026-01-28.log
├── 2026-01-29.log
└── integrity.json    # Hash chain for verification
```

### Log Rotation

- **Frequency**: Daily (at midnight)
- **Retention**: 90 days (configurable)
- **Cleanup**: Automated deletion of logs older than retention period

### Log Format

- **Format**: JSON (one entry per line)
- **Encoding**: UTF-8
- **Line ending**: Unix (LF)

**Example Log File**:
```
{"timestamp": "2026-01-27T10:00:00Z", "level": "INFO", "action": "state_transition", ...}
{"timestamp": "2026-01-27T10:05:00Z", "level": "INFO", "action": "approval_request", ...}
{"timestamp": "2026-01-27T10:30:00Z", "level": "INFO", "action": "approval_decision", ...}
```

---

## Log Integrity

### Hash Chain

Each log entry includes hash of previous entry:

```json
{
  "timestamp": "2026-01-27T10:00:00Z",
  "level": "INFO",
  "action": "state_transition",
  "task_id": "task-001",
  "previous_hash": "abc123...",
  "hash": "def456..."
}
```

### Verification Algorithm

```python
def verify_log_integrity():
    """Verify log hash chain is intact."""
    previous_hash = None
    for entry in read_log_entries():
        if entry['previous_hash'] != previous_hash:
            return False  # Chain broken
        computed_hash = compute_hash(entry)
        if entry['hash'] != computed_hash:
            return False  # Entry modified
        previous_hash = entry['hash']
    return True
```

---

## Structured Logging Configuration

### structlog Setup

```python
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
```

### Context Binding

Automatically add task_id to all log entries:

```python
logger = structlog.get_logger()
logger = logger.bind(task_id="task-001")

logger.info("state_transition", from_state="Plans", to_state="Pending_Approval")
# Output: {"task_id": "task-001", "action": "state_transition", ...}
```

---

## Error Responses

### `LogWriteError`

**Trigger**: Failed to write log entry (disk full, permissions, etc.)

**Fields**:
- `log_file` (Path): Log file that failed to write
- `entry` (LogEntry): Entry that failed to write
- `os_error` (OSError): Original OS-level error
- `message` (str): Human-readable error message

**Recovery**:
1. Write emergency log to stderr (console)
2. Mark task with "unlogged_transition" flag
3. Retry on next state change

**Example**:
```python
try:
    logger.log_transition(transition)
except LogWriteError as e:
    print(f"CRITICAL: Log write failed - {e.message}", file=sys.stderr)
    task.metadata['unlogged_transition'] = {
        'transition_id': transition.transition_id,
        'timestamp': transition.timestamp.isoformat()
    }
```

---

## Performance Guarantees

Per Constitutional requirements:

| Operation | Performance Target (p95) |
|-----------|--------------------------|
| `log_transition()` | < 50ms |
| `log_approval_request()` | < 50ms |
| `log_error()` | < 50ms |
| `query_logs()` | < 1 second (10k entries) |
| `verify_log_integrity()` | < 5 seconds (100k entries) |

---

## Constitutional Compliance

**Section 8 (Auditability & Logging)**:
- Every action logged with: timestamp, action type, triggering file, result, approval status
- Logs are append-only (never modified)
- Logs are structured (JSON) for programmatic analysis
- Logs are verifiable (hash chain integrity)

**Section 9 (Error Handling)**:
- All errors logged with full context
- Stack traces included for debugging
- Errors never hidden from logs

**Section 2 (Source of Truth)**:
- Logs stored in file system (/Logs/)
- Logs fully reconstructable from disk
- No hidden logging state in memory

---

## Example: Complete Audit Trail

Task lifecycle from creation to completion:

```json
{"timestamp": "2026-01-27T10:00:00Z", "level": "INFO", "action": "task_created", "task_id": "task-001"}
{"timestamp": "2026-01-27T10:01:00Z", "level": "INFO", "action": "state_transition", "task_id": "task-001", "from_state": "Inbox", "to_state": "Needs_Action"}
{"timestamp": "2026-01-27T10:05:00Z", "level": "INFO", "action": "state_transition", "task_id": "task-001", "from_state": "Needs_Action", "to_state": "Plans"}
{"timestamp": "2026-01-27T10:30:00Z", "level": "INFO", "action": "state_transition", "task_id": "task-001", "from_state": "Plans", "to_state": "Pending_Approval"}
{"timestamp": "2026-01-27T10:30:00Z", "level": "INFO", "action": "approval_request", "task_id": "task-001", "approval_status": "pending"}
{"timestamp": "2026-01-27T11:00:00Z", "level": "INFO", "action": "approval_decision", "task_id": "task-001", "approval_status": "approved", "context": {"approved_by": "human"}}
{"timestamp": "2026-01-27T11:00:00Z", "level": "INFO", "action": "state_transition", "task_id": "task-001", "from_state": "Pending_Approval", "to_state": "Approved"}
{"timestamp": "2026-01-27T11:05:00Z", "level": "INFO", "action": "task_execution_started", "task_id": "task-001"}
{"timestamp": "2026-01-27T11:10:00Z", "level": "INFO", "action": "task_execution_completed", "task_id": "task-001", "result": "success"}
{"timestamp": "2026-01-27T11:10:00Z", "level": "INFO", "action": "state_transition", "task_id": "task-001", "from_state": "Approved", "to_state": "Done"}
```

---

*API designed for complete auditability and constitutional compliance.*

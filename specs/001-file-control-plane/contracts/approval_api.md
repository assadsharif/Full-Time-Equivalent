# Approval API Contract

**Feature**: File-Driven Control Plane
**Module**: `src/control_plane/approval.py`
**Created**: 2026-01-27

---

## Overview

The Approval API implements Constitutional Section 6-7 requirements (Autonomy Boundaries & HITL). It detects sensitive actions and enforces human approval before execution.

---

## ApprovalChecker Class

### `is_sensitive_action(task_content: str) -> bool`

Detects whether task content contains sensitive actions requiring approval.

**Parameters**:
- `task_content` (str): Full task content (markdown body)

**Returns**: `bool`
- `True` if sensitive action detected
- `False` otherwise

**Sensitive Action Patterns** (per Constitution Section 6):
- Send message: `send email`, `send message`, `post to slack`
- Make payment: `make payment`, `transfer funds`, `charge card`
- Post publicly: `post to twitter`, `publish blog`, `send tweet`
- Delete data: `delete`, `remove`, `drop table`

**Example**:
```python
checker = ApprovalChecker()

content1 = "Send project update email to stakeholders"
is_sensitive = checker.is_sensitive_action(content1)
# Returns: True (contains "send email")

content2 = "Read configuration file and validate settings"
is_sensitive = checker.is_sensitive_action(content2)
# Returns: False (no sensitive actions)
```

**Constitutional Mapping**: Section 6 (Autonomy Boundaries) - defines sensitive actions

---

### `requires_approval(task_file: TaskFile) -> bool`

Determines whether a task requires human approval before execution.

**Parameters**:
- `task_file` (TaskFile): Task to check

**Returns**: `bool`
- `True` if approval required
- `False` if task can proceed autonomously

**Logic**:
1. Check if task content contains sensitive action patterns
2. Check if task explicitly marked as requiring approval in metadata
3. Check risk level (high risk always requires approval)

**Example**:
```python
task = TaskFile.from_file(Path("/Plans/task-001.md"))
requires_approval = checker.requires_approval(task)

if requires_approval:
    # Move to /Pending_Approval, create ApprovalRequest
    pass
```

**Constitutional Mapping**: Section 6-7 (Autonomy & HITL) - determines approval requirement

---

### `is_approved(task_file: TaskFile) -> bool`

Checks whether a task has been approved by human.

**Parameters**:
- `task_file` (TaskFile): Task to check

**Returns**: `bool`
- `True` if task is in `/Approved` folder
- `False` otherwise

**Logic**:
1. Check file location (must be in `/Approved` folder)
2. Check approval_request.decision field (must be "approved")
3. Check approval_request.approved_at timestamp (must be set)

**Example**:
```python
task = TaskFile.from_file(Path("/Approved/task-001.md"))
is_approved = checker.is_approved(task)
# Returns: True (file in /Approved folder)

task2 = TaskFile.from_file(Path("/Pending_Approval/task-002.md"))
is_approved = checker.is_approved(task2)
# Returns: False (still pending)
```

**Constitutional Mapping**: Section 7 (HITL) - "No action without file in /Approved"

---

### `block_unapproved_action(task_file: TaskFile) -> None`

Blocks execution of sensitive action if not approved. Raises exception if check fails.

**Parameters**:
- `task_file` (TaskFile): Task attempting execution

**Returns**: None (raises exception if blocked)

**Raises**:
- `ApprovalRequiredError`: If task requires approval but is not approved

**Example**:
```python
try:
    checker.block_unapproved_action(task)
    # Safe to proceed
    execute_task(task)
except ApprovalRequiredError as e:
    print(f"Blocked: {e.message}")
    # Move task to /Pending_Approval
```

**Side Effects**:
- Logs attempted bypass (level: CRITICAL)
- Increments constitutional violation counter

**Constitutional Mapping**: Section 6-7 (Autonomy & HITL) - enforces approval requirement

---

### `create_approval_request(task_file: TaskFile, action_type: str, risk_level: str, justification: str) -> ApprovalRequest`

Creates approval request and adds to task metadata.

**Parameters**:
- `task_file` (TaskFile): Task requiring approval
- `action_type` (str): Type of sensitive action (send_message, make_payment, post_public, delete_data)
- `risk_level` (str): Risk level (low, medium, high)
- `justification` (str): Why this action is needed

**Returns**: `ApprovalRequest`

**Side Effects**:
1. Adds `approval_request` to task file YAML frontmatter
2. Moves task to `/Pending_Approval` folder
3. Logs approval request to `/Logs/`

**Example**:
```python
request = checker.create_approval_request(
    task_file=task,
    action_type="send_message",
    risk_level="medium",
    justification="Send weekly project status to stakeholders"
)

print(request.requested_at)  # 2026-01-27T10:30:00Z
print(request.decision)      # "pending"
# Task now in /Pending_Approval/task-001.md
```

**Constitutional Mapping**: Section 7 (HITL) - creates approval request

---

## SensitiveActionDetector Class

### `detect_patterns(content: str) -> List[str]`

Detects all sensitive action patterns in content.

**Parameters**:
- `content` (str): Text to scan

**Returns**: `List[str]`
- List of detected action types (send_message, make_payment, etc.)

**Example**:
```python
detector = SensitiveActionDetector()
content = "Send email notification and delete old logs"
patterns = detector.detect_patterns(content)
# Returns: ["send_message", "delete_data"]
```

---

### `classify_risk_level(action_types: List[str]) -> str`

Classifies risk level based on detected actions.

**Parameters**:
- `action_types` (List[str]): Detected action types

**Returns**: `str`
- Risk level: "low", "medium", or "high"

**Risk Classification**:
- Low: Read-only operations, safe actions
- Medium: Send message, create resource
- High: Delete data, make payment, post publicly

**Example**:
```python
risk = detector.classify_risk_level(["send_message"])
# Returns: "medium"

risk = detector.classify_risk_level(["delete_data", "make_payment"])
# Returns: "high" (highest risk wins)
```

---

## ApprovalRequest Entity

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| task_id | str | Yes | ID of task requiring approval |
| action_type | str | Yes | Type of sensitive action |
| risk_level | str | Yes | low, medium, high |
| justification | str | Yes | Why action is needed |
| requested_at | datetime | Yes | When approval was requested |
| approved_at | datetime | No | When human approved (null if pending) |
| approved_by | str | No | Who approved (null if pending) |
| decision | str | Yes | approved, rejected, pending |

### YAML Representation

```yaml
approval_request:
  action_type: send_message
  risk_level: medium
  justification: "Send project update email to stakeholders"
  requested_at: 2026-01-27T10:30:00Z
  approved_at: null
  approved_by: null
  decision: pending
```

---

## Approval Workflow

### Step 1: Detection (Automatic)

```python
# System detects sensitive action during planning
task = TaskFile.from_file(Path("/Plans/task-001.md"))
if checker.is_sensitive_action(task.content):
    # Create approval request
    request = checker.create_approval_request(
        task_file=task,
        action_type="send_message",
        risk_level="medium",
        justification="Send weekly status email"
    )
    # Task automatically moved to /Pending_Approval/
```

### Step 2: Human Review (Manual)

```bash
# Human reviews task
cat /Pending_Approval/task-001.md

# Human decides: approve or reject
# Approve: mv /Pending_Approval/task-001.md /Approved/task-001.md
# Reject:  mv /Pending_Approval/task-001.md /Rejected/task-001.md
```

### Step 3: Execution Gate (Automatic)

```python
# System checks approval before execution
task = TaskFile.from_file(Path("/Approved/task-001.md"))

try:
    checker.block_unapproved_action(task)
    # Approved: proceed with execution
    execute_sensitive_action(task)
except ApprovalRequiredError:
    # Not approved: halt execution
    print("Task blocked: approval required")
```

---

## Error Responses

### `ApprovalRequiredError`

**Fields**:
- `task_id` (str): Task that requires approval
- `action_type` (str): Type of sensitive action
- `current_state` (WorkflowState): Current state (not Approved)
- `message` (str): Human-readable error message

**Example**:
```json
{
  "error": "ApprovalRequiredError",
  "task_id": "task-001",
  "action_type": "send_message",
  "current_state": "Plans",
  "message": "Task requires approval before execution (action: send_message)"
}
```

**Logged**: Yes (level: CRITICAL - constitutional violation)

---

## Constitutional Compliance

**Section 6 (Autonomy Boundaries)**:
- Defines sensitive actions requiring approval:
  - Sending messages (email, Slack, SMS)
  - Making payments or financial transactions
  - Posting publicly (social media, blog)
  - Deleting data (files, database records)

**Section 7 (Human-in-the-Loop)**:
- File-based approval: Human moves file from `/Pending_Approval` to `/Approved`
- No action without file in `/Approved`
- System logs all approval requests and decisions

**Section 8 (Auditability)**:
- All approval requests logged
- All approval decisions logged
- All attempted bypasses logged (constitutional violations)

**Section 11 (No Spec Drift)**:
- Sensitive action list taken directly from Constitution
- No additional actions added without spec update

---

## Sensitive Action Patterns

### Send Message

**Patterns**:
- `send email`, `send message`, `send notification`
- `post to slack`, `post to teams`, `send to channel`
- `send sms`, `text message`

**Risk Level**: Medium

---

### Make Payment

**Patterns**:
- `make payment`, `send payment`, `transfer funds`
- `charge card`, `process payment`, `withdraw`
- `invoice`, `bill customer`

**Risk Level**: High

---

### Post Publicly

**Patterns**:
- `post to twitter`, `send tweet`, `post to x`
- `publish blog`, `publish article`, `post to medium`
- `post to linkedin`, `share publicly`

**Risk Level**: High

---

### Delete Data

**Patterns**:
- `delete`, `remove`, `drop`
- `drop table`, `truncate`, `purge`
- `delete file`, `remove record`, `erase`

**Risk Level**: High

---

## Performance Guarantees

| Operation | Performance Target (p95) |
|-----------|--------------------------|
| `is_sensitive_action()` | < 10ms |
| `requires_approval()` | < 10ms |
| `is_approved()` | < 5ms |
| `block_unapproved_action()` | < 5ms |
| `create_approval_request()` | < 50ms |

---

*API designed to enforce constitutional approval requirements and prevent unauthorized sensitive actions.*

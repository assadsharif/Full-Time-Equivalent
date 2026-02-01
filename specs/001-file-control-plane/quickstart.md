# Quickstart Guide: File-Driven Control Plane

**Feature**: File-Driven Control Plane
**Branch**: `001-file-control-plane`
**Created**: 2026-01-27

---

## Prerequisites

- Python 3.11 or higher
- Git
- Virtual environment tool (venv, virtualenv, or conda)
- Text editor or IDE

---

## Setup

### 1. Clone Repository and Checkout Feature Branch

```bash
# Clone repository (if not already cloned)
git clone <repository-url>
cd <repository-directory>

# Checkout feature branch
git checkout 001-file-control-plane
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install package in editable mode with dev dependencies
pip install -e ".[dev]"

# This installs:
# - watchdog (file system monitoring)
# - PyYAML (YAML parsing)
# - structlog (structured logging)
# - pytest (testing)
# - pytest-cov (coverage reporting)
```

### 4. Verify Workflow Folders

```bash
# Check that all 8 workflow folders exist
ls -la Inbox Needs_Action Plans Pending_Approval Approved Rejected Done Logs

# Expected output:
# Inbox/.gitkeep
# Needs_Action/.gitkeep
# Plans/.gitkeep
# Pending_Approval/.gitkeep
# Approved/.gitkeep
# Rejected/.gitkeep
# Done/.gitkeep
# Logs/.gitkeep
```

### 5. Run Tests

```bash
# Run all tests with coverage
pytest tests/ -v --cov=src/control_plane

# Run specific test suite
pytest tests/unit/ -v
pytest tests/integration/ -v

# Run with detailed output
pytest tests/ -vv -s
```

---

## Basic Usage

### Example 1: Create and Transition a Task

```python
from pathlib import Path
from control_plane import StateMachine, TaskFile, WorkflowState

# Initialize state machine
sm = StateMachine()

# Create a new task in /Inbox
task = TaskFile.create(
    id="task-001",
    description="Implement user authentication",
    priority="P1",
    content="""
# Task: Implement user authentication

## Description
Add JWT-based authentication to the API.

## Acceptance Criteria
- [ ] User can register with email/password
- [ ] User can login and receive JWT token
- [ ] Protected endpoints validate JWT
- [ ] Tokens expire after 24 hours
"""
)

# Task is now in /Inbox/task-001.md
print(f"Task created: {task.file_path}")
print(f"Current state: {task.state}")  # WorkflowState.INBOX

# Validate task → move to /Needs_Action
transition = sm.execute_transition(task, WorkflowState.NEEDS_ACTION)
print(f"Transition logged: {transition.logged}")
# Result: File moved from /Inbox/task-001.md to /Needs_Action/task-001.md
# Log entry created in /Logs/2026-01-27.log

# Query current state
current_state = sm.get_current_state("task-001")
print(f"Current state: {current_state}")  # WorkflowState.NEEDS_ACTION
```

### Example 2: Check Approval Requirements

```python
from control_plane import ApprovalChecker, TaskFile

# Load task
task = TaskFile.from_file(Path("/Plans/task-002.md"))

# Check if task contains sensitive action
checker = ApprovalChecker()
is_sensitive = checker.is_sensitive_action(task.content)

if is_sensitive:
    print("⚠️ Task requires human approval")
    # System will automatically move task to /Pending_Approval
    # Human must manually move file to /Approved or /Rejected
else:
    print("✓ Task can proceed without approval")
```

### Example 3: Query Task History

```python
from control_plane import AuditLogger
from datetime import date

# Query logs for specific task
logger = AuditLogger()
entries = logger.query_logs(
    start_date=date(2026, 1, 27),
    end_date=date(2026, 1, 27),
    task_id="task-001"
)

# Print audit trail
for entry in entries:
    print(f"{entry.timestamp} - {entry.action}: {entry.from_state} → {entry.to_state}")
```

### Example 4: List Tasks by State

```python
from control_plane import StateMachine, WorkflowState

sm = StateMachine()

# Get all tasks waiting for approval
pending_tasks = sm.list_tasks_in_state(WorkflowState.PENDING_APPROVAL)

print(f"Tasks awaiting approval: {len(pending_tasks)}")
for task in pending_tasks:
    approval = task.metadata.get('approval_request', {})
    print(f"  - {task.id}: {approval.get('action_type')} (risk: {approval.get('risk_level')})")
```

---

## CLI Usage

### Create a Task

```bash
# Create task using CLI
control-plane create task-003 \
  --priority P2 \
  --description "Add rate limiting to API" \
  --content "$(cat task-template.md)"

# Result: Task created in /Inbox/task-003.md
```

### Transition Task

```bash
# Move task to next state
control-plane transition task-003 Needs_Action

# Result: File moved from /Inbox/task-003.md to /Needs_Action/task-003.md
# Log entry created
```

### List Tasks

```bash
# List all tasks in a specific state
control-plane list Pending_Approval

# Output:
# Tasks in Pending_Approval:
# - task-004: Send notification email (medium risk)
# - task-005: Delete archived data (high risk)
```

### Query Logs

```bash
# View logs for specific task
control-plane logs task-001

# Output: (JSON formatted)
# {"timestamp": "2026-01-27T10:00:00Z", "action": "state_transition", ...}
# {"timestamp": "2026-01-27T10:30:00Z", "action": "state_transition", ...}
```

### Verify State Consistency

```bash
# Check that all tasks have consistent state (file location matches metadata)
control-plane verify

# Output:
# ✓ All tasks have consistent state
# ✓ Log integrity verified
# ✓ No orphaned files
```

---

## Task File Format

### Template

```markdown
---
id: task-001
state: Inbox
priority: P1
created_at: 2026-01-27T10:00:00Z
modified_at: 2026-01-27T10:00:00Z
metadata:
  assigned_to: null
  tags: [feature, backend]
  estimated_hours: 8
---

# Task: [Title]

## Description
[Detailed description of what needs to be done]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Notes
[Additional notes, context, or links]
```

### With Approval Request

```markdown
---
id: task-002
state: Pending_Approval
priority: P1
created_at: 2026-01-27T10:00:00Z
modified_at: 2026-01-27T10:30:00Z
approval_request:
  action_type: send_message
  risk_level: medium
  justification: "Send project update email to stakeholders"
  requested_at: 2026-01-27T10:30:00Z
  approved_at: null
  approved_by: null
  decision: pending
metadata:
  tags: [communication]
---

# Task: Send project update email

## Description
Send weekly project status email to all stakeholders.

## Email Content
[Email content here...]

## Approval Required
⚠️ This task requires human approval before execution (sensitive action: send_message)
```

---

## Human Approval Workflow

### Step 1: Task Requests Approval

When a task with sensitive action is planned, the system automatically:
1. Moves task file to `/Pending_Approval/`
2. Adds `approval_request` to YAML frontmatter
3. Logs approval request to `/Logs/`

```bash
# System detects sensitive action
control-plane transition task-002 Plans
# → System detects "send email" in task
# → System automatically moves to /Pending_Approval/
```

### Step 2: Human Reviews Task

```bash
# View pending approvals
control-plane list Pending_Approval

# Read task details
cat Pending_Approval/task-002.md

# Review:
# - What action will be performed?
# - What is the risk level?
# - Is the justification valid?
```

### Step 3: Human Approves or Rejects

```bash
# Option A: Approve (move to /Approved/)
mv Pending_Approval/task-002.md Approved/task-002.md

# Option B: Reject (move to /Rejected/)
mv Pending_Approval/task-002.md Rejected/task-002.md
```

### Step 4: System Executes or Halts

```bash
# If approved: System executes action
# System monitors /Approved/ folder, detects task-002.md, executes

# If rejected: System halts
# Task remains in /Rejected/, no action taken
```

---

## Troubleshooting

### Error: "Disk full during state transition"

**Symptom**: Task stuck in intermediate state, error in logs.

**Solution**:
1. Free disk space
2. Retry transition manually:
   ```bash
   control-plane transition task-001 Needs_Action --force
   ```

### Error: "Permission denied on file move"

**Symptom**: Cannot move task file between folders.

**Solution**:
1. Check file permissions:
   ```bash
   ls -la Inbox/task-001.md
   # Should be: -rw------- (owner-only)
   ```
2. Fix permissions:
   ```bash
   chmod 600 Inbox/task-001.md
   ```

### Error: "State inconsistency detected"

**Symptom**: File location doesn't match metadata state.

**Solution**:
1. Run verification:
   ```bash
   control-plane verify --fix
   ```
2. System will trust file location and update metadata

### Error: "YAML parsing failed"

**Symptom**: Task file has malformed YAML frontmatter.

**Solution**:
1. Validate YAML syntax:
   ```bash
   python -c "import yaml; yaml.safe_load(open('Inbox/task-001.md').read().split('---')[1])"
   ```
2. Fix syntax errors in frontmatter
3. Move task back to /Inbox/

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

```bash
# Edit source code
vim src/control_plane/state_machine.py

# Run tests continuously
pytest tests/ --watch
```

### 3. Verify Constitutional Compliance

```bash
# Run all verification checks
control-plane verify --strict

# Expected checks:
# ✓ All state transitions logged
# ✓ No sensitive actions without approval
# ✓ State fully reconstructable from disk
# ✓ Log integrity verified
# ✓ No hidden state in memory
```

### 4. Commit and Push

```bash
git add .
git commit -m "feat: implement state machine validation"
git push origin feature/my-feature
```

---

## Configuration

### Log Settings

Edit `.specify/config/logging.yaml`:

```yaml
logging:
  level: INFO
  format: json
  output: /Logs/YYYY-MM-DD.log
  rotation: daily
  retention_days: 90
  fields:
    - timestamp
    - level
    - action
    - task_id
    - from_state
    - to_state
    - result
    - approval_status
    - error
```

### State Machine Settings

Edit `.specify/config/control_plane.yaml`:

```yaml
state_machine:
  max_retry_attempts: 3
  transition_timeout: 10  # seconds
  verify_after_transition: true

approval:
  sensitive_actions:
    - send_message
    - make_payment
    - post_public
    - delete_data
  default_risk_level: medium
```

---

## Next Steps

After completing quickstart:

1. **Read Architecture Documentation**: Review `specs/001-file-control-plane/plan.md` for detailed design
2. **Study Data Model**: Review `specs/001-file-control-plane/data-model.md` for entity definitions
3. **Review API Contracts**: Review `specs/001-file-control-plane/contracts/` for API specifications
4. **Run Integration Tests**: Execute full test suite with `pytest tests/integration/`
5. **Read Constitution**: Understand governance in `.specify/memory/constitution.md`

---

## Resources

- **Specification**: `specs/001-file-control-plane/spec.md`
- **Implementation Plan**: `specs/001-file-control-plane/plan.md`
- **Data Model**: `specs/001-file-control-plane/data-model.md`
- **API Contracts**: `specs/001-file-control-plane/contracts/`
- **Constitution**: `.specify/memory/constitution.md`
- **Workflow Guide**: `WORKFLOW.md`

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review log files in `/Logs/`
3. Verify state consistency with `control-plane verify`
4. Review Constitution for governance rules

---

*This quickstart gets you up and running with the file-driven control plane in minutes.*

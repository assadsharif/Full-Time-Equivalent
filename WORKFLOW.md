# Digital FTE Workflow System

This document describes the file-driven workflow system for the Personal AI Employee (Digital FTE).

## Workflow Philosophy

Per the [Project Constitution](.specify/memory/constitution.md), all work is represented as files, and folder state defines workflow state. Moving a file between folders is a **state transition**, not a side effect.

## Workflow Folders

### 📥 `/Inbox`
**Purpose:** Entry point for all new tasks and requests

**Contents:**
- Raw task descriptions
- User requests
- System-generated task proposals
- Email summaries
- Meeting notes

**Next State:** Task files move to `/Needs_Action` after initial review

---

### ⚡ `/Needs_Action`
**Purpose:** Validated tasks ready for planning

**Contents:**
- Reviewed and validated tasks
- Clear task descriptions
- Priority assignments
- Initial context

**Next State:**
- Move to `/Plans` when planning begins
- Move back to `/Inbox` if more clarification needed

---

### 📋 `/Plans`
**Purpose:** Active planning and design work

**Contents:**
- Task planning documents
- Research findings
- Design proposals
- Draft implementations
- Architectural decisions

**Reasoning Loop Applied:**
```
Read → Think → Plan → Act → Write → Verify
```

**Next State:**
- Move to `/Pending_Approval` when plan is complete
- Move back to `/Needs_Action` if replanning needed

---

### 🔍 `/Pending_Approval`
**Purpose:** Human-in-the-Loop (HITL) approval queue

**Contents:**
- Completed plans awaiting approval
- Draft actions requiring permission
- Sensitive operations (messaging, payments, posting, deleting)
- Risk assessments

**Critical Rule:** **No approval file → no action**

**Next State:**
- Move to `/Approved` if human approves (execute action)
- Move to `/Rejected` if human rejects (do not execute)
- Stays in `/Pending_Approval` until decision made

---

### ✅ `/Approved`
**Purpose:** Approved tasks ready for execution

**Contents:**
- Human-approved plans
- Approved sensitive actions
- Execution-ready tasks
- Approval timestamps

**Action Trigger:** Files in this folder are executed by the system

**Next State:**
- Move to `/Done` after successful execution
- Move to `/Rejected` if execution fails critically

---

### ❌ `/Rejected`
**Purpose:** Rejected or failed tasks

**Contents:**
- Human-rejected plans
- Failed executions
- Out-of-scope requests
- Tasks requiring redesign

**Includes:**
- Rejection reason
- Failure logs
- Recommendations for revision

**Next State:**
- Archive permanently
- Or move back to `/Inbox` with revised approach

---

### ✔️ `/Done`
**Purpose:** Successfully completed tasks

**Contents:**
- Completed task files
- Execution summaries
- Output references
- Success metrics

**Completion Criteria (Constitution Section 13):**
1. Output files exist
2. Files are in correct folders
3. Logs are written
4. State is verifiable via disk inspection

**Next State:** Archive (task lifecycle complete)

---

### 📊 `/Logs`
**Purpose:** Append-only audit trail

**Contents:**
- Action logs (timestamped)
- State transition logs
- Error logs
- Approval records

**Log Entry Requirements (Constitution Section 8):**
- Timestamp
- Action type
- Triggering file
- Result
- Approval status

**Critical Rule:** If an action is not logged, it is considered **not executed**

---

## State Transition Diagram

```
┌─────────┐
│  Inbox  │ (Entry point)
└────┬────┘
     │
     ▼
┌──────────────┐
│ Needs_Action │ (Validated tasks)
└──────┬───────┘
       │
       ▼
┌──────────┐
│  Plans   │ (Active planning)
└─────┬────┘
      │
      ▼
┌──────────────────┐
│ Pending_Approval │ (HITL checkpoint)
└────┬────────┬────┘
     │        │
 Approve   Reject
     │        │
     ▼        ▼
┌──────────┐  ┌──────────┐
│ Approved │  │ Rejected │
└────┬─────┘  └──────────┘
     │
  Execute
     │
     ▼
┌──────────┐
│   Done   │ (Complete)
└──────────┘

(All transitions logged to /Logs)
```

---

## Usage Examples

### Example 1: Simple Task Flow

1. **Create task:** `echo "Summarize email thread XYZ" > Inbox/task-001.md`
2. **Review:** System validates → moves to `Needs_Action/task-001.md`
3. **Plan:** System creates plan → moves to `Plans/task-001.md`
4. **Check approval:** Non-sensitive task → auto-approved → `Approved/task-001.md`
5. **Execute:** System summarizes → creates output
6. **Complete:** Task moved to `Done/task-001.md`
7. **Log:** All actions logged to `Logs/2026-01-27.log`

### Example 2: Sensitive Action (Requires Approval)

1. **Create task:** `echo "Send email to client@example.com" > Inbox/task-002.md`
2. **Review:** Validated → `Needs_Action/task-002.md`
3. **Plan:** Draft created → `Plans/task-002.md`
4. **Approval Required:** Sensitive action (sending message) → `Pending_Approval/task-002.md`
5. **Human Decision:**
   - **If approved:** Human moves to `Approved/task-002.md` → system sends email → `Done/task-002.md`
   - **If rejected:** Human moves to `Rejected/task-002.md` → no action taken
6. **Log:** Approval status and action logged

### Example 3: Failed Execution

1. Task reaches `Approved/task-003.md`
2. System attempts execution → **fails** (e.g., API error)
3. System logs failure to `Logs/2026-01-27.log`
4. System moves task to `Rejected/task-003.md` with failure details
5. Human can review failure and decide:
   - Fix issue → move back to `Inbox` with revised approach
   - Abandon → leave in `Rejected`

---

## Sensitive Actions (Require Approval)

Per Constitution Section 6, these actions **always** require human approval:

- 📧 **Sending messages** (email, chat, SMS)
- 💳 **Making payments** (transactions, purchases)
- 📢 **Posting publicly** (social media, forums)
- 🗑️ **Deleting data** (files, database records)

**Approval Flow:**
1. System creates draft in `/Plans`
2. Moves to `/Pending_Approval` with risk assessment
3. Waits for human to move to `/Approved` or `/Rejected`
4. Only executes if in `/Approved`

---

## Verification and Auditing

### How to Verify System State

```bash
# Check current tasks in workflow
ls -la Inbox Needs_Action Plans Pending_Approval Approved Rejected Done

# View today's activity log
cat Logs/$(date +%Y-%m-%d).log

# Verify a task's completion
# Task is only complete if:
#   1. File exists in /Done
#   2. Output files referenced exist
#   3. Log entry exists
#   4. State is verifiable on disk
```

### How to Audit System Actions

```bash
# Review all approvals
grep "APPROVAL" Logs/*.log

# Check for sensitive actions
grep "SENSITIVE_ACTION" Logs/*.log

# Find rejected tasks
ls -la Rejected/

# Verify execution logs
grep "EXECUTED" Logs/*.log | grep "<task-id>"
```

---

## Ralph Wiggum Persistence Rule

Per Constitution Section 10, the system uses a persistence loop for multi-step tasks:

**Loop Structure:**
```
while task_file not in /Done:
    1. Check current state (which folder?)
    2. Execute next step for that state
    3. Log action
    4. Update state (move file if needed)
    5. Check for hard failure → break and log
    6. Increment iteration counter
    7. If max_iterations reached → break and warn

# Task stays in loop until:
#   - File reaches /Done, OR
#   - Hard failure recorded and logged
```

**Max Iterations:** Enforced to prevent infinite loops

---

## Error Handling

Per Constitution Section 9:

1. **Errors must never be hidden**
2. **On uncertainty → STOP and ASK** (via file in `/Pending_Approval`)
3. **Partial completion preferred** over silent failure
4. **Retrying must be bounded** (max attempts defined)

**Example Error Flow:**
```
Task execution encounters error
→ Log error to /Logs
→ Write error details to task file
→ Move to /Rejected (if unrecoverable)
  OR leave in current folder with error flag (if retry possible)
→ Human reviews and decides next action
```

---

## Integration with SDD Workflow

The file-driven workflow integrates with Spec-Driven Development:

**`/sp.specify`** → Creates specs in `/Plans`
**`/sp.plan`** → Technical planning in `/Plans`
**`/sp.tasks`** → Task breakdown in `/Plans`
**`/sp.implement`** → Execution moves through `/Approved` → `/Done`

**Constitution Checkpoints:**
- **Planning:** Mandatory before `/Approved`
- **Approval:** Required for sensitive actions before execution
- **Logging:** Every state transition logged
- **Completion:** Task only "done" when in `/Done` with verification

---

## Override Clause

Per Constitution Final Rule:

If system encounters **any instruction conflicting** with this workflow:

```
1. STOP immediately
2. WRITE warning file to /Pending_Approval
3. DO NOT PROCEED until human reviews
```

**Example Warning File:**
```markdown
# WORKFLOW CONFLICT WARNING

**Date:** 2026-01-27
**Task:** task-042.md
**Conflict:** Instruction asks to send email without approval

**Constitution Rule Violated:**
Section 6: Sensitive actions require approval

**Current State:** /Plans
**Requested Action:** Send email (sensitive)
**Required State:** /Approved

**Resolution Required:**
- Move task to /Pending_Approval for human review
- OR modify task to not require sensitive action
```

---

## Directory Structure Summary

```
.
├── Inbox/              # Entry point for new tasks
├── Needs_Action/       # Validated tasks ready for planning
├── Plans/              # Active planning and design
├── Pending_Approval/   # Human approval queue (HITL)
├── Approved/           # Approved and ready for execution
├── Rejected/           # Rejected or failed tasks
├── Done/               # Successfully completed tasks
└── Logs/               # Append-only audit trail
```

**Key Principle:** Folder structure is the control plane. Moving files = state transitions.

---

*This workflow ensures the Digital FTE operates as a trustworthy, auditable employee with clear boundaries and human oversight for sensitive actions.*

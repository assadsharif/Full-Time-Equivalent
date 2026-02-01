# Orchestrator & Scheduler Specification (P4)

**Feature Name**: Orchestrator & Scheduler (Autonomous Execution Engine)
**Priority**: P4 (Post-MVP, Core Autonomy Component)
**Status**: Draft
**Created**: 2026-01-28
**Last Updated**: 2026-01-28
**Owner**: AI Employee Hackathon Team
**Stakeholders**: System Operators, Security Team, End Users

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Context and Background](#context-and-background)
3. [User Stories](#user-stories)
4. [Functional Requirements](#functional-requirements)
5. [Non-Functional Requirements](#non-functional-requirements)
6. [Technical Architecture](#technical-architecture)
7. [Ralph Wiggum Loop Design](#ralph-wiggum-loop-design)
8. [State Machine](#state-machine)
9. [Security Considerations](#security-considerations)
10. [Error Handling and Recovery](#error-handling-and-recovery)
11. [Constitutional Compliance](#constitutional-compliance)
12. [Implementation Phases](#implementation-phases)
13. [Success Metrics](#success-metrics)
14. [Open Questions](#open-questions)
15. [Appendix](#appendix)

---

## Executive Summary

### Problem Statement

The Digital FTE system has isolated components (watchers, vault, Claude, approvals, MCP servers) but lacks an **orchestration layer** to coordinate them into autonomous workflows. Without orchestration:

- **Tasks remain idle** in `/Needs_Action` folder indefinitely
- **Manual triggering** required for each Claude Code execution
- **No prioritization** of high-urgency tasks over low-priority ones
- **Human oversight gaps** - system may execute unapproved actions
- **No recovery mechanism** when workflows fail mid-execution

Current state: Manual execution of `claude code` with specific file paths by human operators.

### Proposed Solution

Develop an **Orchestrator & Scheduler** (Python daemon) that:

1. **Monitors vault folders** (`/Needs_Action`, `/In_Progress`) for task changes
2. **Prioritizes tasks** based on urgency, deadline, and sender importance
3. **Invokes Claude Code** programmatically via subprocess/API
4. **Enforces HITL workflows** (Human-in-the-Loop) before dangerous actions
5. **Manages state transitions** (INITIALIZED → PLANNING → EXECUTING → DONE)
6. **Implements Ralph Wiggum Loop** ("I'm helping!") - autonomous task completion
7. **Respects stop hooks** for human oversight and emergency stop
8. **Logs all orchestration** using P2 logging infrastructure

### Key Benefits

| Benefit | Impact |
|---------|--------|
| **Autonomous Operation** | System completes tasks without manual intervention |
| **Prioritization** | High-urgency tasks processed first |
| **HITL Enforcement** | Dangerous actions always require approval |
| **Fault Tolerance** | Auto-recovery from Claude errors, retries |
| **Auditability** | Complete audit trail of all orchestration decisions |
| **Scalability** | Parallel task execution within resource limits |

### Scope

**In Scope:**
- Task discovery (watch `/Needs_Action` folder)
- Priority scoring algorithm
- Claude Code invocation (subprocess)
- HITL approval enforcement (check `/Approvals` before MCP execution)
- State machine management (INITIALIZED → PLANNING → EXECUTING → DONE)
- Ralph Wiggum Loop implementation
- Stop hook integration (`.claude_stop` file pattern)
- Error recovery and retry logic
- Scheduler configuration (max concurrent tasks, cooldown periods)
- CLI integration (`fte orchestrator start|stop|status`)

**Out of Scope:**
- Real-time event streaming (WebSocket/SSE) - deferred to P6
- Distributed orchestration (multi-machine) - deferred to P7
- Natural language task interpretation - Claude handles this
- Task delegation to multiple agents - single Claude instance only
- Cost optimization (API usage tracking) - deferred to P8

**Dependencies:**
- ✅ P1: Control Plane (state machine, audit logging)
- ✅ P2: Logging Infrastructure (async logging, query service)
- ✅ P3: CLI Integration (orchestrator lifecycle management)
- ✅ P5: Watcher Scripts (task ingestion from external sources)
- ⏳ P4: MCP Security (approval workflow patterns)

---

## Context and Background

### Architecture Context

The Orchestrator sits at the heart of the Digital FTE, coordinating all components:

```
┌─────────────────────────────────────────────────────────────────┐
│  External Sources (Gmail, WhatsApp, Files)                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Perception Layer (Watchers)                                     │
│  Write tasks to vault                                            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼ (writes Markdown)
┌─────────────────────────────────────────────────────────────────┐
│  Memory Layer (Obsidian Vault)                                   │
│  /Needs_Action/  →  /In_Progress/  →  /Done/                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼ (monitors folders)
┌─────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR & SCHEDULER  ◄── THIS SPEC                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  1. Task Discovery                                      │    │
│  │     - Watch /Needs_Action for new .md files            │    │
│  │     - Parse YAML frontmatter (priority, deadline)      │    │
│  │                                                         │    │
│  │  2. Prioritization                                      │    │
│  │     - Score tasks: urgency + importance + deadline     │    │
│  │     - Sort task queue                                   │    │
│  │                                                         │    │
│  │  3. Claude Invocation                                   │    │
│  │     - Run: claude code <task-file>                     │    │
│  │     - Capture stdout/stderr                             │    │
│  │     - Parse state transitions                           │    │
│  │                                                         │    │
│  │  4. HITL Approval Check                                 │    │
│  │     - Before MCP: check /Approvals/<task-id>.yaml      │    │
│  │     - Wait for approval_status: approved               │    │
│  │                                                         │    │
│  │  5. State Management                                    │    │
│  │     - Move task: /Needs_Action → /In_Progress → /Done │    │
│  │     - Update YAML frontmatter (state, timestamps)      │    │
│  │                                                         │    │
│  │  6. Ralph Wiggum Loop                                   │    │
│  │     - Check stop hook (.claude_stop file)              │    │
│  │     - If not stopped: continue to next task            │    │
│  │     - "I'm helping!" mode                               │    │
│  └────────────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼ (invokes Claude Code)
┌─────────────────────────────────────────────────────────────────┐
│  Reasoning Layer (Claude Code)                                   │
│  - Read task from vault                                          │
│  - Understand requirements                                       │
│  - Generate action plan                                          │
│  - Write approval request to /Approvals                         │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼ (generates actions)
┌─────────────────────────────────────────────────────────────────┐
│  Human-in-the-Loop (HITL) Approval                              │
│  - Review /Approvals/<task-id>.yaml                             │
│  - Edit: approval_status: pending → approved                    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼ (orchestrator checks approval)
┌─────────────────────────────────────────────────────────────────┐
│  Action Layer (MCP Servers)                                      │
│  - Execute approved actions                                      │
│  - Return results to vault                                       │
└─────────────────────────────────────────────────────────────────┘
```

**Orchestrator Responsibilities:**
1. **Task Discovery**: Monitor `/Needs_Action` for new Markdown files
2. **Prioritization**: Score tasks based on urgency, importance, deadline
3. **Scheduling**: Manage task queue, respect concurrency limits
4. **Claude Invocation**: Execute `claude code <task-file>` programmatically
5. **HITL Enforcement**: Block MCP execution until approval granted
6. **State Management**: Move tasks through folders, update YAML frontmatter
7. **Stop Hook Monitoring**: Check `.claude_stop` file before each task
8. **Error Recovery**: Retry failed tasks, log failures, escalate to human

### Constitutional Principles

| Section | Requirement | Orchestrator Compliance |
|---------|-------------|------------------------|
| **Section 2: Source of Truth** | Obsidian vault is authoritative | ✅ Orchestrator reads from vault, updates YAML |
| **Section 4: Frozen Control Plane** | No modifications to `src/control_plane/` | ✅ Orchestrator in `src/orchestrator/` (additive) |
| **Section 5: HITL for Dangerous Actions** | Human approval before MCP | ✅ Approval check before MCP execution |
| **Section 8: Auditability** | All actions logged | ✅ P2 logging for all orchestration events |
| **Section 9: Error Recovery** | Graceful degradation | ✅ Retry logic, exponential backoff |

### Hackathon Tier Alignment

| Tier | Orchestrator Requirements | Estimated Time |
|------|--------------------------|----------------|
| **Bronze** | Not required (manual execution) | 0 hours |
| **Silver** | Basic orchestration (task queue, Claude invocation) | 6-8 hours |
| **Gold** | Full autonomy (Ralph Wiggum Loop, stop hooks) | 10-12 hours |
| **Platinum** | Advanced features (parallel execution, cost optimization) | 12-16 hours |

---

## User Stories

### US1: Automated Task Discovery (Silver Tier)

**As a** system operator
**I want** the orchestrator to automatically detect new tasks in `/Needs_Action`
**So that** I don't have to manually run `claude code` for each task

**Acceptance Criteria:**
- [ ] Orchestrator monitors `/Needs_Action` folder using file system events (inotify)
- [ ] New `.md` files trigger task discovery within 5 seconds
- [ ] Task metadata parsed from YAML frontmatter (priority, deadline, sender)
- [ ] Tasks added to priority queue automatically
- [ ] Orchestrator logs all discovered tasks to P2 logging infrastructure

**Example Scenario:**

```bash
# Gmail watcher creates new task
# File: AI_Employee_Vault/Needs_Action/gmail_ceo_2026-01-28T10-00-00.md

---
source: gmail
from: ceo@company.com
subject: "Urgent: Board meeting prep"
priority: high
deadline: 2026-01-29T09:00:00Z
status: needs_action
---

# Email from CEO: Board meeting prep

**Instructions:**
Prepare Q4 financial summary for board meeting tomorrow.

# Within 5 seconds, orchestrator logs:
[INFO] Task discovered: gmail_ceo_2026-01-28T10-00-00.md
[INFO] Priority: high, Deadline: 2026-01-29T09:00:00Z
[INFO] Added to task queue (position: 1)
```

**Test Cases:**
1. **TC1.1**: Drop 5 tasks in `/Needs_Action` → verify all 5 discovered within 10s
2. **TC1.2**: Task with `priority: high` → verify added to front of queue
3. **TC1.3**: Task with `deadline: 2026-01-28T12:00:00Z` (2 hours from now) → verify prioritized
4. **TC1.4**: Orchestrator stopped → start orchestrator → verify tasks discovered on startup
5. **TC1.5**: Invalid YAML frontmatter → verify error logged, task skipped

---

### US2: Priority-Based Task Scheduling (Silver Tier)

**As a** system operator
**I want** high-priority tasks to be executed before low-priority ones
**So that** urgent work is completed first

**Acceptance Criteria:**
- [ ] Orchestrator scores tasks using priority algorithm (see Technical Architecture)
- [ ] Task queue sorted by score (highest first)
- [ ] Score considers: `priority` field (high=10, medium=5, low=0), deadline proximity (1-7 days = +5), sender importance (CEO = +10)
- [ ] Orchestrator respects max concurrent tasks limit (default: 2)
- [ ] Lower-priority tasks wait until higher-priority tasks complete

**Priority Scoring Formula:**

```python
def calculate_priority_score(task: dict) -> int:
    """
    Calculate priority score for task scheduling.

    Args:
        task: Task dictionary with keys: priority, deadline, from

    Returns:
        Priority score (higher = more urgent)
    """
    score = 0

    # Base priority
    priority_map = {'high': 10, 'medium': 5, 'low': 0}
    score += priority_map.get(task.get('priority', 'low'), 0)

    # Deadline urgency
    if 'deadline' in task:
        deadline = datetime.fromisoformat(task['deadline'])
        hours_until_deadline = (deadline - datetime.now(timezone.utc)).total_seconds() / 3600

        if hours_until_deadline < 2:
            score += 20  # Critical: < 2 hours
        elif hours_until_deadline < 24:
            score += 10  # Urgent: < 1 day
        elif hours_until_deadline < 168:
            score += 5   # Soon: < 1 week

    # Sender importance
    important_senders = ['ceo@company.com', 'legal@company.com']
    if task.get('from') in important_senders:
        score += 10

    return score
```

**Example:**

```markdown
Task A: priority=high, deadline=in 2 hours, from=ceo@company.com
  Score: 10 (high) + 20 (< 2h) + 10 (CEO) = 40

Task B: priority=medium, deadline=in 3 days, from=client@example.com
  Score: 5 (medium) + 5 (< 1 week) + 0 (normal sender) = 10

Task C: priority=low, deadline=in 1 week, from=newsletter@example.com
  Score: 0 (low) + 0 (> 1 week) + 0 (normal sender) = 0

Execution order: Task A → Task B → Task C
```

**Test Cases:**
1. **TC2.1**: 3 tasks (high, medium, low priority) → verify execution order correct
2. **TC2.2**: Task with deadline in 1 hour → verify executed before task with deadline in 1 week
3. **TC2.3**: Task from CEO → verify higher priority than same-priority task from normal sender
4. **TC2.4**: Max concurrent tasks = 2 → verify only 2 tasks run simultaneously
5. **TC2.5**: High-priority task added while low-priority task running → verify high-priority starts immediately after slot opens

---

### US3: Claude Code Invocation (Silver Tier)

**As a** system operator
**I want** the orchestrator to programmatically invoke Claude Code for each task
**So that** Claude can analyze and plan actions autonomously

**Acceptance Criteria:**
- [ ] Orchestrator executes `claude code <task-file>` as subprocess
- [ ] Subprocess inherits environment variables (API keys, vault path)
- [ ] stdout/stderr captured and logged via P2 infrastructure
- [ ] Claude output parsed for state transitions (INITIALIZED → PLANNING → EXECUTING)
- [ ] Task moved from `/Needs_Action` to `/In_Progress` when Claude starts
- [ ] Task metadata updated (state, started_at timestamp)
- [ ] Orchestrator waits for Claude to complete before moving to next task

**Claude Invocation Pseudocode:**

```python
import subprocess
from pathlib import Path
from src.logging import get_logger

logger = get_logger(__name__)


def invoke_claude(task_file: Path) -> dict:
    """
    Invoke Claude Code for a specific task file.

    Args:
        task_file: Path to task Markdown file

    Returns:
        Result dictionary with stdout, stderr, return_code
    """
    logger.info(f"Invoking Claude for task: {task_file.name}")

    # Move task to /In_Progress
    in_progress_path = task_file.parent.parent / "In_Progress" / task_file.name
    task_file.rename(in_progress_path)

    # Update YAML frontmatter
    update_task_metadata(in_progress_path, {
        'state': 'in_progress',
        'started_at': datetime.now(timezone.utc).isoformat()
    })

    # Execute Claude Code
    cmd = [
        'claude',
        'code',
        str(in_progress_path),
        '--non-interactive',  # No user prompts
        '--max-tokens', '8000'
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
            env=os.environ.copy()
        )

        logger.info(
            f"Claude execution complete: {task_file.name}",
            context={
                'return_code': result.returncode,
                'stdout_lines': len(result.stdout.splitlines()),
                'stderr_lines': len(result.stderr.splitlines())
            }
        )

        return {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode
        }

    except subprocess.TimeoutExpired:
        logger.error(f"Claude execution timeout: {task_file.name}")
        return {'error': 'timeout'}

    except Exception as e:
        logger.error(f"Claude execution failed: {e}", exc_info=True)
        return {'error': str(e)}
```

**Test Cases:**
1. **TC3.1**: Invoke Claude on task → verify subprocess created, output captured
2. **TC3.2**: Task moved to `/In_Progress` → verify file moved, YAML updated
3. **TC3.3**: Claude timeout (> 10 min) → verify subprocess killed, error logged
4. **TC3.4**: Claude crashes (exit code != 0) → verify error logged, task not moved to `/Done`
5. **TC3.5**: Claude output contains "State: PLANNING" → verify state transition logged

---

### US4: HITL Approval Enforcement (Gold Tier)

**As a** system operator
**I want** the orchestrator to enforce human approval before executing MCP actions
**So that** dangerous operations (payments, emails, file deletions) require explicit consent

**Acceptance Criteria:**
- [ ] Claude generates approval requests in `/Approvals/<task-id>.yaml`
- [ ] Orchestrator monitors `/Approvals` folder for approval status changes
- [ ] Orchestrator blocks MCP execution until `approval_status: approved`
- [ ] Timeout for approval (default: 24 hours) → task moved to `/Needs_Human_Review`
- [ ] Rejected approvals (`approval_status: rejected`) → task moved to `/Done` with status "rejected"
- [ ] Approved actions logged with approver identity and timestamp

**Approval Workflow:**

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Claude analyzes task                                         │
│     - Determines actions needed (e.g., send payment email)      │
│     - Generates approval request                                 │
│                                                                  │
│  2. Claude writes /Approvals/<task-id>.yaml                     │
│     ---                                                          │
│     task_id: gmail_ceo_2026-01-28T10-00-00                      │
│     action: send_email                                           │
│     to: vendor@example.com                                       │
│     subject: "Payment Confirmation"                              │
│     body: "Wire transfer of $50,000 approved..."                │
│     risk_level: high                                             │
│     approval_status: pending                                     │
│     requested_at: 2026-01-28T10:15:00Z                          │
│     ---                                                          │
│                                                                  │
│  3. Orchestrator detects approval request                       │
│     [INFO] Approval required for gmail_ceo_2026-01-28T10-00-00 │
│     [INFO] Waiting for approval (timeout: 24h)                  │
│                                                                  │
│  4. Human reviews and approves                                  │
│     # Edit /Approvals/<task-id>.yaml                            │
│     approval_status: approved  # Changed from pending           │
│     approved_by: john.doe@company.com                           │
│     approved_at: 2026-01-28T10:30:00Z                           │
│                                                                  │
│  5. Orchestrator detects approval                               │
│     [INFO] Approval granted for gmail_ceo_2026-01-28T10-00-00  │
│     [INFO] Executing MCP action: send_email                     │
│                                                                  │
│  6. Orchestrator invokes Claude to execute action               │
│     - Claude calls MCP server (email-mcp)                       │
│     - Email sent                                                 │
│     - Task moved to /Done                                        │
└─────────────────────────────────────────────────────────────────┘
```

**Test Cases:**
1. **TC4.1**: Claude generates approval request → verify YAML created in `/Approvals`
2. **TC4.2**: Orchestrator waits for approval → verify MCP not executed until approved
3. **TC4.3**: Human approves → verify orchestrator detects within 5s, executes action
4. **TC4.4**: Human rejects → verify task moved to `/Done` with status "rejected"
5. **TC4.5**: Approval timeout (24h) → verify task moved to `/Needs_Human_Review`

---

### US5: Ralph Wiggum Loop (Gold Tier)

**As a** system operator
**I want** the orchestrator to continuously process tasks autonomously
**So that** the AI Employee operates 24/7 without manual intervention

**Acceptance Criteria:**
- [ ] Orchestrator runs in infinite loop (daemon mode)
- [ ] After completing a task, immediately checks queue for next task
- [ ] "I'm helping!" message logged when new task starts
- [ ] Stop hook monitored before each task (`.claude_stop` file)
- [ ] If stop hook detected, gracefully finish current task, then pause
- [ ] Cooldown period between tasks (default: 10 seconds) to prevent resource exhaustion
- [ ] Orchestrator survives system reboot (systemd/PM2 integration)

**Ralph Wiggum Loop Pseudocode:**

```python
from pathlib import Path
import time
from src.logging import get_logger

logger = get_logger(__name__)

STOP_HOOK_FILE = Path("/path/to/AI_Employee_Vault/.claude_stop")
COOLDOWN_SECONDS = 10


def ralph_wiggum_loop(orchestrator):
    """
    Main orchestration loop (Ralph Wiggum: "I'm helping!")

    Continuously processes tasks from queue until stop hook detected.
    """
    logger.info("Starting Ralph Wiggum Loop (autonomous mode)")

    while True:
        # Check stop hook
        if check_stop_hook():
            logger.warning("Stop hook detected (.claude_stop file exists)")
            logger.info("Finishing current task, then pausing...")
            break

        # Get next task from priority queue
        task = orchestrator.get_next_task()

        if task is None:
            logger.debug("Task queue empty, waiting for new tasks...")
            time.sleep(COOLDOWN_SECONDS)
            continue

        # Log "I'm helping!" message
        logger.info(
            f"🤖 I'm helping! Starting task: {task.filename}",
            context={
                'task_id': task.task_id,
                'priority_score': task.priority_score,
                'deadline': task.deadline
            }
        )

        # Execute task
        try:
            orchestrator.execute_task(task)

            logger.info(
                f"✅ Task complete: {task.filename}",
                context={'task_id': task.task_id, 'status': 'success'}
            )

        except Exception as e:
            logger.error(
                f"❌ Task failed: {task.filename} - {e}",
                context={'task_id': task.task_id, 'error': str(e)},
                exc_info=True
            )

            # Move to error queue for retry
            orchestrator.move_to_error_queue(task)

        # Cooldown before next task
        logger.debug(f"Cooldown: {COOLDOWN_SECONDS}s")
        time.sleep(COOLDOWN_SECONDS)

    logger.info("Ralph Wiggum Loop paused (stop hook detected)")


def check_stop_hook() -> bool:
    """Check if stop hook file exists."""
    return STOP_HOOK_FILE.exists()


def create_stop_hook():
    """Create stop hook file (emergency stop)."""
    STOP_HOOK_FILE.write_text("STOP", encoding='utf-8')
    logger.warning("Stop hook created (.claude_stop)")


def remove_stop_hook():
    """Remove stop hook file (resume operation)."""
    if STOP_HOOK_FILE.exists():
        STOP_HOOK_FILE.unlink()
        logger.info("Stop hook removed (resuming operation)")
```

**CLI Commands:**

```bash
# Start Ralph Wiggum Loop
fte orchestrator start
# [INFO] Starting Ralph Wiggum Loop (autonomous mode)
# [INFO] 🤖 I'm helping! Starting task: gmail_ceo_2026-01-28T10-00-00.md

# Emergency stop (creates .claude_stop file)
fte orchestrator stop
# [WARNING] Stop hook created (.claude_stop)
# [INFO] Finishing current task, then pausing...

# Resume operation (removes .claude_stop file)
fte orchestrator resume
# [INFO] Stop hook removed (resuming operation)
# [INFO] Starting Ralph Wiggum Loop (autonomous mode)
```

**Test Cases:**
1. **TC5.1**: Start orchestrator → verify continuous task processing
2. **TC5.2**: Stop hook created → verify orchestrator pauses after current task
3. **TC5.3**: Stop hook removed → verify orchestrator resumes immediately
4. **TC5.4**: Task queue empty → verify orchestrator waits 10s, checks again
5. **TC5.5**: System reboot → verify orchestrator auto-starts via PM2/systemd

---

### US6: Error Recovery and Retry Logic (Gold Tier)

**As a** system operator
**I want** failed tasks to be retried automatically
**So that** transient errors don't require manual intervention

**Acceptance Criteria:**
- [ ] Failed tasks moved to `/Error_Queue` folder
- [ ] Retry logic: exponential backoff (1 min, 5 min, 15 min, 1 hour, 4 hours)
- [ ] Max retry attempts: 5
- [ ] Permanent failures (max retries exhausted) → move to `/Failed`
- [ ] Human escalation: tasks in `/Failed` trigger notification (email/Slack)
- [ ] Retry metadata tracked in YAML frontmatter (retry_count, last_retry_at)

**Retry Logic Pseudocode:**

```python
from datetime import datetime, timedelta
from pathlib import Path

RETRY_DELAYS = [60, 300, 900, 3600, 14400]  # seconds: 1m, 5m, 15m, 1h, 4h
MAX_RETRIES = 5


def handle_task_failure(task: dict, error: Exception):
    """
    Handle task failure with retry logic.

    Args:
        task: Task dictionary with metadata
        error: Exception that caused failure
    """
    retry_count = task.get('retry_count', 0)

    logger.error(
        f"Task failed: {task['filename']} - {error}",
        context={
            'task_id': task['task_id'],
            'retry_count': retry_count,
            'error_type': type(error).__name__
        }
    )

    if retry_count >= MAX_RETRIES:
        # Permanent failure
        logger.error(f"Max retries exhausted: {task['filename']}")
        move_to_failed(task)
        send_human_escalation_notification(task, error)
        return

    # Calculate next retry time
    delay_seconds = RETRY_DELAYS[retry_count]
    next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)

    logger.info(
        f"Scheduling retry {retry_count + 1}/{MAX_RETRIES} for {task['filename']}",
        context={
            'task_id': task['task_id'],
            'next_retry_at': next_retry_at.isoformat(),
            'delay_seconds': delay_seconds
        }
    )

    # Update task metadata
    update_task_metadata(task['path'], {
        'retry_count': retry_count + 1,
        'last_retry_at': datetime.now(timezone.utc).isoformat(),
        'next_retry_at': next_retry_at.isoformat(),
        'last_error': str(error)
    })

    # Move to error queue
    error_queue_path = task['path'].parent.parent / "Error_Queue" / task['filename']
    task['path'].rename(error_queue_path)


def check_retry_queue():
    """
    Check error queue for tasks ready to retry.

    Returns:
        List of tasks ready for retry
    """
    error_queue = Path("/path/to/AI_Employee_Vault/Error_Queue")
    now = datetime.now(timezone.utc)

    ready_tasks = []

    for task_file in error_queue.glob("*.md"):
        metadata = parse_yaml_frontmatter(task_file)

        if 'next_retry_at' in metadata:
            next_retry = datetime.fromisoformat(metadata['next_retry_at'])

            if now >= next_retry:
                logger.info(f"Task ready for retry: {task_file.name}")
                ready_tasks.append({
                    'path': task_file,
                    'filename': task_file.name,
                    'task_id': metadata.get('task_id'),
                    'retry_count': metadata.get('retry_count', 0)
                })

    return ready_tasks
```

**Test Cases:**
1. **TC6.1**: Task fails with network error → verify moved to `/Error_Queue`, retry scheduled
2. **TC6.2**: Retry after 1 minute → verify task re-executed
3. **TC6.3**: Task fails 5 times → verify moved to `/Failed`, notification sent
4. **TC6.4**: Multiple failed tasks → verify retries scheduled independently
5. **TC6.5**: Task succeeds on retry → verify moved to `/Done`, retry metadata cleared

---

## Functional Requirements

### FR1: Task Discovery Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR1.1 | Monitor `/Needs_Action` folder using file system events | P2 (Silver) |
| FR1.2 | Parse YAML frontmatter (priority, deadline, from) | P2 (Silver) |
| FR1.3 | Validate task structure (required fields present) | P2 (Silver) |
| FR1.4 | Add valid tasks to priority queue | P2 (Silver) |
| FR1.5 | Skip invalid tasks, log validation errors | P2 (Silver) |

### FR2: Prioritization Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR2.1 | Calculate priority score using algorithm | P2 (Silver) |
| FR2.2 | Sort task queue by score (highest first) | P2 (Silver) |
| FR2.3 | Support custom sender importance list | P3 (Gold) |
| FR2.4 | Re-prioritize queue when new high-priority task added | P3 (Gold) |

### FR3: Claude Invocation Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR3.1 | Execute `claude code <task-file>` as subprocess | P2 (Silver) |
| FR3.2 | Capture stdout/stderr, log via P2 infrastructure | P2 (Silver) |
| FR3.3 | Move task from `/Needs_Action` to `/In_Progress` | P2 (Silver) |
| FR3.4 | Update task YAML frontmatter (state, timestamps) | P2 (Silver) |
| FR3.5 | Handle Claude timeout (> 10 minutes) | P2 (Silver) |
| FR3.6 | Handle Claude crash (non-zero exit code) | P2 (Silver) |

### FR4: HITL Approval Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR4.1 | Monitor `/Approvals` folder for approval requests | P3 (Gold) |
| FR4.2 | Block MCP execution until `approval_status: approved` | P3 (Gold) |
| FR4.3 | Timeout approval requests after 24 hours | P3 (Gold) |
| FR4.4 | Handle rejected approvals (`approval_status: rejected`) | P3 (Gold) |
| FR4.5 | Log approvals with approver identity and timestamp | P3 (Gold) |

### FR5: Ralph Wiggum Loop Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR5.1 | Run continuous task processing loop (daemon mode) | P3 (Gold) |
| FR5.2 | Check stop hook (`.claude_stop` file) before each task | P3 (Gold) |
| FR5.3 | Gracefully pause when stop hook detected | P3 (Gold) |
| FR5.4 | Resume operation when stop hook removed | P3 (Gold) |
| FR5.5 | Cooldown period between tasks (10 seconds) | P3 (Gold) |

### FR6: Error Recovery Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR6.1 | Move failed tasks to `/Error_Queue` | P3 (Gold) |
| FR6.2 | Retry with exponential backoff (1m, 5m, 15m, 1h, 4h) | P3 (Gold) |
| FR6.3 | Max 5 retry attempts per task | P3 (Gold) |
| FR6.4 | Move permanently failed tasks to `/Failed` | P3 (Gold) |
| FR6.5 | Send human escalation notification for failed tasks | P4 (Platinum) |

---

## Non-Functional Requirements

### NFR1: Performance

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR1.1 | Task discovery latency | < 5s | Time from file creation → task in queue |
| NFR1.2 | Priority queue sort latency | < 100ms | Time to re-sort queue with 100 tasks |
| NFR1.3 | Max concurrent tasks | 2 | Configurable via `config.yaml` |
| NFR1.4 | Cooldown between tasks | 10s | Configurable via `config.yaml` |
| NFR1.5 | Memory footprint (idle) | < 50MB | RSS memory usage |
| NFR1.6 | CPU usage (idle) | < 1% | Average CPU over 1 hour |

### NFR2: Reliability

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR2.1 | Uptime | 99.9% | (total_time - downtime) / total_time |
| NFR2.2 | Task completion rate | 95% | Successful tasks / total tasks |
| NFR2.3 | Auto-recovery from crashes | < 10s | Time from crash → restart |
| NFR2.4 | Data loss rate | 0% | Tasks lost / total tasks |

### NFR3: Observability

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR3.1 | Structured logging (P2 infrastructure) | 100% | All events use `get_logger()` |
| NFR3.2 | Log levels (DEBUG, INFO, WARNING, ERROR) | 100% | Appropriate levels for all events |
| NFR3.3 | Trace correlation (trace IDs) | 100% | All logs include `trace_id` |
| NFR3.4 | Metrics emission (tasks processed, failed, retried) | 100% | Prometheus metrics |

---

## Technical Architecture

### Component Design

```python
# src/orchestrator/orchestrator.py

import time
from pathlib import Path
from queue import PriorityQueue
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.logging import get_logger
from src.orchestrator.task import Task
from src.orchestrator.claude_invoker import ClaudeInvoker
from src.orchestrator.approval_checker import ApprovalChecker

logger = get_logger(__name__)


class OrchestratorConfig:
    """Configuration for orchestrator."""

    def __init__(self, config_dict: dict):
        self.vault_path = Path(config_dict['vault_path'])
        self.max_concurrent_tasks = config_dict.get('max_concurrent_tasks', 2)
        self.cooldown_seconds = config_dict.get('cooldown_seconds', 10)
        self.approval_timeout_hours = config_dict.get('approval_timeout_hours', 24)
        self.stop_hook_file = self.vault_path / '.claude_stop'


class Orchestrator:
    """
    Main orchestrator class.

    Responsibilities:
    - Task discovery (watch /Needs_Action)
    - Prioritization (priority queue)
    - Claude invocation (subprocess)
    - HITL approval enforcement
    - State management
    - Ralph Wiggum Loop
    """

    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.task_queue = PriorityQueue()
        self.running_tasks = []
        self.claude_invoker = ClaudeInvoker(config)
        self.approval_checker = ApprovalChecker(config)

    def start(self):
        """Start orchestrator (Ralph Wiggum Loop)."""
        logger.info("Starting Orchestrator")

        # Start file system observer
        observer = Observer()
        handler = TaskDiscoveryHandler(self, self.config.vault_path / "Needs_Action")
        observer.schedule(handler, str(self.config.vault_path / "Needs_Action"), recursive=False)
        observer.start()

        logger.info("Task discovery started (watching /Needs_Action)")

        # Discover existing tasks on startup
        self._discover_existing_tasks()

        # Start Ralph Wiggum Loop
        self._ralph_wiggum_loop()

        observer.stop()
        observer.join()

    def _discover_existing_tasks(self):
        """Discover tasks already in /Needs_Action on startup."""
        needs_action_dir = self.config.vault_path / "Needs_Action"

        for task_file in needs_action_dir.glob("*.md"):
            logger.info(f"Discovered existing task: {task_file.name}")
            self._add_task_to_queue(task_file)

    def _add_task_to_queue(self, task_file: Path):
        """Parse task and add to priority queue."""
        try:
            task = Task.from_file(task_file)
            priority_score = task.calculate_priority_score()

            # PriorityQueue uses (priority, item) tuples
            # Lower priority value = higher priority, so negate score
            self.task_queue.put((-priority_score, task))

            logger.info(
                f"Task added to queue: {task.filename}",
                context={
                    'task_id': task.task_id,
                    'priority_score': priority_score,
                    'deadline': task.deadline
                }
            )

        except Exception as e:
            logger.error(f"Failed to parse task: {task_file.name} - {e}", exc_info=True)

    def _ralph_wiggum_loop(self):
        """Main orchestration loop (Ralph Wiggum: "I'm helping!")"""
        logger.info("Starting Ralph Wiggum Loop (autonomous mode)")

        while True:
            # Check stop hook
            if self._check_stop_hook():
                logger.warning("Stop hook detected (.claude_stop file exists)")
                logger.info("Finishing current tasks, then pausing...")
                break

            # Check if we can start a new task
            if len(self.running_tasks) >= self.config.max_concurrent_tasks:
                logger.debug("Max concurrent tasks reached, waiting...")
                time.sleep(self.config.cooldown_seconds)
                continue

            # Get next task from priority queue
            if self.task_queue.empty():
                logger.debug("Task queue empty, waiting for new tasks...")
                time.sleep(self.config.cooldown_seconds)
                continue

            _, task = self.task_queue.get()

            # Log "I'm helping!" message
            logger.info(
                f"🤖 I'm helping! Starting task: {task.filename}",
                context={
                    'task_id': task.task_id,
                    'priority_score': task.priority_score,
                    'deadline': task.deadline
                }
            )

            # Execute task
            self._execute_task(task)

            # Cooldown before next task
            logger.debug(f"Cooldown: {self.config.cooldown_seconds}s")
            time.sleep(self.config.cooldown_seconds)

        logger.info("Ralph Wiggum Loop paused (stop hook detected)")

    def _execute_task(self, task: Task):
        """Execute a single task."""
        try:
            # Step 1: Move to /In_Progress
            task.move_to_in_progress(self.config.vault_path)

            # Step 2: Invoke Claude
            result = self.claude_invoker.invoke(task)

            if result.get('error'):
                raise Exception(result['error'])

            # Step 3: Check if approval required
            if self.approval_checker.is_approval_required(task):
                logger.info(f"Approval required for task: {task.filename}")

                # Wait for approval (with timeout)
                approved = self.approval_checker.wait_for_approval(
                    task,
                    timeout_hours=self.config.approval_timeout_hours
                )

                if not approved:
                    logger.warning(f"Approval timeout or rejected: {task.filename}")
                    task.move_to_done(self.config.vault_path, status="approval_timeout")
                    return

            # Step 4: Execute approved actions (Claude continues)
            # (Claude will call MCP servers at this point)

            # Step 5: Move to /Done
            task.move_to_done(self.config.vault_path, status="success")

            logger.info(
                f"✅ Task complete: {task.filename}",
                context={'task_id': task.task_id, 'status': 'success'}
            )

        except Exception as e:
            logger.error(
                f"❌ Task failed: {task.filename} - {e}",
                context={'task_id': task.task_id, 'error': str(e)},
                exc_info=True
            )

            # Handle failure with retry logic
            self._handle_task_failure(task, e)

    def _check_stop_hook(self) -> bool:
        """Check if stop hook file exists."""
        return self.config.stop_hook_file.exists()

    def _handle_task_failure(self, task: Task, error: Exception):
        """Handle task failure with retry logic."""
        # (See US6 pseudocode above for full implementation)
        pass


class TaskDiscoveryHandler(FileSystemEventHandler):
    """File system event handler for task discovery."""

    def __init__(self, orchestrator: Orchestrator, watch_path: Path):
        self.orchestrator = orchestrator
        self.watch_path = watch_path

    def on_created(self, event):
        """Handle new file creation in /Needs_Action."""
        if event.is_directory:
            return

        if not event.src_path.endswith('.md'):
            return

        task_file = Path(event.src_path)
        logger.info(f"New task detected: {task_file.name}")

        self.orchestrator._add_task_to_queue(task_file)
```

---

## Ralph Wiggum Loop Design

### Concept

The "Ralph Wiggum Loop" (named after the Simpsons character who enthusiastically says "I'm helping!") is the autonomous execution mode where the orchestrator continuously processes tasks without manual intervention.

**Key Characteristics:**
1. **Continuous Operation**: Infinite loop that never stops (unless stop hook detected)
2. **Self-Directed**: Orchestrator decides what to work on next based on priority
3. **Graceful Pause**: Stop hook allows human to pause operation safely
4. **Resource-Aware**: Respects concurrency limits, cooldown periods
5. **Resilient**: Handles failures, retries, escalates to human when needed

### State Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Ralph Wiggum Loop States                      │
└─────────────────────────────────────────────────────────────────┘

     START
       │
       ▼
   ┌─────────┐
   │  IDLE   │ ◄──────────────────────────┐
   └────┬────┘                             │
        │                                  │
        │ Task available?                  │
        ▼                                  │
   ┌─────────┐    Stop hook?          ┌───┴────┐
   │ CHECK   │───────YES──────────────►│ PAUSED │
   │  STOP   │                         └────────┘
   │  HOOK   │                              ▲
   └────┬────┘                              │
        │ NO                                │
        ▼                                   │
   ┌─────────┐                              │
   │ EXECUTE │                              │
   │  TASK   │                              │
   └────┬────┘                              │
        │                                   │
        │ Success?                          │
        ▼                                   │
   ┌─────────┐    NO (error)                │
   │ HANDLE  │────────────────────┐         │
   │ RESULT  │                    │         │
   └────┬────┘                    │         │
        │ YES (success)           ▼         │
        │                    ┌─────────┐    │
        │                    │  RETRY  │    │
        │                    │  QUEUE  │    │
        │                    └────┬────┘    │
        │                         │         │
        │                         └─────────┘
        ▼
   ┌─────────┐
   │COOLDOWN │
   │  10s    │
   └────┬────┘
        │
        └──────────────────────────────────┘
           (back to IDLE)
```

### Stop Hook Mechanism

**Purpose**: Allow humans to safely pause the orchestrator for:
- Emergency stop (system under attack, runaway costs)
- Maintenance (updating configurations, reviewing logs)
- Debugging (investigating stuck tasks)

**Implementation:**

```bash
# Create stop hook (emergency stop)
fte orchestrator stop
# Creates file: /AI_Employee_Vault/.claude_stop

# Remove stop hook (resume operation)
fte orchestrator resume
# Deletes file: /AI_Employee_Vault/.claude_stop

# Check if stopped
fte orchestrator status
# Output:
# Orchestrator: PAUSED (stop hook detected)
# Stop hook: /AI_Employee_Vault/.claude_stop
# Last task: gmail_ceo_2026-01-28T10-00-00.md (completed)
```

---

## State Machine

### Task States

```
INITIALIZED ──► NEEDS_ACTION ──► IN_PROGRESS ──► EXECUTING ──► DONE
                     │              │              │
                     │              ▼              ▼
                     │          ERROR_QUEUE    APPROVAL_PENDING
                     │              │              │
                     │              ▼              ▼
                     │           RETRY ──────► APPROVED ──► EXECUTING
                     │              │              │
                     │              ▼              ▼
                     └────────► FAILED      REJECTED ──► DONE
```

**State Descriptions:**

| State | Folder | Description |
|-------|--------|-------------|
| **NEEDS_ACTION** | `/Needs_Action` | Task waiting in queue, not yet started |
| **IN_PROGRESS** | `/In_Progress` | Claude is analyzing task, generating plan |
| **APPROVAL_PENDING** | `/Approvals` | Waiting for human approval before MCP execution |
| **APPROVED** | `/Approvals` | Human approved, ready for MCP execution |
| **EXECUTING** | `/In_Progress` | Claude executing MCP actions |
| **ERROR_QUEUE** | `/Error_Queue` | Task failed, waiting for retry |
| **RETRY** | `/Needs_Action` | Task being retried after failure |
| **REJECTED** | `/Done` | Human rejected approval, task cancelled |
| **DONE** | `/Done` | Task completed successfully |
| **FAILED** | `/Failed` | Permanent failure (max retries exhausted) |

---

## Security Considerations

### SEC1: Subprocess Security

**Risk**: Malicious task files could exploit subprocess execution

**Mitigation:**
1. Validate task file path (must be within vault)
2. Use absolute paths only (no `../` traversal)
3. Sanitize filenames (no shell metacharacters)
4. Run Claude subprocess with timeout (prevent infinite loops)
5. Limit subprocess resource usage (ulimit, cgroups)

**Example:**

```python
def validate_task_path(task_file: Path, vault_path: Path) -> bool:
    """Validate task file path is within vault."""
    try:
        # Resolve to absolute path
        abs_task = task_file.resolve()
        abs_vault = vault_path.resolve()

        # Check if task is within vault
        return abs_task.is_relative_to(abs_vault)

    except (ValueError, OSError):
        return False


def invoke_claude_secure(task_file: Path) -> dict:
    """Invoke Claude with security checks."""
    # Validate path
    if not validate_task_path(task_file, VAULT_PATH):
        raise SecurityError(f"Task file outside vault: {task_file}")

    # Sanitize filename
    if any(char in task_file.name for char in ['&', '|', ';', '$', '`']):
        raise SecurityError(f"Invalid characters in filename: {task_file.name}")

    # Execute with timeout and resource limits
    cmd = ['timeout', '600', 'claude', 'code', str(task_file)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    return result
```

### SEC2: Approval Bypass Prevention

**Risk**: Orchestrator could skip approval check, execute dangerous actions

**Mitigation:**
1. Enforce approval check before any MCP execution
2. Log all approval checks (approved, rejected, timeout)
3. Audit logs regularly for approval bypasses
4. Use file integrity monitoring on `/Approvals` folder

**Example:**

```python
def execute_mcp_action(task: Task, action: dict):
    """Execute MCP action with approval enforcement."""
    # CRITICAL: Always check approval before MCP execution
    if not ApprovalChecker.is_approved(task):
        raise SecurityError(f"MCP action blocked: approval not granted for {task.task_id}")

    logger.info(
        f"Executing approved MCP action: {action['type']}",
        context={
            'task_id': task.task_id,
            'action_type': action['type'],
            'approver': task.approval_metadata.get('approved_by')
        }
    )

    # Execute action
    # ...
```

---

## Error Handling and Recovery

### Error Classification

| Error Type | Example | Recovery Strategy |
|------------|---------|-------------------|
| **Claude Timeout** | Claude execution > 10 minutes | Kill subprocess, retry task |
| **Claude Crash** | Claude exit code != 0 | Log error, move to error queue, retry |
| **Approval Timeout** | No approval after 24 hours | Move to `/Needs_Human_Review` |
| **Subprocess Failure** | `subprocess.CalledProcessError` | Log error, retry task |
| **File System Error** | Disk full, permission denied | Alert operator, pause orchestrator |
| **Invalid Task Format** | Missing YAML frontmatter | Skip task, log validation error |

---

## Constitutional Compliance

| Constitutional Section | Requirement | Orchestrator Compliance |
|------------------------|-------------|------------------------|
| **Section 2: Source of Truth** | Obsidian vault is authoritative | ✅ Orchestrator reads from vault, updates YAML |
| **Section 4: Frozen Control Plane** | No modifications to `src/control_plane/` | ✅ Orchestrator in `src/orchestrator/` (additive) |
| **Section 5: HITL for Dangerous Actions** | Human approval before MCP | ✅ Approval check enforced before MCP |
| **Section 8: Auditability** | All actions logged | ✅ P2 logging for all orchestration events |
| **Section 9: Error Recovery** | Graceful degradation | ✅ Retry logic, exponential backoff, human escalation |

---

## Implementation Phases

### Phase 1: Task Discovery and Prioritization (Silver Tier) - 3-4 hours

**Deliverables:**
- [ ] `src/orchestrator/orchestrator.py` (Main orchestrator class)
- [ ] `src/orchestrator/task.py` (Task model)
- [ ] File system observer for `/Needs_Action`
- [ ] Priority scoring algorithm
- [ ] Priority queue implementation
- [ ] CLI integration (`fte orchestrator start`)

**Acceptance Test:**
```bash
# Start orchestrator
fte orchestrator start

# Drop 3 tasks in /Needs_Action with different priorities
# Verify tasks discovered and prioritized correctly
fte orchestrator status
# Expected:
# Tasks in queue: 3
# Next task: gmail_ceo_2026-01-28T10-00-00.md (priority: 40)
```

### Phase 2: Claude Invocation (Silver Tier) - 2-3 hours

**Deliverables:**
- [ ] `src/orchestrator/claude_invoker.py` (Claude subprocess executor)
- [ ] Task state management (NEEDS_ACTION → IN_PROGRESS → DONE)
- [ ] YAML frontmatter updates
- [ ] stdout/stderr capture and logging

**Acceptance Test:**
```bash
# Place task in /Needs_Action
# Verify Claude invoked, task moved to /In_Progress, then /Done
ls AI_Employee_Vault/Done/
# Expected: gmail_ceo_2026-01-28T10-00-00.md
```

### Phase 3: HITL Approval Enforcement (Gold Tier) - 3-4 hours

**Deliverables:**
- [ ] `src/orchestrator/approval_checker.py` (Approval enforcement)
- [ ] Monitor `/Approvals` folder for approval status changes
- [ ] Block MCP execution until approved
- [ ] Approval timeout (24 hours)
- [ ] Handle rejected approvals

**Acceptance Test:**
```bash
# Task generates approval request
# Verify orchestrator waits for approval
# Approve manually
# Verify orchestrator proceeds with MCP execution
```

### Phase 4: Ralph Wiggum Loop (Gold Tier) - 2-3 hours

**Deliverables:**
- [ ] Ralph Wiggum Loop implementation (infinite loop)
- [ ] Stop hook monitoring (`.claude_stop` file)
- [ ] Graceful pause/resume
- [ ] Cooldown period between tasks
- [ ] PM2/systemd integration

**Acceptance Test:**
```bash
# Start orchestrator
fte orchestrator start

# Verify continuous task processing
# Create stop hook
fte orchestrator stop

# Verify orchestrator pauses after current task
fte orchestrator status
# Expected: PAUSED (stop hook detected)
```

### Phase 5: Error Recovery (Gold Tier) - 2-3 hours

**Deliverables:**
- [ ] Error queue (`/Error_Queue`)
- [ ] Retry logic with exponential backoff
- [ ] Max retry attempts (5)
- [ ] Permanent failure handling (`/Failed`)
- [ ] Human escalation notifications

**Acceptance Test:**
```bash
# Simulate Claude failure (network error)
# Verify task moved to /Error_Queue
# Verify retry scheduled after 1 minute
# Task succeeds on retry
# Verify moved to /Done
```

---

## Success Metrics

### Silver Tier (Basic Orchestration)

- [ ] Task discovery operational (< 5s latency)
- [ ] Priority scoring correct (high > medium > low)
- [ ] Claude invocation successful (subprocess execution)
- [ ] Tasks moved through folders correctly (Needs_Action → In_Progress → Done)
- [ ] Logs captured via P2 infrastructure

### Gold Tier (Autonomous Operation)

- [ ] Ralph Wiggum Loop operational (continuous processing)
- [ ] Stop hook functional (pause/resume)
- [ ] HITL approval enforced (no MCP execution without approval)
- [ ] Error recovery functional (retry with exponential backoff)
- [ ] 95% task completion rate over 7-day test period

### Platinum Tier (Enterprise Grade)

- [ ] Parallel task execution (2+ concurrent tasks)
- [ ] Human escalation notifications (email/Slack)
- [ ] Cost optimization (API usage tracking)
- [ ] Real-time monitoring dashboard (Grafana)
- [ ] 99% uptime over 30-day test period

---

## Open Questions

1. **Claude Code API vs CLI?**
   - Should we use Claude API directly or invoke CLI?
   - **Recommendation:** Start with CLI (simpler), migrate to API for better control.

2. **Approval Timeout Value?**
   - 24 hours may be too long for urgent tasks. Configurable per task?
   - **Recommendation:** Yes, support per-task timeout in YAML frontmatter.

3. **Concurrent Task Limit?**
   - Default is 2 concurrent tasks. Should this be auto-tuned based on system resources?
   - **Recommendation:** Yes, implement auto-tuning in Platinum tier.

4. **Human Escalation Channels?**
   - Email, Slack, SMS, or all three?
   - **Recommendation:** Email (Bronze), Slack (Silver), SMS (Gold).

5. **Retry Strategy Customization?**
   - Should retry delays be configurable per error type?
   - **Recommendation:** Yes, support custom retry strategies in `config/retry_policies.yaml`.

---

## Appendix

### A1: Configuration Schema

```yaml
# config/orchestrator.yaml

vault_path: /path/to/AI_Employee_Vault
max_concurrent_tasks: 2
cooldown_seconds: 10
approval_timeout_hours: 24

claude:
  command: claude
  args: ['code', '--non-interactive', '--max-tokens', '8000']
  timeout_seconds: 600

prioritization:
  important_senders:
    - ceo@company.com
    - legal@company.com
  priority_weights:
    high: 10
    medium: 5
    low: 0
  deadline_weights:
    critical: 20  # < 2 hours
    urgent: 10    # < 1 day
    soon: 5       # < 1 week

retry:
  max_attempts: 5
  delays: [60, 300, 900, 3600, 14400]  # 1m, 5m, 15m, 1h, 4h

notifications:
  escalation_channels: [email, slack]
  email:
    smtp_server: smtp.company.com
    from: fte@company.com
    to: ops@company.com
  slack:
    webhook_url: ${SLACK_WEBHOOK_URL}
    channel: #fte-alerts

process_management:
  pm2_config: ecosystem.config.js
  auto_restart: true
```

### A2: PM2 Configuration

```javascript
// ecosystem.config.js

module.exports = {
  apps: [
    {
      name: 'orchestrator',
      script: 'python',
      args: '-m src.orchestrator',
      cwd: '/path/to/AI_Employee/',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '500M',
      env: {
        VAULT_PATH: '/path/to/AI_Employee_Vault',
        LOG_LEVEL: 'INFO',
        CLAUDE_API_KEY: process.env.CLAUDE_API_KEY,
      },
      error_file: '/var/log/fte/orchestrator-error.log',
      out_file: '/var/log/fte/orchestrator-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      min_uptime: '10s',
      max_restarts: 3,
    },
  ],
};
```

### A3: CLI Commands Reference

```bash
# Start orchestrator (Ralph Wiggum Loop)
fte orchestrator start

# Stop orchestrator (creates stop hook)
fte orchestrator stop

# Resume orchestrator (removes stop hook)
fte orchestrator resume

# Check status
fte orchestrator status

# View logs
fte orchestrator logs --tail 50 --follow

# View task queue
fte orchestrator queue

# View error queue
fte orchestrator errors

# Retry failed task manually
fte orchestrator retry <task-id>

# Clear error queue
fte orchestrator clear-errors

# View metrics
fte orchestrator metrics
```

---

## Change Log

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-01-28 | v1.0 | AI Employee Team | Initial specification |

---

**Next Steps:**
1. Review spec with stakeholders
2. Generate implementation plan using `/sp.plan`
3. Generate task breakdown using `/sp.tasks`
4. Begin Silver Tier implementation (task discovery, Claude invocation)

---

*This specification is part of the Personal AI Employee Hackathon 0 project. For related specs, see:*
- *[P2: Logging Infrastructure](../002-logging-infrastructure/spec.md)*
- *[P3: CLI Integration Roadmap](../003-cli-integration-roadmap/spec.md)*
- *[P4: MCP Threat Model](../004-mcp-threat-model/spec.md)*
- *[P5: Watcher Scripts](../005-watcher-scripts/spec.md)*

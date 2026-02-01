# Implementation Plan: Orchestrator & Scheduler

**Branch**: `006-orchestrator-scheduler` | **Date**: 2026-01-28 | **Spec**: [specs/006-orchestrator-scheduler/spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-orchestrator-scheduler/spec.md`

## Summary

Build an autonomous orchestrator daemon that implements the "Ralph Wiggum Loop" - continuously monitoring the Obsidian vault for tasks in `/Needs_Action`, prioritizing them, invoking Claude Code, enforcing Human-in-the-Loop (HITL) approvals, and managing task state transitions until completion. The orchestrator is the "brain stem" that coordinates all AI Employee components into autonomous workflows.

**Key Approach**: Python daemon with file system watcher (`watchdog`), priority queue for task scheduling, subprocess invocation of Claude Code CLI, HITL approval checking before dangerous actions, stop hook pattern for emergency halts, exponential backoff retry logic.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: watchdog>=3.0.0, schedule>=1.2.0, psutil>=5.9.0, click>=8.1.0
**Storage**: Obsidian vault (file-based), checkpoint files for orchestrator state
**Testing**: pytest>=7.4.0, pytest-mock for subprocess mocking
**Target Platform**: Linux/macOS (primary), Windows (secondary)
**Project Type**: Single project (daemon)
**Performance Goals**: <1s task discovery latency, support 10 concurrent Claude invocations
**Constraints**: ADDITIVE ONLY - no control plane modifications, respect stop hooks, enforce HITL approval
**Scale/Scope**: Process 100+ tasks/day, support 5 concurrent executions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **Section 2 (Source of Truth)**: Vault is source of truth, orchestrator reads state from files
✅ **Section 4 (File-Driven Control Plane)**: Orchestrator respects folder-based state machine
✅ **Section 5 (Reasoning Discipline)**: Enforces Read → Think → Plan → Act → Verify loop
✅ **Section 6-7 (Autonomy & HITL)**: Checks approvals before sensitive actions
✅ **Section 8 (Auditability)**: All orchestration decisions logged
✅ **Section 10 (Ralph Wiggum Rule)**: Continuous loop until task in `/Done` or hard failure
✅ **Section 11 (No Spec Drift)**: Strict implementation of spec requirements

## Project Structure

### Documentation (this feature)

```text
specs/006-orchestrator-scheduler/
├── plan.md              # This file
├── research.md          # Scheduling algorithms, Claude CLI invocation
├── data-model.md        # Priority scoring, task state machine
├── quickstart.md        # Orchestrator setup guide
└── contracts/           # Orchestrator API contracts
    ├── task-scheduler.md
    ├── priority-scorer.md
    └── claude-invoker.md
```

### Source Code (repository root)

```text
src/orchestrator/
├── __init__.py          # Orchestrator module exports
├── scheduler.py         # Main orchestrator daemon (Ralph Wiggum Loop)
├── priority_scorer.py   # Task prioritization algorithm
├── claude_invoker.py    # Claude Code CLI subprocess wrapper
├── approval_checker.py  # HITL approval enforcement
├── stop_hook.py         # Stop hook pattern implementation
├── state_machine.py     # Task state transition management
└── models.py            # Orchestrator data models

config/
└── orchestrator.yaml    # Orchestrator configuration

scripts/
└── run_orchestrator.py  # Orchestrator entry point (PM2 runs this)

tests/orchestrator/
├── test_scheduler.py
├── test_priority_scorer.py
├── test_claude_invoker.py
└── test_orchestrator_integration.py

.fte/
├── orchestrator.checkpoint.json  # Orchestrator state
└── pm2.config.js        # PM2 process configuration (add orchestrator)
```

**Structure Decision**: New `src/orchestrator/` module for autonomous execution engine. Integrates with existing control plane via file system operations only (no code modifications).

## Complexity Tracking

> No constitutional violations - all gates passing.

## Phase 0: Research & Technology Selection

### Research Areas

1. **Task Prioritization Algorithm**
   - **Question**: How to score task priority (urgency + importance + deadline)?
   - **Options**: Eisenhower Matrix, weighted scoring, machine learning-based
   - **Recommendation**: Weighted scoring with configurable weights (urgency: 0.4, deadline: 0.3, sender_vip: 0.3)

2. **Claude Code Invocation**
   - **Question**: Subprocess vs HTTP API vs Python SDK?
   - **Options**: subprocess (`claude code <file>`), HTTP API (if available), Python SDK (if exists)
   - **Recommendation**: Subprocess invocation - most reliable, uses official CLI

3. **Stop Hook Pattern**
   - **Question**: How to implement emergency stop mechanism?
   - **Options**: Signal handling (SIGTERM), file-based hook (`.claude_stop`), database flag
   - **Recommendation**: File-based hook (`.claude_stop`) - simple, auditable, constitutional

4. **Concurrency Model**
   - **Question**: Serial execution vs parallel task processing?
   - **Options**: Single-threaded (simple), thread pool, process pool, async/await
   - **Recommendation**: Process pool (multiprocessing) - isolate Claude invocations, limit concurrency

### Research Deliverable: `research.md`

Document containing:
- Priority scoring algorithm comparison
- Claude Code CLI invocation patterns
- Stop hook design patterns
- Concurrency model analysis (threads vs processes vs async)
- Error recovery strategies

## Phase 1: Design & Contracts

### Data Model (`data-model.md`)

**Priority Scoring Formula**:
```python
priority_score = (
    urgency_weight * urgency_score +      # 0.4 * (1-5)
    deadline_weight * deadline_urgency +   # 0.3 * (1-5)
    sender_weight * sender_importance      # 0.3 * (1-5)
)

urgency_score:
  - 5: Keyword "URGENT" in subject
  - 4: Keyword "ASAP" or "high priority"
  - 3: Normal
  - 2: Keyword "low priority"
  - 1: Keyword "whenever"

deadline_urgency:
  - 5: Deadline <24 hours
  - 4: Deadline <3 days
  - 3: Deadline <1 week
  - 2: Deadline <1 month
  - 1: No deadline

sender_importance:
  - 5: CEO, Board member (VIP list)
  - 4: Client (client list)
  - 3: Team member
  - 2: External contact
  - 1: Unknown sender
```

**Task State Machine**:
```
NEEDS_ACTION → PLANNING → PENDING_APPROVAL → EXECUTING → DONE
      ↓            ↓             ↓                ↓          ↑
   REJECTED ← ── ← ─ ← ── ← ── ← ─ ← ── ← ── ← ─ ┘
```

**Orchestrator Checkpoint**:
```json
{
  "last_iteration_time": "2026-01-28T10:30:00Z",
  "tasks_processed": 42,
  "current_tasks": {
    "gmail_user_2026-01-28": {
      "state": "EXECUTING",
      "claude_pid": 12345,
      "attempts": 1
    }
  },
  "stop_requested": false
}
```

### API Contracts (`contracts/`)

**task-scheduler.md**:
```python
# Task Scheduler (Ralph Wiggum Loop)
class Orchestrator:
    def run(self) -> None:
        """
        Main orchestration loop ("Ralph Wiggum Loop").

        Loop:
            1. Discover tasks in /Needs_Action
            2. Score and prioritize tasks
            3. Select highest priority task
            4. Check stop hook
            5. Invoke Claude Code
            6. Check for HITL approvals
            7. Wait for completion or timeout
            8. Log results
            9. Update checkpoint
            10. Sleep (configurable interval)
            11. Repeat

        Exits when:
            - Stop hook detected (.claude_stop file)
            - SIGTERM received
            - Max iterations reached (configurable)
        """

    def check_stop_hook(self) -> bool:
        """
        Check for emergency stop signal.

        Returns:
            True if .claude_stop file exists in vault root
        """
```

**priority-scorer.md**:
```python
# Priority Scorer
class PriorityScorer:
    def score_task(self, task_file: Path) -> float:
        """
        Calculate priority score for task.

        Args:
            task_file: Path to task markdown file

        Returns:
            Priority score (0.0-5.0)

        Algorithm:
            1. Parse YAML frontmatter
            2. Extract urgency, deadline, sender
            3. Apply weighted formula
            4. Return normalized score
        """
```

**claude-invoker.md**:
```python
# Claude Code Invoker
class ClaudeInvoker:
    def invoke(
        self,
        task_file: Path,
        timeout: int = 3600
    ) -> subprocess.CompletedProcess:
        """
        Invoke Claude Code CLI for task processing.

        Command:
            claude code <task_file>

        Returns:
            CompletedProcess with stdout/stderr

        Raises:
            TimeoutError: Claude execution exceeded timeout
            CalledProcessError: Claude returned non-zero exit code
        """

    def kill(self, pid: int) -> None:
        """
        Terminate Claude process (emergency stop).
        """
```

### Quickstart Guide (`quickstart.md`)

```markdown
# Orchestrator Quickstart

## Configuration

Edit `config/orchestrator.yaml`:
```yaml
orchestrator:
  poll_interval: 30  # seconds
  max_concurrent_tasks: 5
  claude_timeout: 3600  # 1 hour per task
  stop_hook_file: .claude_stop

priority_weights:
  urgency: 0.4
  deadline: 0.3
  sender: 0.3

vip_senders:
  - ceo@company.com
  - board@company.com
```

## Start Orchestrator

```bash
# Start orchestrator daemon
fte orchestrator start

# Check status
fte orchestrator status

# View logs
fte orchestrator logs --tail 50

# Stop orchestrator
fte orchestrator stop
```

## Emergency Stop

```bash
# Create stop hook
touch ~/AI_Employee_Vault/.claude_stop

# Orchestrator will stop after current task completes
# Remove hook to resume
rm ~/AI_Employee_Vault/.claude_stop
```

## Monitor Execution

```bash
# Watch orchestrator dashboard
fte orchestrator dashboard

# Check current tasks
fte orchestrator tasks

# View priority queue
fte orchestrator queue
```
```

## Phase 2: Implementation Roadmap

### Bronze Tier (Week 1-2): Core Orchestration Loop

**Milestone**: Basic Ralph Wiggum Loop with single-task execution

**Tasks**:
1. Implement `Orchestrator` main loop
2. Create `PriorityScorer` with weighted formula
3. Implement `ClaudeInvoker` subprocess wrapper
4. Add file system watcher for `/Needs_Action`
5. Implement stop hook pattern
6. Create checkpoint system
7. Write unit tests
8. PM2 configuration

**Deliverables**:
- Working orchestrator (single-task execution)
- Priority scoring algorithm
- Claude Code invocation
- Stop hook mechanism
- Basic error handling

### Silver Tier (Week 3-4): HITL Enforcement & Concurrency

**Milestone**: Multi-task execution, approval enforcement

**Tasks**:
1. Implement `ApprovalChecker` for HITL enforcement
2. Add concurrent task execution (process pool)
3. Enhance error recovery (retry logic, exponential backoff)
4. Add state machine validation
5. CLI integration (`fte orchestrator` commands)
6. Integration tests
7. Performance optimization

**Deliverables**:
- HITL approval checking before dangerous actions
- Concurrent task execution (5 tasks max)
- Robust error recovery
- CLI orchestrator management
- Integration tests

### Gold Tier (Week 5-6): Advanced Features & Monitoring

**Milestone**: Production-ready orchestrator with monitoring

**Tasks**:
1. Implement orchestrator dashboard (`fte orchestrator dashboard`)
2. Add task queue visualization
3. Implement metrics collection (throughput, latency, errors)
4. Add smart retry strategies (task-specific backoff)
5. Create health check API
6. Comprehensive documentation
7. Load testing

**Deliverables**:
- Real-time orchestrator dashboard
- Task queue visualization
- Performance metrics
- Health monitoring
- Production deployment guide

## Testing Strategy

### Unit Tests
```python
def test_priority_scorer():
    scorer = PriorityScorer()
    task = Task(urgency=5, deadline=datetime.now() + timedelta(hours=12), sender="ceo@company.com")
    score = scorer.score_task(task)
    assert score > 4.0  # High priority

def test_stop_hook():
    orchestrator = Orchestrator()
    Path(".claude_stop").touch()
    assert orchestrator.check_stop_hook() == True
```

### Integration Tests
- End-to-end orchestration with mock Claude responses
- HITL approval workflow integration
- Error recovery scenarios
- Concurrent task execution

### Load Tests
- 100 tasks in queue
- 10 concurrent executions
- Resource usage monitoring (CPU, RAM)

## Risk Analysis

### Risk 1: Claude Code Hangs/Crashes
**Impact**: High (orchestrator blocked)
**Mitigation**: Timeout mechanism, health checks, process monitoring

### Risk 2: Approval Bypass
**Impact**: Critical (dangerous actions executed without approval)
**Mitigation**: Strict approval checking, audit logging, manual override disabled

### Risk 3: Task Starvation
**Impact**: Medium (low-priority tasks never execute)
**Mitigation**: Age-based priority boost, fairness algorithm

## Architectural Decision Records

### ADR-001: Ralph Wiggum Loop Pattern

**Decision**: Implement continuous orchestration loop ("Ralph Wiggum Loop")

**Rationale**:
- Enables autonomous operation
- Constitutional requirement (Section 10)
- Simple to understand and debug
- Supports emergency stop

**Loop Invariant**:
- Task is in `/Done` OR hard failure logged
- Never infinite loop (max iterations enforced)

### ADR-002: File-Based Stop Hook

**Decision**: Use `.claude_stop` file for emergency stop

**Rationale**:
- Simple to implement and understand
- Auditable (file creation timestamp)
- Works across all platforms
- No process signaling complexity
- Graceful shutdown (completes current task)

### ADR-003: Process Pool for Concurrency

**Decision**: Use multiprocessing.Pool for concurrent Claude invocations

**Rationale**:
- Isolates Claude processes
- Limits resource usage
- Easy to implement timeout
- Better than threading (GIL bypass)

## Integration Points

### P1 Control Plane
- Orchestrator reads task state from vault folders
- Respects state machine transitions
- No modifications to control plane code

### P2 Logging Infrastructure
- All orchestration events logged
- Query orchestrator logs: `fte logs query --module orchestrator`

### P3 CLI Integration
- `fte orchestrator` command group
- Start, stop, status, dashboard commands

### P5 Watcher Scripts
- Watchers create tasks in `/Inbox`
- Orchestrator moves to `/Needs_Action` after discovery

### Claude Code
- Orchestrator invokes `claude code <file>` via subprocess
- Captures stdout/stderr for logging
- Monitors process for completion/timeout

## Success Metrics

### Functionality
- [ ] Continuous autonomous operation (Ralph Wiggum Loop)
- [ ] Priority-based task execution
- [ ] HITL approval enforcement (100% compliance)
- [ ] Stop hook works (graceful shutdown)

### Reliability
- [ ] 99.9% orchestrator uptime
- [ ] Auto-recovery from Claude crashes
- [ ] Zero approval bypasses

### Performance
- [ ] Task discovery latency <1s
- [ ] Support 10 concurrent Claude invocations
- [ ] Process 100+ tasks/day without degradation

### Safety
- [ ] All dangerous actions require approval
- [ ] Emergency stop mechanism verified
- [ ] Complete audit trail

---

**Next Steps**: Run `/sp.tasks` to generate actionable task breakdown.

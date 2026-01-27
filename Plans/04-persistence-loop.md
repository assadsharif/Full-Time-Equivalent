# Feature Specification: Persistence Loop (Ralph Wiggum Rule)

**Created**: 2026-01-27
**Status**: Planning
**Priority**: P4 - Medium (Reliability)
**Constitutional Requirements**: Section 10

---

## Overview

Implement the "Ralph Wiggum Persistence Rule" - a bounded iteration loop that ensures multi-step tasks complete fully or fail explicitly. The system stays engaged with tasks until they reach /Done or a hard failure is logged, preventing silent abandonment while protecting against infinite loops.

---

## User Scenarios & Testing

### User Story 1 - Task Persistence Loop (Priority: P1)

**As a** Digital FTE system
**I want** to continuously work on tasks until completion
**So that** tasks are never silently abandoned or left incomplete

**Why this priority**: Core reliability feature - prevents task abandonment

**Independent Test**: Start multi-step task, verify system persists until /Done or failure

**Acceptance Scenarios**:

1. **Given** task in /Approved, **When** execution begins, **Then** system enters persistence loop until task reaches /Done
2. **Given** task encounters recoverable error, **When** retry is possible, **Then** system retries (up to max attempts)
3. **Given** task completes successfully, **When** moving to /Done, **Then** persistence loop exits cleanly
4. **Given** task encounters hard failure, **When** failure is logged, **Then** persistence loop exits with error

---

### User Story 2 - Bounded Iteration Protection (Priority: P1)

**As a** system administrator
**I want** loops to have maximum iteration limits
**So that** infinite loops are prevented and resources are protected

**Why this priority**: Safety mechanism - prevents runaway processes

**Independent Test**: Create task that would loop infinitely, verify max iterations enforced

**Acceptance Scenarios**:

1. **Given** persistence loop, **When** max iterations reached, **Then** loop exits and logs warning
2. **Given** stuck task, **When** iterations exceed limit, **Then** task moves to /Rejected with details
3. **Given** configurable max iterations, **When** setting limit, **Then** limit is respected across all tasks
4. **Given** iteration count, **When** approaching limit, **Then** system warns at 80% threshold

---

### User Story 3 - Progress Checkpointing (Priority: P2)

**As a** Digital FTE system
**I want** to checkpoint progress during multi-step tasks
**So that** partial work is not lost on interruption

**Why this priority**: Resilience - enables recovery from interruptions

**Independent Test**: Interrupt task mid-execution, restart, verify resume from checkpoint

**Acceptance Scenarios**:

1. **Given** multi-step task, **When** each step completes, **Then** progress is checkpointed to task file
2. **Given** task interruption, **When** resuming, **Then** system continues from last checkpoint
3. **Given** checkpointed state, **When** inspecting task file, **Then** progress is visible in metadata
4. **Given** task resume, **When** continuing, **Then** already-completed steps are skipped

---

### User Story 4 - Explicit Failure Handling (Priority: P2)

**As a** human owner
**I want** clear indication of why tasks fail
**So that** I can understand issues and take corrective action

**Why this priority**: Transparency - builds trust through clear communication

**Independent Test**: Cause various failure scenarios, verify clear failure reporting

**Acceptance Scenarios**:

1. **Given** task failure, **When** hard failure occurs, **Then** task file includes: failure reason, stack trace, checkpoint state, retry history
2. **Given** transient failure, **When** retry succeeds, **Then** log includes recovery details
3. **Given** permanent failure, **When** max retries exhausted, **Then** task moves to /Rejected with summary
4. **Given** failure in /Rejected, **When** human reviews, **Then** all context for debugging is available

---

### Edge Cases

- What happens if system crashes during persistence loop?
- How does system handle tasks that take hours/days to complete?
- What if max iterations is too low for legitimate long-running tasks?
- How does system handle external dependencies that become unavailable?
- What if checkpointing fails (disk full)?

---

## Requirements

### Functional Requirements

**FR-001**: System MUST implement persistence loop for all tasks in /Approved state

**FR-002**: System MUST continue loop until task reaches /Done OR hard failure is recorded

**FR-003**: System MUST enforce maximum iteration limit (configurable, default: 100)

**FR-004**: System MUST checkpoint progress after each significant step

**FR-005**: System MUST resume from last checkpoint on restart/resume

**FR-006**: System MUST distinguish between transient failures (retry) and hard failures (stop)

**FR-007**: System MUST implement exponential backoff for retries (1s, 2s, 4s, 8s, 16s)

**FR-008**: System MUST log each iteration with: iteration number, action taken, result, next state

**FR-009**: System MUST warn when approaching max iterations (at 80% threshold)

**FR-010**: System MUST move task to /Rejected when max iterations exceeded with full context

**FR-011**: System MUST support manual loop interruption (via flag file or signal)

**FR-012**: System MUST validate loop exit conditions on every iteration

### Key Entities

- **PersistenceLoop**: Loop state (task_id, iteration_count, max_iterations, started_at, last_checkpoint)
- **Checkpoint**: Progress snapshot (step_number, completed_steps, current_step, state_data, timestamp)
- **RetryPolicy**: Retry configuration (max_attempts, backoff_strategy, retriable_errors)
- **LoopExit**: Exit condition (reason, success, iteration_count, duration, final_state)
- **IterationLog**: Per-iteration record (iteration, action, result, duration, next_action)

---

## Success Criteria

### Measurable Outcomes

**SC-001**: 0 tasks silently abandoned (all reach /Done or /Rejected)

**SC-002**: 100% of loop exits are logged with clear reason

**SC-003**: 0 infinite loops (all respect max iterations)

**SC-004**: Task resume success rate > 95% after interruption

**SC-005**: Checkpoint writes complete in < 100ms (p95)

**SC-006**: Loop iteration overhead < 50ms (p95)

---

## Assumptions

- Task files support metadata updates (YAML frontmatter)
- File system is reliable for checkpoint writes
- Tasks have discrete, identifiable steps
- System can detect task completion conditions
- Max iterations default (100) is sufficient for most tasks

---

## Out of Scope

- Distributed task execution (Phase 3)
- Real-time progress monitoring UI (Phase 3)
- Advanced retry strategies (Phase 2)
- Task prioritization within loop (Phase 2)
- Parallel task execution (Phase 2)

---

## Non-Functional Requirements

**Performance:**
- Loop iteration: < 50ms overhead
- Checkpoint write: < 100ms
- State inspection: < 10ms

**Reliability:**
- No data loss on interruption
- Clean recovery from crashes
- Graceful handling of resource limits

**Observability:**
- Clear progress indicators
- Detailed iteration logs
- Transparent failure reporting

**Safety:**
- Bounded iterations (no infinite loops)
- Resource consumption monitoring
- Timeout enforcement

---

## Persistence Loop Algorithm

```python
def persistence_loop(task_id, max_iterations=100):
    """
    Execute task with bounded persistence until completion or failure.

    Returns: (success: bool, final_state: str, iterations: int)
    """
    iteration = 0
    task = load_task(task_id)
    checkpoint = load_checkpoint(task_id) or initial_checkpoint()

    while iteration < max_iterations:
        iteration += 1
        log_iteration(task_id, iteration)

        # Check exit conditions
        if task.state == "Done":
            return success_exit(task_id, iteration)

        if hard_failure_detected(task):
            return failure_exit(task_id, iteration, "hard_failure")

        # Warn approaching limit
        if iteration >= max_iterations * 0.8:
            log_warning(f"Task {task_id} approaching max iterations")

        # Execute next step
        try:
            result = execute_next_step(task, checkpoint)

            if result.success:
                checkpoint = update_checkpoint(checkpoint, result)
                save_checkpoint(task_id, checkpoint)

                # Check if task complete
                if all_steps_complete(checkpoint):
                    move_task(task, "/Done")
                    return success_exit(task_id, iteration)

            elif result.transient_error:
                # Retry with backoff
                backoff_delay = calculate_backoff(result.retry_count)
                sleep(backoff_delay)
                continue

            else:
                # Hard failure
                log_failure(task_id, result.error)
                move_task(task, "/Rejected")
                return failure_exit(task_id, iteration, "execution_error")

        except InterruptionRequest:
            # Manual stop requested
            save_checkpoint(task_id, checkpoint)
            return interrupted_exit(task_id, iteration)

        except Exception as e:
            # Unexpected error
            log_exception(task_id, e)
            save_checkpoint(task_id, checkpoint)
            move_task(task, "/Rejected")
            return failure_exit(task_id, iteration, "unexpected_error")

    # Max iterations exceeded
    log_warning(f"Task {task_id} exceeded max iterations ({max_iterations})")
    move_task(task, "/Rejected")
    return failure_exit(task_id, iteration, "max_iterations")
```

---

## Checkpoint Format

```yaml
# Task file frontmatter
---
id: task-001
state: Approved
created: 2026-01-27T10:00:00Z
persistence_loop:
  started: 2026-01-27T10:05:00Z
  iteration: 15
  max_iterations: 100
  checkpoint:
    completed_steps:
      - step_1: read_input
      - step_2: validate_data
      - step_3: transform_data
    current_step: step_4_execute_api_call
    state_data:
      api_attempt: 2
      last_error: "timeout"
    timestamp: 2026-01-27T10:06:30Z
---

# Task content...
```

---

## Retry Strategy

### Transient Errors (Retry)
- Network timeouts
- Rate limit exceeded
- Temporary service unavailable
- Lock acquisition failures

**Retry Policy:**
- Max attempts: 3
- Backoff: Exponential (1s, 2s, 4s, 8s, 16s)
- Jitter: ±20% to prevent thundering herd

### Hard Failures (Stop)
- Invalid input data
- Permission denied
- Resource not found
- Validation errors
- Logic errors

**Failure Action:**
- Log full context
- Move to /Rejected
- Exit loop immediately

---

## Dependencies

- YAML parser for checkpoint data
- File system for reliable checkpointing
- Retry library with exponential backoff
- Signal handling for interruption
- State machine for task states

---

## Constitutional Compliance

This feature directly implements:
- **Section 10.1**: Multi-step tasks must use persistence loop
- **Section 10.2**: System must not exit until task in /Done or hard failure logged
- **Section 10.3**: Infinite loops forbidden; max iterations must be enforced
- **Section 5**: Reasoning Discipline - Read → Think → Plan → Act → Write → Verify (loop enforces discipline)
- **Section 9**: Error Handling - Partial completion preferred over silent failure

---

## Configuration

```yaml
# .specify/config/persistence.yaml
persistence_loop:
  max_iterations: 100
  warn_threshold: 0.8  # Warn at 80% of max
  checkpoint_interval: 1  # Checkpoint after every step
  retry:
    max_attempts: 3
    backoff_strategy: exponential
    base_delay: 1.0  # seconds
    max_delay: 16.0  # seconds
    jitter: 0.2  # ±20%
  timeout:
    per_step: 300  # 5 minutes per step
    total: 3600  # 1 hour total per task
```

---

*The Ralph Wiggum Persistence Rule ensures tasks never fall through the cracks - they're either completed or explicitly failed with full context.*

# Tasks: Orchestrator & Scheduler

**Input**: Design documents from `/specs/006-orchestrator-scheduler/`
**Prerequisites**: plan.md ✅, spec.md ✅

**Status**: Bronze ✅ DONE | Silver ✅ DONE | Gold ✅ MOSTLY DONE | Platinum ❌ NOT STARTED

**Completed Work**:
- ✅ Bronze/Silver Tier: Scheduler (Ralph Wiggum Loop), PriorityScorer, ClaudeInvoker, ApprovalChecker, StopHook
- ✅ Gold Tier B: Ralph Wiggum Loop (infinite autonomous loop with stop hook) - commit 8280821
- ✅ Gold Tier C: Persistence loop with bounded retry and checkpointing - commit 1dbaffb
- ✅ HITL Integration: Approve-then-resume flow - commit f25cf7a
- ✅ Core Module: 1339 lines across 9 files (scheduler.py, priority_scorer.py, claude_invoker.py, approval_checker.py, stop_hook.py, persistence_loop.py, state_machine.py, models.py)

**This Document**: Tasks for remaining Gold/Platinum tier features (dashboard, metrics, health check, advanced monitoring)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to  (e.g., US7, US8)
- Include exact file paths in descriptions

---

## Phase 1: Setup (No additional setup needed)

**Bronze/Silver/Gold infrastructure complete**. Existing structure:

```
src/orchestrator/
├── __init__.py              ✅ Module exports
├── scheduler.py             ✅ Ralph Wiggum Loop + persistence loop
├── priority_scorer.py       ✅ Task prioritization algorithm
├── claude_invoker.py        ✅ Subprocess invocation
├── approval_checker.py      ✅ HITL approval enforcement
├── stop_hook.py             ✅ Emergency stop mechanism
├── persistence_loop.py      ✅ Bounded retry + checkpointing
├── state_machine.py         ✅ Task state transitions
└── models.py                ✅ Orchestrator data models

.fte/
└── orchestrator.checkpoint.json  ✅ Orchestrator state persistence
```

---

## Phase 2: Foundational (No blocking prerequisites)

**All foundational work complete**. Silver/Gold tiers provide:
- Continuous autonomous operation (Ralph Wiggum Loop)
- Priority-based task scheduling
- Claude Code invocation via subprocess
- HITL approval checking before dangerous actions
- Stop hook for emergency halt
- Persistence loop with bounded retry (max 5 attempts)
- Checkpoint-based state recovery

**Checkpoint**: Foundation ready - Platinum tier enhancements can now be added

---

## Phase 3: User Story 7 - Orchestrator Dashboard (Priority: P5 - Platinum Tier)

**Goal**: Real-time dashboard showing orchestrator status, task queue, and metrics

**Independent Test**: Run `fte orchestrator dashboard` and verify live display of pending tasks, running tasks, and completion rate

### Implementation for User Story 7

- [ ] T001 [P] [US7] Create OrchestratorDashboard class in src/orchestrator/dashboard.py
- [ ] T002 [US7] Implement get_status method (running, stopped, error state) in src/orchestrator/dashboard.py
- [ ] T003 [US7] Implement get_queue method (pending tasks with priorities) in src/orchestrator/dashboard.py
- [ ] T004 [US7] Implement get_active_tasks method (currently executing tasks) in src/orchestrator/dashboard.py
- [ ] T005 [US7] Implement get_recent_completions method (last 10 tasks) in src/orchestrator/dashboard.py
- [ ] T006 [US7] Add dashboard CLI command (fte orchestrator dashboard) in src/cli/orchestrator.py
- [ ] T007 [US7] Implement live refresh mode (update every 5 seconds) in src/cli/orchestrator.py
- [ ] T008 [US7] Add colorized output (green=running, yellow=pending, red=error) in src/cli/orchestrator.py
- [ ] T009 [P] [US7] Add tests for dashboard data collection in tests/orchestrator/test_dashboard.py

**Checkpoint**: Dashboard operational - Live orchestrator visibility via CLI

---

## Phase 4: User Story 8 - Metrics Collection (Priority: P5 - Platinum Tier)

**Goal**: Collect and report orchestrator performance metrics

**Independent Test**: Query metrics via CLI and verify accuracy (tasks processed, avg latency, error rate)

### Implementation for User Story 8

- [ ] T010 [P] [US8] Create MetricsCollector class in src/orchestrator/metrics.py
- [ ] T011 [P] [US8] Add task_started event tracking in src/orchestrator/metrics.py
- [ ] T012 [P] [US8] Add task_completed event tracking in src/orchestrator/metrics.py
- [ ] T013 [P] [US8] Add task_failed event tracking in src/orchestrator/metrics.py
- [ ] T014 [US8] Implement calculate_throughput method (tasks/hour) in src/orchestrator/metrics.py
- [ ] T015 [US8] Implement calculate_avg_latency method (task duration avg) in src/orchestrator/metrics.py
- [ ] T016 [US8] Implement calculate_error_rate method (failures/total) in src/orchestrator/metrics.py
- [ ] T017 [US8] Integrate MetricsCollector into scheduler main loop in src/orchestrator/scheduler.py
- [ ] T018 [US8] Add metrics CLI command (fte orchestrator metrics) in src/cli/orchestrator.py
- [ ] T019 [US8] Add --since flag for time-based metrics (--since 24h, --since 7d) in src/cli/orchestrator.py
- [ ] T020 [P] [US8] Add tests for metrics calculation in tests/orchestrator/test_metrics.py

**Checkpoint**: Metrics collection working - Performance data queryable via CLI

---

## Phase 5: User Story 9 - Health Check API (Priority: P5 - Platinum Tier)

**Goal**: Expose health check endpoint for monitoring tools

**Independent Test**: Query health check and verify correct status (healthy, degraded, unhealthy)

### Implementation for User Story 9

- [ ] T021 [P] [US9] Create HealthCheck class in src/orchestrator/health_check.py
- [ ] T022 [US9] Implement check_scheduler_alive method in src/orchestrator/health_check.py
- [ ] T023 [US9] Implement check_task_backlog method (warn if >20 pending) in src/orchestrator/health_check.py
- [ ] T024 [US9] Implement check_error_rate method (warn if >10% failures) in src/orchestrator/health_check.py
- [ ] T025 [US9] Implement check_last_completion_time method (warn if >1h since last task) in src/orchestrator/health_check.py
- [ ] T026 [US9] Add get_health_status method (healthy/degraded/unhealthy) in src/orchestrator/health_check.py
- [ ] T027 [US9] Add health CLI command (fte orchestrator health) in src/cli/orchestrator.py
- [ ] T028 [US9] Add JSON output format for programmatic access (--json flag) in src/cli/orchestrator.py
- [ ] T029 [P] [US9] Add tests for health check logic in tests/orchestrator/test_health_check.py

**Checkpoint**: Health checks operational - Monitoring tools can query orchestrator status

---

## Phase 6: User Story 10 - Task Queue Visualization (Priority: P5 - Platinum Tier)

**Goal**: Visualize task queue with priorities and wait times

**Independent Test**: Run `fte orchestrator queue` and verify pending tasks displayed with scores

### Implementation for User Story 10

- [ ] T030 [P] [US10] Create QueueVisualizer class in src/orchestrator/queue_visualizer.py
- [ ] T031 [US10] Implement format_task_entry method (name, priority score, wait time) in src/orchestrator/queue_visualizer.py
- [ ] T032 [US10] Implement render_queue_table method (ASCII table with columns) in src/orchestrator/queue_visualizer.py
- [ ] T033 [US10] Add queue CLI command (fte orchestrator queue) in src/cli/orchestrator.py
- [ ] T034 [US10] Add --verbose flag to show task details in src/cli/orchestrator.py
- [ ] T035 [US10] Add --watch mode for live queue updates in src/cli/orchestrator.py
- [ ] T036 [P] [US10] Add tests for queue visualization in tests/orchestrator/test_queue_visualizer.py

**Checkpoint**: Queue visualization complete - Pending tasks visible with priorities

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Configuration, documentation, testing, and operational improvements

- [ ] T037 [P] Create orchestrator configuration file template in config/orchestrator.yaml
- [ ] T038 [P] Add smart retry strategies (exponential backoff per task type) in src/orchestrator/persistence_loop.py
- [ ] T039 [P] Add task age-based priority boost (old tasks get score boost) in src/orchestrator/priority_scorer.py
- [ ] T040 [P] Add --dry-run mode to CLI commands for testing in src/cli/orchestrator.py
- [ ] T041 [P] Create orchestrator deployment guide in docs/ORCHESTRATOR_DEPLOYMENT.md
- [ ] T042 [P] Add orchestrator troubleshooting guide in docs/ORCHESTRATOR_TROUBLESHOOTING.md
- [ ] T043 [P] Create end-to-end orchestrator test (task discovery → prioritization → execution → completion) in tests/integration/test_orchestrator_e2e.py
- [ ] T044 [P] Add load tests (100 tasks, 10 concurrent) in tests/performance/test_orchestrator_load.py
- [ ] T045 [P] Add resource usage monitoring (CPU, RAM) to metrics in src/orchestrator/metrics.py
- [ ] T046 [P] Add webhook notifications for orchestrator events in src/orchestrator/webhooks.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1-2**: Complete ✅
- **Phase 3-6**: User Stories can proceed in parallel (all independent)
  - US7 (Dashboard): No dependencies
  - US8 (Metrics): No dependencies
  - US9 (Health Check): Benefits from US8 (metrics) but not blocked
  - US10 (Queue Visualization): No dependencies
- **Phase 7**: Can start anytime, runs in parallel with user stories

### User Story Dependencies

- **User Story 7 (Dashboard)**: Can start immediately - No dependencies
- **User Story 8 (Metrics)**: Can start immediately - No dependencies
- **User Story 9 (Health Check)**: Can start immediately - Optional integration with US8 metrics
- **User Story 10 (Queue Visualization)**: Can start immediately - No dependencies

### Within Each User Story

- US7: Dashboard class → CLI integration → live refresh → tests
- US8: MetricsCollector class → scheduler integration → CLI → tests
- US9: HealthCheck class → status checks → CLI → JSON output → tests
- US10: QueueVisualizer class → table rendering → CLI → watch mode → tests

### Parallel Opportunities

- **Phase 3-6**: All four user stories (US7, US8, US9, US10) can be developed in parallel by different team members
- Within US8: Tasks T010-T013 (event tracking) can run in parallel
- Within US9: Tasks T022-T025 (health checks) can run in parallel
- Polish tasks (T037-T046) can all run in parallel

---

## Parallel Example: User Story 8 (Metrics)

```bash
# Launch all event tracking in parallel:
Task T011: "Add task_started event tracking in src/orchestrator/metrics.py"
Task T012: "Add task_completed event tracking in src/orchestrator/metrics.py"
Task T013: "Add task_failed event tracking in src/orchestrator/metrics.py"

# Then calculate metrics:
Task T014: "Implement calculate_throughput method"
Task T015: "Implement calculate_avg_latency method"
Task T016: "Implement calculate_error_rate method"

# Then CLI integration:
Task T018: "Add metrics CLI command"
```

---

## Implementation Strategy

### Recommended Order (Sequential)

1. **US8 (Metrics Collection)** - Foundation for other features
   - Tasks T010-T020 (11 tasks)
   - Enables performance tracking

2. **US9 (Health Check)** - Uses US8 metrics
   - Tasks T021-T029 (9 tasks)
   - Enables monitoring integration

3. **US7 (Dashboard)** - Visualizes US8 metrics
   - Tasks T001-T009 (9 tasks)
   - Operator visibility

4. **US10 (Queue Visualization)** - Independent visualization
   - Tasks T030-T036 (7 tasks)
   - Task queue transparency

5. **Polish (Phase 7)** - Final hardening
   - Tasks T037-T046 (10 tasks)
   - Config, docs, tests, webhooks

### Parallel Team Strategy

With 4 developers:

1. Complete existing Silver/Gold validation together
2. Then split:
   - Developer A: US8 (Metrics) → US9 (Health Check) → Polish (Docs)
   - Developer B: US7 (Dashboard) → Polish (Load Tests)
   - Developer C: US10 (Queue Viz) → Polish (Webhooks)
   - Developer D: Polish (Config, E2E Tests, Resource Monitoring)
3. All features integrate via existing Scheduler interface

### MVP Definition

**Current State (Silver + Gold B+C)** is already production-ready:
- ✅ Continuous autonomous operation
- ✅ Priority-based scheduling
- ✅ HITL approval enforcement
- ✅ Bounded retry with persistence
- ✅ Stop hook for emergency halt

**Next MVP (Platinum Core)**: US8 + US9
- Add metrics collection
- Add health monitoring
- Enable production monitoring

**Full Platinum**: US7 + US8 + US9 + US10
- Complete observability stack

---

## Notes

- Silver/Gold implementation already handles concurrency via persistence loop
- Ralph Wiggum Loop runs indefinitely until stop hook detected
- Bounded retry: max 5 attempts with exponential backoff
- Checkpoint saved after every task completion
- Metrics should be time-series (not just counters) for trend analysis
- Health check should integrate with monitoring tools (Prometheus, Datadog)
- Dashboard should support --watch mode with configurable refresh interval
- Queue visualization should show estimated completion times
- All CLI commands should support --json flag for programmatic access
- Configuration file (orchestrator.yaml) should support environment variable substitution

---

## Test Coverage Goals

- **Unit Tests**: 85%+ coverage for new modules (dashboard, metrics, health_check, queue_visualizer)
- **Integration Tests**: End-to-end orchestrator workflow with metrics collection
- **Load Tests**: 100 tasks queued, 10 concurrent executions, verify no degradation
- **Performance Tests**: Metrics calculation <100ms, dashboard refresh <200ms

---

## Success Metrics

- [ ] Dashboard operational (real-time status, queue, completions)
- [ ] Metrics collection functional (throughput, latency, error rate)
- [ ] Health check API working (healthy/degraded/unhealthy status)
- [ ] Queue visualization complete (priorities, wait times)
- [ ] All tests passing (unit, integration, load, performance)
- [ ] Documentation complete (deployment, troubleshooting)
- [ ] Resource monitoring integrated (CPU, RAM usage)
- [ ] Webhook notifications operational

---

**Total Tasks**: 46
- User Story 7 (Dashboard): 9 tasks
- User Story 8 (Metrics): 11 tasks
- User Story 9 (Health Check): 9 tasks
- User Story 10 (Queue Visualization): 7 tasks
- Polish: 10 tasks

**Estimated Effort**:
- US8: 6-8 hours (metrics collection + integration + CLI)
- US9: 4-6 hours (health checks + CLI + JSON output)
- US7: 6-8 hours (dashboard + live refresh + colorization)
- US10: 4-6 hours (queue viz + table rendering + watch mode)
- Polish: 6-8 hours (config + docs + load tests + webhooks)
- **Total**: 26-36 hours (3-4 days of focused work)

---

## Configuration Example

```yaml
# config/orchestrator.yaml

# Main orchestrator settings
orchestrator:
  poll_interval: 30              # seconds between queue checks
  max_concurrent_tasks: 5        # max parallel Claude invocations
  claude_timeout: 3600           # seconds (1 hour per task)
  stop_hook_file: .claude_stop   # emergency stop trigger

# Priority scoring weights
priority_weights:
  urgency: 0.4                   # 40% weight on urgency keywords
  deadline: 0.3                  # 30% weight on deadline proximity
  sender: 0.3                    # 30% weight on sender importance

# VIP senders (get +10 priority score)
vip_senders:
  - ceo@company.com
  - board@company.com
  - legal@company.com

# Retry configuration
retry:
  max_attempts: 5                # max retry attempts per task
  initial_backoff: 60            # seconds (1 minute)
  backoff_multiplier: 2          # exponential backoff
  max_backoff: 3600              # seconds (1 hour max)

# Metrics settings
metrics:
  enabled: true
  retention_days: 30             # keep metrics for 30 days
  aggregation_interval: 300      # seconds (5 minutes)

# Health check thresholds
health_check:
  max_backlog: 20                # warn if >20 pending tasks
  max_error_rate: 0.10           # warn if >10% failures
  max_idle_time: 3600            # warn if no completions in 1 hour

# Dashboard settings
dashboard:
  refresh_interval: 5            # seconds
  max_recent_tasks: 10           # show last 10 completions

# Notifications
notifications:
  enabled: true
  webhook_url: https://hooks.slack.com/services/...
  events:
    - task_failed
    - health_degraded
    - orchestrator_stopped
```

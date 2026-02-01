# Implementation Tasks: Logging Infrastructure (P2)

**Feature**: 002-logging-infrastructure
**Branch**: `002-logging-infrastructure`
**Status**: Ready for Implementation
**Total Tasks**: 78

**IMPORTANT**: No implementation before tasks are reviewed.

---

## Overview

This document provides the complete task breakdown for implementing the Logging Infrastructure feature. Tasks are organized by user story to enable independent implementation and testing of each story.

**User Stories** (from spec.md):
- **US1**: Developer Debugging (trace IDs, detailed logs)
- **US2**: Operator Monitoring (query logs, filter by level/time)
- **US3**: Compliance Auditing (retention, immutable logs)
- **US4**: Performance Optimization (metrics, operation durations)

**Implementation Strategy**:
- **MVP Scope**: US1 only (Developer Debugging) - 41 tasks
- **MVP+1**: Add US2 (Operator Monitoring) - +16 tasks
- **MVP+2**: Add US3 + US4 (Compliance + Performance) - +14 tasks
- **Polish**: Cross-cutting concerns - +7 tasks

---

## Task Format

All tasks follow this strict format:

```
- [ ] [TaskID] [P?] [Story?] Description with file path
```

**Legend**:
- `[TaskID]`: Sequential ID (T001, T002, ...)
- `[P]`: Task is parallelizable (can run concurrently with others)
- `[US#]`: User story label (US1, US2, US3, US4)
- **No label**: Setup, foundational, or polish tasks

---

## Phase 1: Setup & Dependencies

**Goal**: Initialize project structure and install dependencies
**Duration**: 1-2 hours
**Independent Test**: `pytest --collect-only` succeeds, dependencies installed

### Tasks

- [ ] T001 Install python-ulid dependency in pyproject.toml (version >=2.0.0)
- [ ] T002 Install duckdb dependency in pyproject.toml (version >=0.9.0)
- [ ] T003 Install detect-secrets dev dependency in pyproject.toml (version >=1.4.0)
- [ ] T004 Create src/logging/ module directory with __init__.py
- [ ] T005 Create tests/unit/logging/ directory with __init__.py
- [ ] T006 Create tests/integration/logging/ directory with __init__.py
- [ ] T007 Create tests/performance/ directory with __init__.py
- [ ] T008 Create config/ directory for logging.yaml configuration
- [ ] T009 Create Logs/metrics/ directory for metric log files
- [ ] T010 Create Logs/archive/ directory for compressed log archives

**Parallel Opportunities**: T004-T010 can all run in parallel (different directories)

**Validation**:
```bash
# All directories exist
ls -la src/logging tests/unit/logging tests/integration/logging tests/performance config Logs/metrics Logs/archive

# Dependencies installed
python -c "import ulid; import duckdb; print('Dependencies OK')"
```

---

## Phase 2: Foundational Components

**Goal**: Implement core shared components needed by all user stories
**Duration**: 4-6 hours
**Dependencies**: Phase 1 complete
**Independent Test**: Unit tests for models, config, trace pass

### Tasks

- [ ] T011 [P] Implement LogLevel enum in src/logging/models.py (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- [ ] T012 [P] Implement LogEntry dataclass in src/logging/models.py per data-model.md
- [ ] T013 [P] Implement ExceptionInfo dataclass in src/logging/models.py
- [ ] T014 [P] Implement StackFrame dataclass in src/logging/models.py
- [ ] T015 [P] Implement MetricEntry dataclass in src/logging/models.py
- [ ] T016 [P] Implement MetricType enum in src/logging/models.py (COUNTER, GAUGE, DURATION, HISTOGRAM)
- [ ] T017 [P] Implement LoggerConfig dataclass in src/logging/config.py per data-model.md
- [ ] T018 Implement config loader (from_file) in src/logging/config.py to load logging.yaml
- [ ] T019 Implement config loader (from_env) in src/logging/config.py to load from environment variables
- [ ] T020 [P] Implement new_trace_id() function in src/logging/trace.py using ULID library
- [ ] T021 [P] Implement trace context manager (bind_trace_id) in src/logging/trace.py using contextvars
- [ ] T022 Create default logging.yaml config file in config/ with sensible defaults
- [ ] T023 [P] Write unit tests for LogEntry, ExceptionInfo models in tests/unit/logging/test_models.py
- [ ] T024 [P] Write unit tests for LoggerConfig in tests/unit/logging/test_config.py
- [ ] T025 [P] Write unit tests for trace ID generation in tests/unit/logging/test_trace.py

**Parallel Opportunities**: T011-T017, T020-T021, T023-T025 (different files, no dependencies)

**Validation**:
```bash
# Unit tests pass
pytest tests/unit/logging/test_models.py -v
pytest tests/unit/logging/test_config.py -v
pytest tests/unit/logging/test_trace.py -v

# Models can be imported
python -c "from src.logging.models import LogEntry, LogLevel; print('Models OK')"
```

---

## Phase 3: User Story 1 - Developer Debugging

**Goal**: Implement structured logging with trace IDs for debugging
**Duration**: 10-12 hours
**Dependencies**: Phase 2 complete
**Story Priority**: P1 (MUST HAVE for MVP)

**Acceptance Criteria** (from spec.md):
- ✅ Each operation has a unique trace ID
- ✅ Trace ID appears in all related log entries
- ✅ Logs show module, function, line number
- ✅ Stack traces captured for exceptions

**Independent Test**: Integration test shows trace ID propagation across multiple log calls, exception details captured

### Tasks

#### Secret Redaction (Foundational for US1)

- [ ] T026 [US1] Implement SecretRedactor class in src/logging/redaction.py with regex pattern matching
- [ ] T027 [US1] Add default secret patterns (api_key, Bearer token, password) to src/logging/redaction.py
- [ ] T028 [US1] Implement redact() method in src/logging/redaction.py (< 1μs per entry target)
- [ ] T029 [US1] Write unit tests for secret redaction in tests/unit/logging/test_redaction.py

#### Async Writer (Core US1 Infrastructure)

- [ ] T030 [US1] Implement AsyncWriter class in src/logging/async_writer.py with asyncio.Queue
- [ ] T031 [US1] Implement buffer management (max 1000 entries) in async_writer.py
- [ ] T032 [US1] Implement flush logic (1s interval OR buffer full) in async_writer.py
- [ ] T033 [US1] Implement background writer loop (_writer_loop) in async_writer.py
- [ ] T034 [US1] Implement file rotation (daily + 100MB size limit) in async_writer.py
- [ ] T035 [US1] Implement graceful shutdown (flush pending logs) in async_writer.py
- [ ] T036 [US1] Add error handling (fallback to stderr) in async_writer.py
- [ ] T037 [US1] Write unit tests for AsyncWriter in tests/unit/logging/test_async_writer.py

#### Logger Service (Core US1 API)

- [ ] T038 [US1] Implement LoggerService class skeleton in src/logging/logger_service.py
- [ ] T039 [US1] Implement __init__() with structlog configuration in logger_service.py
- [ ] T040 [US1] Implement log() method in logger_service.py per logger_service.md contract
- [ ] T041 [P] [US1] Implement debug(), info(), warning(), error(), critical() convenience methods in logger_service.py
- [ ] T042 [US1] Implement bind_context() context manager in logger_service.py using contextvars
- [ ] T043 [US1] Implement bind_trace_id() context manager in logger_service.py
- [ ] T044 [US1] Implement measure_duration() context manager in logger_service.py
- [ ] T045 [US1] Implement start_async_writer() method in logger_service.py
- [ ] T046 [US1] Implement stop_async_writer() method in logger_service.py
- [ ] T047 [US1] Implement flush() method in logger_service.py
- [ ] T048 [US1] Add automatic module/function/line injection using structlog processors
- [ ] T049 [US1] Add exception capture with full stack traces in logger_service.py

#### Public API & Integration

- [ ] T050 [US1] Create public API exports in src/logging/__init__.py (get_logger, init_logging, new_trace_id)
- [ ] T051 [US1] Implement get_logger() factory function in src/logging/__init__.py
- [ ] T052 [US1] Implement init_logging() initialization function in src/logging/__init__.py
- [ ] T053 [US1] Write unit tests for LoggerService in tests/unit/logging/test_logger_service.py
- [ ] T054 [US1] Write integration test for logging lifecycle in tests/integration/logging/test_logging_lifecycle.py
- [ ] T055 [US1] Write integration test for trace ID propagation in tests/integration/logging/test_trace_correlation.py
- [ ] T056 [US1] Write integration test for exception logging in tests/integration/logging/test_exception_logging.py

**Parallel Opportunities Within US1**:
- T026-T029 (redaction) can run parallel to T030-T037 (async writer)
- T041 (convenience methods) independent of other logger methods
- T053-T056 (tests) can be written in parallel once core implementation exists

**US1 Validation**:
```bash
# Unit tests pass
pytest tests/unit/logging/ -v

# Integration tests pass
pytest tests/integration/logging/test_logging_lifecycle.py -v
pytest tests/integration/logging/test_trace_correlation.py -v
pytest tests/integration/logging/test_exception_logging.py -v

# Manual smoke test
python -c "
from src.logging import init_logging, get_logger
init_logging(log_dir='./Logs', level='INFO')
logger = get_logger(__name__)
with logger.bind_trace_id() as trace_id:
    logger.info('Test message', context={'test': 'value'})
    print(f'Trace ID: {trace_id}')
"

# Verify log file created with trace ID
cat Logs/$(date +%Y-%m-%d).log | grep trace_id
```

**US1 Deliverables**:
- ✅ Structured logging with trace IDs
- ✅ Async non-blocking writes (< 5μs overhead)
- ✅ Automatic secret redaction
- ✅ Exception capture with stack traces
- ✅ Context binding for correlated logs
- ✅ Module/function/line metadata injection

---

## Phase 4: User Story 2 - Operator Monitoring

**Goal**: Enable operators to query and filter logs via CLI
**Duration**: 8-10 hours
**Dependencies**: US1 complete (needs log files to query)
**Story Priority**: P2 (Should Have for MVP+1)

**Acceptance Criteria** (from spec.md):
- ✅ CLI command to filter logs by level
- ✅ Time range filtering (last hour, last day, custom)
- ✅ Output format options (JSON, CSV, pretty-print)
- ✅ Performance: query 1GB logs in < 10s

**Independent Test**: CLI commands filter logs correctly, performance benchmarks pass

### Tasks

#### Query Service (Core US2)

- [ ] T057 [US2] Implement DuckDBAdapter class in src/logging/duckdb_adapter.py
- [ ] T058 [US2] Implement virtual table registration for NDJSON log files in duckdb_adapter.py
- [ ] T059 [US2] Implement LogQuery dataclass in src/logging/models.py per data-model.md
- [ ] T060 [US2] Implement QueryService class skeleton in src/logging/query_service.py
- [ ] T061 [US2] Implement __init__() with DuckDB connection in query_service.py
- [ ] T062 [US2] Implement query() method in query_service.py per query_service.md contract
- [ ] T063 [US2] Implement query_sql() method for raw SQL queries in query_service.py
- [ ] T064 [P] [US2] Implement filter_by_trace() method in query_service.py
- [ ] T065 [P] [US2] Implement filter_by_time_range() method in query_service.py
- [ ] T066 [P] [US2] Implement search_text() method (full-text search) in query_service.py
- [ ] T067 [US2] Write unit tests for QueryService in tests/unit/logging/test_query_service.py
- [ ] T068 [US2] Write performance benchmark for query operations in tests/performance/test_query_performance.py

#### CLI Tools (US2 User Interface)

- [ ] T069 [US2] Create CLI module src/cli/logs.py with click framework
- [ ] T070 [P] [US2] Implement 'fte logs tail' command in src/cli/logs.py
- [ ] T071 [P] [US2] Implement 'fte logs query' command with filters in src/cli/logs.py
- [ ] T072 [P] [US2] Implement 'fte logs search' command in src/cli/logs.py

**Parallel Opportunities Within US2**:
- T064-T066 (query methods) independent of each other
- T070-T072 (CLI commands) independent of each other

**US2 Validation**:
```bash
# Unit tests pass
pytest tests/unit/logging/test_query_service.py -v

# Performance benchmark meets < 10s requirement
pytest tests/performance/test_query_performance.py -v

# CLI commands work
fte logs tail --lines 100
fte logs query --level ERROR --start "2026-01-28 00:00:00"
fte logs search "disk full" --last 1h

# Verify query performance on large file
dd if=/dev/zero of=Logs/large-test.log bs=1M count=1024  # Create 1GB file
time fte logs query --level INFO --start "2026-01-01"  # Should be < 10s
```

**US2 Deliverables**:
- ✅ SQL query interface (DuckDB)
- ✅ Filter by level, time range, module
- ✅ Full-text search
- ✅ CLI commands (tail, query, search)
- ✅ Performance < 10s for 1GB logs

---

## Phase 5: User Story 3 - Compliance Auditing

**Goal**: Enforce log retention and ensure immutable audit trail
**Duration**: 4-6 hours
**Dependencies**: US1 complete (needs logging infrastructure)
**Story Priority**: P2 (Should Have for MVP+1)

**Acceptance Criteria** (from spec.md):
- ✅ All sensitive operations logged
- ✅ Logs include timestamp, actor, result
- ✅ Logs immutable (append-only)
- ✅ Retention policy enforced (30 days)

**Independent Test**: Archival script runs successfully, old logs compressed/deleted per policy

### Tasks

- [ ] T073 [US3] Implement LogArchive dataclass in src/logging/models.py per data-model.md
- [ ] T074 [US3] Implement Archival class in src/logging/archival.py
- [ ] T075 [US3] Implement compress_old_logs() method (compress logs > 7 days) in archival.py
- [ ] T076 [US3] Implement delete_expired_logs() method (delete logs > 30 days) in archival.py
- [ ] T077 [US3] Implement archive index management (index.json) in archival.py
- [ ] T078 [US3] Add log file permissions enforcement (600) in async_writer.py
- [ ] T079 [US3] Write unit tests for Archival in tests/unit/logging/test_archival.py
- [ ] T080 [US3] Write integration test for retention policy in tests/integration/logging/test_retention.py
- [ ] T081 [P] [US3] Implement 'fte logs export' command (JSON/CSV) in src/cli/logs.py
- [ ] T082 [US3] Implement query_archive() method in query_service.py for querying compressed logs

**Parallel Opportunities Within US3**:
- T078 (permissions) independent of T073-T077 (archival)
- T081 (export CLI) independent of archival implementation

**US3 Validation**:
```bash
# Unit tests pass
pytest tests/unit/logging/test_archival.py -v
pytest tests/integration/logging/test_retention.py -v

# Archival script runs successfully
python -m src.logging.archival --compress --days 7
ls -la Logs/archive/*.gz

# Retention enforced
python -m src.logging.archival --delete --days 30
# Old logs should be deleted

# File permissions correct
stat -c "%a" Logs/*.log  # Should show 600

# Export works
fte logs export errors.json --level ERROR --start "2026-01-28"
cat errors.json | jq '. | length'
```

**US3 Deliverables**:
- ✅ Automatic log compression (gzip, > 7 days)
- ✅ Automatic log deletion (> 30 days)
- ✅ Archive index for fast lookup
- ✅ File permissions enforced (600)
- ✅ Export to JSON/CSV

---

## Phase 6: User Story 4 - Performance Optimization

**Goal**: Log and analyze performance metrics (durations, I/O)
**Duration**: 4-6 hours
**Dependencies**: US1 complete (needs logging infrastructure), US2 helpful (query metrics)
**Story Priority**: P3 (Could Have for MVP+2)

**Acceptance Criteria** (from spec.md):
- ✅ Duration logged for all major operations
- ✅ File I/O metrics (read/write counts, sizes)
- ✅ Aggregation over time windows (hourly, daily)
- ✅ Top slowest operations report

**Independent Test**: Metrics logged to separate file, aggregations produce correct results

### Tasks

- [ ] T083 [US4] Implement log_metric() method in logger_service.py per contract
- [ ] T084 [US4] Implement metrics file writer (separate from application logs) in async_writer.py
- [ ] T085 [P] [US4] Implement count_by_level() aggregation in query_service.py
- [ ] T086 [P] [US4] Implement count_by_module() aggregation in query_service.py
- [ ] T087 [P] [US4] Implement aggregate_metrics() method in query_service.py
- [ ] T088 [P] [US4] Implement analyze_errors() method in query_service.py
- [ ] T089 [P] [US4] Implement 'fte logs stats' command in src/cli/logs.py
- [ ] T090 [P] [US4] Implement 'fte logs metrics' command in src/cli/logs.py
- [ ] T091 [US4] Write integration test for metrics logging in tests/integration/logging/test_metrics.py

**Parallel Opportunities Within US4**:
- T085-T088 (aggregation methods) all independent
- T089-T090 (CLI commands) independent

**US4 Validation**:
```bash
# Metrics logged separately
ls Logs/metrics/*.metrics.log

# Metrics aggregations work
python -c "
from src.logging import QueryService, LogQuery
from datetime import datetime, timedelta
qs = QueryService(log_dir='./Logs')
start = datetime.now() - timedelta(hours=24)
end = datetime.now()
avg = qs.aggregate_metrics('state_transition.duration', start, end, aggregation='avg')
print(f'Avg duration: {avg}ms')
"

# CLI stats commands work
fte logs stats --last 24h
fte logs metrics state_transition.duration --aggregation p95 --last 24h

# Integration test passes
pytest tests/integration/logging/test_metrics.py -v
```

**US4 Deliverables**:
- ✅ Metrics logging (separate file)
- ✅ Duration tracking with measure_duration()
- ✅ Aggregation functions (count, avg, p95, p99)
- ✅ CLI stats and metrics commands
- ✅ Error analysis (analyze_errors method)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Goal**: Final polish, documentation, and cross-story integration
**Duration**: 3-4 hours
**Dependencies**: All user stories complete

### Tasks

- [ ] T092 Write comprehensive docstrings for all public APIs in src/logging/
- [ ] T093 Create usage examples in specs/002-logging-infrastructure/examples/
- [ ] T094 Update quickstart.md with final API examples and CLI usage
- [ ] T095 Run detect-secrets scan on codebase and add to CI pipeline
- [ ] T096 Write performance benchmark comparing sync vs async logging in tests/performance/test_logging_throughput.py
- [ ] T097 Create integration test showing coexistence with frozen AuditLogger in tests/integration/test_audit_logger_coexistence.py
- [ ] T098 Verify constitutional compliance (all sections) and document in plan.md

**Validation**:
```bash
# All tests pass
pytest tests/ -v

# Performance benchmarks meet requirements
pytest tests/performance/ -v

# Documentation complete
ls specs/002-logging-infrastructure/examples/
head -n 50 specs/002-logging-infrastructure/quickstart.md

# Coexistence verified
pytest tests/integration/test_audit_logger_coexistence.py -v

# Detect-secrets scan passes
detect-secrets scan --baseline .secrets.baseline
```

---

## Dependencies Between User Stories

```
Setup (T001-T010)
    ↓
Foundational (T011-T025)
    ↓
    ├─→ US1: Developer Debugging (T026-T056) ← MVP SCOPE
    │   ↓
    │   ├─→ US2: Operator Monitoring (T057-T072)
    │   │   ↓
    │   └─→ US3: Compliance Auditing (T073-T082)
    │       ↓
    └─→ US4: Performance Optimization (T083-T091)
        ↓
    Polish (T092-T098)
```

**Critical Path**: Setup → Foundational → US1 (blocks all other stories)

**Independence**:
- US2 depends on US1 (needs log files to query)
- US3 depends on US1 (needs logging infrastructure)
- US4 depends on US1 (extends logging with metrics)
- US2, US3, US4 can be implemented in parallel after US1 complete

---

## Parallel Execution Examples

### Within User Story 1 (Maximum Parallelism)

**Batch 1** (after Foundational complete):
```bash
# 3 developers in parallel
Developer A: T026-T029 (secret redaction)
Developer B: T030-T037 (async writer)
Developer C: T023-T025 (foundational tests)
```

**Batch 2** (after Batch 1 complete):
```bash
# 2 developers in parallel
Developer A: T038-T049 (logger service implementation)
Developer B: T041, T048-T049 can start early (less dependent)
```

**Batch 3** (after logger service complete):
```bash
# 4 developers in parallel
Developer A: T053 (unit tests)
Developer B: T054 (lifecycle integration test)
Developer C: T055 (trace correlation test)
Developer D: T056 (exception logging test)
```

### Across User Stories (After US1)

**Batch 1** (US2, US3, US4 in parallel):
```bash
Team 1 (US2): T057-T072 (query service + CLI)
Team 2 (US3): T073-T082 (archival + retention)
Team 3 (US4): T083-T091 (metrics + aggregation)
```

---

## Suggested Implementation Order (MVP First)

### Sprint 1: MVP (US1 Only)
**Duration**: 2-3 days
**Tasks**: T001-T056 (56 tasks)
**Deliverable**: Working structured logging with trace IDs

**Day 1**:
- Setup (T001-T010)
- Foundational (T011-T025)

**Day 2**:
- Secret redaction (T026-T029)
- Async writer (T030-T037)

**Day 3**:
- Logger service (T038-T052)
- Integration tests (T053-T056)

### Sprint 2: MVP+1 (Add US2)
**Duration**: 1-2 days
**Tasks**: T057-T072 (16 tasks)
**Deliverable**: Query interface + CLI tools

### Sprint 3: MVP+2 (Add US3 + US4)
**Duration**: 1-2 days
**Tasks**: T073-T091 (19 tasks)
**Deliverable**: Retention + metrics

### Sprint 4: Polish
**Duration**: 0.5-1 day
**Tasks**: T092-T098 (7 tasks)
**Deliverable**: Production-ready logging infrastructure

**Total Duration**: 4-8 days (depending on team size and parallelism)

---

## Task Execution Checklist

For each task:
- [ ] Read task description and understand requirements
- [ ] Check dependencies (previous tasks complete?)
- [ ] Read relevant contract/data-model documentation
- [ ] Implement solution (follow contract specifications)
- [ ] Write unit tests (if not already in tasks)
- [ ] Run tests and verify they pass
- [ ] Update documentation if needed
- [ ] Mark task complete in this file
- [ ] Commit changes with reference to task ID

---

## Success Criteria Summary

### MVP (US1) Success Criteria
- ✅ All T001-T056 tasks complete
- ✅ All unit tests pass (pytest tests/unit/logging/)
- ✅ All integration tests pass (pytest tests/integration/logging/)
- ✅ Trace IDs appear in all log entries
- ✅ Exception stack traces captured
- ✅ Secrets automatically redacted
- ✅ Async logging overhead < 5μs
- ✅ No modifications to frozen control plane code

### MVP+1 (US1 + US2) Success Criteria
- ✅ All T001-T072 tasks complete
- ✅ Query performance < 10s for 1GB logs
- ✅ CLI commands functional (tail, query, search)
- ✅ Filter by level, time, module works

### MVP+2 (US1 + US2 + US3 + US4) Success Criteria
- ✅ All T001-T091 tasks complete
- ✅ Retention policy enforced (30 days)
- ✅ Logs compressed after 7 days
- ✅ Metrics logged and queryable
- ✅ Aggregations work correctly

### Production Ready (All Phases) Success Criteria
- ✅ All T001-T098 tasks complete
- ✅ All tests pass (100% for new code)
- ✅ Performance benchmarks meet requirements
- ✅ Documentation complete
- ✅ Constitutional compliance verified
- ✅ Coexistence with AuditLogger verified
- ✅ detect-secrets CI pipeline added

---

## Risk Mitigation During Implementation

| Risk | Detection | Response |
|------|-----------|----------|
| Performance regression | Run T096 after each US | Optimize hot paths, profile code |
| Breaking frozen code | Run T097 after each change | Revert changes, isolate new code |
| Secret leakage | Run T095 daily | Fix patterns, add to baseline |
| Test failures | Run tests after each task | Debug immediately, don't proceed |
| Task underestimation | Track actual vs estimated time | Re-plan remaining tasks |

---

## Next Steps

1. **Review Tasks**: Validate task breakdown with team
2. **Assign MVP Scope**: Confirm US1 (T001-T056) is MVP
3. **Assign Developers**: Map tasks to team members
4. **Begin Implementation**: Start with T001 (setup)
5. **Track Progress**: Update checkboxes as tasks complete
6. **Run Tests Frequently**: After every 3-5 tasks
7. **Create ADRs**: Document significant decisions
8. **Review Before Merge**: Ensure constitutional compliance

---

**Total Tasks**: 98
**MVP Tasks (US1)**: 56 tasks
**MVP+1 Tasks (US1+US2)**: 72 tasks
**MVP+2 Tasks (US1+US2+US3+US4)**: 91 tasks
**Polish Tasks**: 7 tasks

**Estimated Total Effort**: 30-45 developer-hours (with parallelism: 4-8 calendar days)

**Next Command**: Begin implementation with T001 or run `/sp.adr` to document architectural decisions first.

# Feature Specification: Logging Infrastructure (P2)

**Status**: Planning
**Priority**: P2 (Post-MVP)
**Dependencies**: 001-file-control-plane (frozen)
**Type**: Additive (no modifications to frozen code)

---

## Overview

Extend the basic audit logging (from MVP control plane) into a comprehensive logging infrastructure that supports system-wide observability, debugging, performance monitoring, and compliance requirements.

**Scope Constraint**: The MVP control plane code is FROZEN. This feature adds NEW logging capabilities without modifying existing `AuditLogger` or state transition logging.

---

## Problem Statement

### Current State (MVP)
- ✅ Basic audit logging for state transitions exists (`AuditLogger`)
- ✅ Daily log rotation with JSON format
- ✅ Constitutional compliance for Section 8 (state transitions only)

### Limitations
- ❌ No application-level logging (errors, warnings, info)
- ❌ No performance/metrics logging
- ❌ No structured query capabilities
- ❌ No log aggregation or analysis tools
- ❌ No configurable log levels per module
- ❌ No log correlation (trace IDs across operations)
- ❌ No log retention/archival policy

### User Need
As a Digital FTE operator, I need:
1. **Observability**: See what the system is doing in real-time
2. **Debugging**: Trace errors through multiple components
3. **Compliance**: Prove actions were taken (or not taken)
4. **Performance**: Identify bottlenecks and optimize
5. **Security**: Detect anomalous behavior patterns

---

## Requirements

### Functional Requirements

#### FR1: Application Logging
- **FR1.1**: Structured logging at DEBUG, INFO, WARNING, ERROR, CRITICAL levels
- **FR1.2**: Per-module log level configuration (e.g., `control_plane=DEBUG, mcp_servers=INFO`)
- **FR1.3**: Automatic context injection (module name, function name, line number)
- **FR1.4**: Exception tracking with full stack traces

#### FR2: Correlation & Tracing
- **FR2.1**: Unique trace ID for each user request/workflow
- **FR2.2**: Trace ID propagation across module boundaries
- **FR2.3**: Parent-child relationship tracking for nested operations
- **FR2.4**: Duration tracking for operations (start/end timestamps)

#### FR3: Metrics & Performance
- **FR3.1**: Operation duration logging (latency)
- **FR3.2**: File I/O metrics (read/write counts, sizes)
- **FR3.3**: State transition metrics (count by type, success rate)
- **FR3.4**: Error rate tracking by module and error type

#### FR4: Log Management
- **FR4.1**: Configurable retention policy (default: 30 days)
- **FR4.2**: Automatic log archival (compress logs older than 7 days)
- **FR4.3**: Log rotation by size (max 100MB per file) in addition to daily rotation
- **FR4.4**: Safe log deletion (never delete logs < retention period)

#### FR5: Query & Analysis
- **FR5.1**: Filter logs by level, module, time range, trace ID
- **FR5.2**: Search logs by keyword or regex pattern
- **FR5.3**: Aggregate metrics (count, sum, avg) over time windows
- **FR5.4**: Export filtered logs to JSON/CSV

#### FR6: Constitutional Compliance
- **FR6.1**: All logs remain local (no cloud sync without explicit MCP)
- **FR6.2**: Secrets/tokens automatically redacted from logs
- **FR6.3**: Append-only log files (no in-place edits)
- **FR6.4**: Audit trail for log archival/deletion operations

### Non-Functional Requirements

#### NFR1: Performance
- **NFR1.1**: Logging overhead < 5% of operation time
- **NFR1.2**: Async logging (non-blocking for critical path)
- **NFR1.3**: Buffered writes (flush every 1s or 100 entries)
- **NFR1.4**: No log writes during atomic file operations

#### NFR2: Reliability
- **NFR2.1**: Logging failures never crash the application
- **NFR2.2**: Fallback to stderr if file writes fail
- **NFR2.3**: Graceful degradation (drop logs if buffer full)
- **NFR2.4**: Log integrity checks (detect truncated files)

#### NFR3: Usability
- **NFR3.1**: Human-readable timestamps (ISO 8601)
- **NFR3.2**: Color-coded console output (development mode)
- **NFR3.3**: JSON format for machine parsing
- **NFR3.4**: Clear log messages (who, what, why, when)

#### NFR4: Security
- **NFR4.1**: No PII in logs (file paths redacted to relative)
- **NFR4.2**: Automatic secret detection and redaction
- **NFR4.3**: Log file permissions (600 - owner read/write only)
- **NFR4.4**: Tamper-evident logs (optional: log signing)

---

## Success Criteria

### Must Have (MVP+1)
1. ✅ Structured logging at all levels (DEBUG-CRITICAL)
2. ✅ Per-module log level configuration
3. ✅ Trace ID correlation across operations
4. ✅ Automatic secret redaction
5. ✅ Log retention and archival (30 days)
6. ✅ Basic query interface (filter by level, module, time)

### Should Have (MVP+2)
1. ⏳ Performance metrics logging
2. ⏳ Log aggregation and analysis CLI
3. ⏳ Error rate dashboards
4. ⏳ Async logging with buffering

### Could Have (Future)
1. ❓ Log forwarding to external systems (via MCP)
2. ❓ Real-time log streaming (WebSocket)
3. ❓ Log-based alerting (file-driven)
4. ❓ Distributed tracing (if multi-process)

---

## Out of Scope

- ❌ Modifying existing `AuditLogger` (frozen)
- ❌ Changing state transition log format (frozen)
- ❌ Cloud-based log storage (use MCP if needed)
- ❌ Real-time dashboards (use CLI tools)
- ❌ Log-based alerting (future feature)

---

## User Stories

### US1: Developer Debugging
**As a** developer debugging the Digital FTE
**I want** to see detailed logs with trace IDs
**So that** I can trace errors through multiple components

**Acceptance Criteria**:
- Each operation has a unique trace ID
- Trace ID appears in all related log entries
- Logs show module, function, line number
- Stack traces captured for exceptions

### US2: Operator Monitoring
**As an** FTE operator monitoring system health
**I want** to query logs by level and time range
**So that** I can identify recent errors and warnings

**Acceptance Criteria**:
- CLI command to filter logs by level
- Time range filtering (last hour, last day, custom)
- Output format options (JSON, CSV, pretty-print)
- Performance: query 1GB logs in < 10s

### US3: Compliance Auditing
**As a** compliance officer auditing system actions
**I want** to see a complete history of operations
**So that** I can prove what actions were taken

**Acceptance Criteria**:
- All sensitive operations logged
- Logs include timestamp, actor, result
- Logs immutable (append-only)
- Retention policy enforced (30 days)

### US4: Performance Optimization
**As a** performance engineer optimizing the FTE
**I want** to see operation durations and I/O metrics
**So that** I can identify bottlenecks

**Acceptance Criteria**:
- Duration logged for all major operations
- File I/O metrics (read/write counts, sizes)
- Aggregation over time windows (hourly, daily)
- Top slowest operations report

---

## Technical Constraints

### FROZEN Components (Do Not Modify)
1. `src/control_plane/logger.py::AuditLogger`
2. `src/control_plane/state_machine.py` (logging calls)
3. Existing log format for state transitions
4. Existing log file paths (`/Logs/YYYY-MM-DD.log`)

### Integration Points
1. **New logging module** at `src/utils/logging.py` or `src/logging/`
2. **Configuration** in `.env` or `config/logging.yaml`
3. **CLI tools** in `src/cli/logs.py`
4. **No changes** to existing tests (additive only)

### Technology Choices (To Be Determined)
- **NEEDS CLARIFICATION**: Use structlog (commented out in MVP) or custom?
- **NEEDS CLARIFICATION**: Async logging library (aiofiles, asyncio queues)?
- **NEEDS CLARIFICATION**: Log compression format (gzip, zstd)?
- **NEEDS CLARIFICATION**: Query engine (SQLite, DuckDB, grep/jq)?

---

## Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Performance degradation | High | Medium | Async logging, buffering, benchmarks |
| Disk space exhaustion | Medium | Medium | Retention policy, compression, monitoring |
| Logging failures | High | Low | Fallback to stderr, never crash app |
| Secret leakage | Critical | Low | Automatic detection, redaction patterns |
| Log tampering | Medium | Low | File permissions, optional signing |

---

## Open Questions

1. **Logging Library**: Use structlog (already referenced) or build custom? Structlog pros: mature, fast. Cons: dependency.
2. **Async Strategy**: Thread pool, asyncio queue, or sync with buffering?
3. **Query Performance**: Grep/jq sufficient or need embedded DB (SQLite/DuckDB)?
4. **Secret Detection**: Regex patterns, or integrate with tools like detect-secrets?
5. **Trace ID Generation**: UUID4, ULID, or timestamp-based?

---

## References

- Constitution Section 8: Auditability & Logging
- MVP Implementation: `src/control_plane/logger.py`
- Industry Standards: RFC 5424 (Syslog), OpenTelemetry Logging
- Related Features: 001-file-control-plane (dependency)

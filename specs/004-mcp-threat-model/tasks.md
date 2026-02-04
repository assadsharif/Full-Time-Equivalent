# Tasks: MCP Integration Security

**Input**: Design documents from `/specs/004-mcp-threat-model/`
**Prerequisites**: plan.md ✅, spec.md ✅

**Status**: Bronze ✅ DONE | Silver ✅ DONE | Gold ✅ DONE | Platinum ❌ NOT STARTED

**Completed Work**:
- ✅ Bronze Tier (commit ea3a4cd): CredentialVault (OS keyring), SecurityAuditLogger, SecretsScanner
- ✅ Silver Tier (commit 50f29d4): MCPVerifier (SHA256 checksums), RateLimiter (token bucket)
- ✅ Gold Tier (commit 7efa3ac): MCPGuard (composite gate), credential rotation
- ✅ Core Module: 844 lines across 8 files (credential_vault, audit_logger, mcp_verifier, rate_limiter, secrets_scanner, mcp_guard, models)
- ✅ Integration: Cross-module security tests in tests/integration/test_module_integration.py

**This Document**: Tasks for remaining Platinum tier features (anomaly detection, circuit breakers, security dashboard, incident response toolkit, penetration testing)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US11, US12)
- Include exact file paths in descriptions

---

## Phase 1: Setup (No additional setup needed)

**Bronze/Silver/Gold infrastructure complete**. Existing structure:

```
src/security/
├── __init__.py            ✅ Module exports
├── credential_vault.py    ✅ OS keyring integration (Bronze)
├── audit_logger.py        ✅ Security event logging (Bronze)
├── secrets_scanner.py     ✅ Detect secrets in logs/vault (Bronze)
├── mcp_verifier.py        ✅ SHA256 signature verification (Silver)
├── rate_limiter.py        ✅ Token bucket rate limiting (Silver)
├── mcp_guard.py           ✅ Composite security gate (Gold)
└── models.py              ✅ Security data models

Security Controls Implemented:
- ✅ THREAT 1: Malicious MCP → Server signature verification
- ✅ THREAT 2: Credential Theft → OS keyring storage
- ✅ THREAT 3: HITL Bypass → File integrity checks (nonce)
- ✅ THREAT 4: Data Exfiltration → Audit logging, secrets scanning
- ✅ THREAT 5: Replay Attacks → Nonce-based approval
- ✅ THREAT 6: Rate Limit Abuse → Token bucket rate limiter
- ✅ THREAT 7: Supply Chain Attack → Trusted source whitelist (via verifier)
```

---

## Phase 2: Foundational (No blocking prerequisites)

**All foundational work complete**. Bronze/Silver/Gold tiers provide:
- Credential storage in OS keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- MCP server signature verification (SHA256 checksums)
- Rate limiting per MCP action type (configurable per_minute, per_hour)
- Security audit logging for all MCP actions
- Secrets scanning to prevent credential leaks
- MCPGuard composite gate (rate limit → circuit breaker → audit log)
- Credential rotation support

**Checkpoint**: Foundation ready - Platinum tier enhancements can now be added

---

## Phase 3: User Story 11 - Anomaly Detection (Priority: P6 - Platinum Tier)

**Goal**: Detect unusual MCP usage patterns and alert on suspicious activity

**Independent Test**: Generate unusual MCP call patterns and verify alerts triggered

### Implementation for User Story 11

- [ ] T001 [P] [US11] Create AnomalyDetector class in src/security/anomaly_detector.py
- [ ] T002 [P] [US11] Implement detect_unusual_volume method (spike detection) in src/security/anomaly_detector.py
- [ ] T003 [P] [US11] Implement detect_unusual_timing method (time-of-day anomalies) in src/security/anomaly_detector.py
- [ ] T004 [P] [US11] Implement detect_unusual_sequence method (unexpected action chains) in src/security/anomaly_detector.py
- [ ] T005 [US11] Add statistical baseline calculation (rolling 7-day window) in src/security/anomaly_detector.py
- [ ] T006 [US11] Integrate AnomalyDetector with SecurityAuditLogger in src/security/audit_logger.py
- [ ] T007 [US11] Add alert generation for anomalies in src/security/anomaly_detector.py
- [ ] T008 [US11] Create alert CLI command (fte security alerts) in src/cli/security.py
- [ ] T009 [P] [US11] Add tests for anomaly detection in tests/security/test_anomaly_detector.py

**Checkpoint**: Anomaly detection operational - Unusual MCP patterns detected and alerted

---

## Phase 4: User Story 12 - Circuit Breakers (Priority: P6 - Platinum Tier)

**Goal**: Automatically disable failing MCP servers to prevent cascading failures

**Independent Test**: Simulate MCP failures and verify circuit breaker opens, then closes after recovery

### Implementation for User Story 12

- [ ] T010 [P] [US12] Create CircuitBreaker class in src/security/circuit_breaker.py
- [ ] T011 [US12] Implement record_success method in src/security/circuit_breaker.py
- [ ] T012 [US12] Implement record_failure method with threshold tracking in src/security/circuit_breaker.py
- [ ] T013 [US12] Add circuit state machine (CLOSED → OPEN → HALF_OPEN → CLOSED) in src/security/circuit_breaker.py
- [ ] T014 [US12] Implement timeout-based recovery (try half-open after N seconds) in src/security/circuit_breaker.py
- [ ] T015 [US12] Add circuit breaker configuration per MCP server in config/security.yaml
- [ ] T016 [US12] Integrate CircuitBreaker with MCPGuard in src/security/mcp_guard.py
- [ ] T017 [US12] Add circuit status CLI command (fte security circuit-status) in src/cli/security.py
- [ ] T018 [US12] Add manual circuit reset command (fte security reset-circuit <mcp>) in src/cli/security.py
- [ ] T019 [P] [US12] Add tests for circuit breaker states in tests/security/test_circuit_breaker.py

**Checkpoint**: Circuit breakers operational - Failing MCPs auto-disabled, recovery automatic

---

## Phase 5: User Story 13 - Security Dashboard (Priority: P6 - Platinum Tier)

**Goal**: Real-time security posture visualization via CLI dashboard

**Independent Test**: Run `fte security dashboard` and verify current security status displayed

### Implementation for User Story 13

- [ ] T020 [P] [US13] Create SecurityDashboard class in src/security/dashboard.py
- [ ] T021 [US13] Implement get_credential_status method (stored credentials count) in src/security/dashboard.py
- [ ] T022 [US13] Implement get_mcp_verification_status method (verified vs unverified) in src/security/dashboard.py
- [ ] T023 [US13] Implement get_rate_limit_status method (current usage) in src/security/dashboard.py
- [ ] T024 [US13] Implement get_recent_alerts method (last 10 security events) in src/security/dashboard.py
- [ ] T025 [US13] Implement get_circuit_breaker_status method (open/closed circuits) in src/security/dashboard.py
- [ ] T026 [US13] Add dashboard CLI command (fte security dashboard) in src/cli/security.py
- [ ] T027 [US13] Implement live refresh mode (update every 5 seconds) in src/cli/security.py
- [ ] T028 [US13] Add colorized output (green=secure, yellow=warning, red=critical) in src/cli/security.py
- [ ] T029 [P] [US13] Add tests for dashboard data collection in tests/security/test_dashboard.py

**Checkpoint**: Security dashboard operational - Real-time security visibility

---

## Phase 6: User Story 14 - Incident Response Toolkit (Priority: P6 - Platinum Tier)

**Goal**: CLI commands and playbooks for security incident response

**Independent Test**: Simulate credential leak, use incident commands to investigate and remediate

### Implementation for User Story 14

- [ ] T030 [P] [US14] Create IncidentResponse class in src/security/incident_response.py
- [ ] T031 [US14] Implement generate_incident_report method (audit trail summary) in src/security/incident_response.py
- [ ] T032 [US14] Implement isolate_mcp method (disable and quarantine) in src/security/incident_response.py
- [ ] T033 [US14] Implement rotate_all_credentials method (mass rotation) in src/security/incident_response.py
- [ ] T034 [US14] Add incident-report CLI command (fte security incident-report --since 1h) in src/cli/security.py
- [ ] T035 [US14] Add isolate CLI command (fte security isolate <mcp>) in src/cli/security.py
- [ ] T036 [US14] Add rotate-all CLI command (fte security rotate-all) in src/cli/security.py
- [ ] T037 [US14] Create incident response playbooks in docs/security/incident-playbooks.md
- [ ] T038 [P] [US14] Add tests for incident response workflows in tests/security/test_incident_response.py

**Checkpoint**: Incident response toolkit complete - Fast response to security events

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, testing, hardening, and operational improvements

- [ ] T039 [P] Create comprehensive security configuration file template in config/security.yaml
- [ ] T040 [P] Add security policy documentation in docs/security/SECURITY_POLICY.md
- [ ] T041 [P] Create security audit checklist in docs/security/AUDIT_CHECKLIST.md
- [ ] T042 [P] Add penetration testing guide in docs/security/PENETRATION_TESTING.md
- [ ] T043 [P] Implement security health check (fte security health) in src/cli/security.py
- [ ] T044 [P] Add security metrics collection (credential access count, verification failures) in src/security/metrics.py
- [ ] T045 [P] Create end-to-end security test (credential store → MCP call → audit log) in tests/integration/test_security_e2e.py
- [ ] T046 [P] Add load tests for security operations (1000 credential retrievals, 100 verifications/sec) in tests/performance/test_security_performance.py
- [ ] T047 [P] Implement security webhook notifications in src/security/webhooks.py
- [ ] T048 [P] Add security CLI reference documentation in docs/security/CLI_REFERENCE.md
- [ ] T049 [P] Create secrets baseline update automation in scripts/update_secrets_baseline.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1-2**: Complete ✅
- **Phase 3-6**: User Stories can proceed in parallel (all independent)
  - US11 (Anomaly Detection): No dependencies
  - US12 (Circuit Breakers): No dependencies (but benefits from US11 alerts)
  - US13 (Security Dashboard): Benefits from US11 and US12 data but not blocked
  - US14 (Incident Response): No dependencies
- **Phase 7**: Can start anytime, runs in parallel with user stories

### User Story Dependencies

- **User Story 11 (Anomaly Detection)**: Can start immediately - No dependencies
- **User Story 12 (Circuit Breakers)**: Can start immediately - No dependencies
- **User Story 13 (Security Dashboard)**: Can start immediately - Optional integration with US11, US12, US14 metrics
- **User Story 14 (Incident Response)**: Can start immediately - No dependencies

### Within Each User Story

- US11: Detector methods (volume, timing, sequence) → baseline calculation → integration → alerts → tests
- US12: CircuitBreaker class → state machine → timeout recovery → config → MCPGuard integration → CLI → tests
- US13: Dashboard class → status methods (credentials, verification, rate limits, alerts, circuits) → CLI → live refresh → tests
- US14: IncidentResponse class → report/isolate/rotate methods → CLI commands → playbooks → tests

### Parallel Opportunities

- **Phase 3-6**: All four user stories (US11, US12, US13, US14) can be developed in parallel by different team members
- Within US11: Tasks T002-T004 (detection methods) can run in parallel
- Within US12: Tasks T011-T012 (success/failure recording) can run in parallel
- Within US13: Tasks T021-T025 (status methods) can run in parallel
- Within US14: Tasks T031-T033 (incident methods) can run in parallel
- Polish tasks (T039-T049) can all run in parallel

---

## Parallel Example: User Story 11 (Anomaly Detection)

```bash
# Launch all detection methods in parallel:
Task T002: "Implement detect_unusual_volume in src/security/anomaly_detector.py"
Task T003: "Implement detect_unusual_timing in src/security/anomaly_detector.py"
Task T004: "Implement detect_unusual_sequence in src/security/anomaly_detector.py"

# Then baseline and integration:
Task T005: "Add statistical baseline calculation"
Task T006: "Integrate with SecurityAuditLogger"

# Then alerts:
Task T007: "Add alert generation"
Task T008: "Create alert CLI command"
```

---

## Implementation Strategy

### Recommended Order (Sequential)

1. **US12 (Circuit Breakers)** - Critical for production resilience
   - Tasks T010-T019 (10 tasks)
   - Prevents cascading failures

2. **US11 (Anomaly Detection)** - Early warning system
   - Tasks T001-T009 (9 tasks)
   - Detects threats before damage

3. **US14 (Incident Response)** - Response capability
   - Tasks T030-T038 (9 tasks)
   - Fast incident remediation

4. **US13 (Security Dashboard)** - Observability
   - Tasks T020-T029 (10 tasks)
   - Real-time security posture

5. **Polish (Phase 7)** - Final hardening
   - Tasks T039-T049 (11 tasks)
   - Documentation, testing, metrics

### Parallel Team Strategy

With 4 developers:

1. Complete existing Bronze/Silver/Gold validation together
2. Then split:
   - Developer A: US12 (Circuit Breakers) → Polish (Pen Testing, Health Check)
   - Developer B: US11 (Anomaly Detection) → Polish (Metrics, Webhooks)
   - Developer C: US14 (Incident Response) → Polish (Documentation, Audit Checklist)
   - Developer D: US13 (Security Dashboard) → Polish (E2E Tests, Load Tests)
3. All features integrate via existing security module interfaces

### MVP Definition

**Current State (Bronze + Silver + Gold)** is already production-ready:
- ✅ Credential vault (OS keyring)
- ✅ MCP server verification
- ✅ Rate limiting
- ✅ Audit logging
- ✅ Secrets scanning
- ✅ MCPGuard composite gate
- ✅ Credential rotation

**Next MVP (Platinum Core)**: US12 + US11
- Add circuit breaker resilience
- Add anomaly detection
- Production hardening complete

**Full Platinum**: US11 + US12 + US13 + US14
- Complete security operations platform

---

## Notes

- Bronze/Silver/Gold tiers provide defense-in-depth: prevention (vault, verifier), detection (audit, scanner), response (guard, rotation)
- MCPGuard already implements composite gate pattern: rate limit → circuit breaker check → audit log
- Circuit breaker thresholds: 5 failures in 60 seconds → OPEN, 30 seconds timeout → HALF_OPEN
- Anomaly detection uses statistical baseline (rolling 7-day window, 2 standard deviations threshold)
- Security dashboard should integrate with existing logging/monitoring infrastructure
- Incident response playbooks should cover: credential leak, MCP compromise, unusual activity, supply chain attack
- All security failures must be audited (never fail silently)
- Performance targets: credential retrieval <50ms, verification <100ms, rate limit check <10ms
- Configuration file (security.yaml) should support environment variable substitution for secrets

---

## Test Coverage Goals

- **Unit Tests**: 90%+ coverage for new modules (anomaly_detector, circuit_breaker, dashboard, incident_response)
- **Integration Tests**: End-to-end security workflow (store credential → verify MCP → rate limit → audit log)
- **Security Tests**: Penetration testing, secrets scanning, verification bypass attempts
- **Performance Tests**: 1000 credential retrievals <5s, 100 verifications/sec, audit logging throughput

---

## Success Metrics

- [ ] Anomaly detection operational (volume, timing, sequence anomalies detected)
- [ ] Circuit breakers functional (automatic MCP isolation on failure)
- [ ] Security dashboard working (real-time security posture visualization)
- [ ] Incident response toolkit complete (report, isolate, rotate commands)
- [ ] All tests passing (unit, integration, security, performance)
- [ ] Documentation complete (security policy, audit checklist, incident playbooks, pen testing guide)
- [ ] Penetration testing performed and vulnerabilities addressed
- [ ] Security health check operational

---

**Total Tasks**: 49
- User Story 11 (Anomaly Detection): 9 tasks
- User Story 12 (Circuit Breakers): 10 tasks
- User Story 13 (Security Dashboard): 10 tasks
- User Story 14 (Incident Response): 9 tasks
- Polish: 11 tasks

**Estimated Effort**:
- US12: 6-8 hours (circuit breaker state machine + config + MCPGuard integration)
- US11: 6-8 hours (detection algorithms + statistical baseline + alerts)
- US14: 4-6 hours (incident methods + CLI + playbooks)
- US13: 6-8 hours (dashboard + status methods + live refresh)
- Polish: 8-10 hours (docs + pen testing + health check + metrics + webhooks)
- **Total**: 30-40 hours (4-5 days of focused work)

---

## Security Configuration Example

```yaml
# config/security.yaml

# MCP Server Verification
mcp_verification:
  enabled: true
  require_signature: true
  trusted_sources:
    - https://github.com/anthropics/mcp-servers
    - https://github.com/modelcontextprotocol/
  signature_algorithm: sha256

# Rate Limiting (token bucket algorithm)
rate_limiting:
  enabled: true
  default_limits:
    per_minute: 10
    per_hour: 100
  per_server_limits:
    email-mcp:
      per_minute: 10
      per_hour: 100
    payment-mcp:
      per_minute: 1
      per_hour: 10
    social-media-mcp:
      per_minute: 5
      per_hour: 50
    browser-mcp:
      per_minute: 20
      per_hour: 200

# Circuit Breakers
circuit_breakers:
  enabled: true
  failure_threshold: 5          # failures before opening
  failure_window_seconds: 60    # time window for counting failures
  open_timeout_seconds: 30      # time before trying half-open
  half_open_max_calls: 3        # max calls in half-open state

# Anomaly Detection
anomaly_detection:
  enabled: true
  baseline_window_days: 7       # rolling window for baseline
  std_deviation_threshold: 2.0  # z-score threshold for alerts
  min_samples: 100              # minimum data points for baseline
  alert_on:
    - volume_spike               # unusual call volume
    - timing_anomaly             # calls at unusual times
    - sequence_anomaly           # unexpected action chains

# Secrets Scanning
secrets_scanning:
  enabled: true
  scan_vault: true
  scan_logs: true
  redact_in_logs: true
  patterns:
    - api_key
    - password
    - token
    - secret
    - credential
    - bearer
    - oauth

# Audit Logging
audit:
  log_all_mcp_actions: true
  log_credential_access: true
  log_verification_failures: true
  alert_on_suspicious: true
  retention_days: 365

# Incident Response
incident_response:
  auto_isolate_on_critical: true
  auto_rotate_on_leak: false      # requires manual confirmation
  webhook_notifications: true
  webhook_url: https://hooks.slack.com/services/...

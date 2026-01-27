# Feature Specification: MCP Integration Layer

**Created**: 2026-01-27
**Status**: Planning
**Priority**: P3 - Medium (External Communication)
**Constitutional Requirements**: Section 3

---

## Overview

Implement a comprehensive MCP (Model Context Protocol) integration layer that ensures all external API access goes through explicit, auditable MCP servers. This layer enforces the local-first privacy mandate while enabling controlled external communication for email, calendar, GitHub, and other integrations.

---

## User Scenarios & Testing

### User Story 1 - MCP Server Registry (Priority: P1)

**As a** Digital FTE system
**I want** to maintain a registry of available MCP servers
**So that** all external API access is controlled and auditable

**Why this priority**: Foundation for all external communication

**Independent Test**: Register MCP servers, verify system only allows API calls through registered servers

**Acceptance Scenarios**:

1. **Given** no MCP servers registered, **When** attempting external API call, **Then** system blocks call and logs warning
2. **Given** MCP server registered, **When** attempting API call through it, **Then** system allows call and logs usage
3. **Given** MCP server configuration, **When** loading on startup, **Then** all servers are initialized and available
4. **Given** MCP server failure, **When** call attempted, **Then** system logs error and returns graceful failure

---

### User Story 2 - Secure Credential Management (Priority: P1)

**As a** human owner
**I want** credentials stored securely outside the vault
**So that** sensitive tokens never leak into versioned files

**Why this priority**: Constitutional mandate (Section 3) - secrets never in vault

**Independent Test**: Store credentials, verify they're not in vault files or logs

**Acceptance Scenarios**:

1. **Given** API credentials, **When** storing, **Then** stored in system keyring (not vault)
2. **Given** MCP server needs auth, **When** authenticating, **Then** credentials retrieved from secure storage
3. **Given** any log entry, **When** inspecting, **Then** no credentials or tokens are visible
4. **Given** vault files, **When** searching for secrets, **Then** none are found (verified via grep)

---

### User Story 3 - MCP Call Auditing (Priority: P2)

**As a** system auditor
**I want** all MCP server calls logged with context
**So that** external API usage is transparent and auditable

**Why this priority**: Trust and compliance requirement

**Independent Test**: Make various MCP calls, verify all are logged with details

**Acceptance Scenarios**:

1. **Given** MCP server call, **When** executed, **Then** log includes: server name, method, parameters (sanitized), result, latency
2. **Given** MCP call failure, **When** error occurs, **Then** log includes error type and retry attempts
3. **Given** sensitive data in call, **When** logging, **Then** sensitive fields are redacted
4. **Given** date range, **When** querying MCP logs, **Then** all calls in range are returned

---

### User Story 4 - Rate Limiting & Quotas (Priority: P3)

**As a** system administrator
**I want** MCP calls rate-limited per server
**So that** external APIs are not abused and costs are controlled

**Why this priority**: Cost control and API compliance

**Independent Test**: Make rapid MCP calls, verify rate limiting enforces quotas

**Acceptance Scenarios**:

1. **Given** MCP server with rate limit, **When** exceeding limit, **Then** calls are queued or rejected with clear message
2. **Given** daily quota, **When** approaching limit, **Then** system warns human
3. **Given** quota exceeded, **When** call attempted, **Then** system blocks and logs quota violation
4. **Given** quota reset period, **When** period expires, **Then** quota is reset and calls resume

---

### Edge Cases

- What happens when MCP server is unreachable (network down)?
- How does system handle slow MCP responses (timeouts)?
- What if MCP server returns unexpected data format?
- How does system handle MCP server authentication expiry?
- What if multiple tasks try to use same MCP server concurrently?

---

## Requirements

### Functional Requirements

**FR-001**: System MUST route all external API calls through registered MCP servers

**FR-002**: System MUST block direct API calls that bypass MCP layer

**FR-003**: System MUST store MCP server configurations in `.claude/mcp/` directory

**FR-004**: System MUST store credentials in system keyring (never in vault or config files)

**FR-005**: System MUST log all MCP server calls with: timestamp, server, method, parameters (sanitized), result, latency

**FR-006**: System MUST redact sensitive data from logs (tokens, passwords, API keys)

**FR-007**: System MUST implement rate limiting per MCP server (configurable limits)

**FR-008**: System MUST implement timeout handling for slow MCP calls (default: 30 seconds)

**FR-009**: System MUST implement retry logic for transient MCP failures (exponential backoff, max 3 retries)

**FR-010**: System MUST validate MCP server responses against expected schema

**FR-011**: System MUST support MCP server health checks (ping/status)

**FR-012**: System MUST alert human when quota thresholds are approached (80%, 90%)

### Key Entities

- **MCPServer**: Registered server (name, type, config_path, status, health, rate_limit)
- **MCPCredential**: Secure credential (server_name, credential_type, keyring_id)
- **MCPCall**: API call record (server, method, parameters, result, latency, timestamp)
- **MCPQuota**: Usage tracking (server, daily_limit, current_usage, reset_time)
- **MCPResponse**: Standardized response (status, data, error, metadata)

---

## Success Criteria

### Measurable Outcomes

**SC-001**: 100% of external API calls go through MCP layer (verified via monitoring)

**SC-002**: 0 credentials found in vault files or logs (verified via security scan)

**SC-003**: MCP calls complete in < 5 seconds (p95) excluding network latency

**SC-004**: Rate limiting enforces quotas with < 1% error rate

**SC-005**: MCP call success rate > 95% (excluding external service failures)

**SC-006**: All MCP calls are logged with complete context (verified via audit)

---

## Assumptions

- System keyring is available (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- MCP servers follow standard protocol (JSON-RPC or similar)
- Network connectivity is generally available
- External APIs have reasonable rate limits
- MCP server configurations are JSON format

---

## Out of Scope

- MCP server development (using existing servers)
- Custom protocol implementations (Phase 2)
- Distributed MCP server management (Phase 3)
- Real-time MCP call monitoring dashboard (Phase 3)
- Automatic MCP server discovery (Phase 2)

---

## Non-Functional Requirements

**Performance:**
- MCP call overhead: < 100ms
- MCP response parsing: < 50ms
- Rate limit checks: < 10ms

**Reliability:**
- Graceful degradation on MCP server failure
- Automatic retry with exponential backoff
- Circuit breaker for failing servers

**Security:**
- Credentials in system keyring only
- TLS for all MCP communication
- No secrets in logs or files
- Input validation for all MCP calls

**Maintainability:**
- Clear error messages for MCP failures
- Comprehensive logging
- Simple MCP server registration

---

## MCP Server Examples

### Currently Available MCP Servers

**Communication:**
- GitHub (issues, PRs, repos)
- Gmail (read, send, search)
- Vercel (deployments)

**Storage:**
- Filesystem (local file operations)
- Memory (knowledge graph)

**Development:**
- Git (version control)
- Fetch (web content)

### Registration Format

```yaml
# .claude/mcp/github.yaml
name: github
type: github
enabled: true
rate_limit:
  calls_per_hour: 5000
  daily_quota: 50000
timeout: 30s
retry:
  max_attempts: 3
  backoff: exponential
credentials:
  type: oauth
  keyring_id: github-token
health_check:
  enabled: true
  interval: 5m
```

---

## MCP Call Flow

```
User Task → System Planning → External API Needed
    ↓
Check MCP Registry (is server registered?)
    ↓
Load Credentials (from keyring)
    ↓
Check Rate Limit (within quota?)
    ↓
Make MCP Call (with timeout)
    ↓
Validate Response (schema check)
    ↓
Log Call Details (sanitized)
    ↓
Return Result (to task)
```

---

## Security Checklist

- [ ] No credentials in `.git` history
- [ ] No credentials in vault files
- [ ] No credentials in logs
- [ ] No credentials in error messages
- [ ] Credentials stored in system keyring
- [ ] TLS enforced for all MCP communication
- [ ] Input validation on all MCP calls
- [ ] Output sanitization in logs
- [ ] Rate limiting prevents abuse
- [ ] Quota alerts for cost control

---

## Dependencies

- System keyring library (keyring for Python)
- MCP client library (claude-code MCP integration)
- JSON schema validator
- Rate limiting library (e.g., ratelimit)
- Network library with timeout support

---

## Constitutional Compliance

This feature directly implements:
- **Section 3.1**: All sensitive data remains local by default
- **Section 3.2**: External APIs accessed only through explicit MCP servers
- **Section 3.3**: Secrets, tokens, credentials never written to vault
- **Section 3.4**: Cloud components operate on least privilege

---

*This MCP integration layer ensures the Digital FTE respects privacy while enabling controlled external communication.*

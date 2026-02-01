# Implementation Plan: MCP Integration Security

**Branch**: `004-mcp-threat-model` | **Date**: 2026-01-28 | **Spec**: [specs/004-mcp-threat-model/spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-mcp-threat-model/spec.md`

## Summary

Implement comprehensive security controls for MCP (Model Context Protocol) server integrations to protect against the 10 identified threats in the threat model. This includes: MCP server verification, credential management, network security, audit logging, rate limiting, sandboxing, and incident response. All implementations will be **additive security layers** without modifying core control plane code.

**Key Approach**: Defense-in-depth strategy with three security layers: (1) Prevention (server signing, credential vaults), (2) Detection (audit logs, anomaly detection), (3) Response (circuit breakers, incident runbooks).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: cryptography>=41.0.0, keyring>=24.0.0, python-nonce>=1.0.0, detect-secrets>=1.4.0
**Storage**: Encrypted credential vault (OS keyring), audit logs (DuckDB P2)
**Testing**: pytest>=7.4.0, pytest-security for vulnerability scanning
**Target Platform**: Linux/macOS/Windows (OS-specific credential storage)
**Project Type**: Single project (security layer)
**Performance Goals**: <50ms credential retrieval, <100ms signature verification
**Constraints**: ADDITIVE ONLY - no modifications to control plane, all security controls must be opt-in with safe defaults
**Scale/Scope**: Support 10+ MCP servers, handle 1000+ daily actions

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **Section 3 (Local-First & Privacy)**: Credentials stored in OS keyring, never in vault
✅ **Section 6-7 (Autonomy & HITL)**: All sensitive MCP actions require approval
✅ **Section 8 (Auditability)**: All MCP actions logged with full context
✅ **Section 9 (Error Handling)**: Security failures stop execution, never silent
✅ **Section 11 (No Spec Drift)**: Implementation follows threat model exactly

## Project Structure

### Documentation (this feature)

```text
specs/004-mcp-threat-model/
├── plan.md              # This file
├── research.md          # Credential storage options, signing algorithms
├── data-model.md        # Security policy schema, audit log format
├── quickstart.md        # Security setup guide
└── contracts/           # Security API contracts
    ├── credential-vault.md
    ├── mcp-verification.md
    ├── audit-logging.md
    └── incident-response.md
```

### Source Code (repository root)

```text
src/security/
├── __init__.py          # Security module exports
├── credential_vault.py  # OS keyring integration
├── mcp_verifier.py      # MCP server signature verification
├── secrets_scanner.py   # Detect secrets in logs/vault
├── rate_limiter.py      # Token bucket rate limiting
├── audit_logger.py      # Security event logging
└── models.py            # Security data models

src/cli/mcp.py           # Enhanced with security checks
src/cli/security.py      # New: Security management commands

config/
└── security.yaml        # Security policy configuration

tests/security/
├── test_credential_vault.py
├── test_mcp_verification.py
├── test_secrets_scanner.py
└── test_security_integration.py

.fte/
├── mcp-signatures.json  # MCP server signatures
└── security-policy.yaml # User security settings

docs/security/
├── threat-model.md      # Copy of threat model spec
├── incident-response.md # Incident playbooks
└── security-audit.md    # Audit checklist
```

**Structure Decision**: New `src/security/` module for all security controls. CLI enhanced with security commands. All credential storage uses OS keyring (never filesystem).

## Complexity Tracking

> No constitutional violations - all gates passing.

## Phase 0: Research & Technology Selection

### Research Areas

1. **Credential Storage**
   - **Question**: How to securely store MCP credentials (API keys, OAuth tokens)?
   - **Options**: OS keyring (keyring library), HashiCorp Vault, encrypted files, environment variables
   - **Decision Criteria**: Security, cross-platform support, ease of use, no external dependencies
   - **Recommendation**: Python `keyring` library (uses macOS Keychain, Windows Credential Manager, Linux Secret Service)

2. **MCP Server Verification**
   - **Question**: How to verify MCP server authenticity and integrity?
   - **Options**: Code signing (GPG/PGP), checksum verification (SHA256), trusted registries
   - **Decision Criteria**: Balance between security and usability
   - **Recommendation**: SHA256 checksums for initial release, plan for GPG signing in v2

3. **Secrets Scanning**
   - **Question**: How to prevent secrets from being logged or committed?
   - **Options**: detect-secrets, truffleHog, git-secrets, custom regex patterns
   - **Recommendation**: `detect-secrets` (Yelp's tool, widely used, good Python integration)

4. **Rate Limiting Algorithm**
   - **Question**: Which rate limiting algorithm to use for MCP actions?
   - **Options**: Token bucket, leaky bucket, fixed window, sliding window
   - **Recommendation**: Token bucket (allows bursts, smooth rate control)

### Research Deliverable: `research.md`

Document containing:
- Credential storage comparison (keyring vs. Vault vs. encrypted files)
- Signing algorithm analysis (SHA256 vs. GPG vs. Minisign)
- Secrets scanning tools evaluation
- Rate limiting algorithms comparison
- OS-specific credential storage mechanisms

## Phase 1: Design & Contracts

### Data Model (`data-model.md`)

**Security Policy Schema**:
```yaml
# .fte/security-policy.yaml
mcp_servers:
  verification:
    enabled: true
    require_signature: true
    trusted_sources:
      - https://github.com/anthropics/mcp-servers
      - https://github.com/modelcontextprotocol/

  rate_limiting:
    enabled: true
    limits:
      email:
        per_minute: 10
        per_hour: 100
      payment:
        per_minute: 1
        per_hour: 10
      social_media:
        per_minute: 5
        per_hour: 50

  secrets:
    scan_enabled: true
    redact_in_logs: true
    patterns:
      - api_key
      - password
      - token
      - secret

audit:
  log_all_mcp_actions: true
  log_credential_access: true
  alert_on_suspicious: true
```

**Audit Log Format**:
```json
{
  "timestamp": "2026-01-28T10:30:00Z",
  "event_type": "mcp_action",
  "mcp_server": "gmail-mcp",
  "action": "send_email",
  "approved": true,
  "approval_id": "PAYMENT_Client_A_2026-01-28",
  "nonce": "7a9b3c4d-5e6f-7890-ab12",
  "user": "user@example.com",
  "risk_level": "high",
  "rate_limit_consumed": {"tokens": 1, "remaining": 9},
  "result": "success",
  "duration_ms": 234
}
```

### API Contracts (`contracts/`)

**credential-vault.md**:
```python
# Credential Vault API
class CredentialVault:
    def store_credential(
        self,
        service: str,
        username: str,
        credential: str
    ) -> None:
        """
        Store credential in OS keyring.

        Args:
            service: MCP server name (e.g., "gmail-mcp")
            username: Account identifier
            credential: API key, OAuth token, or password

        Raises:
            SecurityError: If keyring access fails
        """

    def retrieve_credential(
        self,
        service: str,
        username: str
    ) -> str:
        """
        Retrieve credential from OS keyring.

        Raises:
            CredentialNotFoundError: If credential doesn't exist
            SecurityError: If keyring access fails
        """
```

**mcp-verification.md**:
```python
# MCP Server Verification API
class MCPVerifier:
    def verify_server(
        self,
        server_path: Path,
        expected_signature: str
    ) -> bool:
        """
        Verify MCP server integrity using SHA256 checksum.

        Args:
            server_path: Path to MCP server executable
            expected_signature: Expected SHA256 hash

        Returns:
            True if verification passes

        Raises:
            VerificationError: If signature mismatch
        """
```

**audit-logging.md**:
```python
# Security Audit Logging API
class SecurityAuditLogger:
    def log_mcp_action(
        self,
        mcp_server: str,
        action: str,
        approved: bool,
        approval_id: Optional[str],
        risk_level: RiskLevel
    ) -> None:
        """
        Log MCP action to security audit trail.

        All MCP actions are logged regardless of success/failure.
        """

    def log_credential_access(
        self,
        service: str,
        operation: Literal["store", "retrieve", "delete"]
    ) -> None:
        """
        Log credential vault access (CRITICAL security event).
        """
```

### Quickstart Guide (`quickstart.md`)

```markdown
# MCP Security Quickstart

## Setup Credential Vault

```bash
# Store Gmail API credentials
fte security store gmail-mcp user@gmail.com <api-key>

# Verify storage
fte security list
```

## Verify MCP Server

```bash
# Calculate server signature
fte security verify gmail-mcp --calculate

# Add to trusted servers
fte security trust gmail-mcp <signature>
```

## Configure Rate Limits

```bash
# Edit security policy
fte security policy edit

# Test rate limits
fte security test-rate-limit gmail-mcp
```

## Scan for Secrets

```bash
# Scan vault for exposed secrets
fte security scan vault

# Scan logs
fte security scan logs --since 7d
```

## Incident Response

If suspicious activity detected:

```bash
# View security events
fte logs query --level CRITICAL --module security

# Disable compromised MCP
fte mcp disable <name>

# Rotate credentials
fte security rotate <service>

# Generate incident report
fte security incident-report --since 1h
```
```

## Phase 2: Implementation Roadmap

### Bronze Tier (Week 1-2): Core Security Infrastructure

**Milestone**: Credential vault, basic audit logging

**Tasks**:
1. Implement `CredentialVault` with OS keyring integration
2. Add `SecurityAuditLogger` for MCP action logging
3. Create `fte security` CLI commands (store, retrieve, list)
4. Implement secrets scanner integration
5. Write unit tests for credential operations
6. Documentation for credential management

**Deliverables**:
- Working credential vault (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- Security audit logging integrated with P2 logging
- CLI commands for credential management
- Secrets scanning on commit (pre-commit hook)

### Silver Tier (Week 3-4): MCP Verification & Rate Limiting

**Milestone**: Server verification, rate limiting, enhanced audit logs

**Tasks**:
1. Implement MCP server signature verification (SHA256)
2. Create rate limiter with token bucket algorithm
3. Enhance `fte mcp add` with security checks
4. Add signature calculation tools
5. Implement rate limit enforcement in MCP calls
6. Integration tests with real MCP servers
7. Security policy configuration

**Deliverables**:
- MCP server verification system
- Rate limiting for all MCP actions
- Security policy configuration file
- Enhanced audit logs with rate limit info

### Gold Tier (Week 5-6): Advanced Security & Incident Response

**Milestone**: Anomaly detection, circuit breakers, incident playbooks

**Tasks**:
1. Implement circuit breaker pattern for MCP failures
2. Add anomaly detection for unusual MCP patterns
3. Create incident response CLI commands
4. Build security dashboard (`fte security dashboard`)
5. Implement credential rotation
6. Write incident response playbooks
7. Security audit checklist
8. Penetration testing

**Deliverables**:
- Circuit breaker for MCP actions
- Anomaly detection alerts
- Incident response toolkit
- Security audit checklist
- Penetration test report

## Testing Strategy

### Unit Tests
```python
def test_credential_vault_store_retrieve():
    vault = CredentialVault()
    vault.store_credential("test-mcp", "user", "secret")
    assert vault.retrieve_credential("test-mcp", "user") == "secret"

def test_mcp_verifier_detects_tampering():
    verifier = MCPVerifier()
    # Modify server file
    with pytest.raises(VerificationError):
        verifier.verify_server(tampered_path, original_signature)

def test_rate_limiter_enforces_limits():
    limiter = RateLimiter(max_tokens=10, refill_rate=1)
    # Consume 10 tokens
    for _ in range(10):
        assert limiter.consume(1) == True
    # 11th should fail
    assert limiter.consume(1) == False
```

### Security Tests
- Secrets scanning on test data
- Credential vault access control
- MCP signature verification with corrupted files
- Rate limit enforcement under load
- Audit log integrity verification

### Integration Tests
- End-to-end MCP action with all security layers
- Credential rotation without service interruption
- Incident response workflow
- Security policy enforcement

## Risk Analysis

### Risk 1: OS Keyring Unavailable
**Impact**: High (credentials inaccessible)
**Mitigation**: Fallback to encrypted file with warning, provide troubleshooting guide

### Risk 2: Performance Overhead
**Impact**: Medium (security checks add latency)
**Mitigation**: Cache verifications, optimize rate limiter, async audit logging

### Risk 3: False Positive Secrets Scanning
**Impact**: Low (legitimate tokens flagged)
**Mitigation**: Whitelist patterns, manual override option, clear error messages

## Architectural Decision Records

### ADR-001: OS Keyring for Credential Storage

**Decision**: Use Python `keyring` library for credential storage

**Rationale**:
- Leverages OS-provided secure storage (Keychain, Credential Manager, Secret Service)
- No plaintext credentials on disk
- Cross-platform support
- Well-maintained library
- Complies with constitution Section 3 (Local-First & Privacy)

**Alternatives Considered**:
- HashiCorp Vault: Requires external service, complex setup
- Encrypted files: Risk of improper encryption, key management burden
- Environment variables: Credentials visible in process list

### ADR-002: SHA256 Checksums for MCP Verification

**Decision**: Use SHA256 checksums for MCP server verification (v1)

**Rationale**:
- Simple to implement and verify
- No external PKI required
- Fast computation (<100ms)
- Good enough for initial release
- Plan migration to GPG signing in v2

**Alternatives Considered**:
- GPG signing: Too complex for users, key management burden
- Minisign: Less widely known, adoption risk
- No verification: Unacceptable security risk

### ADR-003: Token Bucket for Rate Limiting

**Decision**: Use token bucket algorithm for rate limiting

**Rationale**:
- Allows controlled bursts (better UX)
- Smooth rate control over time
- Simple to implement and understand
- Per-MCP, per-action granularity

**Alternatives Considered**:
- Leaky bucket: Too strict, poor UX for bursty workloads
- Fixed window: Allows burst at window edges
- Sliding window: More complex, overkill for this use case

## Integration Points

### P1 Control Plane
- **No modifications** to control plane code
- Security checks wrap control plane operations

### P2 Logging Infrastructure
- Security audit events logged to DuckDB
- Query interface for security events
- Integration with `fte logs` commands

### CLI Integration (P2 Feature 003)
- New `fte security` command group
- Enhanced `fte mcp add` with verification
- Security status in `fte status`

### MCP Servers
- Credential injection at runtime
- Signature verification before execution
- Rate limit enforcement on all calls
- Audit logging for all actions

## Security Controls Summary

| Threat | STRIDE | Control | Status |
|--------|--------|---------|--------|
| Malicious MCP | Spoofing, EoP | Server signature verification | Bronze |
| Credential Theft | Info Disclosure | OS keyring storage | Bronze |
| HITL Bypass | Tampering | File integrity checks (nonce) | Silver |
| Data Exfiltration | Info Disclosure | Audit logging, secrets scanning | Bronze |
| Replay Attacks | Tampering | Nonce-based approval | Silver |
| Rate Limit Abuse | DoS | Token bucket rate limiter | Silver |
| Supply Chain Attack | Tampering | Trusted source whitelist | Silver |
| Session Hijacking | Spoofing | MCP process isolation | Gold |
| Secrets in Logs | Info Disclosure | Secrets redaction | Bronze |
| Insider Threat | EoP | Audit trail, least privilege | Gold |

## Incident Response Playbooks

### Playbook 1: Suspicious MCP Activity Detected

**Trigger**: Anomaly detection alert or unusual log patterns

**Steps**:
1. `fte security disable <mcp-name>` - Immediately disable MCP
2. `fte logs query --level CRITICAL --module security --since 1h` - Investigate
3. `fte security audit <mcp-name>` - Generate audit report
4. `fte security rotate <service>` - Rotate compromised credentials
5. Document incident in `/Logs/incidents/`

### Playbook 2: Credential Leak Detected

**Trigger**: Secrets scanner finds exposed credential

**Steps**:
1. Identify leaked credential location
2. `fte security rotate <service>` - Rotate immediately
3. Scan entire vault: `fte security scan vault --deep`
4. Review access logs: `fte logs query --module credential_vault`
5. Update security policy to prevent recurrence

## Success Metrics

### Security
- [ ] Zero plaintext credentials in filesystem
- [ ] All MCP servers verified before execution
- [ ] 100% of MCP actions audit logged
- [ ] Rate limits enforced for all high-risk actions
- [ ] Secrets scanner catches all test patterns

### Performance
- [ ] Credential retrieval <50ms
- [ ] Signature verification <100ms
- [ ] Rate limit check <10ms
- [ ] Audit logging async (no blocking)

### Usability
- [ ] Security setup completes in <5 minutes
- [ ] Clear error messages for all security failures
- [ ] Incident response playbooks available
- [ ] Security dashboard shows current posture

---

**Next Steps**: Run `/sp.tasks` to generate actionable task breakdown.

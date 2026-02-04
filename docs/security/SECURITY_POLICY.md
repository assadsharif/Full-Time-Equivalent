# Security Policy – Digital FTE

## 1. Purpose

Establishes the security principles, controls, and responsibilities for the Digital FTE system. Applies to all components: credential storage, MCP integration, orchestration, and approval workflows.

## 2. Scope

- All MCP server integrations
- Credential storage and rotation
- Approval and HITL workflows
- Orchestrator task execution
- Audit logging and monitoring

## 3. Core Principles

### 3.1 Defense in Depth

| Layer | Control |
|-------|---------|
| Prevention | Rate limiting, signature verification, secrets scanning |
| Detection | Anomaly detection, audit logging, health checks |
| Response | Incident response toolkit, server isolation, credential rotation |
| Recovery | Circuit breakers, bounded retry, checkpoint-based state recovery |

### 3.2 Least Privilege

- MCP servers operate with the minimum permissions needed
- Credential access is logged and auditable
- Approval workflows enforce HITL for high-risk actions

### 3.3 Fail Closed

- Rate-limit violations block the request
- Signature verification failures prevent execution
- Circuit breakers open on repeated failures
- Secrets scanner blocks credentials in logs

### 3.4 Audit Everything

- Every MCP action is logged (append-only)
- Credential access is tracked
- Security scan results are recorded
- Incident response actions are logged

## 4. Credential Management

### 4.1 Storage

- Primary: OS keyring (macOS Keychain / Windows Credential Manager / Linux Secret Service)
- Fallback: Fernet-encrypted JSON file (0600 permissions)

### 4.2 Rotation

- Recommended cycle: 90 days
- Emergency: `fte security rotate-all`
- Individual: `fte vault store <service> <user> <new-value>`

### 4.3 Prohibitions

- Never store credentials in source code or config files
- Never log credentials (SecretsScanner pre-commit hook enforces this)
- Never transmit credentials over unencrypted channels

## 5. MCP Server Policy

### 5.1 Registration

- All MCP servers verified via SHA256 signature
- Trust store: `.fte/mcp-signatures.json`
- Only whitelisted servers may be invoked

### 5.2 Rate Limiting

- Per-server, per-action-type token-bucket limits
- Limits in `config/security.yaml`
- Violations logged and counted toward anomaly baseline

### 5.3 Circuit Breaking

- Repeated failures auto-isolate servers (default: 5 failures → OPEN)
- Recovery probe after 30 seconds (HALF_OPEN)
- Manual reset: `fte security reset-circuit <server>`

## 6. Monitoring

### 6.1 Anomaly Detection

- Volume spikes (7-day baseline, 2σ threshold)
- Timing anomalies (unusual-hour activity)
- Sequence anomalies (never-before-seen action chains)

### 6.2 Health Checks

- Error-rate (warn >10%)
- Throttle-bucket exhaustion
- Circuit-breaker status
- Alert backlog

## 7. Incident Response

See `docs/security/incident-playbooks.md` for full procedures.

| Level | Response Time | Example |
|-------|--------------|---------|
| CRITICAL | Immediate | Credential leak, supply-chain attack |
| HIGH | < 30 min | MCP compromise, mass failures |
| MEDIUM | < 2 h | Anomaly spike, rate-limit abuse |
| LOW | < 24 h | Single verification failure |

## 8. Compliance Checkpoints

- [ ] Quarterly credential rotation review
- [ ] Monthly anomaly-detection threshold review
- [ ] Quarterly incident-response drill
- [ ] Annual penetration test (`PENETRATION_TESTING.md`)
- [ ] Continuous secrets scanning via pre-commit hook

---

**Version**: 1.0 | **Owner**: Security Team | **Updated**: 2026-02-04 | **Review**: Quarterly

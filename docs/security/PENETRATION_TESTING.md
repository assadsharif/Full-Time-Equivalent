# Penetration Testing Guide – Digital FTE

Guide for security teams conducting authorised penetration tests against the FTE system. All tests require written authorisation and must be run in a designated test environment unless explicitly scoped otherwise.

---

## 1. Pre-Test Requirements

- [ ] Written authorisation from Security Lead
- [ ] Test scope document signed
- [ ] Isolated test environment provisioned
- [ ] Baseline snapshot taken (`fte security dashboard --json > baseline.json`)
- [ ] Monitoring enhanced (alert thresholds lowered for duration)
- [ ] Incident-response team on standby

---

## 2. Test Scope

### In Scope

| Area | Test Objective |
|------|----------------|
| Credential Vault | Attempt extraction without authorisation |
| MCP Verification | Supply unsigned / tampered MCP servers |
| Rate Limiter | Burst beyond limits; probe for bypass |
| Circuit Breaker | Exhaust thresholds; confirm auto-open |
| Secrets Scanner | Attempt to inject credentials into logs |
| HITL Bypass | Try to approve without authorised approver |
| Anomaly Detection | Generate traffic that should (and shouldn't) alert |
| Webhook | Replay / forge webhook payloads |

### Out of Scope (unless explicitly included)

- Production credential stores
- External third-party APIs
- Network infrastructure outside the FTE host
- Social-engineering attacks

---

## 3. Test Procedures

### 3.1 Credential Extraction

**Goal**: Prove credentials cannot be retrieved without vault access.

```
Steps:
  1. Attempt to read .fte/security/credentials.json.enc without the key
  2. Attempt keyring access from a non-service account
  3. Try to extract credentials from process memory
  4. Check that SecretsScanner catches any credentials written to stdout/logs

Expected: All attempts blocked or detected
```

### 3.2 MCP Signature Bypass

**Goal**: Attempt to invoke an unsigned or tampered MCP server.

```
Steps:
  1. Create a dummy MCP server binary
  2. Attempt `fte mcp add tampered-server`
  3. Modify an existing trusted server file (change 1 byte)
  4. Attempt invocation via MCPGuard

Expected: VerificationError raised; action logged
```

### 3.3 Rate-Limit Abuse

**Goal**: Exhaust rate limits and confirm enforcement.

```
Steps:
  1. Identify per_minute limit for target action (e.g., email: 10/min)
  2. Fire 11 requests within 60 seconds
  3. Verify RateLimitExceededError on the 11th request
  4. Confirm audit log entry with result=rate_limit_exceeded
  5. Wait for refill and confirm service recovers

Expected: 11th request blocked; log entry present; recovery automatic
```

### 3.4 Circuit-Breaker Exhaustion

**Goal**: Trip a circuit breaker and verify protection.

```
Steps:
  1. Set failure_threshold to 3 in test config
  2. Force 3 consecutive failures (return errors from mock MCP)
  3. Confirm circuit transitions to OPEN
  4. Confirm further requests get CircuitBreakerError immediately
  5. Wait for open_timeout_seconds; confirm HALF_OPEN probe
  6. Return success on probe; confirm circuit closes

Expected: State machine transitions correctly at each threshold
```

### 3.5 Secrets Injection

**Goal**: Attempt to leak credentials into the audit log.

```
Steps:
  1. Craft an MCP action whose result field contains a password string
  2. Submit action through MCPGuard
  3. Check audit log for credential content

Expected: SecretsScanner strips or redacts credential before log write
```

### 3.6 HITL Approval Bypass

**Goal**: Approve a high-risk action without authorisation.

```
Steps:
  1. Create a pending approval for a payment action
  2. Attempt to approve from an account not in authorised_approvers
  3. Attempt to tamper with the approval file (change nonce)
  4. Attempt replay of a previously used nonce

Expected: All bypass attempts rejected; IntegrityChecker / NonceGenerator block
```

### 3.7 Anomaly-Detection Evasion

**Goal**: Generate suspicious traffic that evades detection.

```
Steps:
  1. Gradually ramp volume over 24 h (stay within 2σ each hour)
  2. Distribute unusual actions across many servers
  3. Inject one clearly anomalous burst

Expected: Gradual ramp not flagged; burst detected within 1 refresh cycle
         Note: evasion techniques that succeed should be reported for tuning
```

### 3.8 Webhook Forgery

**Goal**: Send forged webhook payloads.

```
Steps:
  1. Capture a legitimate webhook POST body
  2. Modify severity to critical
  3. Replay to the configured webhook_url

Expected: Receiver does not trust unauthenticated payloads
         Recommendation: add HMAC signing to webhook payloads
```

---

## 4. Reporting

After every test:

1. Record outcome (PASS / FAIL / FINDING)
2. Attach evidence (logs, screenshots, reproductions)
3. For FAIL: open a finding with severity, impact, and recommended fix
4. Update `AUDIT_CHECKLIST.md` with test date and result

### Finding Severity

| Severity | Definition |
|----------|------------|
| Critical | Credential exfiltration or full system compromise possible |
| High | Security control bypassed; data at risk |
| Medium | Partial bypass; requires chained exploitation |
| Low | Informational; no immediate risk |

---

## 5. Post-Test

- [ ] Restore baseline configuration
- [ ] Remove test artifacts (dummy servers, forged payloads)
- [ ] Run `fte security health` to confirm system healthy
- [ ] Deliver findings report within 48 hours
- [ ] Re-test any High or Critical findings after fix

---

**Version**: 1.0 | **Owner**: Security Team | **Updated**: 2026-02-04

# Security Audit Checklist – Digital FTE

Use for periodic or ad-hoc security audits.

---

## 1. Credential Management

- [ ] **Vault integrity** – `fte vault list` shows all expected services
- [ ] **Rotation age** – No credential older than 90 days
- [ ] **Keyring backend** – Active in production; fallback file absent
- [ ] **Key-file perms** – `.vault_key` is 0600, owned by service account
- [ ] **Plaintext leaks** – SecretsScanner clean on `/Logs/` and source tree

## 2. MCP Server Verification

- [ ] **Trust store** – `fte mcp list --verify` all VERIFIED
- [ ] **Unverified servers** – Investigated or removed
- [ ] **Signature freshness** – Re-signed after any upstream release
- [ ] **Whitelist review** – All trusted servers still needed and from approved sources

## 3. Rate Limiting

- [ ] **No throttled buckets** – `fte security dashboard` steady-state clean
- [ ] **Limits vs traffic** – Compare `security.yaml` limits against peak
- [ ] **No bypass paths** – Every MCP call routed through MCPGuard

## 4. Circuit Breakers

- [ ] **No stuck-open circuits** – `fte security circuit-status` all CLOSED
- [ ] **Threshold accuracy** – Replay failure logs; confirm trip at configured threshold
- [ ] **Recovery tested** – Force-open a test circuit; verify HALF_OPEN → CLOSED

## 5. Anomaly Detection

- [ ] **Baseline data** – ≥ 7 days of audit events present
- [ ] **False-positive rate** – ≤ 20 % over last 30 days; tune if exceeded
- [ ] **Alert delivery** – Webhook fires for a test alert

## 6. Incident Response

- [ ] **Playbooks current** – `incident-playbooks.md` reviewed
- [ ] **Isolation test** – Isolate non-production MCP; confirm blocked; restore
- [ ] **Rotation drill** – Single-service credential rotation end-to-end
- [ ] **History audit** – `fte security incident-report --since 30d`

## 7. Audit Logging

- [ ] **Completeness** – Spot-check 20 MCP actions against audit entries
- [ ] **Append-only** – Line count matches backup
- [ ] **Log rotation** – Rotated files exist and are uncorrupted
- [ ] **Retention** – Old logs archived per policy

## 8. Health and Metrics

- [ ] **Health green** – `fte security health` reports HEALTHY
- [ ] **Metrics baseline** – `fte security metrics --since 7d` reviewed
- [ ] **Webhook test** – Test notification received

## 9. Access Controls

- [ ] **Pending approvals** – No stale approvals > 48 h
- [ ] **Approver lists** – `approval.yaml` current
- [ ] **HITL enforcement** – High-risk actions (payment, deploy) require approval

## 10. Configuration

- [ ] **Config diff** – Running config matches committed `security.yaml`
- [ ] **No hardcoded secrets** – `grep -r` scan clean
- [ ] **Environment parity** – Dev and production configs aligned

---

## Sign-Off

| Section | Auditor | Date | Status |
|---------|---------|------|--------|
| Credentials | | | |
| MCP Verification | | | |
| Rate Limiting | | | |
| Circuit Breakers | | | |
| Anomaly Detection | | | |
| Incident Response | | | |
| Audit Logging | | | |
| Health & Metrics | | | |
| Access Controls | | | |
| Configuration | | | |

---

**Version**: 1.0 | **Frequency**: Quarterly

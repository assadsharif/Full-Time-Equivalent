# Security Incident Response Playbooks

Standardized procedures for responding to security incidents in the Digital FTE system.

## Quick Reference

| Incident Type | Severity | Initial Action | Command |
|--------------|----------|---------------|---------|
| Credential Leak | **CRITICAL** | Isolate + Rotate | `fte security isolate <mcp> -r "credential leak"` |
| MCP Compromise | **HIGH** | Isolate + Investigate | `fte security isolate <mcp> -r "compromised"` |
| Anomaly Spike | **MEDIUM** | Investigate + Monitor | `fte security incident-report --since 1h` |
| Rate Limit Abuse | **MEDIUM** | Review + Adjust | `fte security alerts` |

---

## Playbook 1: Credential Leak Response

**Trigger**: Credentials discovered in logs, audit trail, or external breach notification

**Severity**: 🔴 **CRITICAL**

### Immediate Actions (First 5 Minutes)

1. **Isolate Affected Systems**
   ```bash
   # Isolate the compromised MCP server
   fte security isolate <mcp-server> -r "Credential leak detected" -y
   ```

2. **Generate Incident Report**
   ```bash
   # Analyze recent activity
   fte security incident-report --since 24h
   ```

3. **Identify Scope**
   - Which credentials were leaked?
   - Which services are affected?
   - When did the leak occur?
   - Who has access?

### Investigation (Next 30 Minutes)

4. **Review Audit Logs**
   ```bash
   # Check for suspicious access patterns
   fte security alerts --limit 50

   # Scan for anomalies
   fte security scan
   ```

5. **Assess Damage**
   - Review all MCP actions using leaked credentials
   - Check for unauthorized data access
   - Identify lateral movement attempts

### Remediation (Next 2 Hours)

6. **Rotate Compromised Credentials**
   ```bash
   # For single service
   fte vault store <service> <username> <new-password>

   # For mass compromise
   fte security rotate-all -r "Credential vault compromised" -y
   ```

7. **Update Access Controls**
   - Revoke compromised API keys
   - Reset MCP server authentication
   - Update vault permissions

8. **Verify System Integrity**
   ```bash
   # Check MCP server verification
   fte mcp list --verify

   # Scan for secrets in logs
   grep -r "password\|api_key\|token" vault_path/Logs/
   ```

### Recovery (Next 24 Hours)

9. **Restore Services**
   ```bash
   # After credential rotation
   fte security restore <mcp-server> -y
   ```

10. **Post-Incident Analysis**
    - Document timeline
    - Identify root cause
    - Update security controls
    - Schedule follow-up review

### Prevention Measures

- Enable secrets scanning: Pre-commit hooks for credential detection
- Implement credential rotation schedule (90 days)
- Audit vault access logs weekly
- Use temporary credentials where possible

---

## Playbook 2: MCP Server Compromise

**Trigger**: Anomalous behavior, unauthorized actions, or external compromise notification

**Severity**: 🟠 **HIGH**

### Immediate Actions (First 10 Minutes)

1. **Isolate the Server**
   ```bash
   fte security isolate <mcp-server> -r "Suspected compromise" -y
   ```

2. **Generate Incident Report**
   ```bash
   fte security incident-report --since 12h
   ```

3. **Check Circuit Breakers**
   ```bash
   fte security circuit-status
   ```

### Investigation (Next 1 Hour)

4. **Analyze Anomalies**
   ```bash
   # Check for unusual patterns
   fte security alerts --limit 100
   fte security scan --server <mcp-server>
   ```

5. **Review Action History**
   - Examine all actions from compromised server
   - Identify unauthorized operations
   - Check for data exfiltration attempts

6. **Verify Server Integrity**
   ```bash
   # Check MCP server signature
   fte mcp verify <mcp-server>

   # Compare against known-good checksum
   fte mcp list --verify
   ```

### Remediation (Next 4 Hours)

7. **Remove Malicious Changes**
   - Revert unauthorized configuration changes
   - Remove backdoors or persistence mechanisms
   - Restore from clean backup if needed

8. **Update MCP Server**
   ```bash
   # Re-register with verified source
   fte mcp remove <mcp-server>
   fte mcp add <mcp-server> --verify
   ```

9. **Rotate Related Credentials**
   ```bash
   # Rotate credentials for affected services
   fte vault store <service> <username> <new-password>
   ```

### Recovery (Next 24 Hours)

10. **Test and Restore**
    ```bash
    # Test MCP in isolated environment
    fte mcp test <mcp-server>

    # Restore if tests pass
    fte security restore <mcp-server>
    ```

11. **Enhanced Monitoring**
    - Enable verbose audit logging
    - Set up real-time anomaly alerts
    - Schedule increased inspection frequency

### Prevention Measures

- Maintain MCP server whitelist
- Enable signature verification for all MCPs
- Implement least-privilege access
- Regular security audits of MCP configurations

---

## Playbook 3: Unusual Activity Detection

**Trigger**: Anomaly alerts, volume spikes, or timing anomalies

**Severity**: 🟡 **MEDIUM**

### Initial Assessment (First 15 Minutes)

1. **Review Anomaly Alerts**
   ```bash
   fte security alerts --limit 20
   ```

2. **Generate Current Report**
   ```bash
   fte security incident-report --since 1h
   ```

3. **Scan for Active Anomalies**
   ```bash
   fte security scan
   ```

### Investigation (Next 30 Minutes)

4. **Classify Anomaly Type**
   - **Volume Spike**: Unusual number of requests
     - Check if legitimate load increase
     - Review rate limit effectiveness

   - **Timing Anomaly**: Operations at unusual hours
     - Verify if authorized maintenance
     - Check for compromised credentials

   - **Sequence Anomaly**: Unexpected action patterns
     - Compare against known workflows
     - Identify if automation or manual

5. **Identify Root Cause**
   ```bash
   # Check specific server
   fte security incident-report --since 6h | grep <mcp-server>
   ```

### Response Actions

6. **For Legitimate Activity**
   - Document as false positive
   - Adjust baseline thresholds if needed
   - Update anomaly detection rules

7. **For Suspicious Activity**
   - Escalate to MCP Compromise playbook
   - Consider temporary isolation
   - Increase monitoring

8. **For Abuse/Misconfiguration**
   ```bash
   # Adjust rate limits
   # (requires config update)

   # Review and update access patterns
   fte approval pending
   ```

### Prevention Measures

- Tune anomaly detection thresholds
- Document legitimate unusual patterns
- Implement rate limiting per action type
- Schedule regular pattern reviews

---

## Playbook 4: Supply Chain Attack

**Trigger**: Compromised MCP source, malicious dependency, or upstream breach

**Severity**: 🔴 **CRITICAL**

### Immediate Actions (First 5 Minutes)

1. **Isolate All Affected MCPs**
   ```bash
   # Identify affected servers
   fte mcp list --verify

   # Isolate each compromised server
   for mcp in $(cat compromised_servers.txt); do
     fte security isolate "$mcp" -r "Supply chain compromise" -y
   done
   ```

2. **Freeze MCP Updates**
   - Disable automatic MCP updates
   - Block new MCP registrations
   - Document current MCP versions

### Investigation (Next 2 Hours)

3. **Identify Compromise Scope**
   ```bash
   # Check all MCP signatures
   fte mcp list --verify

   # Review installation history
   grep "mcp_installed" vault_path/Logs/security_audit.log
   ```

4. **Analyze Impact**
   - List all actions performed by compromised MCPs
   - Check for data exfiltration
   - Identify compromised credentials

### Remediation (Next 8 Hours)

5. **Remove Compromised MCPs**
   ```bash
   # Remove each affected MCP
   for mcp in $(cat compromised_servers.txt); do
     fte mcp remove "$mcp"
   done
   ```

6. **Rotate All Credentials (If Needed)**
   ```bash
   fte security rotate-all -r "Supply chain compromise" -y
   ```

7. **Install Clean Versions**
   ```bash
   # From verified source only
   fte mcp add <mcp-server> --verify --source <trusted-source>
   ```

### Recovery (Next 48 Hours)

8. **Comprehensive Security Audit**
   - Review all audit logs for compromise period
   - Check for persistence mechanisms
   - Verify data integrity

9. **Restore Operations**
   ```bash
   # After thorough verification
   fte security restore <mcp-server>
   ```

10. **Post-Incident Hardening**
    - Update MCP verification requirements
    - Implement additional supply chain controls
    - Schedule increased monitoring

### Prevention Measures

- Maintain curated MCP whitelist
- Require signature verification for all MCPs
- Implement MCP source pinning
- Regular dependency audits
- Vendor security assessments

---

## Emergency Contacts

### Internal Team
- **Security Lead**: [Contact Info]
- **On-Call Engineer**: [Contact Info]
- **Management**: [Contact Info]

### External Resources
- **Incident Response Partner**: [Contact Info]
- **Legal Counsel**: [Contact Info]
- **Public Relations**: [Contact Info]

---

## Post-Incident Checklist

After any security incident:

- [ ] Incident timeline documented
- [ ] Root cause identified
- [ ] All affected systems remediated
- [ ] Credentials rotated (if applicable)
- [ ] Security controls updated
- [ ] Monitoring enhanced
- [ ] Team debriefed
- [ ] Lessons learned documented
- [ ] Prevention measures implemented
- [ ] Post-incident report filed

---

## Useful Commands Reference

### Investigation
```bash
# Generate incident report
fte security incident-report --since <time>

# View anomaly alerts
fte security alerts --limit <N>

# Scan for current anomalies
fte security scan [--server <mcp>]

# Check circuit breaker status
fte security circuit-status
```

### Response Actions
```bash
# Isolate compromised server
fte security isolate <mcp> -r "<reason>" [-y]

# Restore isolated server
fte security restore <mcp> [-y]

# List isolated servers
fte security isolated

# Mass credential rotation
fte security rotate-all -r "<reason>" [-y]
```

### Verification
```bash
# Verify MCP servers
fte mcp list --verify

# Check vault integrity
fte vault list

# Review approval workflow
fte approval pending
```

---

## Training and Drills

### Quarterly Incident Response Drills

1. **Q1**: Credential Leak Simulation
2. **Q2**: MCP Compromise Simulation
3. **Q3**: Anomaly Detection Exercise
4. **Q4**: Supply Chain Attack Simulation

### Training Materials

- Security incident response training deck
- Hands-on playbook walkthrough
- Tabletop exercises
- Red team assessments

---

**Document Version**: 1.0
**Last Updated**: 2026-02-04
**Owner**: Security Team
**Review Schedule**: Quarterly

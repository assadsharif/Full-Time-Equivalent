# Orchestrator Troubleshooting Guide

## Quick Diagnostics

```bash
# Check orchestrator status
fte orchestrator health

# View recent metrics
fte orchestrator metrics --since 1h

# Inspect queue
fte orchestrator queue

# Tail logs
tail -f ~/AI_Employee_Vault/orchestrator.log
```

## Common Issues

### 1. Orchestrator Not Starting

**Symptoms:**
- `fte orchestrator run` exits immediately
- No checkpoint file created

**Causes & Solutions:**

**A. Vault not initialized**
```bash
# Check vault exists
ls ~/AI_Employee_Vault

# If missing, initialize
fte vault init --path ~/AI_Employee_Vault
```

**B. Permission errors**
```bash
# Check vault permissions
ls -ld ~/AI_Employee_Vault

# Fix permissions
chmod 755 ~/AI_Employee_Vault
chmod 644 ~/AI_Employee_Vault/*.md
```

**C. Configuration errors**
```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('config/orchestrator.yaml'))"

# Check for required fields
grep -E 'vault_path|poll_interval' config/orchestrator.yaml
```

---

### 2. Tasks Stuck in Needs_Action

**Symptoms:**
- Tasks remain in `/Needs_Action` indefinitely
- Queue shows pending tasks but none execute

**Causes & Solutions:**

**A. Stop hook active**
```bash
# Check for stop hook
ls ~/AI_Employee_Vault/.claude_stop

# Remove if present
rm ~/AI_Employee_Vault/.claude_stop
```

**B. All tasks require approval**
```bash
# Check approval keywords
fte orchestrator queue --verbose

# Review pending approvals
ls ~/AI_Employee_Vault/Approvals/APR-*.md

# Approve or reject tasks
fte approval pending
fte approval review <approval-id>
```

**C. Orchestrator not running**
```bash
# Check last checkpoint time
stat ~/.fte/orchestrator.checkpoint.json

# If stale (>5 min), orchestrator stopped
# Restart: fte orchestrator run
```

---

### 3. High Error Rate

**Symptoms:**
- `fte orchestrator health` shows high error rate
- Many tasks in `/Rejected`

**Causes & Solutions:**

**A. Claude Code invocation failures**
```bash
# Check Claude Code is installed
which claude-code

# Test Claude invocation
claude-code --version

# Check logs for Claude errors
grep -i "claude" ~/AI_Employee_Vault/orchestrator.log | tail -20
```

**B. Task format issues**
```bash
# Validate task format
cat ~/AI_Employee_Vault/Done/*.md | head -20

# Ensure tasks have required fields:
# - Title (# heading)
# - **Priority**: High/Medium/Low
# - Task description
```

**C. Timeout issues**
```bash
# Check timeout setting
grep claude_timeout config/orchestrator.yaml

# Increase if tasks are complex
# Edit config/orchestrator.yaml:
orchestrator:
  claude_timeout: 7200  # 2 hours
```

---

### 4. Approval Workflow Problems

**Symptoms:**
- Tasks requiring approval never progress
- Approval files missing

**Causes & Solutions:**

**A. Approval checker not detecting keywords**
```bash
# List approval keywords
grep -A 10 approval_keywords config/orchestrator.yaml

# Verify task content matches
grep -i "deploy" ~/AI_Employee_Vault/Needs_Action/*.md
```

**B. Approval nonce expired**
```bash
# Check approval age
ls -lt ~/AI_Employee_Vault/Approvals/APR-*.md

# Approvals expire after 24 hours
# Re-create expired approvals by moving task back to Needs_Action
```

**C. Approval response format incorrect**
```bash
# Correct format:
# **Decision**: APPROVED or REJECTED
# **Nonce**: <nonce-from-request>

# Check existing approval responses
grep -E "Decision|Nonce" ~/AI_Employee_Vault/Approvals/APR-*.md
```

---

### 5. Checkpoint Corruption

**Symptoms:**
- Orchestrator crashes on startup
- `checkpoint read error` in health check

**Solutions:**

```bash
# Backup corrupted checkpoint
mv ~/.fte/orchestrator.checkpoint.json ~/.fte/orchestrator.checkpoint.json.bak

# Orchestrator will create fresh checkpoint on next run
fte orchestrator run --once
```

---

### 6. Metrics Not Updating

**Symptoms:**
- `fte orchestrator metrics` shows 0 events
- Empty metrics log

**Causes & Solutions:**

**A. Orchestrator not running with metrics enabled**
```bash
# Check metrics config
grep -A 3 metrics: config/orchestrator.yaml

# Ensure enabled: true

# Restart orchestrator to apply
```

**B. Metrics log permissions**
```bash
# Check log file permissions
ls -l ~/.fte/orchestrator_metrics.log

# Fix if needed
chmod 644 ~/.fte/orchestrator_metrics.log
```

**C. No tasks executed yet**
```bash
# Metrics only collected after task execution
# Wait for at least one task to complete
fte orchestrator queue
```

---

### 7. Dashboard / CLI Commands Hanging

**Symptoms:**
- `fte orchestrator dashboard` hangs
- `fte orchestrator health` times out

**Causes & Solutions:**

**A. Large checkpoint file**
```bash
# Check checkpoint size
du -h ~/.fte/orchestrator.checkpoint.json

# If >10MB, truncate exit_log manually
python3 <<'EOF'
import json
from pathlib import Path
ckpt = Path.home() / '.fte' / 'orchestrator.checkpoint.json'
data = json.loads(ckpt.read_text())
data['exit_log'] = data['exit_log'][-100:]  # Keep last 100
ckpt.write_text(json.dumps(data, indent=2))
EOF
```

**B. Filesystem latency**
```bash
# Check vault disk I/O
df -h ~/AI_Employee_Vault
iostat 1 5

# Consider moving vault to faster storage (SSD)
```

---

## Performance Issues

### Slow Task Processing

**Check:**
1. **Priority scoring**: High-priority tasks processed first
2. **Approval gate**: Tasks waiting for approval
3. **Retry backoff**: Failed tasks exponentially delayed

**Tune:**
```yaml
orchestrator:
  poll_interval: 15  # Check more frequently

retry:
  max_delay: 8.0     # Shorter max backoff
```

### High Memory Usage

**Monitor:**
```bash
# Check orchestrator process
ps aux | grep "fte orchestrator"

# If >500MB, investigate:
# - Large task files
# - Excessive logging
# - Checkpoint bloat
```

---

## Debugging Tools

### Enable Verbose Logging

```bash
# Run with verbose output
fte orchestrator run --verbose

# Or set in config
export FTE_LOG_LEVEL=DEBUG
```

### Inspect Checkpoint

```bash
# Pretty-print checkpoint
python3 -m json.tool ~/.fte/orchestrator.checkpoint.json | less

# Check active tasks
jq '.active_tasks' ~/.fte/orchestrator.checkpoint.json

# Check exit log
jq '.exit_log | .[-10:]' ~/.fte/orchestrator.checkpoint.json
```

### Analyze Metrics

```bash
# Count events by type
grep -oP '"event":\s*"\K[^"]+' ~/.fte/orchestrator_metrics.log | sort | uniq -c

# Average task duration
grep task_completed ~/.fte/orchestrator_metrics.log | \
  jq '.duration_seconds' | \
  awk '{sum+=$1; n++} END {print sum/n}'
```

---

## Emergency Recovery

### Orchestrator Looping on Bad Task

**Stop immediately:**
```bash
touch ~/AI_Employee_Vault/.claude_stop
```

**Identify problematic task:**
```bash
# Check active tasks in checkpoint
jq '.active_tasks' ~/.fte/orchestrator.checkpoint.json

# Check recent failures
tail -50 ~/AI_Employee_Vault/orchestrator.log | grep -i error
```

**Move problematic task aside:**
```bash
mv ~/AI_Employee_Vault/Needs_Action/bad_task.md ~/AI_Employee_Vault/Quarantine/
```

**Resume orchestrator:**
```bash
rm ~/AI_Employee_Vault/.claude_stop
fte orchestrator run
```

---

## Getting Help

**Collect diagnostics:**
```bash
# Create diagnostic bundle
mkdir fte-diagnostics
cp ~/.fte/orchestrator.checkpoint.json fte-diagnostics/
tail -100 ~/AI_Employee_Vault/orchestrator.log > fte-diagnostics/orchestrator.log
fte orchestrator health --json > fte-diagnostics/health.json
fte orchestrator metrics > fte-diagnostics/metrics.txt
tar -czf fte-diagnostics.tar.gz fte-diagnostics/

# Share fte-diagnostics.tar.gz with support
```

**Report issues:**
- GitHub: https://github.com/assadsharif/Full-Time-Equivalent/issues
- Include diagnostic bundle
- Describe expected vs. actual behavior
- Include orchestrator.yaml (sanitize secrets)

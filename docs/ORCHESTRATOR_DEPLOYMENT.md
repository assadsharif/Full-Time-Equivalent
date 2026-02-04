# Orchestrator Deployment Guide

## Overview

The Orchestrator (Ralph Wiggum Loop) continuously discovers tasks in `Needs_Action`, scores priorities, enforces HITL approvals, invokes Claude Code, and drives tasks to `/Done` or `/Rejected`.

## Prerequisites

- Python 3.11+
- Git repository initialized
- Claude Code CLI installed (`claude-code`)
- Vault structure initialized (`fte vault init`)

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize vault
fte vault init --path ~/AI_Employee_Vault

# Verify installation
fte status
```

## Configuration

Edit `config/orchestrator.yaml`:

```yaml
orchestrator:
  vault_path: ~/AI_Employee_Vault
  poll_interval: 30
  max_concurrent_tasks: 5
  claude_timeout: 3600

priority_weights:
  urgency: 0.4
  deadline: 0.3
  sender: 0.3

vip_senders:
  - ceo@company.com

approval_keywords:
  - deploy
  - production
  - delete
```

**Key settings:**
- `poll_interval`: How often to check for new tasks (seconds)
- `max_iterations`: Ralph Wiggum bound (max retries per task)
- `approval_keywords`: Triggers HITL approval gate

## Running the Orchestrator

### Development / Testing

```bash
# Dry-run mode (no actual execution)
fte orchestrator run --dry-run

# Single sweep (process once, then exit)
fte orchestrator run --once
```

### Production

```bash
# Continuous operation (recommended)
fte orchestrator run

# With specific config
fte orchestrator run --config /path/to/orchestrator.yaml

# Background mode (tmux/screen recommended)
tmux new -s orchestrator
fte orchestrator run
# Ctrl+B, D to detach
```

## Monitoring

### Real-time Dashboard

```bash
# Live dashboard (refreshes every 5s)
fte orchestrator dashboard --watch

# Queue view
fte orchestrator queue --watch

# Metrics
fte orchestrator metrics --since 24h

# Health check
fte orchestrator health
```

### Checkpoints

Orchestrator state persisted to `.fte/orchestrator.checkpoint.json`:
- Last iteration
- Active tasks
- Exit log (completed/failed tasks)

### Logs

- **Orchestrator log**: `~/AI_Employee_Vault/orchestrator.log`
- **Metrics log**: `.fte/orchestrator_metrics.log`
- **Approval audit**: `.fte/approval_audit.log`

## Emergency Stop

```bash
# Create stop hook
touch ~/AI_Employee_Vault/.claude_stop

# Orchestrator will detect and shut down gracefully at next sweep
```

## Production Deployment

### Systemd Service (Linux)

Create `/etc/systemd/system/orchestrator.service`:

```ini
[Unit]
Description=FTE Orchestrator (Ralph Wiggum Loop)
After=network.target

[Service]
Type=simple
User=fte
WorkingDirectory=/home/fte/orchestrator
ExecStart=/usr/bin/python3 -m fte orchestrator run
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable orchestrator
sudo systemctl start orchestrator
sudo systemctl status orchestrator
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python3", "-m", "fte", "orchestrator", "run"]
```

## Health Checks for Monitoring

Integrate with monitoring tools (Prometheus, Datadog, etc.):

```bash
# JSON output for programmatic access
fte orchestrator health --json

# Exit code 0 = healthy, 1 = degraded/unhealthy
```

## Scaling Considerations

- **Single instance**: Recommended (file-based control plane)
- **Distributed**: Not supported (no leader election)
- **Concurrency**: Controlled via `max_concurrent_tasks` (future enhancement)

## Backup & Recovery

**Critical state:**
- `.fte/orchestrator.checkpoint.json`
- `.fte/orchestrator_metrics.log`
- `.fte/approval_audit.log`

**Backup strategy:**
```bash
# Daily backup
tar -czf orchestrator-backup-$(date +%Y%m%d).tar.gz .fte/
```

## Security

- Approval keywords enforce HITL for dangerous actions
- Secrets stored in `.env` (never commit)
- Audit trail: every state transition logged

## Performance Tuning

**High-volume workloads:**
- Increase `poll_interval` (reduce sweep frequency)
- Decrease `max_iterations` (fail faster)
- Increase `claude_timeout` (longer tasks)

**Low-latency:**
- Decrease `poll_interval` (check more frequently)
- Use priority weights to favor urgent tasks

## Next Steps

- Configure monitoring: `fte orchestrator health --json | your-monitor`
- Set up alerts: hook into `.fte/orchestrator_metrics.log`
- Review troubleshooting guide: `docs/ORCHESTRATOR_TROUBLESHOOTING.md`

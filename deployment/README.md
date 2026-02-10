# FTE Personal AI Employee - Deployment Guide

This directory contains deployment configurations for running the FTE system in production with automatic scheduling.

## Directory Structure

```
deployment/
├── systemd/              # Linux systemd service files
│   ├── fte-gmail-watcher.service
│   ├── fte-filesystem-watcher.service
│   ├── fte-orchestrator.service
│   ├── fte-health-check.service
│   ├── fte-health-check.timer
│   ├── fte-briefing.service
│   └── fte-briefing.timer
├── cron/                 # Cron-based scheduling (alternative)
│   └── crontab.example
├── windows/              # Windows Task Scheduler setup
│   └── Task-Scheduler-Setup.md
└── README.md             # This file
```

## Quick Start

### Linux (systemd) - Recommended

```bash
# 1. Copy service files
sudo cp deployment/systemd/*.service /etc/systemd/system/
sudo cp deployment/systemd/*.timer /etc/systemd/system/

# 2. Create log directory
sudo mkdir -p /var/log/fte
sudo chown fte:fte /var/log/fte

# 3. Create environment files (add your credentials)
sudo mkdir -p /etc/fte
sudo touch /etc/fte/gmail-watcher.env
sudo touch /etc/fte/orchestrator.env
sudo touch /etc/fte/briefing.env

# 4. Reload systemd
sudo systemctl daemon-reload

# 5. Enable and start services
sudo systemctl enable fte-gmail-watcher
sudo systemctl enable fte-filesystem-watcher
sudo systemctl enable fte-orchestrator
sudo systemctl enable fte-health-check.timer
sudo systemctl enable fte-briefing.timer

sudo systemctl start fte-gmail-watcher
sudo systemctl start fte-filesystem-watcher
sudo systemctl start fte-orchestrator
sudo systemctl start fte-health-check.timer
sudo systemctl start fte-briefing.timer

# 6. Check status
sudo systemctl status fte-*
```

### Linux (cron) - Alternative

```bash
# 1. Edit your crontab
crontab -e

# 2. Add entries from deployment/cron/crontab.example
# (Copy and paste relevant lines)

# 3. Verify cron is running
sudo systemctl status cron

# 4. Check logs
tail -f /var/log/fte/orchestrator.log
```

### Windows (Task Scheduler)

See [`windows/Task-Scheduler-Setup.md`](windows/Task-Scheduler-Setup.md) for detailed instructions.

## Environment Variables

### Gmail Watcher (`/etc/fte/gmail-watcher.env`)

```bash
GMAIL_API_KEY=your-gmail-api-key
GMAIL_CLIENT_ID=your-client-id
GMAIL_CLIENT_SECRET=your-client-secret
VAULT_DIR=/home/fte/AI_Employee_Vault
```

### Orchestrator (`/etc/fte/orchestrator.env`)

```bash
VAULT_DIR=/home/fte/AI_Employee_Vault
ORCHESTRATOR_POLL_INTERVAL=300
CLAUDE_API_KEY=your-claude-api-key
```

### CEO Briefing (`/etc/fte/briefing.env`)

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
CEO_EMAIL=ceo@yourcompany.com
VAULT_DIR=/home/fte/AI_Employee_Vault
XERO_ACCESS_TOKEN=your-xero-token
```

## Monitoring

### Check Service Status

```bash
# All FTE services
sudo systemctl status fte-*

# Individual service
sudo systemctl status fte-orchestrator

# View logs
sudo journalctl -u fte-orchestrator -f
sudo journalctl -u fte-gmail-watcher --since "1 hour ago"
```

### View Application Logs

```bash
# Orchestrator
tail -f /var/log/fte/orchestrator.log

# Gmail Watcher
tail -f /var/log/fte/gmail-watcher.log

# All logs
tail -f /var/log/fte/*.log
```

### Health Check

```bash
# Manual health check
fte orchestrator health

# Check timer status
sudo systemctl status fte-health-check.timer
sudo systemctl list-timers --all | grep fte
```

## Restart Services

```bash
# Restart all FTE services
sudo systemctl restart fte-gmail-watcher
sudo systemctl restart fte-filesystem-watcher
sudo systemctl restart fte-orchestrator

# Restart timers
sudo systemctl restart fte-health-check.timer
sudo systemctl restart fte-briefing.timer
```

## Stop Services

```bash
# Stop all FTE services
sudo systemctl stop fte-*

# Disable from auto-start
sudo systemctl disable fte-gmail-watcher
sudo systemctl disable fte-orchestrator
```

## Troubleshooting

### Service Won't Start

1. Check service logs:
   ```bash
   sudo journalctl -xeu fte-orchestrator
   ```

2. Verify paths in service files:
   ```bash
   sudo systemctl cat fte-orchestrator
   ```

3. Test command manually:
   ```bash
   sudo -u fte /opt/fte-employee/.venv/bin/python3 /opt/fte-employee/src/orchestrator/scheduler.py
   ```

### Permission Errors

```bash
# Grant vault access to fte user
sudo chown -R fte:fte /home/fte/AI_Employee_Vault

# Grant log access
sudo chown -R fte:fte /var/log/fte
```

### High CPU/Memory Usage

```bash
# Check resource usage
sudo systemctl status fte-orchestrator

# Limit resources (edit service file)
sudo systemctl edit fte-orchestrator

# Add:
[Service]
CPUQuota=50%
MemoryLimit=512M
```

## Security Considerations

1. **Use Dedicated User**: Run services as `fte` user, not root
2. **Secure Credentials**: Store in environment files with 600 permissions
3. **Log Rotation**: Configure logrotate for `/var/log/fte/*.log`
4. **Firewall**: Only open necessary ports
5. **Regular Updates**: Keep system and Python dependencies updated

## Log Rotation

Create `/etc/logrotate.d/fte`:

```
/var/log/fte/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 fte fte
    sharedscripts
    postrotate
        systemctl reload fte-* || true
    endscript
}
```

## Uninstall

```bash
# Stop and disable services
sudo systemctl stop fte-*
sudo systemctl disable fte-*

# Remove service files
sudo rm /etc/systemd/system/fte-*.service
sudo rm /etc/systemd/system/fte-*.timer

# Reload systemd
sudo systemctl daemon-reload

# Remove logs
sudo rm -rf /var/log/fte

# Remove environment files
sudo rm -rf /etc/fte
```

## Cloud Deployment

For cloud deployment (AWS, GCP, Azure, DigitalOcean), see specific guides:
- AWS: Use EC2 + EBS for vault storage
- GCP: Use Compute Engine + Persistent Disk
- Azure: Use VM + Managed Disks
- DigitalOcean: Use Droplets + Volumes

Key considerations for cloud:
- Use cloud secret management (AWS Secrets Manager, GCP Secret Manager)
- Set up automatic backups for vault
- Configure monitoring/alerting (CloudWatch, Stackdriver, Azure Monitor)
- Use reserved/spot instances for cost optimization
- Set up auto-recovery for failed instances

## Support

For issues or questions:
1. Check logs: `sudo journalctl -xeu fte-orchestrator`
2. Run health check: `fte orchestrator health`
3. Review service status: `sudo systemctl status fte-*`
4. Consult troubleshooting docs in project README

# Digital FTE User Manual

**Version 1.0.0** | **Last Updated: February 2026**

Welcome to the Digital FTE (Full-Time Employee) User Manual. This guide will help you understand, install, and effectively use your AI assistant.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Getting Started](#3-getting-started)
4. [Core Features](#4-core-features)
5. [Command Reference](#5-command-reference)
6. [Workflows & Best Practices](#6-workflows--best-practices)
7. [Troubleshooting](#7-troubleshooting)
8. [Advanced Topics](#8-advanced-topics)
9. [FAQ](#9-faq)

---

## 1. Introduction

### What is Digital FTE?

Digital FTE is an intelligent AI assistant that helps you manage tasks, monitor communications, and generate executive reports. It operates through a file-driven architecture using an Obsidian-compatible vault for task management.

### Key Capabilities

- **📁 Task Management**: Organize work in structured workflows
- **👀 Event Monitoring**: Watch Gmail, WhatsApp, and file system events
- **🔗 External Integrations**: Connect services via MCP (Model Context Protocol)
- **✅ Approval Workflows**: Human-in-the-loop for high-risk actions
- **📊 Executive Briefings**: Automated weekly CEO summaries
- **🎨 Rich CLI**: Beautiful terminal interface with tables and progress bars

### Who Should Use This?

- **Executives**: Monitor tasks and get weekly briefings
- **Personal Assistants**: Manage workflows and approvals
- **Developers**: Integrate external services and automate workflows
- **Teams**: Collaborate on task management with approval controls

---

## 2. Installation

### System Requirements

- **Operating System**: Linux, macOS, or Windows (WSL2)
- **Python**: 3.11 or higher
- **PM2**: For running watcher daemons (optional)
- **Storage**: 100MB minimum for vault and logs

### Prerequisites

#### Install Python 3.11+

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

**macOS:**
```bash
brew install python@3.11
```

**Windows (WSL2):**
```bash
sudo apt update && sudo apt install python3.11
```

#### Install PM2 (Optional, for watchers)

```bash
npm install -g pm2
```

### Installation Steps

#### Option 1: Install from Source (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/digital-fte.git
cd digital-fte

# Create virtual environment
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate  # Windows

# Install the package
pip install -e .

# Verify installation
fte --version
```

#### Option 2: Install via pip (Future)

```bash
pip install digital-fte
```

### Post-Installation

Enable shell completion (optional):

**Bash:**
```bash
echo 'eval "$(_FTE_COMPLETE=bash_source fte)"' >> ~/.bashrc
source ~/.bashrc
```

**Zsh:**
```bash
echo 'eval "$(_FTE_COMPLETE=zsh_source fte)"' >> ~/.zshrc
source ~/.zshrc
```

---

## 3. Getting Started

### Quick Start (5 Minutes)

#### Step 1: Initialize Your Vault

```bash
fte init
```

This creates a vault at `~/.ai_employee_vault/` with the following structure:

```
~/.ai_employee_vault/
├── Inbox/              # New tasks land here
├── Needs_Action/       # Tasks requiring attention
├── In_Progress/        # Currently working on
├── Done/               # Completed tasks
├── Approvals/          # Pending approval requests
├── Briefings/          # Generated reports
├── Attachments/        # File attachments
├── Templates/          # Task templates
├── Dashboard.md        # System overview
├── Company_Handbook.md # AI context & policies
└── config/
    └── mcp_servers.yaml
```

#### Step 2: Check System Status

```bash
fte status
```

**Expected Output:**
```
✅ Vault Structure: OK
📁 Tasks: 0 in Inbox, 0 in Needs_Action
⚠️ Watchers: Not running (use 'fte watcher start')
🔌 MCP Servers: 0 configured
```

#### Step 3: Create Your First Task

```bash
fte vault create \
  --task "Review Q1 financial reports" \
  --priority high
```

**What Happens:**
- A new task file is created in `Inbox/`
- Task ID and metadata are automatically generated
- File is ready to be viewed in Obsidian or moved to `Needs_Action/`

#### Step 4: View Your Tasks

```bash
fte vault list inbox
```

#### Step 5: Open Vault in Obsidian (Optional)

1. Download [Obsidian](https://obsidian.md)
2. Open Obsidian → "Open folder as vault"
3. Select `~/.ai_employee_vault/`
4. Browse `Dashboard.md` for overview

---

## 4. Core Features

### 4.1 Vault Management

The vault is your central task repository organized into folders representing workflow states.

#### Task Lifecycle

```
Inbox → Needs_Action → In_Progress → Done
          ↓
      Approvals (for sensitive actions)
```

#### Creating Tasks

**Via CLI:**
```bash
fte vault create \
  --task "Send payment to vendor" \
  --priority medium
```

**Manually (in Obsidian):**

Create a new file in `Inbox/` with this structure:

```markdown
---
task_id: "task-20260209-001"
priority: high
created_at: "2026-02-09T10:00:00Z"
status: inbox
tags: [urgent, finance]
---

# Task: Review Budget

## Description
Review and approve Q1 budget allocations.

## Acceptance Criteria
- [ ] All departments reviewed
- [ ] Adjustments documented
- [ ] CEO approval obtained
```

#### Listing Tasks

```bash
# List tasks in Inbox
fte vault list inbox

# List all tasks in Needs_Action
fte vault list needs_action

# List completed tasks
fte vault list done
```

#### Moving Tasks

```bash
fte vault move TASK_FILE.md inbox needs_action
```

### 4.2 Watchers (Event Monitoring)

Watchers monitor external sources for new tasks.

#### Available Watchers

- **gmail**: Monitor Gmail inbox for new emails
- **whatsapp**: Monitor WhatsApp messages
- **filesystem**: Watch specific directories for file changes

#### Starting a Watcher

```bash
fte watcher start gmail
```

**What Happens:**
- Watcher runs as a background daemon (via PM2)
- New emails are converted to tasks in `Inbox/`
- Runs continuously until stopped

#### Checking Watcher Status

```bash
fte watcher status
```

**Expected Output:**
```
┌──────────┬──────────┬────────┬──────────┐
│ Watcher  │ Status   │ PID    │ Uptime   │
├──────────┼──────────┼────────┼──────────┤
│ gmail    │ running  │ 12345  │ 2h 15m   │
│ whatsapp │ stopped  │ -      │ -        │
└──────────┴──────────┴────────┴──────────┘
```

#### Viewing Watcher Logs

```bash
# Show last 50 lines
fte watcher logs gmail --tail 50

# Follow logs in real-time
fte watcher logs gmail --follow
```

#### Stopping a Watcher

```bash
fte watcher stop gmail
```

### 4.3 MCP Server Integration

MCP (Model Context Protocol) allows you to connect external APIs and services.

#### Adding an MCP Server

```bash
fte mcp add github-api https://api.github.com/v1/mcp
```

**With Authentication:**
```bash
fte mcp add github-api https://api.github.com/v1/mcp \
  --auth-file ~/.config/github-auth.json
```

**Auth file format (JSON):**
```json
{
  "type": "bearer",
  "token": "ghp_your_token_here"
}
```

#### Listing MCP Servers

```bash
fte mcp list
```

#### Testing MCP Server Health

```bash
fte mcp test github-api
```

#### Viewing Available Tools

```bash
fte mcp tools github-api
```

### 4.4 Approval Workflows

High-risk actions require explicit human approval before execution.

#### Reviewing Pending Approvals

```bash
fte approval list
```

**Expected Output:**
```
┌──────────────┬─────────────────┬────────────┬─────────┐
│ Approval ID  │ Action Type     │ Created    │ Status  │
├──────────────┼─────────────────┼────────────┼─────────┤
│ APR-001      │ send_payment    │ 2h ago     │ pending │
│ APR-002      │ send_email      │ 30m ago    │ pending │
└──────────────┴─────────────────┴────────────┴─────────┘
```

#### Reviewing a Specific Approval

```bash
fte approval show APR-001
```

**What You'll See:**
- Task details
- Action type
- Risk level
- Justification

#### Approving an Action

```bash
fte approval approve APR-001
```

#### Rejecting an Action

```bash
fte approval reject APR-001 --reason "Insufficient budget"
```

### 4.5 CEO Briefings

Generate executive summary reports automatically.

#### Generating a Weekly Briefing

```bash
fte briefing generate
```

**Default:** Last 7 days

#### Generating a Monthly Briefing

```bash
fte briefing generate --days 30
```

#### Generating PDF Output

```bash
fte briefing generate --pdf
```

Output saved to: `~/.ai_employee_vault/Briefings/briefing-YYYYMMDD.pdf`

#### Viewing Latest Briefing

```bash
fte briefing view
```

#### Emailing a Briefing

```bash
fte briefing generate --pdf --email ceo@company.com
```

---

## 5. Command Reference

### Global Options

```bash
--verbose, -v       # Enable verbose logging
--quiet, -q         # Suppress output (errors only)
--no-color          # Disable colored output
--help              # Show help message
```

### Command Groups

#### `fte init`

Initialize a new vault structure.

**Options:**
- `--vault-path PATH`: Custom vault location
- `--force`: Overwrite existing vault

**Example:**
```bash
fte init --vault-path ~/my-custom-vault
```

#### `fte status`

Display system health and statistics.

**Options:**
- `--json`: Output in JSON format

**Example:**
```bash
fte status --json
```

#### `fte vault`

Vault management commands.

**Subcommands:**

- `list FOLDER`: List tasks in folder
- `create`: Create new task
- `move SOURCE DEST`: Move task between folders
- `validate`: Validate vault structure

**Examples:**
```bash
fte vault list inbox
fte vault create --task "Review contracts" --priority high
fte vault move task-001.md inbox needs_action
fte vault validate
```

#### `fte watcher`

Manage event watchers.

**Subcommands:**

- `start NAME`: Start a watcher
- `stop NAME`: Stop a watcher
- `status`: Show all watcher statuses
- `logs NAME`: View watcher logs

**Examples:**
```bash
fte watcher start gmail
fte watcher status
fte watcher logs gmail --tail 100 --follow
fte watcher stop gmail
```

#### `fte mcp`

MCP server management.

**Subcommands:**

- `list`: List configured servers
- `add NAME URL`: Add new server
- `test NAME`: Health check
- `tools NAME`: List available tools

**Examples:**
```bash
fte mcp add slack-api https://slack.com/api/mcp
fte mcp list
fte mcp test slack-api
fte mcp tools slack-api
```

#### `fte approval`

Approval workflow commands.

**Subcommands:**

- `list`: Show pending approvals
- `show ID`: View approval details
- `approve ID`: Approve action
- `reject ID`: Reject action

**Examples:**
```bash
fte approval list
fte approval show APR-001
fte approval approve APR-001
fte approval reject APR-002 --reason "Not authorized"
```

#### `fte briefing`

Generate and manage CEO briefings.

**Subcommands:**

- `generate`: Create new briefing
- `view`: Open latest briefing

**Options:**

- `--days N`: Time period (default: 7)
- `--pdf`: Generate PDF output
- `--email EMAIL`: Send via email

**Examples:**
```bash
fte briefing generate --days 30 --pdf
fte briefing generate --email ceo@company.com
fte briefing view
```

---

## 6. Workflows & Best Practices

### Workflow 1: Daily Task Management

**Morning Routine (5 minutes):**

1. Check system status
   ```bash
   fte status
   ```

2. Review new tasks
   ```bash
   fte vault list inbox
   ```

3. Prioritize and move tasks
   ```bash
   fte vault move urgent-task.md inbox needs_action
   ```

4. Review pending approvals
   ```bash
   fte approval list
   ```

**Evening Routine (3 minutes):**

1. Mark completed tasks
   - Move files from `In_Progress/` to `Done/` in Obsidian

2. Check watcher health
   ```bash
   fte watcher status
   ```

### Workflow 2: Weekly Briefing Generation

**Every Monday at 9 AM:**

```bash
# Generate last week's briefing with PDF
fte briefing generate --days 7 --pdf

# Email to CEO
fte briefing generate --days 7 --pdf --email ceo@company.com
```

**Automate with cron:**
```bash
0 9 * * 1 cd /path/to/digital-fte && source .venv/bin/activate && fte briefing generate --days 7 --pdf --email ceo@company.com
```

### Workflow 3: Approval Request Handling

**When you receive a sensitive action request:**

1. List pending approvals
   ```bash
   fte approval list
   ```

2. Review details
   ```bash
   fte approval show APR-001
   ```

3. Make decision
   ```bash
   # If approved
   fte approval approve APR-001

   # If rejected
   fte approval reject APR-001 --reason "Requires CFO approval"
   ```

### Best Practices

#### ✅ DO

- **Keep vault organized**: Move tasks promptly to appropriate folders
- **Use priority flags**: Mark urgent tasks with `priority: high`
- **Review approvals daily**: Don't let approvals pile up
- **Monitor watcher logs**: Check for errors weekly
- **Archive old briefings**: Keep last 3 months, delete older ones
- **Backup vault regularly**: `tar -czf vault-backup.tar.gz ~/.ai_employee_vault/`

#### ❌ DON'T

- **Don't skip approvals**: High-risk actions need explicit consent
- **Don't edit approval nonces**: This breaks replay protection
- **Don't run multiple watchers on same source**: Creates duplicates
- **Don't store secrets in task files**: Use MCP auth files instead
- **Don't bypass vault validation**: Ensures data integrity

---

## 7. Troubleshooting

### Common Issues

#### Issue: `fte: command not found`

**Cause:** Virtual environment not activated or package not installed

**Solution:**
```bash
source /path/to/digital-fte/.venv/bin/activate
pip install -e /path/to/digital-fte
```

#### Issue: Watcher won't start

**Symptoms:**
```
❌ Error: PM2 not installed
```

**Solution:**
```bash
npm install -g pm2
```

#### Issue: Gmail watcher authentication fails

**Symptoms:**
```
❌ Error: Invalid credentials
```

**Solution:**
1. Visit Google Cloud Console
2. Enable Gmail API
3. Download `credentials.json`
4. Place in `~/.ai_employee_vault/config/`
5. Restart watcher

#### Issue: Approval integrity check fails

**Symptoms:**
```
❌ ApprovalIntegrityError: Hash mismatch
```

**Solution:**
- File was manually edited after creation
- **Fix:** Reject the approval and create a new one
- **Prevention:** Don't edit approval files manually

#### Issue: Briefing generation fails

**Symptoms:**
```
❌ Error: No tasks found in Done folder
```

**Solution:**
- Ensure tasks are in `Done/` folder with completion dates
- Check date range: `--days` parameter may be too narrow

#### Issue: Vault validation errors

**Symptoms:**
```
❌ Validation failed: Missing frontmatter field 'task_id'
```

**Solution:**
```bash
# Run validation to see all errors
fte vault validate

# Fix each file manually or use template
fte vault create --task "Template example"
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
fte --verbose status
fte --verbose watcher start gmail
```

### Log Locations

- **Watchers**: `~/.pm2/logs/`
- **CLI**: Console output (use `--verbose`)
- **Vault operations**: `~/.ai_employee_vault/Logs/`

---

## 8. Advanced Topics

### Custom Vault Locations

Override default vault path:

**Option 1: Environment variable**
```bash
export FTE_VAULT_PATH=~/my-custom-vault
fte init
```

**Option 2: CLI flag**
```bash
fte --vault-path ~/my-custom-vault init
```

### Configuring MCP Auth

**OAuth 2.0:**
```json
{
  "type": "oauth2",
  "client_id": "your-client-id",
  "client_secret": "your-secret",
  "token_url": "https://oauth.example.com/token"
}
```

**API Key:**
```json
{
  "type": "apikey",
  "header": "X-API-Key",
  "value": "your-api-key"
}
```

### Task Templates

Create custom templates in `.ai_employee_vault/Templates/`:

**Example: `meeting_notes_template.md`**
```markdown
---
task_id: "GENERATED"
type: meeting_notes
priority: medium
tags: [meetings]
---

# Meeting: [TITLE]

**Date:** [DATE]
**Attendees:** [LIST]

## Agenda
1.
2.
3.

## Notes


## Action Items
- [ ]
- [ ]

## Next Steps

```

### Scheduled Briefings with Cron

**Edit crontab:**
```bash
crontab -e
```

**Add entry (Monday 9 AM):**
```cron
0 9 * * 1 cd /path/to/digital-fte && source .venv/bin/activate && fte briefing generate --days 7 --pdf --email ceo@company.com >> /var/log/fte-briefing.log 2>&1
```

### Multi-User Setup

**Shared vault on network drive:**

1. Initialize vault on shared location:
   ```bash
   fte init --vault-path /shared/ai-vault
   ```

2. Each user sets vault path:
   ```bash
   export FTE_VAULT_PATH=/shared/ai-vault
   ```

3. Configure file permissions:
   ```bash
   chmod -R 775 /shared/ai-vault
   ```

---

## 9. FAQ

### General

**Q: Is Digital FTE open source?**
A: Yes, released under MIT License.

**Q: Can I use this commercially?**
A: Yes, the MIT License allows commercial use.

**Q: Does it work on Windows?**
A: Yes, via WSL2 (Windows Subsystem for Linux).

### Technical

**Q: Where is data stored?**
A: All data is local in `~/.ai_employee_vault/` by default.

**Q: Can I sync my vault to cloud storage?**
A: Yes! Use Dropbox, Google Drive, or any sync service. Point `FTE_VAULT_PATH` to synced folder.

**Q: How do I back up my vault?**
A: Simple tar archive: `tar -czf backup.tar.gz ~/.ai_employee_vault/`

**Q: Can I customize task workflows?**
A: Yes, edit state transitions in `.vault_schema/state_transitions.md`

### Security

**Q: How are credentials stored?**
A: MCP credentials use OS keyring (secure system-level storage).

**Q: Are approval nonces reusable?**
A: No, nonces are single-use to prevent replay attacks.

**Q: Can I disable approval workflows?**
A: Not recommended, but you can skip by immediately approving.

### Usage

**Q: How many tasks can the vault handle?**
A: Tested with 10,000+ tasks. Performance degrades slightly above 50,000.

**Q: Can I have multiple vaults?**
A: Yes, use `--vault-path` to switch between vaults.

**Q: Does it work offline?**
A: Core features (vault, approvals, briefings) work offline. Watchers and MCP require internet.

---

## Getting Help

### Documentation

- **User Manual**: This document
- **CLI Reference**: `docs/cli/user-guide.md`
- **Developer Guide**: `docs/cli/developer-guide.md`
- **Feature Specs**: `specs/`

### Support Channels

- **GitHub Issues**: Report bugs and feature requests
- **GitHub Discussions**: Ask questions and share tips
- **Email**: support@example.com

### Contributing

Contributions welcome! See `CONTRIBUTING.md` for guidelines.

---

## Appendix

### Glossary

- **Vault**: Your task repository (Obsidian-compatible)
- **MCP**: Model Context Protocol for external integrations
- **Watcher**: Background daemon monitoring events
- **HITL**: Human-in-the-Loop (approval workflows)
- **Frontmatter**: YAML metadata at top of task files
- **Nonce**: One-time-use token for replay protection

### Keyboard Shortcuts (Obsidian)

- `Cmd/Ctrl + N`: New note
- `Cmd/Ctrl + O`: Open quick switcher
- `Cmd/Ctrl + E`: Toggle edit/preview
- `Cmd/Ctrl + ,`: Open settings

### File Naming Conventions

- Tasks: `task-YYYYMMDD-NNN.md`
- Approvals: `approval-ID.md`
- Briefings: `briefing-YYYYMMDD.md`

---

**Digital FTE User Manual v1.0.0**
*Built with ❤️ for productivity*


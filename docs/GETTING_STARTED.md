# Getting Started with Digital FTE

**Fast-track guide to get up and running in 10 minutes**

---

## Prerequisites Checklist

Before you begin, ensure you have:

- [ ] Python 3.11 or higher installed
- [ ] pip (Python package manager) installed
- [ ] Terminal/command line access
- [ ] (Optional) Node.js and npm for watcher daemons

### Quick Python Check

```bash
python3 --version  # Should show 3.11+
```

If not installed, see [Installation Guide](USER_MANUAL.md#2-installation)

---

## Installation (3 minutes)

### Step 1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/yourusername/digital-fte.git
cd digital-fte

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install package
pip install -e .

# Verify
fte --version
```

**Expected output:** `Digital FTE CLI v0.1.0`

---

## Quick Start (5 minutes)

### Step 2: Initialize Your Vault

```bash
fte init
```

**What this does:**
- Creates `~/.ai_employee_vault/` directory
- Sets up folder structure (Inbox, Needs_Action, Done, etc.)
- Generates Dashboard and Company Handbook
- Configures Obsidian settings

**Output:**
```
✅ Vault initialized at /home/user/.ai_employee_vault/
📁 Created 8 folders
📄 Generated Dashboard.md and Company_Handbook.md
```

### Step 3: Create Your First Task

```bash
fte vault create \
  --task "Review quarterly budget" \
  --priority high
```

**Output:**
```
✅ Task created: task-20260209-001.md
📍 Location: /home/user/.ai_employee_vault/Inbox/
```

### Step 4: View Your Tasks

```bash
fte vault list inbox
```

**Output:**
```
┌─────────────────────┬──────────────────────────┬──────────┬────────────┐
│ File                │ Task                     │ Priority │ Created    │
├─────────────────────┼──────────────────────────┼──────────┼────────────┤
│ task-20260209-001   │ Review quarterly budget  │ high     │ 2min ago   │
└─────────────────────┴──────────────────────────┴──────────┴────────────┘
```

### Step 5: Check System Status

```bash
fte status
```

**Output:**
```
Digital FTE System Status
═════════════════════════

✅ Vault Structure: OK
   Location: /home/user/.ai_employee_vault/

📊 Task Summary:
   Inbox: 1
   Needs Action: 0
   In Progress: 0
   Done: 0
   Pending Approvals: 0

👀 Watchers:
   ⚠️ Not running (use 'fte watcher start <name>')

🔌 MCP Servers: 0 configured
```

---

## Next Steps

### Option A: Use CLI Only

Continue using terminal commands:

```bash
# Move task to needs action
fte vault move task-20260209-001.md inbox needs_action

# List tasks requiring action
fte vault list needs_action
```

### Option B: Use with Obsidian

1. **Download Obsidian** (if not installed)
   - Visit: https://obsidian.md
   - Install for your platform

2. **Open Vault**
   - Launch Obsidian
   - Click "Open folder as vault"
   - Navigate to `~/.ai_employee_vault/`
   - Click "Open"

3. **Explore**
   - Open `Dashboard.md` for system overview
   - Browse tasks in `Inbox/` folder
   - Edit tasks with rich markdown editor

### Option C: Setup Watchers

Monitor Gmail for new tasks:

1. **Install PM2**
   ```bash
   npm install -g pm2
   ```

2. **Configure Gmail API** (one-time setup)
   - Visit: https://console.cloud.google.com
   - Enable Gmail API
   - Download `credentials.json`
   - Place in `~/.ai_employee_vault/config/`

3. **Start Watcher**
   ```bash
   fte watcher start gmail
   ```

4. **Verify**
   ```bash
   fte watcher status
   ```

---

## Common Workflows

### Daily Task Triage (Morning)

```bash
# 1. Check for new tasks
fte vault list inbox

# 2. Prioritize important tasks
fte vault move urgent-task.md inbox needs_action

# 3. Check approvals
fte approval list
```

### Weekly Briefing (Monday)

```bash
# Generate last week's summary
fte briefing generate --days 7 --pdf

# Email to CEO
fte briefing generate --days 7 --pdf --email ceo@company.com
```

### Approval Workflow

```bash
# 1. List pending approvals
fte approval list

# 2. Review details
fte approval show APR-001

# 3. Approve or reject
fte approval approve APR-001
# OR
fte approval reject APR-001 --reason "Needs CFO sign-off"
```

---

## Essential Commands Cheat Sheet

```bash
# INITIALIZATION
fte init                           # Create new vault
fte status                         # System health check

# TASKS
fte vault list inbox               # Show inbox tasks
fte vault create --task "..."      # New task
fte vault move FILE inbox done     # Move task

# WATCHERS
fte watcher start gmail            # Start Gmail monitoring
fte watcher status                 # Check watcher health
fte watcher logs gmail             # View logs

# APPROVALS
fte approval list                  # Pending approvals
fte approval approve ID            # Approve action
fte approval reject ID             # Reject action

# BRIEFINGS
fte briefing generate --pdf        # Create PDF report
fte briefing view                  # Open latest

# MCP INTEGRATION
fte mcp list                       # List servers
fte mcp add NAME URL               # Add server
fte mcp test NAME                  # Health check

# HELP
fte --help                         # Main help
fte vault --help                   # Command-specific help
```

---

## Troubleshooting Quick Fixes

### Command Not Found

```bash
# Activate virtual environment
source /path/to/digital-fte/.venv/bin/activate

# Re-install if needed
pip install -e /path/to/digital-fte
```

### Permission Denied

```bash
# Check vault permissions
ls -la ~/.ai_employee_vault/

# Fix if needed
chmod -R 755 ~/.ai_employee_vault/
```

### Watcher Won't Start

```bash
# Install PM2
npm install -g pm2

# Restart watcher
fte watcher stop gmail
fte watcher start gmail
```

---

## Learning Path

1. **Week 1: Master the Basics**
   - ✅ Vault initialization
   - ✅ Task creation and management
   - ✅ CLI commands

2. **Week 2: Automation**
   - ⬜ Setup watchers (Gmail/WhatsApp)
   - ⬜ Configure MCP servers
   - ⬜ Approval workflows

3. **Week 3: Advanced**
   - ⬜ Weekly briefing automation
   - ⬜ Custom task templates
   - ⬜ Multi-user setup

---

## Resources

### Documentation

- **[User Manual](USER_MANUAL.md)** - Complete reference (100+ pages)
- **[CLI Guide](cli/user-guide.md)** - Detailed command documentation
- **[Developer Guide](cli/developer-guide.md)** - For customization

### Examples

- **[Feature Specs](../specs/)** - Implementation details
- **[Sample Tasks](../tests/fixtures/)** - Example task files
- **[Templates](../.vault_templates/Templates/)** - Task templates

### Support

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Community Q&A
- **Email**: support@example.com

---

## What's Next?

### Immediate Actions

1. **Create 3-5 sample tasks** to familiarize yourself with the workflow
2. **Explore vault in Obsidian** (visual interface)
3. **Read `Company_Handbook.md`** to understand AI context

### Optional Enhancements

- **Setup shell completion** for faster typing
- **Configure watchers** for automatic task creation
- **Add MCP servers** for external integrations
- **Schedule weekly briefings** via cron

### Deep Dive

- **Read full [User Manual](USER_MANUAL.md)** for comprehensive understanding
- **Review [Architecture](../README.md#architecture)** to understand system design
- **Explore [Feature Specs](../specs/)** for detailed capabilities

---

## Success Checklist

After completing this guide, you should be able to:

- [ ] Initialize a vault
- [ ] Create and list tasks
- [ ] Check system status
- [ ] Understand folder structure
- [ ] Use basic CLI commands
- [ ] Know where to find help

**Congratulations! You're ready to use Digital FTE.**

---

**Need help?** Open an issue or check the [FAQ](USER_MANUAL.md#9-faq)

**Want to contribute?** See [CONTRIBUTING.md](../CONTRIBUTING.md)


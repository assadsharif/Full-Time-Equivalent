# CLI User Guide

**Digital FTE AI Assistant - Command Line Interface**

Version: 1.0.0
Last Updated: 2026-01-29

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Command Reference](#command-reference)
5. [Common Workflows](#common-workflows)
6. [Troubleshooting](#troubleshooting)
7. [Configuration](#configuration)

---

## Introduction

The Digital FTE CLI (`fte`) is a unified command-line interface for managing your AI Employee system. It provides commands for:

- **Vault Management** - Organize tasks, approvals, and briefings
- **Watcher Lifecycle** - Monitor Gmail, WhatsApp, and filesystem events
- **MCP Server Management** - Integrate external services via Model Context Protocol
- **Approval Workflows** - Review and approve high-risk actions
- **CEO Briefings** - Generate weekly executive summaries

---

## Installation

### Prerequisites

- Python 3.11+
- PM2 (for watcher management): `npm install -g pm2`
- wkhtmltopdf (optional, for PDF briefings): `apt-get install wkhtmltopdf`

### Install from Source

```bash
# Clone the repository
git clone <repository-url>
cd digital-fte

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Verify installation
fte --version
```

---

## Quick Start

### 1. Initialize Your Vault

```bash
# Initialize vault in default location (~/.ai_employee_vault)
fte init

# Or specify custom location
fte init --vault-path ~/my_custom_vault
```

### 2. Check System Status

```bash
# View overall system health
fte status

# Check with verbose output
fte status --verbose
```

### 3. Create Your First Task

```bash
# Create a task interactively
fte vault create

# Or specify task directly
fte vault create --task "Review Q1 reports" --priority high
```

### 4. Start Watchers

```bash
# Start Gmail watcher
fte watcher start gmail

# Check watcher status
fte watcher status
```

---

## Command Reference

### Global Options

All commands support these global flags:

```bash
--help          # Show command help
--verbose       # Enable verbose logging (DEBUG level)
--quiet         # Suppress non-error output (ERROR level only)
--no-color      # Disable colored output (useful for CI/CD)
```

---

### `fte init` - Initialize Vault

Create a new AI Employee vault with proper folder structure.

**Usage:**
```bash
fte init [OPTIONS]
```

**Options:**
- `--vault-path PATH` - Custom vault location (default: `~/.ai_employee_vault`)
- `--force` - Overwrite existing vault

**Examples:**
```bash
# Default initialization
fte init

# Custom location
fte init --vault-path ~/Documents/AI_Vault

# Force reinitialize
fte init --force
```

**Vault Structure Created:**
```
AI_Employee_Vault/
├── Inbox/              # New tasks
├── Needs_Action/       # Tasks requiring attention
├── Done/               # Completed tasks
├── Approvals/          # Pending approvals
├── Briefings/          # Generated briefings
└── config/
    └── mcp_servers.yaml  # MCP server registry
```

---

### `fte status` - System Status

View health status of all system components.

**Usage:**
```bash
fte status [OPTIONS]
```

**Options:**
- `--vault-path PATH` - Path to vault
- `--json` - Output in JSON format
- `--verbose` - Show detailed diagnostics

**Examples:**
```bash
# Quick status check
fte status

# Detailed status
fte status --verbose

# JSON output (for scripts)
fte status --json
```

**Output Includes:**
- ✓ Vault validation and folder structure
- ✓ Watcher status (gmail, whatsapp, filesystem)
- ✓ MCP server health checks
- ✓ Pending approval count
- ✓ Last briefing date

---

### `fte vault` - Vault Management

Manage tasks and vault content.

#### `fte vault list` - List Tasks

List tasks from vault folders.

**Usage:**
```bash
fte vault list [OPTIONS] FOLDER
```

**Arguments:**
- `FOLDER` - Folder to list: `inbox`, `needs_action`, `done`, `approvals`, `briefings`

**Options:**
- `--vault-path PATH` - Path to vault

**Examples:**
```bash
# List inbox tasks
fte vault list inbox

# List completed tasks
fte vault list done

# List pending approvals
fte vault list approvals
```

#### `fte vault create` - Create Task

Create a new task in the vault.

**Usage:**
```bash
fte vault create [OPTIONS]
```

**Options:**
- `--vault-path PATH` - Path to vault
- `--task TEXT` - Task description
- `--priority TEXT` - Priority level: `high`, `medium`, `low`
- `--folder TEXT` - Target folder (default: `inbox`)

**Examples:**
```bash
# Interactive creation
fte vault create

# Quick task creation
fte vault create --task "Review contracts" --priority high

# Create directly in needs_action
fte vault create --task "Call vendor" --folder needs_action
```

#### `fte vault move` - Move Task

Move tasks between folders.

**Usage:**
```bash
fte vault move [OPTIONS] TASK_FILE FROM_FOLDER TO_FOLDER
```

**Arguments:**
- `TASK_FILE` - Task filename (without .md extension)
- `FROM_FOLDER` - Source folder
- `TO_FOLDER` - Destination folder

**Examples:**
```bash
# Move task to needs_action
fte vault move task_001 inbox needs_action

# Mark task as done
fte vault move task_001 needs_action done
```

---

### `fte watcher` - Watcher Lifecycle

Manage daemon processes that monitor external events.

#### `fte watcher start` - Start Watcher

Start a watcher daemon using PM2.

**Usage:**
```bash
fte watcher start [OPTIONS] NAME
```

**Arguments:**
- `NAME` - Watcher name: `gmail`, `whatsapp`, `filesystem`

**Options:**
- `--vault-path PATH` - Path to vault

**Examples:**
```bash
# Start Gmail watcher
fte watcher start gmail

# Start all watchers
fte watcher start gmail
fte watcher start whatsapp
fte watcher start filesystem
```

#### `fte watcher stop` - Stop Watcher

Stop a running watcher daemon.

**Usage:**
```bash
fte watcher stop [OPTIONS] NAME
```

**Examples:**
```bash
# Stop Gmail watcher
fte watcher stop gmail

# Stop all watchers
fte watcher stop gmail
fte watcher stop whatsapp
fte watcher stop filesystem
```

#### `fte watcher status` - Check Status

View status of all watchers.

**Usage:**
```bash
fte watcher status [OPTIONS]
```

**Options:**
- `--vault-path PATH` - Path to vault

**Examples:**
```bash
# View all watcher status
fte watcher status
```

**Output Shows:**
- Watcher name
- Status (online, stopped, errored)
- Uptime
- CPU usage
- Memory usage
- Restart count

#### `fte watcher logs` - View Logs

View watcher logs in real-time or historical.

**Usage:**
```bash
fte watcher logs [OPTIONS] NAME
```

**Arguments:**
- `NAME` - Watcher name

**Options:**
- `--tail INTEGER` - Number of lines to show (default: 50)
- `--follow` - Follow logs in real-time (like `tail -f`)

**Examples:**
```bash
# View last 50 lines
fte watcher logs gmail

# View last 100 lines
fte watcher logs gmail --tail 100

# Follow logs in real-time
fte watcher logs gmail --follow
```

---

### `fte mcp` - MCP Server Management

Manage Model Context Protocol (MCP) server integrations.

#### `fte mcp list` - List Servers

List all registered MCP servers.

**Usage:**
```bash
fte mcp list [OPTIONS]
```

**Options:**
- `--vault-path PATH` - Path to vault

**Examples:**
```bash
# List all MCP servers
fte mcp list
```

**Output Shows:**
- Server name
- URL
- Status (healthy, unhealthy, unknown)
- Auth type

#### `fte mcp add` - Add Server

Register a new MCP server.

**Usage:**
```bash
fte mcp add [OPTIONS] NAME URL
```

**Arguments:**
- `NAME` - Server identifier (alphanumeric, hyphens, underscores)
- `URL` - Server URL (http:// or https://)

**Options:**
- `--vault-path PATH` - Path to vault
- `--auth-file PATH` - Path to authentication file (JSON)

**Examples:**
```bash
# Add public server
fte mcp add github-api https://api.github.com

# Add server with authentication
fte mcp add private-api https://api.example.com --auth-file ~/auth.json
```

**Auth File Format (JSON):**
```json
{
  "type": "bearer",
  "token": "your-token-here"
}
```

#### `fte mcp test` - Health Check

Test connectivity and health of an MCP server.

**Usage:**
```bash
fte mcp test [OPTIONS] NAME
```

**Arguments:**
- `NAME` - Server name

**Options:**
- `--vault-path PATH` - Path to vault
- `--timeout INTEGER` - Request timeout in seconds (default: 5)

**Examples:**
```bash
# Test server health
fte mcp test github-api

# Test with custom timeout
fte mcp test slow-api --timeout 30
```

#### `fte mcp tools` - List Tools

Discover available tools from an MCP server.

**Usage:**
```bash
fte mcp tools [OPTIONS] NAME
```

**Arguments:**
- `NAME` - Server name

**Options:**
- `--vault-path PATH` - Path to vault

**Examples:**
```bash
# List available tools
fte mcp tools github-api
```

**Output Shows:**
- Tool names
- Tool descriptions
- Parameters
- Organized in tree structure

---

### `fte approval` - Approval Workflow

Review and manage approval requests.

#### `fte approval pending` - List Pending

List all pending approval requests.

**Usage:**
```bash
fte approval pending [OPTIONS]
```

**Options:**
- `--vault-path PATH` - Path to vault

**Examples:**
```bash
# List pending approvals
fte approval pending
```

**Output Shows:**
- Approval ID
- Action type
- Risk level (color-coded)
- Created date
- Expiry date
- Task ID

#### `fte approval review` - Review Approval

Interactively review and decide on an approval request.

**Usage:**
```bash
fte approval review [OPTIONS] APPROVAL_ID
```

**Arguments:**
- `APPROVAL_ID` - Approval identifier

**Options:**
- `--vault-path PATH` - Path to vault

**Examples:**
```bash
# Review specific approval
fte approval review PAYMENT_APPROVAL_001
```

**Interactive Prompts:**
1. View approval details (action type, risk level, task context)
2. Choose action:
   - **Approve** - Grant permission for action
   - **Reject** - Deny action with reason
   - **Skip** - Review later

**Security Features:**
- Nonce validation (prevents replay attacks)
- Integrity verification (detects tampering)
- Expiry checking (time-limited approvals)
- Audit logging (tracks all decisions)

---

### `fte briefing` - CEO Briefings

Generate and view executive summary reports.

#### `fte briefing generate` - Generate Report

Create a weekly CEO briefing from completed tasks.

**Usage:**
```bash
fte briefing generate [OPTIONS]
```

**Options:**
- `--vault-path PATH` - Path to vault
- `--days INTEGER` - Number of days to include (default: 7)
- `--pdf` - Generate PDF in addition to Markdown

**Examples:**
```bash
# Generate weekly briefing
fte briefing generate

# Generate bi-weekly briefing
fte briefing generate --days 14

# Generate with PDF
fte briefing generate --pdf
```

**Briefing Includes:**
- Executive summary
- Tasks completed (with priority indicators)
- Key metrics (total tasks, priority breakdown)
- Next week focus areas
- Generated date and period

**Output Location:**
- Markdown: `/Briefings/briefing_YYYY-MM-DD.md`
- PDF: `/Briefings/briefing_YYYY-MM-DD.pdf` (if --pdf flag used)

#### `fte briefing view` - View Latest

Open the most recent briefing report.

**Usage:**
```bash
fte briefing view [OPTIONS]
```

**Options:**
- `--vault-path PATH` - Path to vault

**Examples:**
```bash
# View latest briefing
fte briefing view
```

**Viewer Detection:**
The command automatically detects and uses available Markdown viewers:
1. Typora
2. Obsidian
3. MarkText
4. Ghostwriter
5. Cat (fallback, displays in terminal)

---

## Common Workflows

### Daily Workflow

```bash
# 1. Check system status
fte status

# 2. Review pending approvals
fte approval pending
fte approval review <approval-id>

# 3. Check inbox for new tasks
fte vault list inbox

# 4. Move tasks to needs_action
fte vault move task_001 inbox needs_action

# 5. Check watcher logs
fte watcher logs gmail --tail 20
```

### Weekly Workflow

```bash
# 1. Generate CEO briefing
fte briefing generate --pdf

# 2. View briefing
fte briefing view

# 3. Archive completed tasks
fte vault list done

# 4. Clean up old tasks (manual)
```

### Setup New Integration

```bash
# 1. Add MCP server
fte mcp add slack-api https://slack.com/api --auth-file ~/slack-auth.json

# 2. Test connectivity
fte mcp test slack-api

# 3. Discover available tools
fte mcp tools slack-api

# 4. Use in your workflows
```

### Troubleshooting Watcher Issues

```bash
# 1. Check watcher status
fte watcher status

# 2. View error logs
fte watcher logs gmail --tail 100

# 3. Restart watcher
fte watcher stop gmail
fte watcher start gmail

# 4. Verify PM2 is running
pm2 status
```

---

## Troubleshooting

### Common Issues

#### "Vault not found or invalid"

**Cause:** Vault not initialized or path incorrect.

**Solution:**
```bash
# Initialize vault
fte init

# Or specify correct path
fte status --vault-path ~/correct/path
```

#### "PM2 is not installed"

**Cause:** PM2 process manager not available.

**Solution:**
```bash
# Install PM2 globally
npm install -g pm2

# Verify installation
pm2 --version
```

#### "wkhtmltopdf not installed"

**Cause:** PDF generation tool not available.

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install wkhtmltopdf

# macOS
brew install wkhtmltopdf

# Or skip PDF generation
fte briefing generate  # Without --pdf flag
```

#### "Approval expired"

**Cause:** Approval request exceeded expiry time.

**Solution:**
- Approvals are time-limited for security
- Request must be re-created by AI agent
- Review approvals promptly

#### "Invalid nonce"

**Cause:** Approval file may be corrupted or tampered with.

**Solution:**
- Check file integrity
- Request new approval from AI agent
- Report potential security issue

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Run any command with --verbose
fte status --verbose
fte watcher start gmail --verbose
fte briefing generate --verbose
```

### Log Locations

```
~/.ai_employee_vault/logs/
├── cli.log              # CLI command logs
├── watchers/
│   ├── gmail.log        # Gmail watcher logs
│   ├── whatsapp.log     # WhatsApp watcher logs
│   └── filesystem.log   # Filesystem watcher logs
└── mcp/
    └── servers.log      # MCP server logs
```

---

## Configuration

### Vault Configuration

Edit `~/.ai_employee_vault/config/config.yaml`:

```yaml
vault:
  path: ~/.ai_employee_vault
  auto_archive_days: 30

watchers:
  gmail:
    check_interval: 60  # seconds
  whatsapp:
    check_interval: 30
  filesystem:
    watch_paths:
      - ~/Documents
      - ~/Downloads

mcp:
  health_check_interval: 300  # seconds
  default_timeout: 5

approvals:
  default_expiry: 3600  # seconds (1 hour)
  require_reason_on_reject: true

briefings:
  default_days: 7
  auto_generate: false
```

### Environment Variables

```bash
# Override default vault path
export FTE_VAULT_PATH=~/my_custom_vault

# Set default log level
export FTE_LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR

# Disable colors
export NO_COLOR=1
```

### Shell Completion

Enable command completion for faster typing:

**Bash:**
```bash
# Add to ~/.bashrc
eval "$(_FTE_COMPLETE=bash_source fte)"
```

**Zsh:**
```bash
# Add to ~/.zshrc
eval "$(_FTE_COMPLETE=zsh_source fte)"
```

---

## Support

- **Documentation:** [docs/cli/](.)
- **Issues:** Report bugs and feature requests on GitHub
- **Developer Guide:** See [developer-guide.md](developer-guide.md)

---

## Changelog

### Version 1.0.0 (2026-01-29)

**New Features:**
- ✨ Initial CLI release
- ✨ Vault management commands
- ✨ Watcher lifecycle management (Gmail, WhatsApp, Filesystem)
- ✨ MCP server integration
- ✨ Approval workflow system
- ✨ CEO briefing generation

**Commands Added:**
- `fte init` - Initialize vault
- `fte status` - System status
- `fte vault` - Vault operations
- `fte watcher` - Watcher management
- `fte mcp` - MCP server management
- `fte approval` - Approval workflows
- `fte briefing` - CEO briefings

---

**Last Updated:** 2026-01-29
**Version:** 1.0.0

# Feature Specification: CLI Integration Roadmap (P2)

**Feature ID**: 003-cli-integration-roadmap
**Priority**: P2 (Post-MVP, Additive)
**Status**: Draft
**Created**: 2026-01-28
**Last Updated**: 2026-01-28

---

## Executive Summary

This specification defines a comprehensive CLI (Command Line Interface) integration roadmap for the Digital FTE (Full-Time Equivalent) AI Employee system. The CLI will provide a unified command-line interface for managing all aspects of the AI Employee system **without modifying the frozen P1 control plane code**.

**Key Constraint**: ADDITIVE ONLY. No modifications to existing control plane (`src/control_plane/`).

### Success Criteria

- ✅ Unified `fte` CLI command for all AI Employee operations
- ✅ Zero modifications to frozen control plane code
- ✅ Complete Obsidian vault management via CLI
- ✅ Watcher lifecycle management (start, stop, status)
- ✅ MCP server configuration and testing
- ✅ Human-in-the-loop approval workflows
- ✅ Comprehensive help and documentation
- ✅ All AI functionality implemented as Agent Skills

---

## Problem Statement

### Current State (Pain Points)

1. **Fragmented Interface**: Users must interact with multiple systems separately:
   - Claude Code for reasoning
   - Python scripts for Watchers
   - Manual folder navigation for approvals
   - Separate MCP server management
   - No unified monitoring dashboard

2. **Manual Operations**: Common tasks require manual intervention:
   - Starting/stopping Watchers requires terminal commands
   - Approving actions requires manual file moves
   - No centralized status checking
   - Difficult to debug issues

3. **Steep Learning Curve**: New users face barriers:
   - Need to understand Obsidian vault structure
   - Must learn multiple Python scripts
   - No guided workflows
   - Lack of discoverability

4. **Error-Prone**: Manual operations lead to mistakes:
   - Forgetting to start Watchers
   - Moving approval files to wrong folders
   - Misconfiguring MCP servers
   - No validation or guardrails

### Desired State (Solution)

A **unified, user-friendly CLI** that:

- Provides single entry point (`fte`) for all operations
- Guides users through common workflows
- Automates routine tasks
- Validates operations before execution
- Integrates seamlessly with existing components
- **Never modifies frozen control plane code**

---

## User Stories

### US1: Basic CLI Infrastructure (P1 - Must Have)

**As a** Digital FTE user
**I want** a unified `fte` CLI command
**So that** I can manage my AI Employee from a single interface

**Acceptance Criteria:**
- [ ] `fte --version` displays current version
- [ ] `fte --help` shows all available commands
- [ ] `fte init` initializes new AI Employee workspace
- [ ] `fte status` shows system health overview
- [ ] All commands follow consistent UX patterns
- [ ] Error messages are clear and actionable
- [ ] CLI is installed as Agent Skill

**Technical Notes:**
- Use Click framework for Python CLI
- Follow 12-factor CLI app principles
- Support both long and short flags
- Colorized output with rich/click

---

### US2: Vault Management Commands (P1 - Must Have)

**As a** Digital FTE user
**I want** CLI commands to manage my Obsidian vault
**So that** I don't need to manually navigate folders

**Acceptance Criteria:**
- [ ] `fte vault init` creates standard vault structure
- [ ] `fte vault status` shows pending tasks, approvals
- [ ] `fte vault dashboard` displays Dashboard.md
- [ ] `fte vault goals` manages Business_Goals.md
- [ ] `fte vault approve <task-id>` approves pending actions
- [ ] `fte vault reject <task-id>` rejects pending actions
- [ ] `fte vault archive` moves old tasks to archive
- [ ] All commands work with existing vault structure

**Technical Notes:**
- Read/write Obsidian markdown files
- Parse frontmatter (YAML)
- Respect vault folder conventions
- No database required (file-based)

**Example Usage:**
```bash
# Initialize new vault
fte vault init --path ./AI_Employee_Vault

# Check pending items
fte vault status
# Output:
# 📬 Needs Action: 3 items
# ⏳ Pending Approval: 2 items
# ✅ Done Today: 5 items

# Approve a payment
fte vault approve PAYMENT_Client_A_2026-01-28
# Output:
# ✅ Moved to /Approved
# ⚡ MCP will execute: Send payment $500 to Client A
```

---

### US3: Watcher Lifecycle Management (P1 - Must Have)

**As a** Digital FTE user
**I want** CLI commands to manage Watcher scripts
**So that** I can easily start, stop, and monitor sensors

**Acceptance Criteria:**
- [ ] `fte watcher list` shows all available Watchers
- [ ] `fte watcher start <name>` starts a Watcher
- [ ] `fte watcher stop <name>` stops a Watcher
- [ ] `fte watcher restart <name>` restarts a Watcher
- [ ] `fte watcher status` shows running Watchers
- [ ] `fte watcher logs <name>` displays Watcher logs
- [ ] `fte watcher enable <name>` enables auto-start on boot
- [ ] `fte watcher disable <name>` disables auto-start

**Technical Notes:**
- Integrate with PM2 or supervisord
- Support custom Watchers via config
- Health check endpoints
- Log rotation and management

**Example Usage:**
```bash
# Start Gmail watcher
fte watcher start gmail
# Output:
# 🚀 Starting gmail_watcher...
# ✅ Process started (PID: 12345)
# 📊 Status: Running
# 📁 Logs: /var/log/fte/gmail_watcher.log

# Check all Watchers
fte watcher status
# Output:
# Watcher          Status    PID     Uptime   Last Check
# gmail            running   12345   2h 34m   30s ago
# whatsapp         running   12346   2h 34m   15s ago
# filesystem       stopped   -       -        -
```

---

### US4: MCP Server Management (P1 - Must Have)

**As a** Digital FTE user
**I want** CLI commands to configure and test MCP servers
**So that** I can ensure external actions work correctly

**Acceptance Criteria:**
- [ ] `fte mcp list` shows configured MCP servers
- [ ] `fte mcp add <name> <config>` adds new MCP server
- [ ] `fte mcp test <name>` tests MCP server connectivity
- [ ] `fte mcp remove <name>` removes MCP server
- [ ] `fte mcp logs <name>` shows MCP server logs
- [ ] `fte mcp tools <name>` lists available tools from server
- [ ] Configuration stored in `.fte/mcp.json`

**Technical Notes:**
- Integrate with Claude Code MCP configuration
- Validate MCP server connections
- Test tool invocations
- Secure credential management

**Example Usage:**
```bash
# List configured MCP servers
fte mcp list
# Output:
# Name         Type      Status      Tools
# email        gmail     connected   3
# browser      playwright connected   5
# calendar     google    error       -

# Test email MCP
fte mcp test email
# Output:
# 🔌 Testing MCP: email
# ✅ Connection: OK
# ✅ Authentication: OK
# 📋 Available tools:
#    - send_email
#    - search_email
#    - draft_email
# ✅ All tests passed

# Add new MCP server
fte mcp add slack ./mcp-servers/slack-mcp/index.js
# Output:
# ✅ Added MCP server: slack
# 📝 Updated: ~/.config/claude-code/mcp.json
```

---

### US5: Approval Workflow Commands (P2 - Should Have)

**As a** Digital FTE user
**I want** interactive approval workflows via CLI
**So that** I can quickly review and approve/reject AI actions

**Acceptance Criteria:**
- [ ] `fte approve` shows interactive approval menu
- [ ] Displays pending approval details
- [ ] Allows approve/reject/skip for each item
- [ ] Supports batch approvals with filters
- [ ] Shows approval history
- [ ] Notifications for new approvals

**Example Usage:**
```bash
# Interactive approval mode
fte approve
# Output:
# 📬 2 items pending approval:
#
# [1/2] Payment: $500 to Client A
#      Reason: Invoice #1234
#      Requested: 2026-01-28 10:30
#      Action: [a]pprove / [r]eject / [s]kip / [q]uit?
# > a
# ✅ Approved: Payment to Client A
#
# [2/2] Email: Invoice to client@example.com
#      Subject: January Invoice
#      Action: [a]pprove / [r]eject / [s]kip / [q]uit?
# > a
# ✅ Approved: Email to client@example.com
#
# ✅ 2 items approved, 0 rejected, 0 skipped
```

---

### US6: Monday Briefing Command (P2 - Should Have)

**As a** Digital FTE CEO/business owner
**I want** a command to generate Monday Morning CEO Briefing
**So that** I can get weekly business overview on demand

**Acceptance Criteria:**
- [ ] `fte briefing` generates CEO briefing for current week
- [ ] `fte briefing --week last` generates previous week
- [ ] `fte briefing --format pdf` exports to PDF
- [ ] Includes revenue, bottlenecks, proactive suggestions
- [ ] Stored in `/Briefings/` folder

**Example Usage:**
```bash
# Generate weekly briefing
fte briefing
# Output:
# 📊 Generating Monday Morning CEO Briefing...
# 📅 Period: 2026-01-22 to 2026-01-28
# ✅ Briefing created: /Vault/Briefings/2026-01-28_Monday_Briefing.md
#
# === EXECUTIVE SUMMARY ===
# Revenue this week: $2,450
# MTD: $4,500 (45% of $10,000 target)
# Bottlenecks: 1 identified
# Suggestions: 2 cost optimizations
#
# 📄 Open briefing: fte vault open /Briefings/2026-01-28_Monday_Briefing.md
```

---

### US7: Claude Reasoning Integration (P2 - Should Have)

**As a** Digital FTE user
**I want** CLI commands to trigger Claude reasoning loops
**So that** I can manually invoke AI processing

**Acceptance Criteria:**
- [ ] `fte process` triggers Claude to process /Needs_Action
- [ ] `fte plan <task>` creates Plan.md for task
- [ ] `fte reason --prompt "..."` runs custom reasoning
- [ ] Shows reasoning progress in real-time
- [ ] Supports Ralph Wiggum persistence loop

**Example Usage:**
```bash
# Process pending items
fte process
# Output:
# 🤖 Starting Claude reasoning loop...
# 📂 Found 3 items in /Needs_Action
# 🔄 Processing: EMAIL_client_a_invoice.md
# ✅ Created plan: PLAN_invoice_client_a.md
# ⏳ Waiting for approval: APPROVAL_PAYMENT_Client_A.md
# ✅ Processing complete: 3/3 items
```

---

### US8: Configuration Management (P3 - Could Have)

**As a** Digital FTE user
**I want** CLI commands to manage configuration
**So that** I can easily update settings

**Acceptance Criteria:**
- [ ] `fte config get <key>` displays config value
- [ ] `fte config set <key> <value>` updates config
- [ ] `fte config list` shows all settings
- [ ] `fte config reset` restores defaults
- [ ] Configuration stored in `.fte/config.yaml`

---

### US9: Diagnostics and Debugging (P3 - Could Have)

**As a** Digital FTE developer
**I want** diagnostic commands for troubleshooting
**So that** I can quickly identify and fix issues

**Acceptance Criteria:**
- [ ] `fte doctor` runs comprehensive health checks
- [ ] `fte debug` enables debug mode
- [ ] `fte trace <command>` shows detailed execution trace
- [ ] `fte export-logs` packages logs for support

**Example Usage:**
```bash
# Health check
fte doctor
# Output:
# 🏥 Running system diagnostics...
# ✅ Claude Code: Installed (v2.1.0)
# ✅ Obsidian vault: Found at ./AI_Employee_Vault
# ❌ Gmail Watcher: Not running
# ✅ MCP servers: 2/3 connected
# ⚠️  Disk space: 15% remaining
#
# === ISSUES FOUND ===
# 1. Gmail Watcher stopped unexpectedly
#    Fix: Run `fte watcher start gmail`
# 2. Low disk space
#    Fix: Archive old logs with `fte vault archive`
```

---

## Non-Functional Requirements

### NFR1: Performance
- **Requirement**: CLI commands respond within 2 seconds
- **Measurement**: 95th percentile response time < 2s
- **Acceptance**: Benchmark tests pass

### NFR2: Usability
- **Requirement**: New users can complete basic tasks without documentation
- **Measurement**: User testing with 5 participants
- **Acceptance**: 4/5 complete tasks without help

### NFR3: Reliability
- **Requirement**: CLI handles errors gracefully
- **Measurement**: No unhandled exceptions in error scenarios
- **Acceptance**: Error test suite passes 100%

### NFR4: Security
- **Requirement**: No credentials displayed in plain text
- **Measurement**: Code review + security scan
- **Acceptance**: Zero credential exposures detected

### NFR5: Compatibility
- **Requirement**: Works on Linux, macOS, Windows (WSL2)
- **Measurement**: CI/CD tests on all platforms
- **Acceptance**: All platform tests pass

---

## Technical Architecture

### CLI Framework: Click

```python
# src/cli/fte.py - Main CLI entry point

import click
from .vault import vault_cli
from .watcher import watcher_cli
from .mcp import mcp_cli
from .approval import approval_cli

@click.group()
@click.version_option()
@click.pass_context
def fte(ctx):
    """
    FTE (Full-Time Equivalent) - Digital AI Employee CLI

    Manage your autonomous AI employee from the command line.
    """
    ctx.ensure_object(dict)
    # Load config
    ctx.obj['config'] = load_config()

# Register subcommands
fte.add_command(vault_cli)
fte.add_command(watcher_cli)
fte.add_command(mcp_cli)
fte.add_command(approval_cli)

if __name__ == '__main__':
    fte()
```

### Installation

```bash
# Add to pyproject.toml
[project.scripts]
fte = "src.cli.fte:fte"

# Install
pip install -e .

# Now available globally
fte --help
```

### Project Structure

```
src/
├── cli/                     # ✅ NEW - CLI commands (additive)
│   ├── __init__.py
│   ├── fte.py              # Main CLI entry point
│   ├── vault.py            # Vault management commands
│   ├── watcher.py          # Watcher lifecycle commands
│   ├── mcp.py              # MCP server management
│   ├── approval.py         # Approval workflow commands
│   ├── briefing.py         # CEO briefing generation
│   ├── config.py           # Configuration management
│   └── utils.py            # Shared utilities
│
├── control_plane/          # ❌ FROZEN - Do not modify
│   └── ...
│
├── logging/                # ✅ Existing P2 feature
│   └── ...
```

---

## Dependencies

### Required

- `click>=8.1.0` - CLI framework
- `rich>=13.0.0` - Terminal UI and formatting
- `pyyaml>=6.0` - Configuration files
- `watchdog>=3.0.0` - File system monitoring

### Optional

- `pm2` - Process management (via npm)
- `questionary` - Interactive prompts
- `tabulate` - Table formatting

---

## Constitutional Compliance

### Section 2 (Source of Truth) ✅
- **Requirement**: File system is single source of truth
- **Compliance**: All CLI commands read/write to vault files
- **Evidence**: No in-memory state; all operations are file-based

### Section 3 (Local-First & Privacy) ✅
- **Requirement**: Sensitive data remains local, secrets protected
- **Compliance**: CLI operates on local vault, credentials never logged
- **Evidence**: Configuration in `.fte/`, credentials use environment variables

### Section 4 (File-Driven Control Plane) ✅
- **Requirement**: DO NOT MODIFY frozen code
- **Compliance**: CLI is 100% additive in `src/cli/`
- **Evidence**: Zero modifications to `src/control_plane/`

### Section 8 (Auditability & Logging) ✅
- **Requirement**: Append-only logs with timestamp, action, result
- **Compliance**: All CLI actions logged to `/Vault/Logs/`
- **Evidence**: Audit log format matches logging infrastructure

### Section 9 (Error Handling & Safety) ✅
- **Requirement**: Errors never hidden, bounded retries
- **Compliance**: Clear error messages, no silent failures
- **Evidence**: Error handling tests + user feedback

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Set up Click CLI framework
- [ ] Implement `fte` main command
- [ ] Add `fte vault init` and `fte vault status`
- [ ] Basic error handling and logging

### Phase 2: Vault Management (Week 2)
- [ ] Complete vault subcommands
- [ ] Approval workflow commands
- [ ] Dashboard display command
- [ ] Integration with Obsidian vault

### Phase 3: Watcher Integration (Week 3)
- [ ] Watcher lifecycle management
- [ ] PM2 integration
- [ ] Health monitoring
- [ ] Log viewing commands

### Phase 4: MCP Integration (Week 4)
- [ ] MCP server configuration
- [ ] Connection testing
- [ ] Tool discovery
- [ ] Secure credential handling

### Phase 5: Advanced Features (Week 5)
- [ ] CEO briefing generation
- [ ] Claude reasoning integration
- [ ] Configuration management
- [ ] Diagnostics and debugging

### Phase 6: Polish & Documentation (Week 6)
- [ ] Comprehensive help text
- [ ] Error message improvements
- [ ] User guide and examples
- [ ] Agent Skill conversion

---

## Success Metrics

1. **Adoption Rate**: 80% of users prefer CLI over manual operations
2. **Task Completion Time**: 50% reduction in common task time
3. **Error Rate**: <5% of CLI commands result in errors
4. **User Satisfaction**: NPS score > 8/10
5. **Documentation Coverage**: 100% of commands documented

---

## Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| User learning curve | Medium | High | Comprehensive help, interactive tutorials |
| Breaking changes to vault structure | High | Low | Version vault structure, migration tools |
| Platform compatibility issues | Medium | Medium | CI/CD tests on all platforms |
| Security: credentials exposure | High | Low | Code review, secret scanning, audit |

---

## Open Questions

1. **Q**: Should CLI support plugins/extensions?
   - **Status**: To be decided
   - **Impact**: Architecture design

2. **Q**: CLI-only mode vs GUI integration?
   - **Status**: CLI-first, GUI later
   - **Impact**: UX design

3. **Q**: Multi-user support (team vaults)?
   - **Status**: Out of scope for P2
   - **Impact**: Future enhancement

---

## Appendix: Command Reference

### Full Command Tree

```
fte
├── --version
├── --help
├── init                    # Initialize new workspace
├── status                  # System health overview
├── vault
│   ├── init               # Create vault structure
│   ├── status             # Show pending tasks
│   ├── dashboard          # Display dashboard
│   ├── goals              # Manage business goals
│   ├── approve <id>       # Approve action
│   ├── reject <id>        # Reject action
│   └── archive            # Archive old tasks
├── watcher
│   ├── list               # List all Watchers
│   ├── start <name>       # Start Watcher
│   ├── stop <name>        # Stop Watcher
│   ├── restart <name>     # Restart Watcher
│   ├── status             # Show running Watchers
│   ├── logs <name>        # View Watcher logs
│   ├── enable <name>      # Enable auto-start
│   └── disable <name>     # Disable auto-start
├── mcp
│   ├── list               # List MCP servers
│   ├── add <name> <cfg>   # Add MCP server
│   ├── test <name>        # Test MCP connection
│   ├── remove <name>      # Remove MCP server
│   ├── logs <name>        # View MCP logs
│   └── tools <name>       # List available tools
├── approve                 # Interactive approval
├── briefing                # Generate CEO briefing
│   ├── --week <last|this>
│   └── --format <md|pdf>
├── process                 # Trigger Claude reasoning
├── plan <task>            # Create task plan
├── config
│   ├── get <key>          # Get config value
│   ├── set <key> <val>    # Set config value
│   ├── list               # List all settings
│   └── reset              # Reset to defaults
└── doctor                  # Run diagnostics
```

---

**Next Steps:**
1. Run `/sp.plan` to generate implementation plan
2. Run `/sp.tasks` to generate task breakdown
3. Begin implementation with Phase 1 (Foundation)
4. Convert all AI functionality to Agent Skills

**Constitutional Gate**: ✅ All sections compliant - Proceed with implementation

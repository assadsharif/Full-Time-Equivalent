# Implementation Plan: CLI Integration Roadmap

**Branch**: `003-cli-integration-roadmap` | **Date**: 2026-01-28 | **Spec**: [specs/003-cli-integration-roadmap/spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-cli-integration-roadmap/spec.md`

## Summary

Build a unified `fte` CLI tool that provides command-line access to all Digital FTE operations including vault management, watcher lifecycle control, MCP server configuration, and approval workflows. This CLI will be implemented as an **additive layer** on top of the frozen P1 control plane without modifying existing code.

**Key Approach**: Create new CLI module (`src/cli/`) using Click framework with commands organized into subgroups (vault, watcher, mcp, logs). All functionality will be implemented as Agent Skills that wrap CLI operations.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Click>=8.1.0, Rich>=13.0.0, PyYAML>=6.0, python-ulid>=2.0.0, watchdog>=3.0.0
**Storage**: File-based (Obsidian vault, JSON config files)
**Testing**: pytest>=7.4.0, pytest-click for CLI testing
**Target Platform**: Linux/macOS/Windows (cross-platform)
**Project Type**: Single project (CLI extension)
**Performance Goals**: <100ms for status commands, <1s for operations
**Constraints**: ADDITIVE ONLY - zero modifications to `src/control_plane/`, file-based operations only
**Scale/Scope**: 20+ CLI commands across 5 command groups

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **Section 2 (Source of Truth)**: CLI reads/writes Obsidian vault files directly
✅ **Section 3 (Local-First)**: All operations are local, no cloud dependencies
✅ **Section 4 (File-Driven Control Plane)**: CLI respects workflow folders
✅ **Section 6-7 (Autonomy & HITL)**: Approval commands enforce approval workflows
✅ **Section 8 (Auditability)**: All commands log to P2 logging infrastructure
✅ **Section 11 (No Spec Drift)**: Implementation strictly follows spec, no modifications to control plane

## Project Structure

### Documentation (this feature)

```text
specs/003-cli-integration-roadmap/
├── plan.md              # This file
├── research.md          # CLI framework evaluation, process management options
├── data-model.md        # CLI config schema, command structure
├── quickstart.md        # Getting started guide
└── contracts/           # CLI command specifications
    ├── vault-commands.md
    ├── watcher-commands.md
    ├── mcp-commands.md
    └── logs-commands.md
```

### Source Code (repository root)

```text
src/cli/
├── __init__.py          # CLI version, package info
├── main.py              # Main entry point, `fte` command
├── vault.py             # Vault management commands
├── watcher.py           # Watcher lifecycle commands
├── mcp.py               # MCP server management
├── approval.py          # Approval workflow commands
├── logs.py              # Log query commands (P2 integration)
└── utils/
    ├── config.py        # Config file management
    ├── formatters.py    # Output formatting (tables, JSON)
    ├── validators.py    # Input validation
    └── process_mgr.py   # Process management (PM2/supervisord wrapper)

config/
└── cli.yaml             # Default CLI configuration

tests/cli/
├── test_vault_commands.py
├── test_watcher_commands.py
├── test_mcp_commands.py
└── test_cli_integration.py

.claude/skills/fte-cli/
└── SKILL.md             # Agent skill for CLI operations
```

**Structure Decision**: Single project structure with new `src/cli/` module. All CLI code is additive - no modifications to existing `src/control_plane/` or `src/logging/` modules.

## Complexity Tracking

> No constitutional violations - all gates passing.

## Phase 0: Research & Technology Selection

### Research Areas

1. **CLI Framework Selection**
   - **Question**: Which Python CLI framework best suits our needs?
   - **Options**: Click, Typer, argparse, Fire
   - **Decision Criteria**: Ease of use, subcommand support, testing support, rich output
   - **Recommendation**: Click (widely adopted, excellent docs, pytest-click for testing)

2. **Process Management**
   - **Question**: How to manage watcher processes (start/stop/status)?
   - **Options**: PM2 (Node.js), supervisord (Python), systemd, custom solution
   - **Decision Criteria**: Cross-platform support, ease of installation, feature set
   - **Recommendation**: PM2 for development, systemd for production deployment

3. **Output Formatting**
   - **Question**: How to display command output (tables, JSON, colored text)?
   - **Options**: Rich, Colorama, Tabulate, plain text
   - **Recommendation**: Rich for tables and progress bars, JSON mode for scripting

4. **Configuration Management**
   - **Question**: Where to store CLI configuration?
   - **Options**: YAML files, TOML, JSON, environment variables
   - **Recommendation**: YAML files in `~/.fte/config.yaml` with environment variable overrides

### Research Deliverable: `research.md`

Document containing:
- CLI framework comparison table
- Process management options analysis
- Output formatting patterns
- Configuration file schema design
- Cross-platform compatibility notes

## Phase 1: Design & Contracts

### Data Model (`data-model.md`)

**CLI Configuration Schema**:
```yaml
# ~/.fte/config.yaml
vault:
  path: ~/AI_Employee_Vault
  auto_init: true

watchers:
  auto_start: [gmail, whatsapp]
  poll_interval: 60

mcp:
  servers_dir: ~/.fte/mcp
  timeout: 30

logging:
  level: INFO
  file: ~/.fte/cli.log
```

**Command Structure**:
```text
fte
├── init                 # Initialize workspace
├── status               # System status overview
├── vault               # Vault management
│   ├── init
│   ├── status
│   ├── dashboard
│   ├── approve <id>
│   └── reject <id>
├── watcher             # Watcher management
│   ├── list
│   ├── start <name>
│   ├── stop <name>
│   ├── status
│   └── logs <name>
├── mcp                 # MCP management
│   ├── list
│   ├── add <name>
│   ├── test <name>
│   └── tools <name>
└── logs                # Log queries (P2)
    ├── tail
    ├── query
    └── search <term>
```

### API Contracts (`contracts/`)

**vault-commands.md**:
```bash
# Vault Status Command
fte vault status [--format json|table]

Output:
- Pending tasks count by folder
- Approval requests count
- Recent activity summary
- Watcher status summary

Exit Codes:
- 0: Success
- 1: Vault not initialized
- 2: Invalid vault structure
```

**watcher-commands.md**:
```bash
# Watcher Start Command
fte watcher start <name> [--daemon]

Behavior:
- Validates watcher exists
- Checks if already running
- Starts process with PM2
- Logs startup to audit trail
- Returns PID and status

Exit Codes:
- 0: Started successfully
- 1: Watcher not found
- 2: Already running
- 3: Start failed
```

**mcp-commands.md**:
```bash
# MCP Test Command
fte mcp test <name> [--verbose]

Behavior:
- Loads MCP server config
- Attempts connection
- Lists available tools
- Validates tool schemas
- Reports connection health

Exit Codes:
- 0: Connection successful
- 1: Server not configured
- 2: Connection failed
- 3: Invalid configuration
```

**logs-commands.md**:
```bash
# Log Query Command (P2 integration)
fte logs query --level ERROR --since 1h [--format json]

Behavior:
- Integrates with P2 DuckDB logging
- Filters by level, time, module
- Supports full-text search
- Outputs in requested format

Exit Codes:
- 0: Query successful
- 1: Invalid query parameters
- 2: Log database unavailable
```

### Quickstart Guide (`quickstart.md`)

```markdown
# CLI Integration Quickstart

## Installation

```bash
pip install -e .
fte --version
```

## First-Time Setup

```bash
# Initialize workspace
fte init

# Verify setup
fte status

# Start watchers
fte watcher start gmail
fte watcher start whatsapp
```

## Common Workflows

**Approve a pending task:**
```bash
fte vault status
fte vault approve PAYMENT_Client_A_2026-01-28
```

**Check watcher health:**
```bash
fte watcher status
fte watcher logs gmail --tail 50
```

**Test MCP server:**
```bash
fte mcp test gmail-mcp
fte mcp tools gmail-mcp
```
```

## Phase 2: Implementation Roadmap

### Bronze Tier (Week 1-2): Core CLI Infrastructure

**Milestone**: Basic CLI with vault and watcher commands

**Tasks**:
1. Set up Click framework structure
2. Implement `fte init` and `fte status`
3. Create vault management commands (status, approve, reject)
4. Implement watcher commands (list, start, stop, status)
5. Add rich output formatting
6. Write unit tests for all commands
7. Create CLI agent skill

**Deliverables**:
- Working `fte` command with 15+ subcommands
- Test coverage >80%
- Basic documentation
- Agent skill for CLI operations

### Silver Tier (Week 3-4): MCP Integration & Advanced Features

**Milestone**: MCP management, logging integration

**Tasks**:
1. Implement MCP server management commands
2. Integrate with P2 logging infrastructure for `fte logs`
3. Add config file management
4. Implement daemon mode for watchers
5. Add auto-completion support (bash/zsh)
6. Comprehensive error handling
7. Integration tests with real vault

**Deliverables**:
- Complete MCP command set
- Log query CLI (P2 integration)
- Shell auto-completion scripts
- End-to-end integration tests

### Gold Tier (Week 5-6): Polish & Advanced Workflows

**Milestone**: Production-ready CLI with automation

**Tasks**:
1. Add `fte doctor` health check command
2. Implement `fte backup` and `fte restore`
3. Create interactive setup wizard
4. Add watch mode for status commands
5. Implement plugin system for custom commands
6. Performance optimization
7. Comprehensive documentation

**Deliverables**:
- Health check and diagnostics
- Backup/restore functionality
- Interactive wizards
- Plugin architecture
- Production deployment guide

## Testing Strategy

### Unit Tests
- Test each command in isolation
- Mock file system operations
- Validate output formatting
- Test error handling paths

### Integration Tests
- Test with real vault structure
- Test watcher lifecycle (start/stop/status)
- Test MCP server interactions
- Test approval workflows end-to-end

### CLI Testing with pytest-click
```python
from click.testing import CliRunner
from src.cli.main import cli

def test_fte_status():
    runner = CliRunner()
    result = runner.invoke(cli, ['status'])
    assert result.exit_code == 0
    assert 'System Status' in result.output
```

## Risk Analysis

### Risk 1: Process Management Complexity
**Impact**: Medium
**Mitigation**: Use battle-tested PM2, provide fallback to manual process management

### Risk 2: Cross-Platform Compatibility
**Impact**: Medium
**Mitigation**: Test on Windows/macOS/Linux, use pathlib for paths, document platform-specific notes

### Risk 3: Configuration Management
**Impact**: Low
**Mitigation**: Provide sensible defaults, validate config on load, clear error messages

## Architectural Decision Records

### ADR-001: Click Framework for CLI

**Decision**: Use Click framework for building the CLI

**Rationale**:
- Industry standard for Python CLIs
- Excellent subcommand support
- Rich integration available
- pytest-click for testing
- Extensive documentation

**Alternatives Considered**:
- Typer: Too opinionated, newer/less mature
- argparse: Too low-level, poor subcommand support
- Fire: Magic, poor discoverability

### ADR-002: PM2 for Process Management

**Decision**: Use PM2 for managing watcher processes in development

**Rationale**:
- Cross-platform support
- Built-in log management
- Process monitoring and auto-restart
- Simple CLI interface
- Well-documented

**Alternatives Considered**:
- supervisord: Python-only, less active development
- systemd: Linux-only, requires root access
- Custom solution: High maintenance burden

### ADR-003: YAML for Configuration

**Decision**: Use YAML format for CLI configuration files

**Rationale**:
- Human-readable and editable
- Supports comments
- Consistent with vault frontmatter
- Good Python support (PyYAML)

**Alternatives Considered**:
- JSON: No comments, less human-friendly
- TOML: Less familiar to users
- INI: Limited structure support

## Integration Points

### P1 Control Plane
- **Read-only access** to `src/control_plane/models.py` for WorkflowState enum
- **No modifications** to control plane code
- CLI wraps control plane operations through file system

### P2 Logging Infrastructure
- `fte logs` commands integrate with DuckDB logging
- Query service from `src/logging/query_service.py`
- Log parsing and formatting

### Obsidian Vault
- Direct file system operations
- YAML frontmatter parsing
- Markdown file creation/editing
- Folder structure validation

### MCP Servers
- Configuration file management
- Server process lifecycle
- Tool discovery and validation
- Connection testing

## Agent Skill Design

The CLI will be packaged as an Agent Skill: `.claude/skills/fte-cli/SKILL.md`

**Skill Description**:
```markdown
# FTE CLI Skill

Comprehensive command-line interface for managing the Digital FTE AI Employee.

## When to Use

Use this skill when the user needs to:
- Manage the Obsidian vault (status, approvals)
- Control watcher processes (start, stop, logs)
- Configure MCP servers
- Query system logs
- Perform system health checks

## Available Commands

[Include command reference here]

## Examples

[Include usage examples here]
```

## Success Metrics

### Functionality
- [ ] All 20+ CLI commands implemented and tested
- [ ] Zero modifications to frozen control plane code
- [ ] Integration with P2 logging infrastructure
- [ ] Cross-platform compatibility verified

### Quality
- [ ] Test coverage >85%
- [ ] All commands complete in <1s
- [ ] Clear error messages for all failure cases
- [ ] Comprehensive documentation

### Usability
- [ ] Interactive setup wizard
- [ ] Auto-completion support
- [ ] Colorized output with Rich
- [ ] Help text for all commands

---

**Next Steps**: Run `/sp.tasks` to generate actionable task breakdown.

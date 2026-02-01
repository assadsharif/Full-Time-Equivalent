# Tasks: CLI Integration Roadmap

**Feature**: CLI Integration Roadmap | **Branch**: `003-cli-integration-roadmap` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Overview

This document breaks down the CLI Integration Roadmap implementation into actionable, testable tasks organized by user story. Each phase represents an independently deliverable increment.

**Task Format**: `- [ ] [TaskID] [P?] [Story?] Description with file path`
- **TaskID**: Sequential task number (T001, T002, ...)
- **[P]**: Parallelizable task (can be done concurrently with other [P] tasks)
- **[Story]**: User story label ([US1], [US2], etc.) for user story phases only

## Implementation Strategy

**MVP Scope**: User Story 1 (Basic CLI Infrastructure) provides immediate value - users can run `fte --version`, `fte --help`, `fte init`, and `fte status`.

**Incremental Delivery**: Each user story is independently testable and deliverable. Stories can be implemented in priority order (US1 → US2 → US3 → US4 → US5 → US6) with each story providing incremental value.

**Parallel Opportunities**: Tasks marked [P] can be executed in parallel within each phase. Setup and foundational tasks have maximum parallelism opportunities.

---

## Phase 1: Setup

**Goal**: Initialize project structure, install dependencies, configure development environment.

**Tasks**:

- [ ] T001 Create src/cli/ module directory structure per plan.md
- [ ] T002 [P] Install Click framework (click>=8.1.0) and add to pyproject.toml dependencies
- [ ] T003 [P] Install Rich library (rich>=13.0.0) for styled terminal output and add to pyproject.toml
- [ ] T004 [P] Install Typer library (typer>=0.9.0) for enhanced CLI features and add to pyproject.toml
- [ ] T005 [P] Install python-dotenv (python-dotenv>=1.0.0) for environment configuration and add to pyproject.toml
- [ ] T006 [P] Create tests/cli/ test directory structure
- [ ] T007 [P] Create config/cli.yaml configuration file template
- [ ] T008 [P] Create src/cli/__init__.py module exports file
- [ ] T009 Set up pytest-click (pytest-click>=1.1.0) for CLI testing and add to pyproject.toml dev dependencies
- [ ] T010 Create .fte/cli.checkpoint.json checkpoint file structure for state tracking

---

## Phase 2: Foundational Tasks

**Goal**: Build shared infrastructure required by all user stories. Must complete before implementing user story phases.

**Tasks**:

- [ ] T011 [P] Implement config loader in src/cli/config.py to read config/cli.yaml
- [ ] T012 [P] Implement logging setup in src/cli/logging_setup.py with Rich console integration
- [ ] T013 [P] Create CLI utilities in src/cli/utils.py (path resolution, vault detection, error formatting)
- [ ] T014 [P] Implement checkpoint manager in src/cli/checkpoint.py for state persistence
- [ ] T015 [P] Create error handlers in src/cli/errors.py (VaultNotFoundError, ConfigError, CLIError)
- [ ] T016 [P] Write unit tests for config loader in tests/cli/test_config.py
- [ ] T017 [P] Write unit tests for checkpoint manager in tests/cli/test_checkpoint.py
- [ ] T018 [P] Write unit tests for CLI utilities in tests/cli/test_utils.py
- [ ] T019 Create main CLI entry point skeleton in src/cli/main.py with Click group
- [ ] T020 Add pyproject.toml console_scripts entry point: fte = "src.cli.main:cli"

---

## Phase 3: US1 - Basic CLI Infrastructure

**Story Goal**: Users can verify installation, get help, initialize vault configuration, and check system status.

**User Story**: As a Digital FTE user, I want basic CLI commands (`fte --version`, `fte --help`, `fte init`, `fte status`) so I can verify installation and understand available commands.

**Independent Test Criteria**:
- ✅ `fte --version` displays correct version from pyproject.toml
- ✅ `fte --help` shows all command groups and global options
- ✅ `fte init` creates vault configuration and confirms path
- ✅ `fte status` displays vault status, watcher states, MCP server health
- ✅ All commands return proper exit codes (0 for success, 1 for errors)
- ✅ Error messages are styled with Rich for readability

**Tasks**:

- [ ] T021 [US1] Implement --version flag in src/cli/main.py reading from pyproject.toml
- [ ] T022 [US1] Implement --help flag with Click's auto-generated help in src/cli/main.py
- [ ] T023 [US1] Implement `fte init` command in src/cli/init.py to create .fte/config.yaml
- [ ] T024 [US1] Add vault path prompt to init command using Click.prompt()
- [ ] T025 [US1] Add vault path validation (check if directory exists) in init command
- [ ] T026 [US1] Implement `fte status` command in src/cli/status.py showing system health
- [ ] T027 [US1] Add vault status check (folder structure validation) to status command
- [ ] T028 [US1] Add watcher status aggregation (read checkpoint files) to status command
- [ ] T029 [US1] Add MCP server health checks (ping endpoints) to status command
- [ ] T030 [US1] Style status output with Rich tables and panels in src/cli/status.py
- [ ] T031 [US1] Write integration test for `fte --version` in tests/cli/test_main.py
- [ ] T032 [US1] Write integration test for `fte --help` in tests/cli/test_main.py
- [ ] T033 [US1] Write integration test for `fte init` workflow in tests/cli/test_init.py
- [ ] T034 [US1] Write integration test for `fte status` output in tests/cli/test_status.py
- [ ] T035 [US1] Add error handling for missing vault in status command (exit code 1)

---

## Phase 4: US2 - Vault Management Commands

**Story Goal**: Users can initialize vault structure, check vault health, and manage approvals through CLI.

**User Story**: As a Digital FTE user, I want vault management commands (`fte vault init`, `fte vault status`, `fte vault approve`, `fte vault reject`) so I can manage the Obsidian vault from the command line.

**Independent Test Criteria**:
- ✅ `fte vault init` creates all 7 core folders (Inbox, Needs_Action, In_Progress, Done, Approvals, Briefings, Attachments)
- ✅ `fte vault status` displays folder statistics (task counts per folder)
- ✅ `fte vault approve <approval_id>` updates approval file status to "approved"
- ✅ `fte vault reject <approval_id>` updates approval file status to "rejected"
- ✅ Approval commands validate nonce and check file integrity (SHA256 hash)
- ✅ All commands handle missing vault gracefully with clear error messages

**Tasks**:

- [ ] T036 [US2] Create src/cli/vault.py Click command group for vault commands
- [ ] T037 [US2] Implement `fte vault init` command to create folder structure in src/cli/vault.py
- [ ] T038 [US2] Add Dashboard.md template creation to vault init in src/cli/vault.py
- [ ] T039 [US2] Add Company_Handbook.md template creation to vault init in src/cli/vault.py
- [ ] T040 [US2] Implement `fte vault status` command in src/cli/vault.py showing folder stats
- [ ] T041 [US2] Add task counting logic (count .md files per folder) to vault status
- [ ] T042 [US2] Style vault status output with Rich tables in src/cli/vault.py
- [ ] T043 [US2] Implement `fte vault approve <approval_id>` command in src/cli/vault.py
- [ ] T044 [US2] Add approval file lookup in /Approvals folder for approve command
- [ ] T045 [US2] Add YAML frontmatter update (approval_status: approved) for approve command
- [ ] T046 [US2] Add nonce validation in approval commands using src/approval/nonce_generator.py
- [ ] T047 [US2] Add file integrity verification (SHA256 check) in approval commands
- [ ] T048 [US2] Implement `fte vault reject <approval_id>` command in src/cli/vault.py
- [ ] T049 [US2] Add rejection reason prompt using Click.prompt() in reject command
- [ ] T050 [US2] Add audit logging for approval/rejection actions in src/cli/vault.py
- [ ] T051 [US2] Write integration test for `fte vault init` in tests/cli/test_vault.py
- [ ] T052 [US2] Write integration test for `fte vault status` in tests/cli/test_vault.py
- [ ] T053 [US2] Write integration test for `fte vault approve` workflow in tests/cli/test_vault.py
- [ ] T054 [US2] Write integration test for `fte vault reject` workflow in tests/cli/test_vault.py
- [ ] T055 [US2] Add error handling for invalid approval IDs (exit code 1)

---

## Phase 5: US3 - Watcher Lifecycle Management

**Story Goal**: Users can start/stop watchers, check their status, and view logs through CLI.

**User Story**: As a Digital FTE user, I want watcher lifecycle commands (`fte watcher start`, `fte watcher stop`, `fte watcher status`, `fte watcher logs`) so I can control task detection services.

**Independent Test Criteria**:
- ✅ `fte watcher start <name>` launches watcher daemon via PM2/supervisord
- ✅ `fte watcher stop <name>` gracefully stops watcher daemon
- ✅ `fte watcher status` shows all watchers with state (running/stopped), PID, uptime
- ✅ `fte watcher logs <name> --tail 50` displays last 50 log lines
- ✅ Commands validate watcher name (gmail, whatsapp, filesystem)
- ✅ PM2 integration uses subprocess to invoke `pm2 start/stop/list`

**Tasks**:

- [ ] T056 [US3] Create src/cli/watcher.py Click command group for watcher commands
- [ ] T057 [US3] Implement `fte watcher start <name>` command in src/cli/watcher.py
- [ ] T058 [US3] Add PM2 subprocess wrapper in src/cli/watcher.py for `pm2 start scripts/run_<name>_watcher.py`
- [ ] T059 [US3] Add watcher name validation (gmail, whatsapp, filesystem) in start command
- [ ] T060 [US3] Add PM2 configuration validation before start in src/cli/watcher.py
- [ ] T061 [US3] Implement `fte watcher stop <name>` command in src/cli/watcher.py
- [ ] T062 [US3] Add PM2 subprocess wrapper for `pm2 stop <name>` in stop command
- [ ] T063 [US3] Add graceful shutdown confirmation (wait for PM2 stop) in stop command
- [ ] T064 [US3] Implement `fte watcher status` command in src/cli/watcher.py
- [ ] T065 [US3] Add PM2 status parsing (parse `pm2 jlist` JSON output) in status command
- [ ] T066 [US3] Style watcher status output with Rich table (name, status, PID, uptime, restarts)
- [ ] T067 [US3] Implement `fte watcher logs <name>` command in src/cli/watcher.py
- [ ] T068 [US3] Add --tail flag (default 50) to logs command using Click.option()
- [ ] T069 [US3] Add --follow flag for live log streaming in logs command
- [ ] T070 [US3] Add PM2 subprocess wrapper for `pm2 logs <name> --lines <tail>` in logs command
- [ ] T071 [US3] Write integration test for `fte watcher start` in tests/cli/test_watcher.py
- [ ] T072 [US3] Write integration test for `fte watcher stop` in tests/cli/test_watcher.py
- [ ] T073 [US3] Write integration test for `fte watcher status` in tests/cli/test_watcher.py
- [ ] T074 [US3] Write integration test for `fte watcher logs` in tests/cli/test_watcher.py
- [ ] T075 [US3] Add error handling for PM2 not installed (exit code 1 with helpful message)

---

## Phase 6: US4 - MCP Server Management

**Story Goal**: Users can list available MCP servers, add new servers, test connections, and discover tools.

**User Story**: As a Digital FTE user, I want MCP management commands (`fte mcp list`, `fte mcp add`, `fte mcp test`, `fte mcp tools`) so I can manage external integrations.

**Independent Test Criteria**:
- ✅ `fte mcp list` displays all configured MCP servers with status (active/inactive)
- ✅ `fte mcp add <name> <url> --auth-file <path>` registers new MCP server
- ✅ `fte mcp test <name>` pings server and validates response
- ✅ `fte mcp tools <name>` lists all available tools from server
- ✅ Commands validate MCP server configuration (URL format, auth file existence)
- ✅ Server credentials are stored securely using OS keyring

**Tasks**:

- [ ] T076 [US4] Create src/cli/mcp.py Click command group for MCP commands
- [ ] T077 [US4] Implement `fte mcp list` command in src/cli/mcp.py
- [ ] T078 [US4] Add MCP registry reading (parse config/mcp_servers.yaml) in list command
- [ ] T079 [US4] Add health check integration (ping each server) for list command
- [ ] T080 [US4] Style MCP list output with Rich table (name, URL, status, tools count)
- [ ] T081 [US4] Implement `fte mcp add <name> <url>` command in src/cli/mcp.py
- [ ] T082 [US4] Add --auth-file option to add command using Click.option()
- [ ] T083 [US4] Add URL validation (validate scheme, port) in add command
- [ ] T084 [US4] Add credential storage using src/security/credential_vault.py in add command
- [ ] T085 [US4] Add MCP registry update (append to config/mcp_servers.yaml) in add command
- [ ] T086 [US4] Implement `fte mcp test <name>` command in src/cli/mcp.py
- [ ] T087 [US4] Add MCP server lookup in registry for test command
- [ ] T088 [US4] Add health check ping (HTTP GET /health or MCP ping) in test command
- [ ] T089 [US4] Add connection timeout handling (5 second timeout) in test command
- [ ] T090 [US4] Style test output with Rich status indicators (✓ pass, ✗ fail) in src/cli/mcp.py
- [ ] T091 [US4] Implement `fte mcp tools <name>` command in src/cli/mcp.py
- [ ] T092 [US4] Add MCP tools discovery (GET /tools endpoint) in tools command
- [ ] T093 [US4] Add tool schema parsing and validation in tools command
- [ ] T094 [US4] Style tools output with Rich tree structure (tool name → parameters) in src/cli/mcp.py
- [ ] T095 [US4] Write integration test for `fte mcp list` in tests/cli/test_mcp.py
- [ ] T096 [US4] Write integration test for `fte mcp add` workflow in tests/cli/test_mcp.py
- [ ] T097 [US4] Write integration test for `fte mcp test` in tests/cli/test_mcp.py
- [ ] T098 [US4] Write integration test for `fte mcp tools` in tests/cli/test_mcp.py
- [ ] T099 [US4] Add error handling for invalid URLs (exit code 1)
- [ ] T100 [US4] Add error handling for failed health checks (exit code 1)

---

## Phase 7: US5 - Approval Workflow Commands

**Story Goal**: Users can interactively approve/reject pending approvals with rich context display.

**User Story**: As a Digital FTE user, I want interactive approval commands (`fte approval pending`, `fte approval review <id>`) so I can review and approve/reject dangerous actions with full context.

**Independent Test Criteria**:
- ✅ `fte approval pending` lists all approval files in /Approvals with status=pending
- ✅ `fte approval review <id>` displays approval details (action, risk, context) in Rich panel
- ✅ Review command prompts user for decision (approve/reject/skip) interactively
- ✅ Approval updates YAML frontmatter and logs audit trail
- ✅ Commands handle expired approvals (past expires_at timestamp)

**Tasks**:

- [ ] T101 [US5] Create src/cli/approval.py Click command group for approval commands
- [ ] T102 [US5] Implement `fte approval pending` command in src/cli/approval.py
- [ ] T103 [US5] Add approval file discovery (scan /Approvals for status=pending) in pending command
- [ ] T104 [US5] Add expiry checking (filter out past expires_at) in pending command
- [ ] T105 [US5] Style pending list with Rich table (ID, type, risk, created, expires) in src/cli/approval.py
- [ ] T106 [US5] Implement `fte approval review <id>` command in src/cli/approval.py
- [ ] T107 [US5] Add approval file loading and YAML parsing in review command
- [ ] T108 [US5] Add context display with Rich panel (action details, risk level, recipient) in review command
- [ ] T109 [US5] Add interactive decision prompt (approve/reject/skip) using Click.confirm() in review command
- [ ] T110 [US5] Add approval logic (update YAML, verify nonce) for approve choice in review command
- [ ] T111 [US5] Add rejection logic (update YAML, prompt reason) for reject choice in review command
- [ ] T112 [US5] Add skip logic (no changes) for skip choice in review command
- [ ] T113 [US5] Add audit logging for all approval decisions in src/cli/approval.py
- [ ] T114 [US5] Write integration test for `fte approval pending` in tests/cli/test_approval.py
- [ ] T115 [US5] Write integration test for `fte approval review` approve flow in tests/cli/test_approval.py
- [ ] T116 [US5] Write integration test for `fte approval review` reject flow in tests/cli/test_approval.py
- [ ] T117 [US5] Add error handling for expired approvals (display warning, skip)
- [ ] T118 [US5] Add error handling for missing approval files (exit code 1)

---

## Phase 8: US6 - Monday Briefing Command

**Story Goal**: Users can generate and view weekly CEO briefing reports from CLI.

**User Story**: As a Digital FTE user, I want a briefing command (`fte briefing generate`, `fte briefing view`) so I can create and view weekly CEO reports.

**Independent Test Criteria**:
- ✅ `fte briefing generate` aggregates tasks from /Done folder for past week
- ✅ Generate command creates Markdown report in /Briefings folder
- ✅ Generate command optionally creates PDF using wkhtmltopdf
- ✅ `fte briefing view` opens most recent briefing in default Markdown viewer
- ✅ Commands handle empty /Done folder gracefully (no tasks completed message)

**Tasks**:

- [ ] T119 [US6] Create src/cli/briefing.py Click command group for briefing commands
- [ ] T120 [US6] Implement `fte briefing generate` command in src/cli/briefing.py
- [ ] T121 [US6] Add date range calculation (last 7 days) in generate command
- [ ] T122 [US6] Add task aggregation from /Done folder (filter by completion date) in generate command
- [ ] T123 [US6] Add integration with src/briefing/aggregator.py for data processing in generate command
- [ ] T124 [US6] Add Jinja2 template rendering (templates/briefing/executive_summary.md.j2) in generate command
- [ ] T125 [US6] Add Markdown report creation in /Briefings/briefing_YYYY-MM-DD.md in generate command
- [ ] T126 [US6] Add --pdf flag to generate command using Click.option()
- [ ] T127 [US6] Add PDF generation using wkhtmltopdf subprocess for --pdf flag in generate command
- [ ] T128 [US6] Style generation progress with Rich progress bar in src/cli/briefing.py
- [ ] T129 [US6] Implement `fte briefing view` command in src/cli/briefing.py
- [ ] T130 [US6] Add most recent briefing lookup (sort /Briefings by date) in view command
- [ ] T131 [US6] Add default Markdown viewer detection (typora, obsidian, cat fallback) in view command
- [ ] T132 [US6] Add subprocess invocation to open briefing in viewer in view command
- [ ] T133 [US6] Write integration test for `fte briefing generate` in tests/cli/test_briefing.py
- [ ] T134 [US6] Write integration test for `fte briefing view` in tests/cli/test_briefing.py
- [ ] T135 [US6] Add error handling for empty /Done folder (display info message, exit 0)
- [ ] T136 [US6] Add error handling for missing wkhtmltopdf (skip PDF, warn user)

---

## Final Phase: Polish & Cross-Cutting Concerns

**Goal**: Add documentation, performance optimizations, and cross-cutting features.

**Tasks**:

- [ ] T137 [P] Create CLI user guide in docs/cli/user-guide.md with command examples
- [ ] T138 [P] Create CLI developer guide in docs/cli/developer-guide.md with architecture
- [ ] T139 [P] Add command completion scripts for Bash in scripts/completion/fte-completion.bash
- [ ] T140 [P] Add command completion scripts for Zsh in scripts/completion/fte-completion.zsh
- [ ] T141 [P] Add global --verbose flag to main CLI group in src/cli/main.py
- [ ] T142 [P] Add global --quiet flag to main CLI group in src/cli/main.py
- [ ] T143 [P] Implement verbose logging (DEBUG level) for --verbose flag in src/cli/main.py
- [ ] T144 [P] Implement quiet mode (ERROR level only) for --quiet flag in src/cli/main.py
- [ ] T145 Add performance optimization for status checks (parallel health checks) in src/cli/status.py
- [ ] T146 Add caching for MCP server tool discovery (cache for 5 minutes) in src/cli/mcp.py
- [ ] T147 Add unified error handling middleware in src/cli/errors.py for all commands
- [ ] T148 Add telemetry collection (command usage stats) with opt-out in src/cli/telemetry.py
- [ ] T149 Add --no-color flag for CI/CD environments in src/cli/main.py
- [ ] T150 Write end-to-end integration test suite in tests/cli/test_e2e.py covering all user stories
- [ ] T151 Run security audit on CLI dependencies using pip-audit
- [ ] T152 Add CLI performance benchmarks in tests/cli/test_performance.py (target <100ms startup)
- [ ] T153 Update main README.md with CLI installation and usage instructions
- [ ] T154 Create CHANGELOG.md entry for CLI integration feature

---

## Dependencies

**User Story Completion Order** (based on technical dependencies):

```
Setup (Phase 1)
   ↓
Foundational (Phase 2)
   ↓
US1 (Basic CLI Infrastructure) ← Must complete first
   ↓
┌──────────────┬─────────────┬──────────────┐
↓              ↓             ↓              ↓
US2 (Vault)   US3 (Watcher) US4 (MCP)     US6 (Briefing)
                                           ↓
                                        US5 (Approval) ← Depends on US2 (vault commands)
```

**Phase Dependencies**:
- Phase 2 (Foundational) BLOCKS all user story phases
- Phase 3 (US1) BLOCKS all other user story phases (provides CLI infrastructure)
- Phase 7 (US5) depends on Phase 4 (US2) for vault approval integration
- All other user story phases can proceed in parallel after Phase 3

**Task Dependencies Within Phases**:
- Setup: T001 blocks T008 (need directory before __init__.py)
- Foundational: T019 blocks T020 (need main.py before entry point)
- All user story phases: First task (create Click group) blocks subsequent tasks

---

## Parallel Execution Examples

**Phase 1 (Setup) - Maximum Parallelism**:
```
Batch 1: T001 (create directory)
Batch 2: T002, T003, T004, T005, T006, T007, T009, T010 (all [P] tasks run in parallel)
Batch 3: T008 (depends on T001)
```

**Phase 2 (Foundational) - High Parallelism**:
```
Batch 1: T011, T012, T013, T014, T015 (all [P] tasks run in parallel)
Batch 2: T016, T017, T018 (test tasks run in parallel)
Batch 3: T019 (create main.py)
Batch 4: T020 (depends on T019)
```

**Phase 3 (US1) - Moderate Parallelism**:
```
Batch 1: T021, T022 (version and help flags)
Batch 2: T023, T024, T025 (init command)
Batch 3: T026, T027, T028, T029, T030 (status command)
Batch 4: T031, T032, T033, T034, T035 (tests run in parallel)
```

**Phase 4-8 (User Stories) - Similar Pattern**:
- Create Click group (sequential)
- Implement command logic (some parallel within command)
- Write tests (all tests can run in parallel)

---

## Testing Strategy

**Unit Tests** (tests/cli/):
- test_config.py: Config loader validation
- test_checkpoint.py: State persistence
- test_utils.py: Utility functions

**Integration Tests** (tests/cli/):
- test_main.py: CLI entry point, version, help
- test_init.py: Vault initialization workflow
- test_status.py: System status display
- test_vault.py: Vault management commands
- test_watcher.py: Watcher lifecycle management
- test_mcp.py: MCP server management
- test_approval.py: Approval workflow
- test_briefing.py: Briefing generation

**End-to-End Tests** (tests/cli/test_e2e.py):
- Complete user workflows across multiple commands
- CLI behavior in CI/CD environments (--no-color flag)

**Performance Tests** (tests/cli/test_performance.py):
- CLI startup time (<100ms target)
- Status check latency
- MCP server discovery caching

---

## Success Metrics

**Functionality**:
- [ ] All 6 user stories implemented and tested
- [ ] CLI commands return proper exit codes (0 success, 1 error)
- [ ] Rich terminal output works across platforms (Linux, macOS, Windows)
- [ ] PM2 integration functional for watcher management

**Quality**:
- [ ] Test coverage >90% for src/cli/ module
- [ ] All integration tests passing
- [ ] Security audit passing (pip-audit)
- [ ] No hardcoded credentials or tokens

**Performance**:
- [ ] CLI startup time <100ms (T152)
- [ ] Status checks complete <2s with 5 MCP servers
- [ ] MCP tool discovery cached (5min TTL)

**Usability**:
- [ ] User guide documentation complete (T137)
- [ ] Command completion scripts available (T139, T140)
- [ ] Error messages clear and actionable
- [ ] Help text comprehensive for all commands

---

**Total Tasks**: 154
**Tasks per User Story**:
- Setup (Phase 1): 10 tasks
- Foundational (Phase 2): 10 tasks
- US1 (Basic CLI Infrastructure): 15 tasks
- US2 (Vault Management): 20 tasks
- US3 (Watcher Lifecycle): 20 tasks
- US4 (MCP Server Management): 25 tasks
- US5 (Approval Workflow): 18 tasks
- US6 (Monday Briefing): 18 tasks
- Polish: 18 tasks

**Parallel Opportunities**: 47 tasks marked [P] can run concurrently
**Suggested MVP Scope**: Phase 1 + Phase 2 + Phase 3 (US1) = 35 tasks
**Format Validation**: ✅ All tasks follow checklist format (checkbox, ID, labels, file paths)

---

**Next Steps**: Begin implementation with Phase 1 (Setup) tasks. Run `fte --version` after T020 to verify CLI entry point configuration.

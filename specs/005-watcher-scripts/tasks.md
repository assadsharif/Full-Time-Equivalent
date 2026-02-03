---
description: "Task breakdown for Watcher Scripts (Perception Layer)"
---

# Tasks: Watcher Scripts (005-watcher-scripts)

**Input**: Design documents from `/specs/005-watcher-scripts/`
**Prerequisites**: plan.md, spec.md, research.md
**Focus**: Bronze Tier - Gmail and FileSystem watchers (minimum viable implementation)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic watcher structure

- [ ] T001 Create watcher directory structure: src/watchers/, config/watchers/, tests/watchers/
- [ ] T002 [P] Install watcher dependencies: google-auth>=2.23.0, google-api-python-client>=2.100.0, watchdog>=3.0.0, pyyaml>=6.0
- [ ] T003 [P] Create .fte/watchers/ directory for checkpoint files
- [ ] T004 [P] Add watcher module imports to src/watchers/__init__.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY watcher can be implemented

**⚠️ CRITICAL**: No watcher work can begin until this phase is complete

- [ ] T005 [P] Create BaseWatcher abstract class in src/watchers/base_watcher.py with run(), retry_with_backoff(), _sanitize_filename() methods
- [ ] T006 [P] Implement PIIRedactor class in src/watchers/pii_redactor.py with redact() method for emails, phone numbers
- [ ] T007 [P] Create MarkdownFormatter class in src/watchers/markdown_formatter.py for YAML frontmatter + body generation
- [ ] T008 [P] Implement checkpoint system in src/watchers/checkpoint.py for read_checkpoint(), write_checkpoint()
- [ ] T009 [P] Create watcher data models in src/watchers/models.py: WatcherEvent, EmailMessage, FileEvent
- [ ] T010 Create base watcher config schema in config/watchers/base.yaml with vault_path, log_level, poll_interval
- [ ] T011 [P] Add PII patterns config in config/pii-patterns.yaml with email, phone, SSN patterns

**Checkpoint**: Foundation ready - watcher implementation can now begin in parallel

---

## Phase 3: User Story 1 - Gmail Watcher (Priority: P1) 🎯 MVP (Bronze Tier)

**Goal**: AI Employee can automatically detect new emails from Gmail and convert to structured Markdown tasks

**Independent Test**: Send test email to monitored Gmail account, verify Markdown file created in vault /Inbox with correct frontmatter and PII redacted

### Implementation for User Story 1

- [ ] T012 [P] [US1] Create GmailWatcher class in src/watchers/gmail_watcher.py inheriting from BaseWatcher
- [ ] T013 [P] [US1] Implement OAuth2 authentication in GmailWatcher.authenticate() using google-auth-oauthlib
- [ ] T014 [US1] Implement GmailWatcher.poll() to fetch unread emails from Gmail API (depends on T013)
- [ ] T015 [US1] Implement GmailWatcher.parse_message() to extract sender, subject, body, attachments (depends on T014)
- [ ] T016 [US1] Implement GmailWatcher.download_attachment() to save attachments to vault /Attachments/<message-id>/ (depends on T015)
- [ ] T017 [US1] Integrate PIIRedactor in GmailWatcher to redact PII before logging (depends on T006)
- [ ] T018 [US1] Integrate MarkdownFormatter to generate email task files in vault /Inbox (depends on T007)
- [ ] T019 [US1] Implement checkpoint persistence to avoid duplicate email processing (depends on T008)
- [ ] T020 [US1] Add exponential backoff retry logic for Gmail API errors in GmailWatcher.run() (depends on T005)
- [ ] T021 [US1] Create Gmail watcher config in config/watchers/gmail.yaml with OAuth credentials path, poll_interval
- [ ] T022 [US1] Add Gmail watcher entry point in scripts/run_watcher.py for CLI execution
- [ ] T023 [P] [US1] Write unit test for GmailWatcher.parse_message() in tests/watchers/test_gmail_watcher.py
- [ ] T024 [P] [US1] Write unit test for GmailWatcher.download_attachment() in tests/watchers/test_gmail_watcher.py
- [ ] T025 [US1] Write integration test for full Gmail polling cycle with mocked API in tests/watchers/test_gmail_integration.py

**Checkpoint**: At this point, Gmail Watcher should be fully functional - send test email and verify task appears in vault

---

## Phase 4: User Story 2 - File System Watcher (Priority: P1) 🎯 MVP (Bronze Tier)

**Goal**: AI Employee can detect new files dropped into monitored folders and create structured Markdown tasks

**Independent Test**: Drop test PDF file into monitored directory, verify Markdown file created in vault /Inbox with file metadata and SHA256 hash

### Implementation for User Story 2

- [ ] T026 [P] [US2] Create FileSystemWatcher class in src/watchers/filesystem_watcher.py inheriting from BaseWatcher and FileSystemEventHandler
- [ ] T027 [P] [US2] Implement FileSystemWatcher._load_gitignore() to parse .gitignore patterns using pathspec library
- [ ] T028 [US2] Implement FileSystemWatcher._should_ignore() to check files against .gitignore patterns (depends on T027)
- [ ] T029 [US2] Implement FileSystemWatcher._compute_hash() to calculate SHA256 for file deduplication (depends on T026)
- [ ] T030 [US2] Implement FileSystemWatcher.on_created() event handler for new file detection (depends on T028, T029)
- [ ] T031 [US2] Implement FileSystemWatcher._detect_mime_type() for file type detection in on_created()
- [ ] T032 [US2] Integrate MarkdownFormatter to generate file detection task in vault /Inbox (depends on T007, T030)
- [ ] T033 [US2] Implement FileSystemWatcher.run() to start watchdog Observer with recursive monitoring (depends on T026)
- [ ] T034 [US2] Add error handling for large files (skip hash if >1GB, log warning) in _compute_hash()
- [ ] T035 [US2] Create filesystem watcher config in config/watchers/filesystem.yaml with watch_path, recursive, gitignore settings
- [ ] T036 [US2] Add filesystem watcher entry point in scripts/run_watcher.py for CLI execution
- [ ] T037 [P] [US2] Write unit test for FileSystemWatcher._should_ignore() in tests/watchers/test_filesystem_watcher.py
- [ ] T038 [P] [US2] Write unit test for FileSystemWatcher._compute_hash() in tests/watchers/test_filesystem_watcher.py
- [ ] T039 [US2] Write integration test for file creation event with temporary directory in tests/watchers/test_filesystem_integration.py

**Checkpoint**: At this point, FileSystem Watcher should be fully functional - drop test file and verify task appears in vault

---

## Phase 5: User Story 4 - Process Management (Priority: P2) (Silver Tier)

**Goal**: Watchers auto-restart on failure and survive system reboots for 24/7 operation

**Independent Test**: Start watchers via PM2, kill process manually, verify auto-restart within 10 seconds

### Implementation for User Story 4

- [ ] T040 [P] [US4] Create PM2 ecosystem config in .fte/pm2.config.js for watcher-gmail and watcher-filesystem processes
- [ ] T041 [P] [US4] Configure PM2 auto-restart settings: max_memory_restart=200M, max_restarts=3, min_uptime=10s
- [ ] T042 [P] [US4] Add PM2 log paths to config: error_file and out_file in /var/log/fte/
- [ ] T043 [US4] Create fte CLI watcher command group in src/cli/commands/watcher.py with start, stop, status subcommands
- [ ] T044 [US4] Implement `fte watcher start <name>` to launch PM2 process for specified watcher (depends on T043)
- [ ] T045 [US4] Implement `fte watcher stop <name>` to stop PM2 process (depends on T043)
- [ ] T046 [US4] Implement `fte watcher status` to show running watchers with PID and uptime (depends on T043)
- [ ] T047 [US4] Implement `fte watcher logs <name> --tail N` to aggregate watcher logs (depends on T043)
- [ ] T048 [P] [US4] Write integration test for PM2 auto-restart in tests/watchers/test_process_management.py
- [ ] T049 [US4] Document PM2 setup in specs/005-watcher-scripts/quickstart.md with installation and startup commands

**Checkpoint**: All watchers should be manageable via CLI and auto-restart on crashes

---

## Phase 6: User Story 5 - Error Recovery (Priority: P2) (Silver Tier)

**Goal**: Watchers gracefully handle transient failures without manual intervention

**Independent Test**: Disconnect network while watcher running, verify exponential backoff retries in logs, reconnect and verify recovery

### Implementation for User Story 5

- [ ] T050 [P] [US5] Implement CircuitBreaker class in src/watchers/circuit_breaker.py with call(), _half_open() methods
- [ ] T051 [P] [US5] Add permanent error detection in BaseWatcher.retry_with_backoff() for 401/403 errors
- [ ] T052 [US5] Integrate CircuitBreaker in GmailWatcher.poll() to prevent retry storms (depends on T050)
- [ ] T053 [US5] Add Gmail API rate limit handling: parse Retry-After header in 429 responses in GmailWatcher
- [ ] T054 [US5] Implement partial failure isolation in GmailWatcher.run(): skip failed email, continue batch
- [ ] T055 [US5] Add error recovery logging with retry count and reason in BaseWatcher.retry_with_backoff()
- [ ] T056 [P] [US5] Write unit test for CircuitBreaker state transitions (CLOSED→OPEN→HALF_OPEN) in tests/watchers/test_circuit_breaker.py
- [ ] T057 [P] [US5] Write integration test for network timeout retry with mocked Gmail API in tests/watchers/test_error_recovery.py
- [ ] T058 [US5] Write integration test for circuit breaker opening after 5 consecutive failures in tests/watchers/test_error_recovery.py

**Checkpoint**: Watchers should handle network failures gracefully and recover automatically

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, testing, and production readiness

- [ ] T059 [P] Create Gmail OAuth2 setup guide in specs/005-watcher-scripts/quickstart.md with Google Cloud Console steps
- [ ] T060 [P] Create filesystem watcher setup guide in specs/005-watcher-scripts/quickstart.md with directory configuration
- [ ] T061 [P] Document PII redaction patterns in specs/005-watcher-scripts/quickstart.md with custom pattern examples
- [ ] T062 [P] Create watcher monitoring guide with PM2 dashboard and log analysis in specs/005-watcher-scripts/quickstart.md
- [ ] T063 [P] Add unit test for PIIRedactor.redact() with email/phone patterns in tests/watchers/test_pii_redactor.py
- [ ] T064 [P] Add unit test for MarkdownFormatter with YAML frontmatter validation in tests/watchers/test_markdown_formatter.py
- [ ] T065 [P] Add unit test for checkpoint read/write operations in tests/watchers/test_checkpoint.py
- [ ] T066 Run full integration test suite: send 10 test emails, drop 10 test files, verify all tasks created
- [ ] T067 Validate Gmail watcher meets NFR1.1: 30s poll interval, verify timing in logs
- [ ] T068 Validate filesystem watcher meets NFR1.2: <1s event latency, measure with timestamps
- [ ] T069 Validate PII redaction meets NFR3.1: 100% redaction rate, audit 100 log entries manually
- [ ] T070 Performance test: 100 emails/hour processing, monitor CPU and memory usage
- [ ] T071 Performance test: 1000 file events/hour, monitor watchdog event queue

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all watchers
- **User Story 1 - Gmail (Phase 3)**: Depends on Foundational phase completion
- **User Story 2 - FileSystem (Phase 4)**: Depends on Foundational phase completion (can run parallel to Phase 3)
- **User Story 4 - Process Management (Phase 5)**: Depends on US1 and US2 completion
- **User Story 5 - Error Recovery (Phase 6)**: Depends on US1 completion
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (Gmail)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (FileSystem)**: Can start after Foundational - No dependencies on other stories (can run parallel to US1)
- **User Story 4 (Process Mgmt)**: Depends on US1 and US2 having runnable watchers
- **User Story 5 (Error Recovery)**: Depends on US1 for Gmail-specific error handling

### Within Each User Story

- Authentication/setup before polling logic
- Parsing before formatting
- Core implementation before error handling
- Implementation before tests (write tests, verify they fail, then implement)
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T002, T003, T004)
- All Foundational tasks marked [P] can run in parallel (T005-T007, T009, T011)
- US1 and US2 can be implemented in parallel after Foundational phase
- Tests within each story marked [P] can run in parallel
- Documentation tasks in Polish phase marked [P] can run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch all foundational infrastructure together:
Task T005: "BaseWatcher abstract class in src/watchers/base_watcher.py"
Task T006: "PIIRedactor class in src/watchers/pii_redactor.py"
Task T007: "MarkdownFormatter class in src/watchers/markdown_formatter.py"
Task T009: "Watcher data models in src/watchers/models.py"
Task T011: "PII patterns config in config/pii-patterns.yaml"

# Wait for all to complete before starting any watcher implementation
```

---

## Implementation Strategy

### MVP First (Bronze Tier - Gmail + FileSystem)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all watchers)
3. Complete Phase 3: User Story 1 (Gmail Watcher)
4. Complete Phase 4: User Story 2 (FileSystem Watcher)
5. **STOP and VALIDATE**: Test both watchers independently with real data
6. Demo Bronze Tier completion

**Bronze Tier Success**: Two working watchers writing tasks to vault with PII redaction

### Silver Tier Extension (Process Management + Error Recovery)

1. Complete Phase 5: User Story 4 (Process Management)
2. Complete Phase 6: User Story 5 (Error Recovery)
3. **STOP and VALIDATE**: Test auto-restart and error recovery scenarios
4. Demo Silver Tier completion

**Silver Tier Success**: Watchers run 24/7 with auto-restart and graceful error handling

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Gmail Watcher)
   - Developer B: User Story 2 (FileSystem Watcher)
3. Both watchers integrate independently into vault
4. Team tackles Process Management together (US4)
5. Team tackles Error Recovery together (US5)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story (US1=Gmail, US2=FileSystem, US4=Process Mgmt, US5=Error Recovery)
- Bronze Tier focus: US1 + US2 (minimum viable watchers)
- Silver Tier: Add US4 + US5 (production readiness)
- Gold Tier (US3, US6): Deferred to future iteration (WhatsApp, advanced filtering)
- Verify tests fail before implementing features
- Commit after each task or logical group
- Stop at checkpoints to validate watchers independently
- All watchers write to same vault format (consistent Markdown + YAML frontmatter)

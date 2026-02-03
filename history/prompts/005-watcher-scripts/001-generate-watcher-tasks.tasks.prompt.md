---
id: 001
title: Generate watcher tasks for Bronze Tier
stage: tasks
date: 2026-02-03
surface: agent
model: claude-sonnet-4-5-20250929
feature: 005-watcher-scripts
branch: master
user: HomePC
command: sp.tasks
labels: ["tasks", "watcher-scripts", "bronze-tier", "gmail", "filesystem"]
links:
  spec: specs/005-watcher-scripts/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/005-watcher-scripts/tasks.md
tests:
  - null
---

## Prompt

Generate an actionable, dependency-ordered tasks.md for the 005-watcher-scripts feature.

Read:
- specs/005-watcher-scripts/spec.md
- specs/005-watcher-scripts/plan.md

Focus on Bronze Tier first (Gmail and FileSystem watchers) as that's the minimum viable implementation. Create tasks that are:
1. Small and testable (1-4 hours each)
2. Dependency-ordered
3. Include test criteria
4. Parallelizable where possible (mark with [P])

Write the tasks to: specs/005-watcher-scripts/tasks.md

Use the SDD tasks template format with YAML frontmatter.

## Response snapshot

Generated comprehensive tasks.md with 71 tasks organized into 7 phases:

**Phase 1: Setup (4 tasks)**
- Project structure creation
- Dependency installation
- Directory initialization

**Phase 2: Foundational (7 tasks)**
- BaseWatcher abstract class
- PIIRedactor for privacy compliance
- MarkdownFormatter for vault output
- Checkpoint system for idempotency
- Data models and configuration

**Phase 3: User Story 1 - Gmail Watcher (14 tasks)** 🎯 MVP Bronze Tier
- OAuth2 authentication
- Email polling and parsing
- Attachment download
- PII redaction integration
- Markdown generation
- Checkpoint persistence
- Error recovery with exponential backoff
- Configuration and CLI integration
- Unit and integration tests

**Phase 4: User Story 2 - FileSystem Watcher (14 tasks)** 🎯 MVP Bronze Tier
- Watchdog integration for inotify events
- .gitignore pattern support
- SHA256 hash computation
- File event handlers
- MIME type detection
- Large file handling
- Configuration and CLI integration
- Unit and integration tests

**Phase 5: User Story 4 - Process Management (10 tasks)** - Silver Tier
- PM2 ecosystem configuration
- Auto-restart settings
- CLI commands: start, stop, status, logs
- Integration tests for auto-restart

**Phase 6: User Story 5 - Error Recovery (9 tasks)** - Silver Tier
- Circuit breaker pattern
- Permanent error detection
- Rate limit handling
- Partial failure isolation
- Error recovery tests

**Phase 7: Polish (13 tasks)**
- Documentation (OAuth setup, directory config, PII patterns, monitoring)
- Additional unit tests
- Integration test suite
- NFR validation (polling interval, event latency, PII redaction)
- Performance tests (100 emails/hour, 1000 file events/hour)

## Outcome

- ✅ Impact: Complete task breakdown for Bronze Tier (Gmail + FileSystem watchers) with clear MVP path
- 🧪 Tests: Test tasks included for all user stories (US1: 3 tests, US2: 3 tests, US5: 2 tests)
- 📁 Files: 1 file created (specs/005-watcher-scripts/tasks.md)
- 🔁 Next prompts: "Start Bronze Tier implementation with Phase 1 Setup", "Create research.md for Gmail API and watchdog library", "Implement BaseWatcher abstract class (T005)"
- 🧠 Reflection: Tasks properly organized by user story with clear checkpoints. Bronze Tier (US1+US2) is achievable MVP with 35 tasks. Silver Tier adds 19 tasks for production readiness. Parallel opportunities identified in foundational phase and between US1/US2.

## Evaluation notes (flywheel)

- Failure modes observed: None - spec and plan were comprehensive, all user stories clearly defined with priorities
- Graders run and results (PASS/FAIL): Manual validation PASS - tasks follow SDD template format, include [P] markers for parallelization, [Story] labels for traceability, dependency ordering correct
- Prompt variant (if applicable): Standard sp.tasks workflow
- Next experiment (smallest change to try): Consider adding estimated hours per task for better sprint planning

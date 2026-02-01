---
id: 001
title: File Control Plane Implementation Plan
stage: plan
date: 2026-01-27
surface: agent
model: claude-sonnet-4-5
feature: 001-file-control-plane
branch: 001-file-control-plane
user: system
command: /sp.plan
labels: ["planning", "architecture", "control-plane", "file-driven", "constitutional-compliance"]
links:
  spec: specs/001-file-control-plane/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/001-file-control-plane/plan.md
  - specs/001-file-control-plane/data-model.md
  - specs/001-file-control-plane/quickstart.md
  - specs/001-file-control-plane/contracts/state_machine_api.md
  - specs/001-file-control-plane/contracts/approval_api.md
  - specs/001-file-control-plane/contracts/logger_api.md
  - CLAUDE.md (updated via update-agent-context.sh)
tests:
  - None (planning phase - tests defined in plan but not yet implemented)
---

## Prompt

Building file-driven control plane with Python. Using pathlib for atomic file operations, watchdog for file system monitoring, PyYAML for task file metadata, and structlog for append-only logging. Focus on constitutional compliance: atomic state transitions (Section 4), approval checks (Section 6-7), comprehensive logging (Section 8), and state verification (Section 2).

Read Plans/01-file-control-plane.md completely. Create /sp.plan only. Do not generate tasks or code. Map every plan step to constitutional sections. Explicitly list failure modes. Stop after plan creation.

## Response snapshot

Created comprehensive implementation plan for file-driven control plane with complete constitutional compliance mapping:

**Plan Structure Created:**
1. Summary - Folder-based state machine with 8 workflow folders using Python 3.11+, pathlib, watchdog, PyYAML, structlog
2. Technical Context - Language, dependencies, storage, testing, performance goals, constraints, scale
3. Constitution Check - Mapped ALL applicable sections (2, 4, 5, 6-7, 8, 9, 11, 13) with ✅ PASS gate status
4. Project Structure - Documentation layout and source code organization (src/control_plane/ with 7 modules)
5. Complexity Tracking - No constitutional violations identified
6. Phase 0: Research & Technology Decisions - Justified Python 3.11+, pathlib, watchdog, PyYAML, structlog, pytest choices with rationale, alternatives, and constitutional mappings
7. Phase 1: Design & Contracts - Generated data-model.md, quickstart.md, and 3 API contracts (state_machine_api.md, approval_api.md, logger_api.md)
8. Explicit Failure Modes - Documented 10 failure modes across file system, logging, state machine, and dependencies with detection, handling, recovery, and constitutional mappings

**Key Design Decisions:**
- Python 3.11+ for pathlib atomic operations, match statements, type hints
- pathlib over os module for atomic file moves (Path.rename())
- watchdog for cross-platform file system monitoring (event-driven vs polling)
- PyYAML for human-readable YAML frontmatter in task files
- structlog for structured JSON logging with context binding
- pytest with fixtures for isolated file system testing

**Constitutional Compliance:**
- Section 2 (Source of Truth): All state in file location + YAML frontmatter, no hidden state
- Section 4 (File-Driven Control Plane): 8 folders enforced, atomic pathlib.Path.rename()
- Section 5 (Reasoning Discipline): Read→Think→Plan→Act→Write→Verify loop in StateTransition class
- Section 6-7 (Autonomy & HITL): SensitiveActionDetector blocks without /Approved, file-based approval
- Section 8 (Auditability): structlog append-only JSON logs with all required fields
- Section 9 (Error Handling): All exceptions logged, max 3 retries, partial completion preferred
- Section 11 (No Spec Drift): Implementation follows spec exactly, no invented requirements
- Section 13 (Completion Definition): StateVerifier checks 4 criteria (files exist, correct folders, logs written, disk verifiable)

**Artifacts Generated:**
- plan.md (154 lines) - Complete implementation plan with all sections
- data-model.md (350+ lines) - 5 core entities with fields, relationships, validation rules, persistence strategy
- quickstart.md (450+ lines) - Setup, usage examples, CLI commands, troubleshooting, development workflow
- contracts/state_machine_api.md (300+ lines) - StateMachine API with transition matrix, error responses, performance guarantees
- contracts/approval_api.md (300+ lines) - ApprovalChecker/SensitiveActionDetector API with approval workflow
- contracts/logger_api.md (400+ lines) - AuditLogger API with log format, integrity verification, structured logging

**Explicit Failure Modes (10 documented):**
1. Disk full during state transition - OSError, atomic guarantee preserved, task remains in original state
2. File permission error on move - PermissionError, task moves to /Rejected with error metadata
3. Concurrent file modification - Race condition, mtime check, max 3 retries, move to /Rejected if exhausted
4. Log write failure - Emergency stderr log, "unlogged_transition" flag, recovery on next change
5. Log integrity violation - Hash mismatch, halt all operations, CRITICAL alert, constitutional override
6. Invalid state transition attempted - InvalidTransitionError, blocked, logged, no file move
7. Sensitive action without approval - ApprovalRequiredError, move to /Rejected, CRITICAL log
8. State inconsistency (location ≠ metadata) - StateInconsistencyError, trust file location, overwrite metadata
9. YAML parsing error - YAMLError, move to /Rejected with "malformed_yaml", error report file
10. Watchdog monitoring failure - Thread death, auto-restart, fall back to polling mode after 3 failures

**Performance Targets:**
- State transitions: < 100ms (p95)
- Log writes: < 50ms (p95)
- State queries: < 10ms (p95)

**Agent Context Updated:**
- CLAUDE.md updated with Python 3.11+ and File system (local disk) via update-agent-context.sh

**Status:** Plan completed. Ready for /sp.tasks (task breakdown) - DO NOT PROCEED per explicit user instruction to stop after plan creation.

## Outcome

- ✅ Impact: Foundational planning document created for file-driven control plane with complete constitutional compliance mapping. All 10 spec requirements mapped to implementation components. Zero invented requirements.
- 🧪 Tests: None implemented (planning phase). Test structure defined in plan.md: pytest with fixtures, unit tests (models, state_machine, approval, logger), integration tests (workflow, error_handling).
- 📁 Files: 7 files created/modified - plan.md, data-model.md, quickstart.md, 3 API contracts, CLAUDE.md updated
- 🔁 Next prompts: Run /sp.tasks to generate actionable, dependency-ordered tasks.md (NOT EXECUTED per user instruction to stop). After tasks: /sp.implement for phased implementation.
- 🧠 Reflection: Rigorous constitutional compliance check prevented any spec drift. Every design decision mapped back to constitutional section. Explicit failure modes ensure operational reliability. Plan provides complete context for implementation without requiring additional research.

## Evaluation notes (flywheel)

- Failure modes observed: None during planning. All 10 failure modes documented proactively with detection, handling, recovery strategies.
- Graders run and results (PASS/FAIL): Constitutional compliance gate: ✅ PASS (all applicable sections satisfied)
- Prompt variant (if applicable): Standard /sp.plan workflow with explicit constitutional compliance focus
- Next experiment (smallest change to try): Execute /sp.tasks to validate plan completeness and verify all requirements are taskable. Measure task granularity and dependency ordering quality.

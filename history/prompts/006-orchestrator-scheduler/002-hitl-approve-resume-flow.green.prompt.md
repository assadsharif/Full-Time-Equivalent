---
id: 002
title: HITL approve-then-resume flow
stage: green
date: 2026-02-04
surface: agent
model: claude-sonnet-4-5-20250929
feature: 010-hitl-approval-workflows
branch: master
user: assadsharif
command: continue working
labels: ["orchestrator","hitl","approval","resume","spec-010"]
links:
  spec: specs/010-hitl-approval-workflows/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - src/orchestrator/scheduler.py
 - tests/orchestrator/test_orchestrator.py
tests:
 - tests/orchestrator/test_orchestrator.py::TestHITLResumeFlow::test_approve_and_resume_completes_task
 - tests/orchestrator/test_orchestrator.py::TestHITLResumeFlow::test_unapproved_task_not_resumed
 - tests/orchestrator/test_orchestrator.py::TestHITLResumeFlow::test_apr_request_files_not_resumed
 - tests/orchestrator/test_orchestrator.py::TestHITLResumeFlow::test_resume_exit_log_has_correct_final_state
---

## Prompt

please continue working (continuation from compacted context — HITL resume flow was in progress)

## Response snapshot

Added `_discover_approved()` and `_resume_task()` methods to the Orchestrator.
`_discover_approved()` scans the Approvals folder, skips APR-* request files and
non-task files (via `**Priority**:` marker check), and returns scored TaskRecords
for any file whose approval has been granted.  `_resume_task()` drives the
PENDING_APPROVAL → EXECUTING → DONE|REJECTED path, reusing the persistence loop.
Both `run()` and `run_once()` now call the resume phase after new-task processing.

Bug during development: legacy approval-response files (e.g., `approval-deploy-svc.md`)
were being picked up as resumable tasks because they didn't start with `APR-`.  Fixed
by adding a `**Priority**:` structure check — only files with task markers are considered.

## Outcome

- ✅ Impact: Tasks parked in PENDING_APPROVAL are now automatically resumed on next sweep once approved. Closes the loop between HITL approval and execution.
- 🧪 Tests: 4 new integration tests, all green. Full suite 1084/1084 pass.
- 📁 Files: 2 modified (scheduler.py +105 lines, test_orchestrator.py +100 lines)
- 🔁 Next prompts: Implement MCP security Bronze tier (spec 004)
- 🧠 Reflection: The `**Priority**:` marker check is a reliable task-file discriminator used consistently across the codebase (TaskValidator, PriorityScorer). Prefixing alone (APR-) is insufficient when approval-response files coexist in the same folder.

## Evaluation notes (flywheel)

- Failure modes observed: Legacy approval-response files picked up as resumable tasks; filtered by task-structure marker.
- Graders run and results (PASS/FAIL): PASS — 1084/1084
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Add expiry-aware resume (skip tasks whose approval has timed out)

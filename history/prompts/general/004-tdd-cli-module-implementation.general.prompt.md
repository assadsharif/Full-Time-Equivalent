---
id: 004
title: TDD CLI Module Implementation
stage: general
date: 2026-02-02
surface: agent
model: claude-opus-4-5-20251101
feature: none
branch: master
user: asad
command: implement plan
labels: ["tdd", "cli", "click", "pytest"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/cli/tdd_state.py
  - src/cli/tdd.py
  - src/cli/main.py
  - tests/cli/test_tdd.py
tests:
  - tests/cli/test_tdd.py::TestTDDState (8 tests)
  - tests/cli/test_tdd.py::TestParsePytestSummary (3 tests)
  - tests/cli/test_tdd.py::TestTDDInit (2 tests)
  - tests/cli/test_tdd.py::TestTDDRed (2 tests)
  - tests/cli/test_tdd.py::TestTDDGreen (2 tests)
  - tests/cli/test_tdd.py::TestTDDRefactor (3 tests)
  - tests/cli/test_tdd.py::TestTDDStatus (2 tests)
  - tests/cli/test_tdd.py::TestTDDCycle (3 tests)
  - tests/cli/test_tdd.py::TestTDDWatch (2 tests)
  - tests/cli/test_tdd.py::TestTDDGroup (1 test)
---

## Prompt

Implement the following plan:

# Plan: TDD Sub-Agent CLI Module

## Goal
Create a `fte tdd` CLI command group that acts as the TDD sub-agent — orchestrating Red-Green-Refactor cycles, running pytest, tracking TDD state, and enforcing TDD-Skill rules.

## Context
- Existing CLI uses Click command groups registered in `src/cli/main.py`
- Pattern: each command group is its own module (e.g., `watcher.py`, `mcp.py`)
- Tests live in `tests/cli/` using pytest + click.testing.CliRunner

## Files to Create
1. `src/cli/tdd_state.py` — TDD State Manager
2. `src/cli/tdd.py` — TDD Agent CLI Commands (init, red, green, refactor, cycle, status, watch)
3. Update `src/cli/main.py` — Register tdd_group
4. `tests/cli/test_tdd.py` — Tests for TDD Agent

## Response snapshot

Implemented the complete TDD Sub-Agent CLI module with 4 files:

1. **`src/cli/tdd_state.py`** — TDDState class with JSON persistence to `.fte/tdd_state.json`. Tracks phase (idle/red/green/refactor), target test, pass/fail/error counts, and cycle history.

2. **`src/cli/tdd.py`** — 7 Click commands under `fte tdd` group:
   - `init` — creates tests/ dir, conftest.py, resets state
   - `red <test_path>` — runs tests, exits 0 if they fail (expected), exits 1 if pass
   - `green <test_path>` — runs tests, exits 0 if they pass, exits 1 if fail
   - `refactor [--cov]` — runs ALL tests, records cycle on success
   - `cycle <test_path>` — interactive RED->GREEN->REFACTOR with pauses
   - `status` — Rich table showing current phase, counts, cycles
   - `watch [path]` — delegates to pytest-watch

3. **`src/cli/main.py`** — Added 2 lines to register tdd_group (same pattern as other groups).

4. **`tests/cli/test_tdd.py`** — 28 tests covering all commands with mocked subprocess. All pass.

Key fix during implementation: replaced `ctx.exit()` with `raise SystemExit()` to avoid Click's Exit exception being caught by the generic except handler.

## Outcome

- ✅ Impact: New `fte tdd` command group enabling TDD workflow management from CLI
- 🧪 Tests: 28/28 passed; 291/291 CLI suite passed (zero regressions)
- 📁 Files: 3 created, 1 modified
- 🔁 Next prompts: Consider adding `fte tdd report` for cycle history, coverage thresholds in refactor
- 🧠 Reflection: Click's ctx.exit() raises click.Exit which gets caught by broad except clauses — use raise SystemExit(code) instead for clean exit code propagation in CliRunner tests

## Evaluation notes (flywheel)

- Failure modes observed: ctx.exit(0) caught by except Exception causing exit code 1 in 4 tests
- Graders run and results (PASS/FAIL): pytest 28/28 PASS, full CLI suite 291/291 PASS
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Add --json output flag to tdd status for scripting integration

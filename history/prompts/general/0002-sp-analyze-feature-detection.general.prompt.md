---
id: 0002
title: sp.analyze Feature Detection
stage: general
date: 2026-02-03
surface: agent
model: claude-opus-4-5-20251101
feature: none
branch: master
user: asad
command: /sp.analyze
labels: ["analysis", "features", "detection"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - specs/*/spec.md
  - specs/*/plan.md
  - specs/*/tasks.md
tests:
  - Feature artifact detection
---

## Prompt

/sp.analyze (no feature specified)

## Response snapshot

Detected 10 feature specifications in specs/ directory:
- 3 complete features (001, 002, 003) with spec+plan+tasks
- 7 features (004-010) missing tasks.md

Analysis blocked: Not on feature branch and no feature specified.

Provided options:
1. Analyze specific feature with `/sp.analyze <feature>`
2. Switch to feature branch
3. Generate missing tasks.md files

## Outcome

- Impact: Identified feature inventory and completeness status
- Tests: Artifact detection passed
- Files: 10 specs, 10 plans, 3 tasks found
- Next prompts: /sp.analyze with specific feature, or /sp.tasks for missing features
- Reflection: Need feature context for full analysis

## Evaluation notes (flywheel)

- Failure modes observed: Branch detection requires feature branch
- Graders run and results (PASS/FAIL): Detection PASS, Analysis BLOCKED
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): Allow master branch analysis with explicit feature arg

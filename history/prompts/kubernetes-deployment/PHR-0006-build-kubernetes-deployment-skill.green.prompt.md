---
id: PHR-0006
title: Build Kubernetes Deployment Skill and MCP Server
stage: green
date: 2026-02-04
surface: agent
model: claude-sonnet-4-5-20250929
feature: kubernetes-deployment
branch: master
user: developer
command: execution-mode build
labels: ["kubernetes", "skill", "mcp", "pydantic", "manifest-generation", "validation"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - .claude/skills/kubernetes-deployment/SKILL.md
  - .claude/skills/kubernetes-deployment/__init__.py
  - .claude/skills/kubernetes-deployment/models.py
  - .claude/skills/kubernetes-deployment/skill.py
  - .claude/skills/kubernetes-deployment/metadata.yaml
  - .claude/skills/kubernetes-deployment/references/k8s-best-practices.md
  - src/mcp_servers/k8s_deployment_mcp.py
tests:
  - AST syntax validation of k8s_deployment_mcp.py (all 7 classes, 11 private funcs, 5 tools present)
  - Skill-validator 7-category scoring: 95.7/100 Production
  - Memory graph integration verified (4 entities, 3 relations)
---

## Prompt

Create a reusable, production-grade Kubernetes Deployment Skill with 6-step execution:
1. Create the skill (SKILL.md, models, logic, metadata, references)
2. Evaluate Factory / Sub-Agent necessity
3. Validate against skill-validator (90+ required)
4. Integrate memory-mcp
5. Convert to MCP server
6. Deliver final output

Constraints: deterministic, infrastructure-safe, validation-first, Pydantic v2, no placeholders.

## Response snapshot

Built a complete Kubernetes Deployment Skill with 8 files across the skill directory and MCP server. The skill generates validated Deployment, Service, and ConfigMap manifests from typed Pydantic v2 schemas — all output is deterministic YAML. Key design decisions: Factory pattern rejected (single parameterized skill handles all variants); Sub-Agent rejected (pure stateless functions, no isolated transformation). SKILL.md updated with clarification triggers, source URLs, error handling, dependencies, and update guidance to achieve Production-grade validation score. MCP server (k8s_deployment_mcp) follows the project's helm_packaging_mcp.py pattern exactly: self-contained inline models and generation logic, 5 FastMCP async tools, JSON string returns. Memory integration stores 4 entities (component, pattern, fact) with 3 relations encoding the skill's design patterns and resource defaults for cross-session recall.

## Outcome

- ✅ Impact: Production-grade Kubernetes manifest generation skill + MCP server. 5 tools covering the full Deployment/Service/ConfigMap lifecycle with auto-derivation stack composition and structural validation. Scored 95.7/100 against skill-validator (Production threshold: 90).
- 🧪 Tests: AST verification confirmed all expected symbols present (7 classes, 5 async tool functions, 11 private helpers). Skill-validator 7-category scoring completed. Memory graph integrity verified.
- 📁 Files: 7 skill files in .claude/skills/kubernetes-deployment/ + 1 MCP server at src/mcp_servers/k8s_deployment_mcp.py (611 lines). README.md intentionally removed per skill-validator requirement (SKILL.md IS the readme).
- 🔁 Next prompts: Register k8s_deployment_mcp in .mcp.json; write integration tests for MCP tools; generate sample manifests for validation smoke tests
- 🧠 Reflection: The Factory/Sub-Agent evaluation phase saved significant complexity — a single parameterized skill with Pydantic's optional fields and the generate_stack auto-derivation pattern handles all manifest variants cleanly. The skill-validator clarification-triggers requirement (15% weight) was the highest-impact gap in the initial SKILL.md draft.

## Evaluation notes (flywheel)

- Failure modes observed: Initial SKILL.md scored ~62/100 due to missing User Interaction section (clarification triggers). README.md was also flagged as extraneous. Both corrected before formal scoring.
- Graders run and results (PASS/FAIL): PASS — Skill-validator score 95.7/100 (Production). All 5 MCP tools syntactically valid. Memory entities/relations created successfully.
- Prompt variant (if applicable): Execution-mode build with 6 mandatory steps
- Next experiment (smallest change to try): Add good/bad code examples to SKILL.md for the most common anti-patterns (latest tag, secrets in ConfigMap) to push Documentation score from 87 to 100

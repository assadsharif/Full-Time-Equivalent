---
id: PHR-0002
title: Build kubectl-ai MCP Server
stage: green
date: 2026-02-03
surface: agent
model: claude-opus-4-5-20251101
feature: kubectl-ai
branch: master
user: asad
command: build the next mcp server
labels: ["mcp", "kubectl", "kubernetes", "ai-assistance", "diagnostics"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/mcp_servers/kubectl_ai_mcp.py
  - .mcp.json
tests:
  - Manual verification of tool loading
---

## Prompt

build the next mcp server

## Response snapshot

Built kubectl_ai_mcp.py MCP server with 10 tools (kubectl_generate_prompt, kubectl_diagnose_pod, kubectl_diagnose_service, kubectl_diagnose_deployment, kubectl_classify_safety, kubectl_suggest_workflow, kubectl_check_helm_safety, kubectl_generate_triage, kubectl_list_prompt_patterns, kubectl_suggest_resolution). Registered in .mcp.json. Verified all tools load. This is the 8th active MCP server, completing the Kubernetes operations stack (Docker -> Helm -> kubectl-ai).

## Outcome

- ✅ Impact: Created kubectl-ai MCP server with 10 AI-powered diagnostic and safety tools for Kubernetes operations. Completes the k8s stack alongside Docker and Helm servers.
- 🧪 Tests: Manual verification confirmed all 10 tools load correctly via .mcp.json registration
- 📁 Files: Created src/mcp_servers/kubectl_ai_mcp.py (10 tools, 450+ lines), modified .mcp.json
- 🔁 Next prompts: Test kubectl_generate_prompt with real scenarios, validate kubectl_diagnose_pod output quality, create integration tests for safety classification
- 🧠 Reflection: kubectl-ai bridges the gap between raw kubectl commands and intelligent operational assistance, providing prompt generation, diagnostics, safety checks, and resolution suggestions in a unified MCP interface

## Evaluation notes (flywheel)

- Failure modes observed: None. Tool loading and registration successful on first attempt.
- Graders run and results (PASS/FAIL): Manual inspection PASS - all tools registered and available
- Prompt variant (if applicable): Direct instruction "build the next mcp server" - no variant testing
- Next experiment (smallest change to try): Add real kubectl execution capabilities to diagnostic tools (currently they generate commands/analysis but don't execute)

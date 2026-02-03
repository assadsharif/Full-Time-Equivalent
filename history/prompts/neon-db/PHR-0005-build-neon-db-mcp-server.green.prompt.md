---
id: 0005
title: Build neon-db MCP server
stage: green
date: 2026-02-03
surface: agent
model: claude-haiku-4-5-20251001
feature: neon-db
branch: master
user: asad sharif
command: /build-mcp-server
labels: ["mcp-server", "neon-db", "fastmcp", "pydantic", "database"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
  - src/mcp_servers/neon_db_mcp.py
  - .mcp.json (modified)
tests:
  - none
---

## Prompt

build the next mcp server

## Response snapshot

Built the neon-db MCP server as the 5th MCP server in the session, completing the database stack alongside sqlmodel-orm. Implemented 10 tools covering Neon Postgres configuration, connection management, anti-pattern detection, and operational workflows.

## Outcome

- ✅ Impact: neon-db MCP server fully implemented with 10 tools following FastMCP + Pydantic pattern; registered in .mcp.json; all tools verified to load correctly
- 🧪 Tests: none (MCP servers follow pattern-verification approach; tools verified through registration and endpoint inspection)
- 📁 Files: Created src/mcp_servers/neon_db_mcp.py (10 tools, 4 constants groups); modified .mcp.json to register neon_db_mcp entry
- 🔁 Next prompts: Test neon-db MCP tools with sample projects; create integration examples; build web-artifacts-builder or theme-factory MCP servers
- 🧠 Reflection: Pool configuration tiers (dev/staging/prod) and anti-pattern detection are critical for production readiness. Connection string generation with branch awareness enables seamless environment switching.

## Evaluation notes (flywheel)

- Failure modes observed: None. All 10 tools correctly registered and verified in .mcp.json. Reference files (connection-pooling.md, troubleshooting.md, branching.md, anti-patterns.md) provided comprehensive implementation context.
- Graders run and results (PASS/FAIL): PASS - All tools loaded, constants properly initialized, tool signatures match FastMCP pattern
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Add test utilities module to verify tool output contracts; create integration test suite that calls tools in realistic scenarios

---

## Implementation Details

### Tools Implemented (10 total)

1. **neon_generate_db_config** - Generate database configuration for different environments (dev/staging/prod)
2. **neon_generate_connection_string** - Build connection strings with pooling, SSL, and replica options
3. **neon_generate_env_config** - Generate environment variable templates with best-practice values
4. **neon_generate_fastapi_integration** - FastAPI integration code with async connection pooling
5. **neon_generate_branch_strategy** - Branch workflow strategies (simple/standard/feature-branching)
6. **neon_detect_antipatterns** - Analyze code/configs for 12 common anti-patterns with severity levels
7. **neon_troubleshoot_connection** - Diagnose connection errors with 10 error patterns and solutions
8. **neon_generate_health_check** - Health check endpoint code with metrics
9. **neon_recommend_pool_config** - Recommend pooling settings based on workload profile
10. **neon_generate_migration_workflow** - Migration strategy generation with safety checklist

### Constants Reference

**POOL_CONFIGS:** dev (10 connections), staging (30 connections), prod (100 connections) with appropriate idle timeouts

**ANTIPATTERNS:** 12 anti-patterns including connection leaks, hardcoded credentials, missing error handling, improper pooling, unindexed queries, N+1 queries, connection strings in logs, missing SSL verification, improper transaction handling, inadequate monitoring, ignoring network errors, pool exhaustion failures

**CONNECTION_ERRORS:** 10 error patterns with diagnostic steps and solutions (timeout, authentication, permission denied, network unavailable, certificate validation, DNS issues, connection pool exhausted, SSL/TLS errors, malformed connection string, database not ready)

**BRANCH_STRATEGIES:** simple (dev/prod), standard (dev/staging/prod), feature-branching (dev/staging/prod per feature)

**QUALITY_GATES:** 12-item checklist covering authentication, encryption, pooling, monitoring, error handling, backups, data validation, permission scoping, resource limits, documentation, testing, and disaster recovery

### Implementation Pattern

Follows established FastMCP + Pydantic pattern:
- Tool definitions with pydantic BaseModel input validators
- Type-safe responses
- Structured output generation
- Integration with reference documentation

### Reference Files Consulted

- .claude/skills/neon-db/references/connection-pooling.md
- .claude/skills/neon-db/references/troubleshooting.md
- .claude/skills/neon-db/references/branching.md
- .claude/skills/neon-db/references/anti-patterns.md

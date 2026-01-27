---
name: memory-mcp
description: Persistent semantic memory using the Memory MCP server. Use when Claude needs to store information for future recall, remember decisions, maintain context across sessions, or retrieve previously stored information. Triggers on requests to remember, recall, store, or retrieve information, decisions, preferences, or project context.
---

# Memory MCP

Persistent semantic memory using the @modelcontextprotocol/server-memory MCP server.

## Overview

Store and retrieve information across sessions. Enables Claude to maintain context, remember decisions, and recall important project information.

## Core Capabilities

### 1. Store Memory
```
"Remember that we use FastAPI for the backend"
"Store this decision: database is PostgreSQL with Neon"
```
→ Use `store_memory` to save information

### 2. Recall Memory
```
"What did we decide about authentication?"
"Recall what backend framework we're using"
```
→ Use `recall_memory` to retrieve information

### 3. Search Memories
```
"Search for anything about database"
"Find memories related to authentication"
```
→ Use `search_memory` to find relevant information

### 4. Context Management
```
"Create a new context for user-profile feature"
"Switch to authentication context"
```
→ Use `create_context` and `switch_context` to organize

## Memory Organization

### By Feature
- authentication-context
- user-profile-context
- payment-context

### By Topic
- architecture-decisions
- coding-standards
- design-patterns

### By Phase
- spec-phase
- implementation-phase
- testing-phase

## Workflow Decision Tree

```
Memory operation request
│
├─ Need to save? → store_memory
├─ Need to retrieve? → recall_memory
├─ Need to search? → search_memory
├─ Organize by context? → create_context / switch_context
└─ List all? → list_memories
```

## Common Patterns

### Pattern 1: Store Decision
```
1. Make architectural decision
2. Store in memory → store_memory({
     key: "database-choice",
     value: "PostgreSQL with Neon",
     context: "architecture"
   })
3. Link to ADR if created
```

### Pattern 2: Recall for New Feature
```
1. Switch context → switch_context("user-profile")
2. Recall patterns → recall_memory("authentication-patterns")
3. Apply to new feature
```

### Pattern 3: Cross-Session Continuity
```
1. At session start → list_contexts()
2. Switch to relevant context
3. Recall recent decisions
4. Continue work with full context
```

## Memory Types

**Decisions:**
```
"Decision: Use JWT for authentication"
"Decision: Repository pattern for data access"
```

**Preferences:**
```
"Preference: Python type hints required"
"Preference: Tests before implementation"
```

**Facts:**
```
"Fact: Database is PostgreSQL with Neon"
"Fact: API base URL is /api/v1"
```

**Patterns:**
```
"Pattern: Use dependency injection for services"
"Pattern: Feature-based directory structure"
```

## Integration with Spec-Driven Development

**Store spec decisions:**
```
store_memory({
  key: "auth-approach",
  value: "JWT with refresh tokens",
  context: "authentication"
})
```

**Recall for implementation:**
```
recall_memory("auth-approach")
→ Apply stored decision during implementation
```

**Link to ADRs:**
```
store_memory({
  key: "database-adr",
  value: "See ADR-001 for database choice rationale",
  context: "architecture"
})
```

## Best Practices

### ✅ DO
- Store important decisions
- Use clear, descriptive keys
- Organize by context
- Update memories when decisions change
- Link to documentation (ADRs, specs)

### ❌ DON'T
- Store temporary information
- Store sensitive data (secrets, passwords)
- Store large code blocks (use files instead)
- Duplicate information in files and memory
- Let memories become stale

## Reference

For detailed documentation:
- [Memory MCP README](../../mcp/memory/README.md)
- [MCP Installation Summary](../../mcp/INSTALLATION_SUMMARY.md)

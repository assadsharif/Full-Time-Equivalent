---
name: <namespace>.<category>.<action>
version: 1.0.0
description: |
  Brief description of what the skill does.
  One or two sentences max.

triggers:
  - trigger phrase 1
  - trigger phrase 2
  - trigger phrase 3

command: /<namespace>.<category>.<action>
aliases: []

category: <task|query|config|diagnostic|workflow|git|vault|briefing|watcher|orchestrator|security|approval>
tags: [tag1, tag2]

requires:
  tools: []
  skills: []
  env: []

parameters: []

safety_level: low    # low | medium | high
approval_required: false
destructive: false

constitutional_compliance:
  - section: 8       # Auditability

author: AI Employee Team
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
---

## Overview

What does this skill do?  When should a user invoke it?  When should they
NOT use it (point to an alternative if one exists)?

## Instructions

### Prerequisites
1. Check that required tools / env vars are available.
2. Any state that must be true before proceeding.

### Step 1: <first action>
Detailed, imperative instructions.  Each step should be executable
without ambiguity.

### Step 2: <second action>
…

### Step 3: <third action>
…

### Error Handling
- **Error type A:** What to do (e.g. "inform user and exit").
- **Error type B:** What to do.

## Examples

### Example 1: <happy-path title>

**User Input:**
```
/skill-name <args>
```

**Execution:**
```bash
# Commands the skill runs, in order
```

**Output:**
```
What the user sees on success.
```

### Example 2: <edge-case or error title>

**User Input:**
```
/skill-name <different args>
```

**Execution:**
```bash
# …
```

**Output:**
```
…
```

## Validation Criteria

### Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

### Safety Checks
- [ ] No sensitive data exposed
- [ ] Approval gating respected (if safety_level: high)
- [ ] All actions logged for audit trail

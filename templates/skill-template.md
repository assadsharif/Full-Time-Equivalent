---
name: <namespace>.<category>.<action>
version: 1.0.0
description: |
  Brief description of what the skill does.
  One or two sentences max.

triggers:
  - trigger phrase 1
  - trigger phrase 2

command: /<skill-name>
category: <category>
tags: [tag1, tag2]

requires:
  tools: []
  skills: []
  env: []

parameters: []

safety_level: low          # low | medium | high
approval_required: false   # must be true when safety_level = high
destructive: false

constitutional_compliance:
  - section: 8   # Auditability
  - section: 9   # Error recovery

author: AI Employee Team
created: YYYY-MM-DD
last_updated: YYYY-MM-DD
---

## Overview

What does this skill do?  When should it be used?  When should it NOT be used?

## Instructions for Claude

### Step 1: [First step title]
Detailed instructions for this step.  Include exact commands if applicable.

### Step 2: [Second step title]
Detailed instructions for this step.

### Error Handling
- **Error type 1:** What to do when this happens.
- **Error type 2:** What to do when this happens.

## Examples

### Example 1: [Normal case title]
**User Input:**
```
User: "..."
```

**Skill Execution:**
```bash
# Commands Claude would run
```

**Output:**
```
Expected user-facing output
```

### Example 2: [Edge-case or error title]
**User Input:**
```
User: "..."
```

**Output:**
```
Expected output for this scenario
```

## Validation Criteria

### Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2

### Safety Checks
- [ ] Safety check 1
- [ ] Safety check 2

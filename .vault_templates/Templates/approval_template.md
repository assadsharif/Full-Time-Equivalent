---
approval_id: APR-YYYYMMDD-NNN
title: Approval Request Title
task_id: TASK-YYYYMMDD-NNN
task_path: /path/to/task.md
action_type: other
risk_level: medium
status: pending
nonce: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
requested_by: orchestrator
created_at: YYYY-MM-DDTHH:MM:SSZ
expires_at: YYYY-MM-DDTHH:MM:SSZ
priority: high
---

# 🔐 Approval Request: {{title}}

## ⚠️ Action Requiring Approval

**Task**: [[{{task_path}}]]
**Action Type**: {{action_type}}
**Risk Level**: {{risk_level}}
**Requested By**: {{requested_by}}
**Expires**: {{expires_at}}

---

## 📋 Description

[Detailed description of the action requiring approval]

## 🎯 Reason for Approval

[Explanation of why this action requires human approval]

**Trigger Keywords**: [List of keywords that triggered approval requirement]

---

## 🔍 Proposed Action Details

**Command/Action**:
```
[Command or action to be executed]
```

**Target**: [Target system/resource]

**Expected Impact**: [What will change]

**Rollback Plan**: [How to undo if needed]

---

## 🤔 Alternatives Considered

1. **Alternative 1**: [Description]
   - Pros: [List]
   - Cons: [List]

2. **Alternative 2**: [Description]
   - Pros: [List]
   - Cons: [List]

---

## ✅ Decision (Fill this out)

**Status**: [ ] APPROVED / [ ] REJECTED

**Decision Reason**:
[Explain your decision]

**Nonce**: `{{nonce}}` (copy this value to confirm)

**Decided By**: [Your name/email]
**Decided At**: [Timestamp]

---

## 📝 Notes

[Any additional notes or context]

---

*⏰ This approval request expires at {{expires_at}}*
*🔒 Security nonce required for validation*

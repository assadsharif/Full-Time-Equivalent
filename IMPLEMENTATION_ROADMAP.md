# Digital FTE Implementation Roadmap

**Last Updated**: 2026-01-27
**Status**: Constitution Established, Specifications Created

---

## Overview

This document provides a roadmap for implementing the Personal AI Employee (Digital FTE) system based on the project constitution and prioritized feature specifications.

---

## ✅ Completed Steps

### 1. Constitution Established
**File**: `.specify/memory/constitution.md`
**Commit**: f60627c

**Key Principles Defined:**
- ✅ Core Identity: System as Employee (not chatbot)
- ✅ Source of Truth: Obsidian Vault (files are facts)
- ✅ Local-First & Privacy: MCP gateway, no secrets in vault
- ✅ File-Driven Control Plane: 8 workflow folders
- ✅ Reasoning Discipline: Read → Think → Plan → Act → Write → Verify
- ✅ Autonomy Boundaries: Autonomous vs. requires approval
- ✅ Human-in-the-Loop: File-based approval system
- ✅ Auditability & Logging: Append-only logs
- ✅ Error Handling: Transparent, no hidden failures
- ✅ Ralph Wiggum Rule: Persistence loop with bounds
- ✅ No Spec Drift: Explicit requirement changes only
- ✅ Engineering Ethics: No emotional/legal/medical judgments
- ✅ Completion Definition: Files + folders + logs + verification
- ✅ Override Clause: STOP → WARN → DO NOT PROCEED

---

### 2. Workflow Infrastructure Created
**Files**: `Inbox/`, `Needs_Action/`, `Plans/`, `Pending_Approval/`, `Approved/`, `Rejected/`, `Done/`, `Logs/`, `WORKFLOW.md`
**Commit**: 7207c58

**Workflow Folders Established:**
```
📥 /Inbox           → Entry point for new tasks
⚡ /Needs_Action    → Validated tasks ready for planning
📋 /Plans           → Active planning and design
🔍 /Pending_Approval → Human approval queue (HITL)
✅ /Approved        → Approved tasks ready for execution
❌ /Rejected        → Rejected or failed tasks
✔️  /Done           → Successfully completed tasks
📊 /Logs            → Append-only audit trail
```

**State Transitions Defined:**
```
Inbox → Needs_Action → Plans → Pending_Approval → [Approved|Rejected] → Done
```

---

### 3. SDD Agent Infrastructure Created
**Files**: `.claude/agents/sdd-*/AGENT.md`
**Commit**: 8b62e17

**13 Autonomous Agents Created:**
- sdd-specify, sdd-plan, sdd-tasks, sdd-implement, sdd-git-commit-pr
- sdd-clarify, sdd-adr, sdd-phr, sdd-constitution, sdd-analyze
- sdd-checklist, sdd-reverse-engineer, sdd-taskstoissues

**Each agent includes:**
- Complete documentation with workflows
- When to use criteria
- Execution strategies
- Error handling
- Integration points
- Example workflows

---

### 4. Feature Specifications Created
**Files**: `Plans/01-file-control-plane.md`, `Plans/02-logging-infrastructure.md`, `Plans/03-mcp-integration.md`, `Plans/04-persistence-loop.md`
**Commit**: 07b4778

**4 Priority Specifications:**

**P1 - File-Driven Control Plane**
- Folder-based state machine
- File moves as state transitions
- Sensitive action approval
- State verification and recovery

**P2 - Logging Infrastructure**
- Append-only audit trail
- Structured JSON logging
- Log integrity verification
- Query and analysis capabilities

**P3 - MCP Integration Layer**
- MCP server registry
- Secure credential management (keyring)
- Call auditing and sanitization
- Rate limiting and quotas

**P4 - Persistence Loop (Ralph Wiggum Rule)**
- Bounded iteration loop
- Progress checkpointing
- Retry with exponential backoff
- Explicit failure handling

---

## 📋 Next Steps: Implementation

### Phase 1: Foundation (Weeks 1-2)

**Goal**: Implement core file-driven control plane and logging

**Tasks**:
1. **File Control Plane** (Priority: P1)
   - [ ] Implement folder-based state machine
   - [ ] Create file move utilities (atomic operations)
   - [ ] Build approval checking system
   - [ ] Implement state verification
   - [ ] Add constitution violation detection
   - **Spec**: `Plans/01-file-control-plane.md`
   - **Next**: Run `/sp.plan` to create implementation plan

2. **Logging Infrastructure** (Priority: P2)
   - [ ] Set up append-only log system
   - [ ] Implement structured logging (JSON)
   - [ ] Create log integrity verification
   - [ ] Build log query interface
   - [ ] Add log rotation (daily)
   - **Spec**: `Plans/02-logging-infrastructure.md`
   - **Next**: Run `/sp.plan` to create implementation plan

**Success Criteria**:
- ✅ Tasks can move through workflow folders
- ✅ All transitions are logged
- ✅ Sensitive actions require approval
- ✅ Log integrity is verifiable

---

### Phase 2: External Communication (Weeks 3-4)

**Goal**: Secure external API access through MCP layer

**Tasks**:
3. **MCP Integration** (Priority: P3)
   - [ ] Create MCP server registry
   - [ ] Implement secure credential storage (keyring)
   - [ ] Add MCP call auditing
   - [ ] Implement rate limiting
   - [ ] Build quota monitoring
   - [ ] Add MCP health checks
   - **Spec**: `Plans/03-mcp-integration.md`
   - **Next**: Run `/sp.plan` to create implementation plan

**Success Criteria**:
- ✅ All external API calls go through MCP
- ✅ No credentials in vault or logs
- ✅ MCP calls are audited
- ✅ Rate limits are enforced

---

### Phase 3: Reliability (Weeks 5-6)

**Goal**: Task persistence and completion guarantees

**Tasks**:
4. **Persistence Loop** (Priority: P4)
   - [ ] Implement Ralph Wiggum persistence rule
   - [ ] Add bounded iteration loop
   - [ ] Create progress checkpointing
   - [ ] Implement retry with backoff
   - [ ] Add explicit failure handling
   - [ ] Build loop interruption handling
   - **Spec**: `Plans/04-persistence-loop.md`
   - **Next**: Run `/sp.plan` to create implementation plan

**Success Criteria**:
- ✅ No tasks silently abandoned
- ✅ All tasks reach /Done or /Rejected
- ✅ No infinite loops
- ✅ Resume after interruption works

---

## 🎯 Implementation Workflow

For each feature:

### Step 1: Planning
```bash
# Read the feature spec
cat Plans/01-file-control-plane.md

# Create implementation plan
/sp.plan Building with Python, using pathlib and watchdog for file operations

# Review plan
cat specs/1-file-control-plane/plan.md
```

### Step 2: Task Breakdown
```bash
# Generate implementation tasks
/sp.tasks

# Review tasks
cat specs/1-file-control-plane/tasks.md

# Optional: Create GitHub issues
/sp.taskstoissues
```

### Step 3: Implementation
```bash
# Execute tasks in phases
/sp.implement

# Or implement manually by phase:
# Phase 1: Setup
# Phase 2: Core implementation
# Phase 3: Testing
# Phase 4: Documentation
```

### Step 4: Validation
```bash
# Run quality analysis
/sp.analyze

# Create validation checklist
/sp.checklist "Create validation checklist for file-control-plane"

# Verify against constitution
grep "Constitutional Compliance" specs/1-file-control-plane/plan.md
```

### Step 5: Commit & Deploy
```bash
# Commit changes
/sp.git.commit_pr "Implement file-driven control plane"

# Create PR
# Human reviews and approves
# Merge to main
```

---

## 📊 Success Metrics

### Constitutional Compliance
- [ ] All external APIs go through MCP (Section 3)
- [ ] No secrets in vault or logs (Section 3)
- [ ] State reconstructable from files (Section 2)
- [ ] All actions logged (Section 8)
- [ ] Sensitive actions require approval (Section 6-7)
- [ ] Persistence loop prevents abandonment (Section 10)

### Functional Metrics
- [ ] 100% of state transitions logged
- [ ] 0 sensitive actions without approval
- [ ] 0 infinite loops
- [ ] 0 tasks silently abandoned
- [ ] Log integrity 100% verified
- [ ] MCP call success rate > 95%

### Performance Metrics
- [ ] State transitions < 100ms (p95)
- [ ] Log writes < 50ms (p95)
- [ ] MCP call overhead < 100ms
- [ ] Checkpoint writes < 100ms (p95)

---

## 🔒 Security Checklist

Before deployment, verify:

- [ ] No credentials in `.git` history
- [ ] No credentials in vault files
- [ ] No credentials in logs
- [ ] Credentials stored in system keyring
- [ ] TLS enforced for MCP communication
- [ ] Input validation on all external data
- [ ] Output sanitization in logs
- [ ] File permissions enforced (owner-only)
- [ ] Constitution override clause active

---

## 📚 Documentation Status

### ✅ Complete
- [x] Constitution (.specify/memory/constitution.md)
- [x] Workflow System (WORKFLOW.md)
- [x] Agent Documentation (.claude/agents/*/AGENT.md)
- [x] Feature Specifications (Plans/*.md)
- [x] Implementation Roadmap (this document)

### 🚧 In Progress
- [ ] Technical Plans (specs/*/plan.md) - Created via /sp.plan
- [ ] Task Lists (specs/*/tasks.md) - Created via /sp.tasks
- [ ] API Documentation - Created during implementation
- [ ] User Guide - Created after MVP

---

## 🎓 Learning & Iteration

After each feature implementation:

1. **Record PHR** (Prompt History Record)
   ```bash
   /sp.phr "Implemented file-control-plane: lessons learned and improvements"
   ```

2. **Create ADR** (Architecture Decision Record)
   ```bash
   /sp.adr "file-state-machine-design" "Document state machine implementation decisions"
   ```

3. **Update Constitution** (if needed)
   ```bash
   /sp.constitution "Update with new learnings from implementation"
   ```

---

## 🚀 MVP Definition

**Minimum Viable Product** consists of:

1. ✅ Constitution (complete)
2. ✅ Workflow folders (complete)
3. 🚧 File-Driven Control Plane (P1)
4. 🚧 Logging Infrastructure (P2)
5. ⏳ MCP Integration (P3)
6. ⏳ Persistence Loop (P4)

**MVP Success Criteria**:
- User can create task in /Inbox
- System validates and moves to /Needs_Action
- System plans and moves to /Pending_Approval
- Human approves by moving to /Approved
- System executes and moves to /Done
- All transitions are logged
- No sensitive actions without approval

**Target**: 6-8 weeks for MVP

---

## 📞 Support & Questions

**Constitution**: Reference `.specify/memory/constitution.md` for all governance
**Workflow**: Reference `WORKFLOW.md` for state management
**Agents**: Reference `.claude/agents/README.md` for agent capabilities
**Specs**: Reference `Plans/*.md` for feature details

---

*This roadmap ensures the Digital FTE is built according to constitutional principles: trustworthy, auditable, safe, and boringly reliable.*

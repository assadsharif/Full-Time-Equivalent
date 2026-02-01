# Obsidian Vault Structure Specification (P1)

**Feature Name**: Obsidian Vault Structure (Memory Layer)
**Priority**: P1 (Bronze Tier, Foundational)
**Status**: Draft
**Created**: 2026-01-28
**Last Updated**: 2026-01-28
**Owner**: AI Employee Hackathon Team
**Stakeholders**: All System Components

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Context and Background](#context-and-background)
3. [User Stories](#user-stories)
4. [Functional Requirements](#functional-requirements)
5. [Vault Structure](#vault-structure)
6. [File Naming Conventions](#file-naming-conventions)
7. [YAML Frontmatter Standards](#yaml-frontmatter-standards)
8. [Dashboard Design](#dashboard-design)
9. [Company Handbook Structure](#company-handbook-structure)
10. [State Flow Between Folders](#state-flow-between-folders)
11. [Constitutional Compliance](#constitutional-compliance)
12. [Implementation Phases](#implementation-phases)
13. [Success Metrics](#success-metrics)
14. [Appendix](#appendix)

---

## Executive Summary

### Problem Statement

The Digital FTE system requires a **centralized, human-readable memory layer** that:

- **Stores all task data** (incoming, in-progress, completed)
- **Maintains system configuration** (company handbook, policies)
- **Provides human oversight** (dashboard for monitoring)
- **Serves as source of truth** (all components read/write here)
- **Enables search and linking** (Obsidian graph view, backlinks)

Without a well-structured vault:
- **Data fragmentation** - tasks scattered across systems
- **No visibility** - humans can't see what AI is working on
- **Lost context** - AI can't reference past decisions
- **Difficult auditing** - no clear audit trail

### Proposed Solution

Design a **standardized Obsidian vault structure** with:

1. **Folder hierarchy** for state management (Inbox → Needs_Action → In_Progress → Done)
2. **Markdown file standards** (YAML frontmatter, consistent formatting)
3. **Dashboard.md** for human monitoring and control
4. **Company_Handbook.md** for AI context and policies
5. **Clear naming conventions** for discoverability
6. **State flow rules** for task lifecycle management

### Key Benefits

| Benefit | Impact |
|---------|--------|
| **Human-Readable** | Non-technical users can read/edit tasks in Obsidian |
| **Source of Truth** | Single location for all system state |
| **Auditability** | Complete history in `/Done` folder |
| **Searchability** | Obsidian search, tags, backlinks |
| **Interoperability** | Plain text Markdown, no vendor lock-in |
| **Version Control** | Git-compatible for backups |

### Scope

**In Scope:**
- Folder structure design
- File naming conventions
- YAML frontmatter standards
- Dashboard.md template
- Company_Handbook.md template
- State flow rules (folder-based state machine)
- Metadata standards
- Obsidian configuration (.obsidian folder)

**Out of Scope:**
- Custom Obsidian plugins (use core plugins only)
- Advanced visualizations (graph view customization)
- Database integrations (keep it file-based)
- Real-time sync (Obsidian Sync) - use Git instead
- Encryption at rest (handled by OS-level encryption)

**Dependencies:**
- ✅ Obsidian installed (desktop app)
- ✅ Git for version control
- ⏳ P5: Watcher Scripts (write to Inbox)
- ⏳ P6: Orchestrator (move files between folders)

---

## Context and Background

### Architecture Context

The Obsidian Vault is the **central memory layer** of the Digital FTE:

```
┌─────────────────────────────────────────────────────────────────┐
│                     External World                               │
│  (Gmail, WhatsApp, File System)                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Perception Layer (Watchers)                                     │
│  - Gmail Watcher                                                 │
│  - WhatsApp Watcher                                              │
│  - File System Watcher                                           │
└────────────────────┬────────────────────────────────────────────┘
                     │ Write Markdown
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  OBSIDIAN VAULT (Memory Layer) ◄── THIS SPEC                   │
│                                                                  │
│  /Inbox/              ← New tasks from watchers                 │
│  /Needs_Action/       ← Tasks ready for processing              │
│  /In_Progress/        ← Tasks being worked on                   │
│  /Done/               ← Completed tasks                          │
│  /Approvals/          ← Pending human approvals                 │
│  /Briefings/          ← Weekly CEO briefings                    │
│  /Attachments/        ← Files, images, documents                │
│  /Templates/          ← Task and note templates                 │
│  Dashboard.md         ← Human control center                    │
│  Company_Handbook.md  ← AI context and policies                │
│                                                                  │
└────────────────────┬────────────────────────────────────────────┘
                     │ Read Markdown
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Reasoning Layer (Claude Code)                                   │
│  - Read tasks from vault                                         │
│  - Update task status                                            │
│  - Reference Company_Handbook.md                                │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Human Oversight (Obsidian GUI)                                  │
│  - View Dashboard.md                                             │
│  - Approve actions in /Approvals                                │
│  - Monitor /In_Progress                                          │
└─────────────────────────────────────────────────────────────────┘
```

### Constitutional Principles

| Section | Requirement | Vault Compliance |
|---------|-------------|------------------|
| **Section 2: Source of Truth** | Obsidian vault is authoritative | ✅ All state stored in vault |
| **Section 3: Privacy First** | No PII in public repos | ✅ Vault is local, not synced publicly |
| **Section 4: Frozen Control Plane** | No modifications to frozen code | ✅ Vault is data layer, not code |
| **Section 8: Auditability** | All actions logged | ✅ `/Done` folder is audit trail |

### Hackathon Tier Alignment

| Tier | Vault Requirements | Estimated Time |
|------|-------------------|----------------|
| **Bronze** | Basic structure (Inbox, Needs_Action, Done), Dashboard.md, Company_Handbook.md | 1-2 hours |
| **Silver** | Full structure (all folders), templates, metadata standards | 2-3 hours |
| **Gold** | Advanced features (tags, links, search patterns) | 1-2 hours |

---

## User Stories

### US1: Initialize Vault Structure (Bronze Tier)

**As a** system operator
**I want** to create a standardized Obsidian vault structure
**So that** all system components have a consistent memory layer

**Acceptance Criteria:**
- [ ] Vault initialized via `fte vault init` command
- [ ] Required folders created: `/Inbox`, `/Needs_Action`, `/In_Progress`, `/Done`, `/Attachments`
- [ ] `Dashboard.md` created with monitoring template
- [ ] `Company_Handbook.md` created with policy template
- [ ] `.obsidian` folder configured (core plugins enabled)
- [ ] `.gitignore` configured (exclude `.obsidian/workspace.json`)

**Example Command:**

```bash
# Initialize vault
fte vault init --path ~/AI_Employee_Vault

# Output:
# ✅ Vault initialized: /Users/user/AI_Employee_Vault
# 📁 Created folders:
#    - Inbox
#    - Needs_Action
#    - In_Progress
#    - Done
#    - Approvals
#    - Briefings
#    - Attachments
#    - Templates
# 📄 Created files:
#    - Dashboard.md
#    - Company_Handbook.md
# ⚙️  Configured Obsidian (.obsidian/)
# 🔒 Configured Git (.gitignore)
```

**Vault Structure After Initialization:**

```
AI_Employee_Vault/
├── .obsidian/
│   ├── app.json           # Obsidian settings
│   ├── appearance.json    # Theme settings
│   ├── core-plugins.json  # Enabled core plugins
│   └── workspace.json     # Current workspace (gitignored)
├── .gitignore
├── Inbox/
├── Needs_Action/
├── In_Progress/
├── Done/
├── Approvals/
├── Briefings/
├── Attachments/
├── Templates/
│   ├── task_template.md
│   └── approval_template.md
├── Dashboard.md
└── Company_Handbook.md
```

**Test Cases:**
1. **TC1.1**: Run `fte vault init` → verify all folders created
2. **TC1.2**: Open vault in Obsidian → verify Dashboard.md opens
3. **TC1.3**: Check `.gitignore` → verify `.obsidian/workspace.json` excluded
4. **TC1.4**: Run `fte vault init` twice → verify error (vault already exists)
5. **TC1.5**: Run `fte vault status` → verify vault health check passes

---

### US2: Dashboard Monitoring (Bronze Tier)

**As a** system operator
**I want** a Dashboard.md file that shows system status at a glance
**So that** I can monitor the AI Employee without running CLI commands

**Acceptance Criteria:**
- [ ] Dashboard.md includes task count summary (Inbox, Needs_Action, In_Progress)
- [ ] Dashboard includes recent activity log (last 10 tasks completed)
- [ ] Dashboard includes system health indicators (watchers, orchestrator, MCP servers)
- [ ] Dashboard auto-updates on file change (Obsidian live preview)
- [ ] Dashboard includes quick action links (approve tasks, view briefings)

**Dashboard.md Template:**

```markdown
# 🤖 AI Employee Dashboard

**Last Updated:** 2026-01-28 10:30:00

---

## 📊 Task Summary

| Folder | Count | Oldest Task |
|--------|-------|-------------|
| 📥 Inbox | 3 | gmail_client_2026-01-28T09-00-00.md (1h ago) |
| ⚡ Needs_Action | 5 | file_Contract_v2_2026-01-27T14-00-00.md (20h ago) |
| 🔄 In_Progress | 2 | gmail_ceo_2026-01-28T10-00-00.md (30m ago) |
| ✅ Done (Today) | 12 | - |

**Total Pending:** 10 tasks
**Avg Response Time (7d):** 2.3 hours

---

## 🚦 System Health

| Component | Status | Last Checked |
|-----------|--------|--------------|
| 👁️ Gmail Watcher | ✅ Running | 10:29:45 |
| 👁️ WhatsApp Watcher | ✅ Running | 10:29:50 |
| 👁️ File Watcher | ✅ Running | 10:29:55 |
| 🎯 Orchestrator | ✅ Running | 10:30:00 (processing task) |
| 🔌 MCP Servers | ⚠️ 2/3 active | 10:29:30 (email-mcp offline) |

**Uptime:** 99.8% (7d)
**Errors (24h):** 2 (network timeouts)

---

## 📋 Recent Activity

| Time | Task | Action | Status |
|------|------|--------|--------|
| 10:15 | gmail_client_2026-01-28T10-15-00 | Email response drafted | ✅ Done |
| 10:00 | whatsapp_1234567890_2026-01-28T10-00-00 | Customer inquiry answered | ✅ Done |
| 09:45 | file_Invoice_2026-01-28T09-45-00 | Invoice processed | ✅ Done |
| 09:30 | gmail_legal_2026-01-28T09-30-00 | Contract review requested | ⏳ Awaiting approval |
| 09:00 | gmail_ceo_2026-01-28T09-00-00 | Board prep started | 🔄 In Progress |

---

## ⚠️ Needs Attention

### High Priority (Urgent Deadlines)
- [[Needs_Action/gmail_ceo_2026-01-28T09-00-00|Board meeting prep]] (due in 23h)
- [[Needs_Action/gmail_legal_2026-01-27T14-00-00|Contract review]] (due in 2h)

### Pending Approvals (3)
- [[Approvals/PAYMENT_Client_A_2026-01-28|Payment to Client A]] ($5,000 wire transfer)
- [[Approvals/EMAIL_Legal_2026-01-28|External email to legal firm]] (contract negotiation)
- [[Approvals/FILE_DELETE_Archive_2026-01-28|Delete archived files]] (cleanup old contracts)

### Failed Tasks (2)
- [[Done/gmail_client_2026-01-27T16-00-00|Client inquiry]] (retry #3 failed, escalated to human)

---

## 🎯 Quick Actions

- [[Approvals/|📝 Review Pending Approvals]]
- [[Briefings/|📊 View Weekly Briefings]]
- [[Needs_Action/|⚡ View Tasks Needing Action]]
- [[Done/|✅ View Completed Tasks]]
- [[Company_Handbook|📖 View Company Handbook]]

---

## 📈 Weekly Trends

```
Task Volume (Past 4 Weeks):
Week 1: 35 tasks
Week 2: 38 tasks (+9%)
Week 3: 41 tasks (+8%)
Week 4: 47 tasks (+15%)

Trend: ↗️ Consistent growth, consider scaling resources
```

---

## 🛠️ System Commands

```bash
# Restart watchers
fte watcher restart --all

# Check orchestrator status
fte orchestrator status

# Generate weekly briefing
fte briefing --week last

# Emergency stop (pause orchestrator)
fte orchestrator stop
```

---

**Dashboard Generated:** Via `fte vault update-dashboard` (run every 5 minutes)
```

**Test Cases:**
1. **TC2.1**: Open Dashboard.md in Obsidian → verify all sections render
2. **TC2.2**: Dashboard shows correct task counts (match folder contents)
3. **TC2.3**: Click approval link → opens `/Approvals` folder
4. **TC2.4**: Dashboard updates automatically (file watcher)
5. **TC2.5**: Dashboard readable on mobile (Obsidian mobile app)

---

### US3: Company Handbook (Bronze Tier)

**As an** AI Employee (Claude)
**I want** a Company_Handbook.md with policies and context
**So that** I can make decisions aligned with company values

**Acceptance Criteria:**
- [ ] Company_Handbook.md includes company mission and values
- [ ] Handbook includes decision-making guidelines
- [ ] Handbook includes approval thresholds (payment amounts, external communications)
- [ ] Handbook includes common scenarios and responses
- [ ] Handbook is referenced by Claude in task planning

**Company_Handbook.md Template:**

```markdown
# 📖 Company Handbook

**For:** AI Employee (Digital FTE)
**Last Updated:** 2026-01-28
**Version:** 1.0

---

## 🎯 Mission & Values

### Company Mission
> To deliver exceptional service to our clients through innovation, integrity, and responsiveness.

### Core Values
1. **Customer First:** Prioritize customer needs and satisfaction above all else.
2. **Integrity:** Operate with honesty and transparency in all interactions.
3. **Excellence:** Strive for the highest quality in every task.
4. **Collaboration:** Work seamlessly with human colleagues and clients.
5. **Continuous Improvement:** Learn from every interaction and optimize processes.

---

## 🤖 AI Employee Role

### Your Purpose
You are the Digital Full-Time Equivalent (FTE) AI Employee. Your role is to:
- **Monitor** incoming tasks from Gmail, WhatsApp, and file system
- **Analyze** task requirements and determine appropriate actions
- **Execute** approved actions via MCP servers
- **Report** on activities and performance
- **Escalate** complex or high-risk tasks to human operators

### Your Constraints
- **Human-in-the-Loop:** Always request approval for dangerous actions (payments, external emails, file deletions)
- **Privacy First:** Never log or expose PII (personally identifiable information)
- **Constitutional Compliance:** Follow all principles in `.specify/memory/constitution.md`
- **Transparency:** Explain reasoning and provide audit trails

---

## 💰 Approval Thresholds

### Financial Actions
| Action | Threshold | Approval Required |
|--------|-----------|-------------------|
| Payment (wire transfer) | > $1,000 | ✅ Yes |
| Payment (invoice processing) | > $500 | ✅ Yes |
| Refund to customer | > $200 | ✅ Yes |
| Purchase request | > $100 | ✅ Yes |
| Budget allocation | Any amount | ✅ Yes |

### Communications
| Action | Threshold | Approval Required |
|--------|-----------|-------------------|
| Internal email (to team@company.com) | Any | ❌ No (auto-send) |
| External email (to clients) | High risk topics | ✅ Yes |
| Email with attachments | Any | ✅ Yes |
| WhatsApp customer response | Standard inquiries | ❌ No |
| WhatsApp escalation | Complex issues | ✅ Yes |

### File Operations
| Action | Threshold | Approval Required |
|--------|-----------|-------------------|
| Read file | Any | ❌ No |
| Create new file | Any | ❌ No |
| Modify existing file | Critical files | ✅ Yes |
| Delete file | Any | ✅ Yes |
| Move to archive | Non-critical | ❌ No |

---

## 📋 Common Scenarios & Responses

### Scenario 1: Customer Inquiry (Product Availability)
**Example:** "Do you have Product X in stock?"

**Your Response:**
1. Check inventory system (via MCP server)
2. If in stock: "Yes, Product X is available. We have [quantity] units in stock. Would you like to place an order?"
3. If out of stock: "Product X is currently out of stock. Expected restock date: [date]. Would you like us to notify you when it's available?"
4. Log interaction in vault

**Approval Required:** ❌ No (standard inquiry)

---

### Scenario 2: Payment Request
**Example:** "Please process payment of $5,000 to Vendor A for invoice #12345."

**Your Response:**
1. Verify invoice details (vendor, amount, invoice number)
2. Generate approval request in `/Approvals/PAYMENT_Vendor_A_2026-01-28.yaml`
3. Wait for human approval
4. If approved: Execute payment via MCP server
5. If rejected: Notify requester of rejection reason
6. Log outcome in vault

**Approval Required:** ✅ Yes (> $1,000)

---

### Scenario 3: Contract Review
**Example:** "Please review the attached contract and highlight key terms."

**Your Response:**
1. Extract text from PDF attachment (OCR if needed)
2. Identify: parties, duration, payment terms, termination clauses
3. Generate summary in Markdown with key points highlighted
4. Flag any unusual clauses for legal review
5. Save summary to `/Done/contract_review_[client]_[date].md`

**Approval Required:** ❌ No (analysis only, no external actions)

---

### Scenario 4: Urgent Deadline (< 2 hours)
**Example:** Email from CEO: "Need Q4 report by 2 PM today (in 1 hour)."

**Your Response:**
1. Immediately prioritize task (move to front of queue)
2. Analyze requirements and determine if achievable
3. If achievable: Start work, provide progress updates every 15 minutes
4. If not achievable: Escalate to human immediately with explanation
5. Log all actions with timestamps

**Approval Required:** ❌ No (time-sensitive, standard analysis)

---

### Scenario 5: Ambiguous Request
**Example:** "Handle the client situation."

**Your Response:**
1. Do NOT guess or assume
2. Ask clarifying questions:
   - Which client?
   - What situation are you referring to?
   - What outcome do you want?
3. Wait for clarification before proceeding
4. Log ambiguous request for training data

**Approval Required:** N/A (clarification needed first)

---

## 🚨 Escalation Guidelines

### When to Escalate to Human

**Immediately escalate if:**
- Legal risk (lawsuits, compliance violations, contracts)
- Reputational risk (negative PR, public criticism)
- Financial risk (> $10,000, fraudulent activity)
- Security risk (data breach, unauthorized access)
- Ambiguous instructions (cannot determine intent)
- Ethical concerns (request conflicts with values)

**How to Escalate:**
1. Create task file in `/Needs_Human_Review/`
2. Tag with `#escalation` and `#urgent`
3. Send notification via email/Slack (if configured)
4. Do NOT proceed with task until human responds

---

## 🎓 Learning & Improvement

### Feedback Loop
- Review weekly briefings for patterns and bottlenecks
- Identify common tasks that could be automated further
- Request policy updates when guidelines are unclear
- Track approval rejection reasons to improve future requests

### Performance Metrics
- Response time (target: < 2 hours for standard tasks)
- Approval request accuracy (target: > 95% approval rate)
- Escalation rate (target: < 10% of tasks)
- Customer satisfaction (tracked via feedback forms)

---

## 📞 Contact Information

### Human Operators
- **Primary:** operations@company.com
- **Escalations:** manager@company.com
- **Technical Issues:** tech@company.com

### Emergency Stop
If AI Employee is behaving unexpectedly:
```bash
fte orchestrator stop
```
This creates a `.claude_stop` file that pauses autonomous operation.

---

**Handbook Maintained By:** Operations Team
**Review Frequency:** Quarterly (or as needed)
**Next Review:** 2026-04-01
```

**Test Cases:**
1. **TC3.1**: Claude references Company_Handbook.md during task planning
2. **TC3.2**: Approval thresholds correctly enforced (payment > $1,000 requires approval)
3. **TC3.3**: Escalation guidelines followed (legal risk → immediate escalation)
4. **TC3.4**: Handbook accessible via Dashboard.md link
5. **TC3.5**: Handbook version controlled in Git (track changes)

---

### US4: Task State Flow (Silver Tier)

**As a** system component
**I want** clear rules for moving tasks between folders
**So that** task lifecycle is consistent and auditable

**Acceptance Criteria:**
- [ ] Tasks move through folders in defined order: Inbox → Needs_Action → In_Progress → Done
- [ ] State transitions logged in YAML frontmatter (state, timestamps)
- [ ] Invalid state transitions prevented (e.g., Inbox → Done directly)
- [ ] Human can manually move files (overrides automation if needed)
- [ ] State transition history preserved in frontmatter

**State Flow Diagram:**

```
                    ┌─────────────┐
                    │   INBOX     │
                    │  (New tasks │
                    │ from watchers)│
                    └──────┬──────┘
                           │
                           │ Watcher writes task
                           ▼
                    ┌─────────────┐
                    │NEEDS_ACTION │
                    │ (Ready for  │
                    │ processing) │
                    └──────┬──────┘
                           │
                           │ Orchestrator picks task
                           ▼
                    ┌─────────────┐
                    │IN_PROGRESS  │
                    │  (Claude    │
                    │  working)   │
                    └──────┬──────┘
                           │
                  ┌────────┴────────┐
                  │                 │
        Approval  │                 │ No approval
        required? │                 │ needed
                  ▼                 │
           ┌─────────────┐          │
           │ APPROVALS   │          │
           │  (Pending   │          │
           │  human OK)  │          │
           └──────┬──────┘          │
                  │                 │
                  │ Approved        │
                  └────────┬────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    DONE     │
                    │ (Completed, │
                    │ audit trail)│
                    └─────────────┘
                           │
                           │ Error?
                           ▼
                    ┌─────────────┐
                    │ERROR_QUEUE  │
                    │  (Failed,   │
                    │ will retry) │
                    └──────┬──────┘
                           │
                           │ Max retries?
                           ▼
                    ┌─────────────┐
                    │   FAILED    │
                    │ (Permanent  │
                    │   failure)  │
                    └─────────────┘
```

**State Transition Rules:**

| From State | To State | Trigger | Validation |
|------------|----------|---------|------------|
| INBOX | NEEDS_ACTION | Watcher completes writing | YAML frontmatter valid |
| NEEDS_ACTION | IN_PROGRESS | Orchestrator starts task | Task not already in progress |
| IN_PROGRESS | APPROVALS | Claude needs approval | Approval request created |
| IN_PROGRESS | DONE | Task completed (no approval needed) | Status = success |
| APPROVALS | IN_PROGRESS | Human approves | approval_status = approved |
| APPROVALS | DONE | Human rejects | approval_status = rejected |
| IN_PROGRESS | ERROR_QUEUE | Task fails | Error logged |
| ERROR_QUEUE | NEEDS_ACTION | Retry scheduled | retry_count < max_retries |
| ERROR_QUEUE | FAILED | Max retries exceeded | retry_count >= max_retries |

**YAML Frontmatter State Tracking:**

```yaml
---
# State tracking
state: in_progress
state_history:
  - state: inbox
    timestamp: 2026-01-28T10:00:00Z
  - state: needs_action
    timestamp: 2026-01-28T10:00:05Z
    moved_by: watcher-gmail
  - state: in_progress
    timestamp: 2026-01-28T10:15:00Z
    moved_by: orchestrator

# Timestamps
created_at: 2026-01-28T10:00:00Z
started_at: 2026-01-28T10:15:00Z
completed_at: null  # Not completed yet

# Status
status: processing
error: null
retry_count: 0
---
```

**Test Cases:**
1. **TC4.1**: Task moves Inbox → Needs_Action → verify state updated in YAML
2. **TC4.2**: Task moves In_Progress → Approvals → verify approval request exists
3. **TC4.3**: Attempt invalid transition (Inbox → Done) → verify error logged
4. **TC4.4**: Task state_history includes all transitions with timestamps
5. **TC4.5**: Human manually moves file → verify system detects and logs manual override

---

### US5: File Naming Conventions (Silver Tier)

**As a** system component
**I want** standardized file naming conventions
**So that** files are sortable, searchable, and collision-free

**Acceptance Criteria:**
- [ ] File names include source, sender, and timestamp
- [ ] File names use ISO 8601 timestamps (sortable)
- [ ] File names sanitized (no special characters that break filesystems)
- [ ] File names unique (timestamp to the second)
- [ ] File names human-readable (not UUID hashes)

**Naming Pattern:**

```
<source>_<sender-identifier>_<timestamp>.md

Examples:
- gmail_ceo_2026-01-28T10-00-00.md
- whatsapp_1234567890_2026-01-28T10-15-30.md
- file_Contract_v2_2026-01-28T09-45-00.md
- approval_PAYMENT_Client_A_2026-01-28T10-30-00.yaml
```

**Components:**

1. **Source** (required): `gmail`, `whatsapp`, `file`, `manual`, `approval`, `briefing`
2. **Sender Identifier** (required):
   - Gmail: First part of email before `@` (sanitized)
   - WhatsApp: Last 4 digits of phone number
   - File: Filename stem (without extension)
   - Manual: Username of creator
3. **Timestamp** (required): ISO 8601 format with hyphens (not colons, which break Windows filesystems)
   - Format: `YYYY-MM-DDTHH-MM-SS`
   - Example: `2026-01-28T10-00-00`
4. **Extension** (required): `.md` for tasks, `.yaml` for approvals

**Sanitization Rules:**

```python
def sanitize_filename_component(text: str) -> str:
    """
    Sanitize text for use in filenames.

    Rules:
    - Replace spaces with underscores
    - Remove special characters: < > : " / \\ | ? *
    - Truncate to 50 characters max
    - Convert to lowercase (optional, for consistency)
    """
    import re

    # Replace spaces with underscores
    text = text.replace(' ', '_')

    # Remove invalid filesystem characters
    text = re.sub(r'[<>:"/\\|?*]', '', text)

    # Truncate to 50 chars
    text = text[:50]

    return text

# Examples:
# "CEO <ceo@company.com>" → "ceo"
# "John Doe" → "john_doe"
# "Contract v2 (Final).pdf" → "contract_v2_final"
```

**Test Cases:**
1. **TC5.1**: Generate filename with special characters → verify sanitized
2. **TC5.2**: Generate filename with timestamp → verify ISO 8601 format
3. **TC5.3**: Generate 100 filenames in same second → verify all unique (timestamp collision handling)
4. **TC5.4**: Files sortable by name (oldest first) → verify alphabetical sort = chronological sort
5. **TC5.5**: Filename readable by human → verify source and sender identifiable

---

## Functional Requirements

### FR1: Vault Initialization Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR1.1 | Create vault folder structure (8 folders) | P1 (Bronze) |
| FR1.2 | Create Dashboard.md from template | P1 (Bronze) |
| FR1.3 | Create Company_Handbook.md from template | P1 (Bronze) |
| FR1.4 | Configure Obsidian (.obsidian folder) | P1 (Bronze) |
| FR1.5 | Configure Git (.gitignore) | P1 (Bronze) |
| FR1.6 | Validate vault structure on startup | P2 (Silver) |

### FR2: Dashboard Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR2.1 | Display task count summary (all folders) | P1 (Bronze) |
| FR2.2 | Display system health indicators | P1 (Bronze) |
| FR2.3 | Display recent activity log (last 10 tasks) | P1 (Bronze) |
| FR2.4 | Display pending approvals count | P2 (Silver) |
| FR2.5 | Auto-update dashboard every 5 minutes | P2 (Silver) |

### FR3: State Management Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR3.1 | Move tasks between folders (state transitions) | P2 (Silver) |
| FR3.2 | Update YAML frontmatter on state change | P2 (Silver) |
| FR3.3 | Validate state transitions (prevent invalid moves) | P2 (Silver) |
| FR3.4 | Preserve state history in frontmatter | P2 (Silver) |
| FR3.5 | Handle manual file moves (human override) | P3 (Gold) |

### FR4: File Naming Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR4.1 | Generate unique filenames (source + sender + timestamp) | P2 (Silver) |
| FR4.2 | Sanitize filename components (remove special chars) | P2 (Silver) |
| FR4.3 | Handle timestamp collisions (add microseconds if needed) | P2 (Silver) |
| FR4.4 | Validate filename format before creation | P2 (Silver) |

---

## Vault Structure

### Complete Folder Hierarchy

```
AI_Employee_Vault/
├── .obsidian/                    # Obsidian configuration (auto-generated)
│   ├── app.json                  # App settings
│   ├── appearance.json           # Theme, font size
│   ├── core-plugins.json         # Enabled plugins
│   ├── hotkeys.json              # Keyboard shortcuts
│   └── workspace.json            # Current workspace (gitignored)
│
├── .git/                         # Git repository (version control)
├── .gitignore                    # Git ignore rules
│
├── Inbox/                        # New tasks from watchers (staging area)
│   ├── gmail_client_2026-01-28T09-00-00.md
│   ├── whatsapp_1234567890_2026-01-28T09-15-00.md
│   └── file_Invoice_2026-01-28T09-30-00.md
│
├── Needs_Action/                 # Tasks ready for processing (queue)
│   ├── gmail_ceo_2026-01-27T14-00-00.md
│   ├── gmail_legal_2026-01-27T16-00-00.md
│   └── file_Contract_v2_2026-01-28T08-00-00.md
│
├── In_Progress/                  # Tasks currently being worked on
│   ├── gmail_ceo_2026-01-28T10-00-00.md
│   └── whatsapp_customer_2026-01-28T10-15-00.md
│
├── Done/                         # Completed tasks (audit trail)
│   ├── gmail_client_2026-01-27T10-00-00.md
│   ├── gmail_client_2026-01-27T11-00-00.md
│   └── ... (hundreds of files, organized by completion date)
│
├── Approvals/                    # Pending human approvals (HITL)
│   ├── PAYMENT_Client_A_2026-01-28.yaml
│   ├── EMAIL_Legal_2026-01-28.yaml
│   └── FILE_DELETE_Archive_2026-01-28.yaml
│
├── Briefings/                    # Weekly CEO briefings
│   ├── 2026-01-29_Weekly_Briefing.md
│   ├── 2026-01-29_Weekly_Briefing.pdf
│   ├── 2026-01-22_Weekly_Briefing.md
│   └── 2026-01-22_Weekly_Briefing.pdf
│
├── Attachments/                  # Files, images, documents
│   ├── <message-id>/
│   │   ├── Q4_Budget.xlsx
│   │   ├── image.png
│   │   └── Contract_v2.pdf
│   └── ...
│
├── Templates/                    # Task and note templates
│   ├── task_template.md
│   ├── approval_template.yaml
│   └── briefing_template.md
│
├── Error_Queue/                  # Failed tasks (will retry)
│   ├── gmail_client_2026-01-27T16-00-00.md
│   └── ...
│
├── Failed/                       # Permanently failed tasks (max retries exceeded)
│   ├── gmail_client_2026-01-27T08-00-00.md
│   └── ...
│
├── Needs_Human_Review/           # Tasks requiring human intervention
│   ├── gmail_legal_escalation_2026-01-28.md
│   └── ...
│
├── Archive/                      # Old tasks (moved from Done after 90 days)
│   └── 2025/
│       ├── 12/
│       └── ...
│
├── Dashboard.md                  # System monitoring dashboard
├── Company_Handbook.md           # AI context and policies
└── README.md                     # Vault documentation
```

### Folder Purposes

| Folder | Purpose | Managed By | Retention |
|--------|---------|------------|-----------|
| **Inbox** | Staging for new tasks | Watchers | 1 hour (moved to Needs_Action) |
| **Needs_Action** | Task queue | Orchestrator | Until processed |
| **In_Progress** | Active tasks | Orchestrator + Claude | Until completed |
| **Done** | Completed tasks | Orchestrator | 90 days (then Archive) |
| **Approvals** | Pending approvals | Claude + Human | Until approved/rejected |
| **Briefings** | Weekly reports | Briefing Generator | Forever (or manually archived) |
| **Attachments** | Files, images | Watchers | Matches parent task lifecycle |
| **Templates** | Reusable templates | Manual | Forever |
| **Error_Queue** | Failed tasks (retrying) | Orchestrator | Until retry succeeds or max retries |
| **Failed** | Permanent failures | Orchestrator | Forever (manual review) |
| **Needs_Human_Review** | Escalations | Orchestrator | Until human reviews |
| **Archive** | Old completed tasks | Archive job (cron) | Forever (compressed) |

---

## File Naming Conventions

### Task Files

**Format:** `<source>_<sender>_<timestamp>.md`

**Examples:**
```
gmail_ceo_2026-01-28T10-00-00.md
gmail_client.a_2026-01-28T10-15-00.md
whatsapp_1234_2026-01-28T10-30-00.md  # Last 4 digits of phone
file_contract_v2_2026-01-28T10-45-00.md
manual_john_doe_2026-01-28T11-00-00.md
```

### Approval Files

**Format:** `<action-type>_<target>_<date>.yaml`

**Examples:**
```
PAYMENT_Client_A_2026-01-28.yaml
EMAIL_Legal_Firm_2026-01-28.yaml
FILE_DELETE_Old_Contracts_2026-01-28.yaml
MCP_INVOKE_Slack_Message_2026-01-28.yaml
```

### Briefing Files

**Format:** `<date>_<period>_Briefing.<ext>`

**Examples:**
```
2026-01-29_Weekly_Briefing.md
2026-01-29_Weekly_Briefing.pdf
2026-01-31_Monthly_Briefing.md
2026-03-31_Quarterly_Briefing.pdf
```

---

## YAML Frontmatter Standards

### Required Fields (All Tasks)

```yaml
---
# Identification
source: gmail  # gmail, whatsapp, file, manual
task_id: gmail_ceo_2026-01-28T10-00-00  # Unique ID (matches filename)
message_id: <msg-id-from-source>  # Optional, source-specific ID

# Content metadata
from: ceo@company.com
subject: "Board meeting prep"
priority: high  # high, medium, low
deadline: 2026-01-29T09:00:00Z  # ISO 8601, optional

# State tracking
state: in_progress  # inbox, needs_action, in_progress, approval_pending, done
status: processing  # pending, processing, waiting_approval, success, failed
state_history:
  - state: inbox
    timestamp: 2026-01-28T10:00:00Z
  - state: needs_action
    timestamp: 2026-01-28T10:00:05Z
    moved_by: watcher-gmail
  - state: in_progress
    timestamp: 2026-01-28T10:15:00Z
    moved_by: orchestrator

# Timestamps
created_at: 2026-01-28T10:00:00Z  # When task was created
started_at: 2026-01-28T10:15:00Z  # When Claude started working
completed_at: null  # When task was completed (null if in progress)

# Processing metadata
assigned_to: orchestrator  # Component handling task
retry_count: 0
last_error: null

# Labels and tags
labels: [INBOX, IMPORTANT]  # Source-specific labels (Gmail)
tags: [urgent, finance, board-prep]  # User-defined tags

# Attachments
attachments:
  - path: Attachments/gmail_ceo_2026-01-28T10-00-00/Q4_Budget.xlsx
    size: 524288
    type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
---
```

### Optional Fields (Source-Specific)

#### Gmail-Specific

```yaml
---
# Gmail-specific fields
labels: [INBOX, IMPORTANT, UNREAD]
thread_id: thread_abc123
cc: [colleague@company.com]
bcc: []
reply_to: ceo@company.com
---
```

#### WhatsApp-Specific

```yaml
---
# WhatsApp-specific fields
phone: +1234567890
message_type: text  # text, image, document, audio, video
media_url: https://...
---
```

#### File System-Specific

```yaml
---
# File system-specific fields
file_path: /Input_Documents/contracts/Contract_v2.pdf
file_size: 524288
file_type: application/pdf
file_hash: a1b2c3d4e5f6...
---
```

---

## Dashboard Design

(See US2 above for complete Dashboard.md template)

**Key Features:**
- Task count summary (all folders)
- System health indicators (watchers, orchestrator, MCP servers)
- Recent activity log (last 10 tasks)
- Pending approvals list
- Quick action links (navigate to folders)
- Weekly trends (task volume, response time)
- Emergency commands (restart, stop)

**Update Frequency:** Every 5 minutes via `fte vault update-dashboard`

---

## Company Handbook Structure

(See US3 above for complete Company_Handbook.md template)

**Key Sections:**
1. Mission & Values
2. AI Employee Role & Constraints
3. Approval Thresholds (financial, communications, file operations)
4. Common Scenarios & Responses (customer inquiries, payments, contracts, etc.)
5. Escalation Guidelines
6. Learning & Improvement
7. Contact Information

**Review Frequency:** Quarterly or as needed

---

## State Flow Between Folders

(See US4 above for complete state flow diagram and rules)

**Key Principles:**
- Tasks move through folders in defined order (Inbox → Needs_Action → In_Progress → Done)
- State transitions logged in YAML frontmatter
- Invalid transitions prevented (except manual override by human)
- Error handling: Failed tasks → Error_Queue → retry or Failed

---

## Constitutional Compliance

| Constitutional Section | Requirement | Vault Compliance |
|------------------------|-------------|------------------|
| **Section 2: Source of Truth** | Obsidian vault is authoritative | ✅ All system state in vault |
| **Section 3: Privacy First** | No PII in public repos | ✅ Vault local-only, gitignored workspace |
| **Section 4: Frozen Control Plane** | No code modifications | ✅ Vault is pure data layer |
| **Section 8: Auditability** | All actions logged | ✅ `/Done` folder = complete audit trail |

---

## Implementation Phases

### Phase 1: Vault Initialization (Bronze Tier) - 1-2 hours

**Deliverables:**
- [ ] CLI command: `fte vault init`
- [ ] Create folder structure (8 core folders)
- [ ] Dashboard.md template
- [ ] Company_Handbook.md template
- [ ] .obsidian configuration
- [ ] .gitignore configuration

**Acceptance Test:**
```bash
# Initialize vault
fte vault init --path ~/AI_Employee_Vault

# Verify structure
ls -la ~/AI_Employee_Vault/
# Expected: All 8 folders, Dashboard.md, Company_Handbook.md

# Open in Obsidian
open ~/AI_Employee_Vault/
# Expected: Obsidian opens, Dashboard.md displays
```

### Phase 2: State Management (Silver Tier) - 1-2 hours

**Deliverables:**
- [ ] State transition logic (move files between folders)
- [ ] YAML frontmatter updates on state change
- [ ] State validation (prevent invalid transitions)
- [ ] State history tracking

**Acceptance Test:**
```python
# Test state transition
task = Task(path="Inbox/task.md")
task.move_to_needs_action()

# Verify file moved
assert task.path == "Needs_Action/task.md"

# Verify YAML updated
assert task.metadata['state'] == 'needs_action'
assert len(task.metadata['state_history']) == 2
```

### Phase 3: Dashboard Auto-Update (Silver Tier) - 1 hour

**Deliverables:**
- [ ] Dashboard generator script
- [ ] Task count aggregation
- [ ] System health checks
- [ ] Cron job (update every 5 minutes)

**Acceptance Test:**
```bash
# Manually update dashboard
fte vault update-dashboard

# Verify Dashboard.md updated
cat Dashboard.md | grep "Task Summary"
# Expected: Current task counts displayed

# Schedule cron job
crontab -e
# Add: */5 * * * * /usr/local/bin/fte vault update-dashboard
```

---

## Success Metrics

### Bronze Tier (Minimum Viable)

- [ ] Vault structure initialized with 8 core folders
- [ ] Dashboard.md created with monitoring template
- [ ] Company_Handbook.md created with policy template
- [ ] Obsidian opens vault without errors
- [ ] Git repository initialized, .gitignore configured

### Silver Tier (Production Ready)

- [ ] Tasks move through folders correctly (Inbox → Needs_Action → In_Progress → Done)
- [ ] YAML frontmatter updated on state transitions
- [ ] State history preserved (audit trail)
- [ ] Dashboard auto-updates every 5 minutes
- [ ] File naming conventions followed (source + sender + timestamp)

### Gold Tier (Enterprise Grade)

- [ ] Manual file moves detected and logged
- [ ] Invalid state transitions prevented
- [ ] Dashboard includes system health indicators
- [ ] Company_Handbook referenced by Claude during task planning
- [ ] Vault backed up to Git daily

---

## Appendix

### A1: Task Template

```markdown
---
# Task metadata (YAML frontmatter)
source: gmail
task_id: gmail_example_2026-01-28T10-00-00
from: example@company.com
subject: "Example task"
priority: medium
state: needs_action
status: pending
created_at: 2026-01-28T10:00:00Z
---

# Email from example@company.com

**Subject:** Example task

**Body:**

[Email body content here]

---

**AI Employee Instructions:**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected Actions:**
- [ ] Action 1
- [ ] Action 2
- [ ] Action 3
```

### A2: Approval Template

```yaml
---
# Approval request metadata
task_id: gmail_example_2026-01-28T10-00-00
action_type: payment
risk_level: high
requested_at: 2026-01-28T10:30:00Z
approval_status: pending  # pending, approved, rejected
---

# Payment Request

**Amount:** $5,000
**Recipient:** Client A
**Purpose:** Invoice #12345 payment
**Account:** Company checking account
**Method:** Wire transfer

## Justification

Invoice #12345 for Q4 consulting services. Payment due date: 2026-01-30.

## Risks

- Financial risk: $5,000 outgoing transfer
- Reputational risk: Late payment if not processed

## Approval Required By

2026-01-29T17:00:00Z (COB Friday)

---

## Approval Section (Human completes)

**Approved By:** [Your name]
**Approved At:** [Timestamp]
**Approval Status:** [approved/rejected]
**Comments:** [Optional notes]
```

### A3: CLI Commands Reference

```bash
# Initialize vault
fte vault init --path ~/AI_Employee_Vault

# Check vault status
fte vault status

# Update dashboard
fte vault update-dashboard

# Validate vault structure
fte vault validate

# Archive old tasks (move Done → Archive)
fte vault archive --older-than 90d

# Search tasks
fte vault search "invoice" --folder Done

# List pending approvals
fte vault approvals --status pending

# Backup vault to Git
fte vault backup --message "Daily backup"

# Repair vault (fix missing folders, corrupted files)
fte vault repair
```

---

## Change Log

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-01-28 | v1.0 | AI Employee Team | Initial specification |

---

**Next Steps:**
1. Review spec with stakeholders
2. Initialize first vault using `/fte vault init`
3. Customize Company_Handbook.md for your organization
4. Begin Bronze Tier implementation (vault initialization, Dashboard, Handbook)

---

*This specification is part of the Personal AI Employee Hackathon 0 project. For related specs, see:*
- *[P2: Logging Infrastructure](../002-logging-infrastructure/spec.md)*
- *[P3: CLI Integration Roadmap](../003-cli-integration-roadmap/spec.md)*
- *[P5: Watcher Scripts](../005-watcher-scripts/spec.md)*
- *[P6: Orchestrator & Scheduler](../006-orchestrator-scheduler/spec.md)*
- *[P7: CEO Briefing](../007-ceo-briefing/spec.md)*

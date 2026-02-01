# HITL Approval Workflows Specification (P4)

**Feature Name**: Human-in-the-Loop (HITL) Approval Workflows
**Priority**: P4 (Silver Tier, Security Critical)
**Status**: Draft
**Created**: 2026-01-28
**Last Updated**: 2026-01-28
**Owner**: AI Employee Hackathon Team
**Stakeholders**: Security Team, Operations Team, Executive Leadership

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Context and Background](#context-and-background)
3. [User Stories](#user-stories)
4. [Functional Requirements](#functional-requirements)
5. [Approval Criteria](#approval-criteria)
6. [Approval File Format](#approval-file-format)
7. [Approval State Machine](#approval-state-machine)
8. [Approval UI Options](#approval-ui-options)
9. [Security Considerations](#security-considerations)
10. [Error Handling](#error-handling)
11. [Constitutional Compliance](#constitutional-compliance)
12. [Implementation Phases](#implementation-phases)
13. [Success Metrics](#success-metrics)
14. [Appendix](#appendix)

---

## Executive Summary

### Problem Statement

The Digital FTE AI Employee can execute **dangerous actions** (payments, emails, file deletions) autonomously. Without human oversight:

- **Financial risk**: AI could send unauthorized payments ($50,000 wire transfer)
- **Reputational risk**: AI could send embarrassing emails to clients or public
- **Data loss risk**: AI could delete critical files or contracts
- **Compliance risk**: Actions may violate company policies or regulations

Current state: No approval mechanism exists. AI either executes everything autonomously (unsafe) or requires manual execution (defeats autonomy).

### Proposed Solution

Implement **Human-in-the-Loop (HITL) Approval Workflows** where:

1. **Claude identifies dangerous actions** during task planning
2. **Approval request generated** in `/Approvals/<task-id>.yaml` file
3. **Orchestrator blocks MCP execution** until approval granted
4. **Human reviews and approves** via CLI, Obsidian, or web UI
5. **AI proceeds** only after explicit approval
6. **Audit trail preserved** (who approved what, when, why)

### Key Benefits

| Benefit | Impact |
|---------|--------|
| **Risk Mitigation** | Humans review dangerous actions before execution |
| **Accountability** | Clear audit trail of who approved what |
| **Flexibility** | Approval thresholds configurable per company |
| **Transparency** | Full context provided (what, why, risks) |
| **Compliance** | Meets regulatory requirements (SOX, GDPR, etc.) |

### Scope

**In Scope:**
- Approval criteria (what requires approval)
- Approval file format (YAML in `/Approvals` folder)
- Approval state machine (pending → approved/rejected)
- Approval UI (CLI, Obsidian integration)
- Timeout handling (24 hour default)
- Approval audit trail
- Security features (nonce-based replay protection, file integrity)

**Out of Scope:**
- Advanced approval workflows (multi-level approvals, voting)
- Mobile approval app (defer to P9)
- Slack/Teams integration for approvals (defer to P8)
- Delegated approvals (manager approval on behalf of others)
- Approval analytics dashboard (defer to P10)

**Dependencies:**
- ✅ P1: Obsidian Vault Structure (/Approvals folder)
- ✅ P2: Logging Infrastructure (approval logging)
- ✅ P3: CLI Integration (approval commands)
- ✅ P4: MCP Threat Model (approval enforcement)
- ✅ P6: Orchestrator (approval checking before MCP execution)

---

## Context and Background

### Architecture Context

The HITL Approval system sits between Claude's reasoning and MCP execution:

```
┌─────────────────────────────────────────────────────────────────┐
│  Perception Layer (Watchers)                                     │
│  New tasks arrive                                                │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Orchestrator                                                    │
│  - Pick task from queue                                          │
│  - Invoke Claude Code                                            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Reasoning Layer (Claude Code)                                   │
│  - Analyze task                                                  │
│  - Determine required actions                                    │
│  - Identify if actions are dangerous                            │
└────────────────────┬────────────────────────────────────────────┘
                     │
              ┌──────┴──────┐
              │ Dangerous?  │
              └──────┬──────┘
                     │
          ┌──────────┴──────────┐
          │ YES                 │ NO
          ▼                     ▼
┌──────────────────────┐ ┌──────────────────────┐
│ HITL APPROVAL        │ │ Execute Immediately  │
│ WORKFLOW             │ │                      │
│                      │ │ (Orchestrator calls  │
│ 1. Generate approval │ │  MCP directly)       │
│    request in        │ │                      │
│    /Approvals        │ └──────────────────────┘
│                      │
│ 2. Wait for human    │
│    (max 24h)         │
│                      │
│ 3. Human reviews in  │
│    Obsidian or CLI   │
│                      │
│ 4. Human approves or │
│    rejects           │
│                      │
│ 5. If approved:      │
│    proceed to MCP    │
│                      │
│    If rejected:      │
│    mark task done    │
│    (status=rejected) │
└──────────┬───────────┘
           │ Approved
           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Action Layer (MCP Servers)                                      │
│  - Execute approved action                                       │
│  - email-mcp, payment-mcp, filesystem-mcp, etc.                 │
└─────────────────────────────────────────────────────────────────┘
```

**Critical Invariant:** MCP servers MUST NEVER be called directly without approval check.

### Constitutional Principles

| Section | Requirement | HITL Compliance |
|---------|-------------|----------------|
| **Section 5: HITL for Dangerous Actions** | Human approval before risky operations | ✅ Core feature |
| **Section 8: Auditability** | All approvals logged | ✅ Audit trail in YAML + P2 logs |
| **Section 9: Error Recovery** | Graceful handling of timeouts | ✅ Timeout → escalation |

### Hackathon Tier Alignment

| Tier | HITL Requirements | Estimated Time |
|------|------------------|----------------|
| **Bronze** | Not required (manual execution) | 0 hours |
| **Silver** | Basic approval workflow (file-based, CLI) | 4-6 hours |
| **Gold** | Advanced features (timeout, audit, Obsidian UI) | 4-6 hours |

---

## User Stories

### US1: Generate Approval Request (Silver Tier)

**As** Claude Code
**I want** to generate approval requests for dangerous actions
**So that** humans can review before execution

**Acceptance Criteria:**
- [ ] Claude identifies dangerous actions during task analysis
- [ ] Approval request file created in `/Approvals/<task-id>.yaml`
- [ ] Request includes: action details, risks, justification, deadline
- [ ] Request includes unique nonce (prevent replay attacks)
- [ ] Orchestrator detects approval request and pauses MCP execution

**Example: Payment Approval Request**

Claude analyzes email:
```
From: ceo@company.com
Subject: "Please pay vendor invoice"
Body: "Pay Vendor A $5,000 for invoice #12345"
```

Claude generates `/Approvals/PAYMENT_Vendor_A_2026-01-28.yaml`:

```yaml
---
# Approval Request Metadata
task_id: gmail_ceo_2026-01-28T10-00-00
approval_id: PAYMENT_Vendor_A_2026-01-28
nonce: 7a9b3c4d-5e6f-7890-ab12-3456789abcde  # Prevents replay attacks

# Action Details
action_type: payment
action_category: financial
risk_level: high

# Request Details
requested_at: 2026-01-28T10:30:00Z
requested_by: claude-code
timeout_at: 2026-01-29T10:30:00Z  # 24 hours from request

# Approval Status
approval_status: pending  # pending, approved, rejected, timeout
approved_by: null
approved_at: null
rejection_reason: null

# Action Payload
action:
  type: wire_transfer
  recipient: Vendor A
  amount: 5000.00
  currency: USD
  account: Company Checking (****1234)
  purpose: Invoice #12345 payment
  invoice_file: /Attachments/gmail_ceo_2026-01-28T10-00-00/invoice_12345.pdf

# Justification
justification: |
  CEO requested payment for Invoice #12345 from Vendor A.
  Invoice due date: 2026-01-30.
  Payment is within standard vendor payment terms.

# Risk Assessment
risks:
  financial:
    amount: 5000.00
    reversible: false
    impact: medium
  reputational:
    impact: low
    rationale: Standard vendor payment, no reputation risk
  compliance:
    impact: low
    rationale: Within authorization limits (< $10,000)

# Expected Outcome
expected_outcome: |
  Wire transfer of $5,000 to Vendor A will be initiated.
  Payment confirmation will be emailed to finance@company.com.
  Invoice #12345 will be marked as paid in accounting system.

# Alternative Actions
alternatives:
  - action: Delay payment
    pros: More time to verify invoice details
    cons: May incur late payment fees, damage vendor relationship

  - action: Partial payment
    pros: Reduce financial risk
    cons: Vendor may not accept partial payment

# Context Links
related_files:
  - path: /In_Progress/gmail_ceo_2026-01-28T10-00-00.md
    description: Original task file
  - path: /Attachments/gmail_ceo_2026-01-28T10-00-00/invoice_12345.pdf
    description: Invoice document

# Company Handbook Reference
handbook_section: Financial Actions > Payment Threshold (> $1,000)
---

# Approval Request: Payment to Vendor A

## Summary
Request to pay Vendor A $5,000 for Invoice #12345 via wire transfer.

## Details
- **Amount:** $5,000.00 USD
- **Recipient:** Vendor A
- **Account:** Company Checking (****1234)
- **Purpose:** Invoice #12345 payment
- **Due Date:** 2026-01-30 (2 days from now)

## Justification
CEO authorized this payment via email. Invoice is for Q4 consulting services.
Payment is within standard vendor payment terms (Net 30).

## Risks
- **Financial:** $5,000 outgoing transfer (irreversible)
- **Reputational:** Low (standard vendor payment)
- **Compliance:** Low (within $10,000 authorization limit)

## Approval Required By
2026-01-29 10:30 AM (24 hours from request)

---

## For Human Reviewer

### Review Checklist
- [ ] Verify invoice #12345 is legitimate
- [ ] Verify Vendor A is in approved vendor list
- [ ] Verify amount matches invoice ($5,000)
- [ ] Verify CEO email is authentic (not spoofed)
- [ ] Verify payment terms (Net 30)

### To Approve
```bash
# Option 1: Edit this file
approval_status: approved
approved_by: john.doe@company.com
approved_at: 2026-01-28T11:00:00Z

# Option 2: Use CLI
fte approval approve PAYMENT_Vendor_A_2026-01-28
```

### To Reject
```bash
# Option 1: Edit this file
approval_status: rejected
rejection_reason: "Invoice not verified, need more details"

# Option 2: Use CLI
fte approval reject PAYMENT_Vendor_A_2026-01-28 --reason "Invoice not verified"
```
```

**Test Cases:**
1. **TC1.1**: Claude identifies dangerous action → approval request generated
2. **TC1.2**: Approval request includes nonce (prevents replay)
3. **TC1.3**: Approval request includes risk assessment
4. **TC1.4**: Orchestrator detects approval request, blocks MCP execution
5. **TC1.5**: Timeout set to 24 hours from request time

---

### US2: Review and Approve (Silver Tier)

**As a** human operator
**I want** to review and approve/reject dangerous actions
**So that** I maintain control over the AI Employee

**Acceptance Criteria:**
- [ ] Approval requests visible in `/Approvals` folder (Obsidian)
- [ ] CLI command available: `fte approval list --status pending`
- [ ] Approval can be granted via CLI or file edit
- [ ] Approval timestamp and approver identity captured
- [ ] Rejected approvals include rejection reason
- [ ] Approved actions proceed immediately to MCP execution

**CLI Workflow:**

```bash
# List pending approvals
$ fte approval list --status pending

# Output:
# Pending Approvals (3):
#
# 1. PAYMENT_Vendor_A_2026-01-28 (requested 30m ago)
#    Action: Wire transfer $5,000 to Vendor A
#    Risk: High (financial)
#    Timeout: 23h 30m
#
# 2. EMAIL_Legal_2026-01-28 (requested 1h ago)
#    Action: Send contract terms to external legal firm
#    Risk: Medium (external communication)
#    Timeout: 23h
#
# 3. FILE_DELETE_Archive_2026-01-28 (requested 2h ago)
#    Action: Delete 50 archived contract files
#    Risk: High (data loss)
#    Timeout: 22h

# View approval details
$ fte approval show PAYMENT_Vendor_A_2026-01-28

# Output:
# [Full YAML content displayed]

# Approve
$ fte approval approve PAYMENT_Vendor_A_2026-01-28

# Output:
# ✅ Approval granted: PAYMENT_Vendor_A_2026-01-28
# Approved by: john.doe@company.com
# Approved at: 2026-01-28T11:00:00Z
#
# Action will proceed immediately.
# Orchestrator will execute MCP action: payment-mcp.wire_transfer

# Reject
$ fte approval reject FILE_DELETE_Archive_2026-01-28 --reason "Need legal review first"

# Output:
# ❌ Approval rejected: FILE_DELETE_Archive_2026-01-28
# Rejected by: john.doe@company.com
# Rejected at: 2026-01-28T11:05:00Z
# Reason: "Need legal review first"
#
# Task will be moved to /Done with status "rejected".
```

**Obsidian Workflow:**

1. Open Obsidian, navigate to `/Approvals` folder
2. See pending approval files (colored by risk level)
3. Open approval file (e.g., `PAYMENT_Vendor_A_2026-01-28.yaml`)
4. Review action details, risks, justification
5. Edit YAML frontmatter:
   ```yaml
   approval_status: approved
   approved_by: john.doe@company.com
   approved_at: 2026-01-28T11:00:00Z
   ```
6. Save file
7. Orchestrator detects change within 5 seconds, proceeds with action

**Test Cases:**
1. **TC2.1**: `fte approval list` shows pending approvals
2. **TC2.2**: `fte approval approve` updates YAML, logs approval
3. **TC2.3**: `fte approval reject` updates YAML, moves task to /Done
4. **TC2.4**: Manual YAML edit detected by orchestrator within 5s
5. **TC2.5**: Approver identity captured (email from git config)

---

### US3: Timeout Handling (Gold Tier)

**As a** system operator
**I want** approval requests to timeout after 24 hours
**So that** tasks don't block indefinitely

**Acceptance Criteria:**
- [ ] Approval timeout configurable (default: 24 hours)
- [ ] Orchestrator checks timeout before waiting for approval
- [ ] Timed-out approvals moved to `/Needs_Human_Review`
- [ ] Notification sent on timeout (email/Slack)
- [ ] Timeout logs include original request and timeout duration

**Timeout Logic:**

```python
def check_approval_timeout(approval_file: Path) -> bool:
    """
    Check if approval request has timed out.

    Args:
        approval_file: Path to approval YAML file

    Returns:
        True if timed out, False otherwise
    """
    metadata = parse_yaml_frontmatter(approval_file)

    requested_at = datetime.fromisoformat(metadata['requested_at'])
    timeout_at = datetime.fromisoformat(metadata['timeout_at'])
    now = datetime.now(timezone.utc)

    if now >= timeout_at:
        logger.warning(
            f"Approval timeout: {approval_file.name}",
            context={
                'approval_id': metadata['approval_id'],
                'requested_at': requested_at.isoformat(),
                'timeout_at': timeout_at.isoformat(),
                'elapsed_hours': (now - requested_at).total_seconds() / 3600
            }
        )

        # Update approval status
        update_approval_status(
            approval_file,
            status='timeout',
            timeout_at=now.isoformat()
        )

        # Move task to /Needs_Human_Review
        move_task_to_needs_human_review(metadata['task_id'], reason='approval_timeout')

        # Send notification
        send_notification(
            channel='email',
            subject=f"Approval Timeout: {metadata['approval_id']}",
            body=f"Approval request timed out after 24 hours. Task moved to /Needs_Human_Review."
        )

        return True

    return False
```

**Test Cases:**
1. **TC3.1**: Approval timeout after 24 hours → status updated to "timeout"
2. **TC3.2**: Timed-out task moved to `/Needs_Human_Review`
3. **TC3.3**: Notification sent on timeout (email)
4. **TC3.4**: Timeout duration logged (24 hours)
5. **TC3.5**: Approval can still be granted after timeout (manual override)

---

### US4: Approval Audit Trail (Gold Tier)

**As a** compliance officer
**I want** a complete audit trail of all approvals
**So that** I can verify proper oversight for regulatory audits

**Acceptance Criteria:**
- [ ] All approval requests logged via P2 infrastructure
- [ ] All approval decisions logged (approved, rejected, timeout)
- [ ] Approver identity captured (email, username)
- [ ] Approval timestamp recorded (ISO 8601)
- [ ] Audit log queryable via P2 query service
- [ ] Audit log immutable (append-only)

**Audit Log Format:**

```json
{
  "timestamp": "2026-01-28T11:00:00Z",
  "level": "INFO",
  "logger": "approval_system",
  "event": "approval_granted",
  "approval_id": "PAYMENT_Vendor_A_2026-01-28",
  "task_id": "gmail_ceo_2026-01-28T10-00-00",
  "action_type": "payment",
  "risk_level": "high",
  "amount": 5000.00,
  "approved_by": "john.doe@company.com",
  "approved_at": "2026-01-28T11:00:00Z",
  "elapsed_time_minutes": 30,
  "context": {
    "request_time": "2026-01-28T10:30:00Z",
    "timeout_at": "2026-01-29T10:30:00Z",
    "recipient": "Vendor A",
    "purpose": "Invoice #12345 payment"
  }
}
```

**Query Examples:**

```bash
# Query all approvals in last 7 days
fte logs query --logger approval_system --days 7

# Query high-risk approvals
fte logs query --logger approval_system --filter "risk_level=high"

# Query approvals by specific approver
fte logs query --logger approval_system --filter "approved_by=john.doe@company.com"

# Query rejected approvals
fte logs query --logger approval_system --filter "event=approval_rejected"

# Query approval timeouts
fte logs query --logger approval_system --filter "event=approval_timeout"
```

**Test Cases:**
1. **TC4.1**: Approval request logged when created
2. **TC4.2**: Approval decision logged (approved/rejected)
3. **TC4.3**: Approver identity captured correctly
4. **TC4.4**: Audit log queryable via P2 query service
5. **TC4.5**: Audit log immutable (cannot be modified post-creation)

---

## Functional Requirements

### FR1: Approval Request Generation

| ID | Requirement | Priority |
|----|-------------|----------|
| FR1.1 | Identify dangerous actions during task analysis | P2 (Silver) |
| FR1.2 | Generate approval request YAML file | P2 (Silver) |
| FR1.3 | Include nonce for replay protection | P2 (Silver) |
| FR1.4 | Include risk assessment (financial, reputational, compliance) | P2 (Silver) |
| FR1.5 | Set timeout (default: 24 hours) | P3 (Gold) |

### FR2: Approval Review

| ID | Requirement | Priority |
|----|-------------|----------|
| FR2.1 | CLI command: `fte approval list --status pending` | P2 (Silver) |
| FR2.2 | CLI command: `fte approval show <approval-id>` | P2 (Silver) |
| FR2.3 | CLI command: `fte approval approve <approval-id>` | P2 (Silver) |
| FR2.4 | CLI command: `fte approval reject <approval-id> --reason "<reason>"` | P2 (Silver) |
| FR2.5 | Obsidian file edit detection (< 5s latency) | P3 (Gold) |

### FR3: Approval Enforcement

| ID | Requirement | Priority |
|----|-------------|----------|
| FR3.1 | Orchestrator checks approval status before MCP execution | P2 (Silver) |
| FR3.2 | Block MCP execution if approval_status != "approved" | P2 (Silver) |
| FR3.3 | Proceed immediately when approval granted | P2 (Silver) |
| FR3.4 | Move to /Done if approval rejected | P2 (Silver) |
| FR3.5 | Handle timeout (move to /Needs_Human_Review) | P3 (Gold) |

### FR4: Audit Trail

| ID | Requirement | Priority |
|----|-------------|----------|
| FR4.1 | Log approval request creation | P2 (Silver) |
| FR4.2 | Log approval decisions (approved, rejected, timeout) | P2 (Silver) |
| FR4.3 | Capture approver identity (email, username) | P2 (Silver) |
| FR4.4 | Queryable via P2 query service | P3 (Gold) |
| FR4.5 | Immutable audit log (append-only) | P3 (Gold) |

---

## Approval Criteria

### What Requires Approval?

Based on Company Handbook thresholds:

#### Financial Actions

| Action | Threshold | Approval Required |
|--------|-----------|-------------------|
| Wire transfer | > $1,000 | ✅ Yes |
| Invoice payment | > $500 | ✅ Yes |
| Customer refund | > $200 | ✅ Yes |
| Purchase request | > $100 | ✅ Yes |
| Budget reallocation | Any amount | ✅ Yes |

#### Communications

| Action | Risk Level | Approval Required |
|--------|-----------|-------------------|
| Internal email | Low | ❌ No |
| External email (client) | High-risk topics | ✅ Yes |
| Email with attachments | Any | ✅ Yes |
| WhatsApp customer response | Standard | ❌ No |
| WhatsApp escalation | Complex | ✅ Yes |
| Public social media post | Any | ✅ Yes |

#### File Operations

| Action | Risk Level | Approval Required |
|--------|-----------|-------------------|
| Read file | Low | ❌ No |
| Create new file | Low | ❌ No |
| Modify critical file | High | ✅ Yes |
| Delete file | Any | ✅ Yes |
| Move to archive | Low | ❌ No |

#### System Operations

| Action | Risk Level | Approval Required |
|--------|-----------|-------------------|
| Restart service | Medium | ✅ Yes |
| Update configuration | High | ✅ Yes |
| Modify database schema | High | ✅ Yes |
| Execute system command | High | ✅ Yes |
| Install dependencies | Medium | ✅ Yes |

### Risk Level Classification

```python
def calculate_risk_level(action: dict) -> str:
    """
    Calculate risk level for an action.

    Args:
        action: Action dictionary with type, parameters, context

    Returns:
        Risk level: "low", "medium", "high", "critical"
    """
    risk_score = 0

    # Financial risk
    if action.get('type') == 'payment':
        amount = action.get('amount', 0)
        if amount > 10000:
            risk_score += 30  # Critical
        elif amount > 5000:
            risk_score += 20  # High
        elif amount > 1000:
            risk_score += 10  # Medium

    # Destructive actions
    if action.get('destructive'):
        risk_score += 20

    # External communication
    if action.get('type') in ['email', 'api_call', 'webhook']:
        if action.get('external'):
            risk_score += 15

    # Data modification
    if action.get('type') in ['file_delete', 'database_update']:
        risk_score += 10

    # Classify risk level
    if risk_score >= 30:
        return 'critical'
    elif risk_score >= 20:
        return 'high'
    elif risk_score >= 10:
        return 'medium'
    else:
        return 'low'
```

---

## Approval File Format

### YAML Structure

```yaml
---
# === Metadata ===
task_id: gmail_ceo_2026-01-28T10-00-00
approval_id: PAYMENT_Vendor_A_2026-01-28
nonce: 7a9b3c4d-5e6f-7890-ab12-3456789abcde

# === Action ===
action_type: payment
action_category: financial
risk_level: high

# === Request Tracking ===
requested_at: 2026-01-28T10:30:00Z
requested_by: claude-code
timeout_at: 2026-01-29T10:30:00Z

# === Status ===
approval_status: pending  # pending, approved, rejected, timeout
approved_by: null
approved_at: null
rejected_by: null
rejected_at: null
rejection_reason: null

# === Action Payload ===
action:
  type: wire_transfer
  recipient: Vendor A
  amount: 5000.00
  currency: USD
  # ... (action-specific fields)

# === Risk Assessment ===
risks:
  financial:
    amount: 5000.00
    reversible: false
    impact: medium
  reputational:
    impact: low
  compliance:
    impact: low

# === Context ===
justification: |
  [Why this action is needed]

expected_outcome: |
  [What will happen if approved]

alternatives:
  - action: [Alternative 1]
    pros: [...]
    cons: [...]

related_files:
  - path: /In_Progress/task.md
    description: Original task

handbook_section: Financial Actions > Payment Threshold
---

# Human-readable content below YAML
```

### Naming Convention

**Format:** `<action-type>_<target>_<date>.yaml`

**Examples:**
- `PAYMENT_Vendor_A_2026-01-28.yaml`
- `EMAIL_Legal_Firm_2026-01-28.yaml`
- `FILE_DELETE_Old_Contracts_2026-01-28.yaml`
- `CONFIG_UPDATE_Approval_Threshold_2026-01-28.yaml`

---

## Approval State Machine

```
                    ┌──────────┐
                    │ PENDING  │
                    └────┬─────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          │ Human        │ Human        │ Timeout
          │ approves     │ rejects      │ (24h)
          ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ APPROVED │   │ REJECTED │   │ TIMEOUT  │
    └────┬─────┘   └────┬─────┘   └────┬─────┘
         │              │              │
         │ Proceed to   │ Move to      │ Move to
         │ MCP exec     │ /Done        │ /Needs_Human_Review
         ▼              ▼              ▼
    [MCP Action]   [Task Done]   [Escalation]
```

**State Descriptions:**

| State | Description | Next States | Actions |
|-------|-------------|-------------|---------|
| **PENDING** | Waiting for human review | APPROVED, REJECTED, TIMEOUT | Orchestrator blocks MCP |
| **APPROVED** | Human granted approval | (Terminal) | Orchestrator proceeds to MCP |
| **REJECTED** | Human rejected approval | (Terminal) | Task moved to /Done (status=rejected) |
| **TIMEOUT** | No response after 24h | (Terminal) | Task moved to /Needs_Human_Review |

---

## Approval UI Options

### Option 1: CLI (Bronze/Silver Tier)

**Pros:**
- Simple, no dependencies
- Scriptable (automation possible)
- Works over SSH

**Cons:**
- Not visual (no rich formatting)
- Requires terminal access

**Commands:**
```bash
fte approval list        # List pending approvals
fte approval show <id>   # Show approval details
fte approval approve <id> # Approve
fte approval reject <id> --reason "<reason>" # Reject
```

### Option 2: Obsidian (Silver/Gold Tier)

**Pros:**
- Visual, easy to read
- No additional tools needed (Obsidian already used)
- Supports rich formatting (Markdown)

**Cons:**
- Requires Obsidian desktop app
- Manual file editing (prone to errors)

**Workflow:**
1. Open Obsidian
2. Navigate to `/Approvals` folder
3. Open approval file
4. Edit YAML frontmatter: `approval_status: approved`
5. Save file

### Option 3: Web UI (Gold/Platinum Tier)

**Pros:**
- Best UX (buttons, forms, validation)
- Mobile-friendly
- Can include rich context (images, charts)

**Cons:**
- Requires web server (additional infrastructure)
- Security concerns (authentication, authorization)

**Future Implementation** (not in scope for Bronze/Silver/Gold tiers)

---

## Security Considerations

### SEC1: Nonce-Based Replay Protection

**Risk:** Attacker copies approved approval file, uses it again later

**Mitigation:**
1. Every approval request includes unique nonce (UUID)
2. Nonce tracked in database or file (prevent reuse)
3. If nonce already used, reject approval

**Example:**

```python
used_nonces = set()  # In production, use database or persistent file

def verify_approval_nonce(approval_file: Path) -> bool:
    """Verify approval nonce hasn't been used before."""
    metadata = parse_yaml_frontmatter(approval_file)
    nonce = metadata.get('nonce')

    if nonce in used_nonces:
        logger.error(f"Replay attack detected: nonce {nonce} already used")
        return False

    used_nonces.add(nonce)
    return True
```

### SEC2: File Integrity Verification

**Risk:** Attacker modifies approval file after approval granted

**Mitigation:**
1. Compute SHA256 hash of approval file when created
2. Store hash in separate integrity file
3. Before execution, verify hash matches
4. If mismatch, reject approval

**Example:**

```python
def compute_approval_hash(approval_file: Path) -> str:
    """Compute SHA256 hash of approval file."""
    import hashlib

    content = approval_file.read_bytes()
    return hashlib.sha256(content).hexdigest()

def verify_approval_integrity(approval_file: Path) -> bool:
    """Verify approval file hasn't been tampered with."""
    integrity_file = approval_file.with_suffix('.integrity')

    if not integrity_file.exists():
        logger.warning(f"Integrity file missing: {integrity_file}")
        return False

    expected_hash = integrity_file.read_text().strip()
    actual_hash = compute_approval_hash(approval_file)

    if expected_hash != actual_hash:
        logger.error(f"Integrity check failed: {approval_file}")
        return False

    return True
```

### SEC3: Approver Authorization

**Risk:** Unauthorized user approves high-risk action

**Mitigation:**
1. Approval requires authentication (git user.email or system user)
2. Check approver against authorized approvers list
3. Log unauthorized approval attempts
4. Reject approval if approver not authorized

**Example:**

```python
AUTHORIZED_APPROVERS = [
    'ceo@company.com',
    'coo@company.com',
    'finance.manager@company.com'
]

def verify_approver_authorization(approver_email: str, risk_level: str) -> bool:
    """Verify approver is authorized for risk level."""
    if risk_level in ['high', 'critical']:
        if approver_email not in AUTHORIZED_APPROVERS:
            logger.error(f"Unauthorized approver: {approver_email} (risk={risk_level})")
            return False

    return True
```

---

## Error Handling

### Error Scenarios

| Error | Handling |
|-------|----------|
| **Approval file missing** | Error logged, orchestrator waits (timeout eventually) |
| **Approval file malformed** | Error logged, approval rejected |
| **Nonce reused** | Replay attack detected, approval rejected |
| **Integrity check failed** | File tampering detected, approval rejected |
| **Approver unauthorized** | Unauthorized approver, approval rejected |
| **Timeout exceeded** | Move task to /Needs_Human_Review, send notification |

---

## Constitutional Compliance

| Constitutional Section | Requirement | HITL Compliance |
|------------------------|-------------|----------------|
| **Section 5: HITL for Dangerous Actions** | Human approval before risky operations | ✅ Core feature |
| **Section 8: Auditability** | All actions logged | ✅ Complete audit trail |
| **Section 9: Error Recovery** | Graceful degradation | ✅ Timeout handling, escalation |

---

## Implementation Phases

### Phase 1: Approval Request Generation (Silver Tier) - 2-3 hours

**Deliverables:**
- [ ] Approval request generation logic
- [ ] YAML file creation in `/Approvals`
- [ ] Nonce generation (UUID)
- [ ] Risk assessment calculation

**Acceptance Test:**
```python
# Test: Claude generates approval request
task = Task(path="In_Progress/payment_task.md")
approval = generate_approval_request(task, action={'type': 'payment', 'amount': 5000})

assert approval.file_path.exists()
assert approval.nonce is not None
assert approval.risk_level == 'high'
```

### Phase 2: CLI Approval Commands (Silver Tier) - 2-3 hours

**Deliverables:**
- [ ] `fte approval list` command
- [ ] `fte approval show <id>` command
- [ ] `fte approval approve <id>` command
- [ ] `fte approval reject <id> --reason "<reason>"` command

**Acceptance Test:**
```bash
# Test: CLI commands work
fte approval list
# Expected: Shows pending approvals

fte approval approve PAYMENT_Vendor_A_2026-01-28
# Expected: Approval granted, YAML updated
```

### Phase 3: Orchestrator Integration (Silver Tier) - 2 hours

**Deliverables:**
- [ ] Orchestrator checks approval status before MCP execution
- [ ] Block MCP execution if approval_status != "approved"
- [ ] Proceed immediately when approval granted

**Acceptance Test:**
```python
# Test: Orchestrator blocks MCP until approval
task = Task(path="In_Progress/payment_task.md")
orchestrator.execute_task(task)

# Orchestrator should wait for approval
assert orchestrator.is_waiting_for_approval(task)

# Approve
approve_action(task.approval_id)

# Orchestrator should proceed
assert orchestrator.has_executed_mcp(task)
```

### Phase 4: Timeout Handling (Gold Tier) - 1-2 hours

**Deliverables:**
- [ ] Timeout check (default: 24 hours)
- [ ] Move timed-out tasks to `/Needs_Human_Review`
- [ ] Send notification on timeout

**Acceptance Test:**
```python
# Test: Approval timeout after 24 hours
approval = ApprovalRequest(timeout_at=now() - timedelta(hours=25))

assert approval.is_timed_out()
assert approval.task_path.parent.name == "Needs_Human_Review"
```

### Phase 5: Audit Trail (Gold Tier) - 1 hour

**Deliverables:**
- [ ] Log all approval requests
- [ ] Log all approval decisions
- [ ] Queryable via P2 query service

**Acceptance Test:**
```bash
# Test: Audit trail queryable
fte logs query --logger approval_system --days 7

# Expected: Shows all approvals in last 7 days
```

---

## Success Metrics

### Silver Tier (Basic Approval Workflow)

- [ ] Approval requests generated for dangerous actions
- [ ] CLI commands functional (`list`, `show`, `approve`, `reject`)
- [ ] Orchestrator blocks MCP until approval granted
- [ ] Audit trail captured (logged via P2)
- [ ] Manual testing: 10 approval workflows (approve/reject) successful

### Gold Tier (Production Ready)

- [ ] Timeout handling operational (24 hour default)
- [ ] Timed-out tasks moved to `/Needs_Human_Review`
- [ ] Nonce-based replay protection implemented
- [ ] File integrity verification implemented
- [ ] Approver authorization checks implemented
- [ ] 100% of dangerous actions require approval (no bypasses)

---

## Appendix

### A1: Example Approval Files

#### Payment Approval

```yaml
---
task_id: gmail_ceo_2026-01-28T10-00-00
approval_id: PAYMENT_Vendor_A_2026-01-28
nonce: 7a9b3c4d-5e6f-7890-ab12-3456789abcde
action_type: payment
risk_level: high
requested_at: 2026-01-28T10:30:00Z
timeout_at: 2026-01-29T10:30:00Z
approval_status: pending

action:
  type: wire_transfer
  recipient: Vendor A
  amount: 5000.00
  currency: USD
---
```

#### Email Approval

```yaml
---
task_id: gmail_ceo_2026-01-28T11-00-00
approval_id: EMAIL_Legal_Firm_2026-01-28
nonce: 8b0c4d5e-6f7g-8901-bc23-4567890bcdef
action_type: email
risk_level: medium
requested_at: 2026-01-28T11:00:00Z
timeout_at: 2026-01-29T11:00:00Z
approval_status: pending

action:
  type: send_email
  to: legal@lawfirm.com
  subject: "Contract terms for review"
  body: |
    [Email body with contract terms]
  attachments:
    - Contract_Draft_v2.pdf
---
```

#### File Deletion Approval

```yaml
---
task_id: manual_cleanup_2026-01-28T12-00-00
approval_id: FILE_DELETE_Archive_2026-01-28
nonce: 9c1d5e6f-7g8h-9012-cd34-567890cdefgh
action_type: file_delete
risk_level: high
requested_at: 2026-01-28T12:00:00Z
timeout_at: 2026-01-29T12:00:00Z
approval_status: pending

action:
  type: delete_files
  files:
    - /Archive/contracts/2023/Contract_A.pdf
    - /Archive/contracts/2023/Contract_B.pdf
    # ... (50 files total)
  total_size: 52428800  # 50 MB
---
```

### A2: CLI Commands Reference

```bash
# List pending approvals
fte approval list --status pending

# List all approvals (any status)
fte approval list --all

# Show approval details
fte approval show <approval-id>

# Approve
fte approval approve <approval-id>

# Reject with reason
fte approval reject <approval-id> --reason "<reason>"

# Query approval history
fte logs query --logger approval_system --days 7

# Check approval status programmatically
fte approval status <approval-id>
# Output: pending, approved, rejected, timeout
```

---

## Change Log

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-01-28 | v1.0 | AI Employee Team | Initial specification |

---

**Next Steps:**
1. Review spec with security team
2. Generate implementation plan using `/sp.plan`
3. Generate task breakdown using `/sp.tasks`
4. Begin Silver Tier implementation (approval request generation, CLI commands)

---

*This specification is part of the Personal AI Employee Hackathon 0 project. For related specs, see:*
- *[P2: Logging Infrastructure](../002-logging-infrastructure/spec.md)*
- *[P3: CLI Integration Roadmap](../003-cli-integration-roadmap/spec.md)*
- *[P4: MCP Threat Model](../004-mcp-threat-model/spec.md)*
- *[P6: Orchestrator & Scheduler](../006-orchestrator-scheduler/spec.md)*
- *[P8: Obsidian Vault Structure](../008-obsidian-vault-structure/spec.md)*

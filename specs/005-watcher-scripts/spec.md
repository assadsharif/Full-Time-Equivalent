# Watcher Scripts Specification (P3)

**Feature Name**: Watcher Scripts (Perception Layer)
**Priority**: P3 (Post-MVP, Core System Component)
**Status**: Draft
**Created**: 2026-01-28
**Last Updated**: 2026-01-28
**Owner**: AI Employee Hackathon Team
**Stakeholders**: System Operators, End Users, Security Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Context and Background](#context-and-background)
3. [User Stories](#user-stories)
4. [Functional Requirements](#functional-requirements)
5. [Non-Functional Requirements](#non-functional-requirements)
6. [Technical Architecture](#technical-architecture)
7. [Data Models](#data-models)
8. [Security Considerations](#security-considerations)
9. [Error Handling and Recovery](#error-handling-and-recovery)
10. [Constitutional Compliance](#constitutional-compliance)
11. [Implementation Phases](#implementation-phases)
12. [Success Metrics](#success-metrics)
13. [Open Questions](#open-questions)
14. [Appendix](#appendix)

---

## Executive Summary

### Problem Statement

The Digital FTE (Full-Time Equivalent) AI Employee needs a perception layer to continuously monitor external data sources (Gmail, WhatsApp, file systems) and convert incoming information into structured Markdown files in the Obsidian vault. Without this perception layer, the AI Employee cannot:

- **Detect new tasks** from email or messaging platforms
- **Monitor file changes** for document processing
- **Maintain situational awareness** of the external environment
- **Operate autonomously** without manual data input

Current state: Manual data entry into Obsidian vault by human operators.

### Proposed Solution

Develop a suite of **Watcher Scripts** (Python daemons) that:

1. **Continuously monitor** external data sources (Gmail, WhatsApp, file system)
2. **Parse and structure** incoming data into Markdown format
3. **Write to Obsidian vault** in designated folders (`/Inbox`, `/Needs_Action`)
4. **Log all activities** using existing P2 logging infrastructure
5. **Recover gracefully** from errors without human intervention
6. **Respect constitutional constraints** (privacy, frozen code, additive only)

### Key Benefits

| Benefit | Impact |
|---------|--------|
| **Autonomous Perception** | AI Employee can detect tasks without human input |
| **Multi-Channel Monitoring** | Email, messaging, file system all integrated |
| **Structured Data Ingestion** | Raw data → clean Markdown for Claude reasoning |
| **24/7 Operation** | Daemon-based architecture with auto-restart |
| **Constitutional Compliance** | Privacy-preserving, audit-logged, secure |

### Scope

**In Scope:**
- Gmail watcher (OAuth2, PII redaction, attachments)
- File system watcher (inotify-based, recursive monitoring)
- WhatsApp watcher (WhatsApp Business API integration)
- Process management (PM2/supervisord configuration)
- Error recovery and retry logic
- Integration with P2 logging infrastructure
- CLI integration (`fte watcher start|stop|status|logs`)

**Out of Scope:**
- Real-time messaging protocols (WebSocket/SSE) - deferred to P5
- Multi-account support (Gmail/WhatsApp) - deferred to P4
- Browser automation for WhatsApp Web - security risk, not recommended
- Slack/Teams watchers - deferred to Gold tier extensions
- Natural language understanding within watchers - Claude handles reasoning

**Dependencies:**
- ✅ P1: Control Plane (frozen, audit logging)
- ✅ P2: Logging Infrastructure (async logging, query service)
- ⏳ P3: CLI Integration (US4: Watcher Lifecycle Management)
- ⏳ P4: MCP Security (credential management patterns)

---

## Context and Background

### Architecture Context

The Digital FTE follows a layered architecture:

```
┌─────────────────────────────────────────────────────────┐
│  External World (Gmail, WhatsApp, File System)         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Perception Layer (Watcher Scripts)  ◄── THIS SPEC     │
│  - Gmail Watcher                                         │
│  - WhatsApp Watcher                                      │
│  - File System Watcher                                   │
└────────────────────┬────────────────────────────────────┘
                     │ Write Markdown
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Memory Layer (Obsidian Vault)                          │
│  /Inbox → /Needs_Action → /In_Progress → /Done         │
└────────────────────┬────────────────────────────────────┘
                     │ Read Markdown
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Reasoning Layer (Claude Code)                          │
│  - Task understanding                                    │
│  - Decision making                                       │
│  - Action planning                                       │
└────────────────────┬────────────────────────────────────┘
                     │ Generate actions
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Human-in-the-Loop (HITL) Approval Layer               │
└────────────────────┬────────────────────────────────────┘
                     │ Approved actions
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Action Layer (MCP Servers)                             │
└─────────────────────────────────────────────────────────┘
```

**Watcher Responsibilities:**
1. **Polling**: Check external sources at configurable intervals (default: 30s)
2. **Parsing**: Extract structured data (sender, subject, body, attachments)
3. **Redaction**: Remove PII using detect-secrets patterns
4. **Formatting**: Convert to Markdown with YAML frontmatter
5. **Writing**: Atomic file operations to Obsidian vault
6. **Logging**: All events logged via P2 infrastructure
7. **Error Recovery**: Exponential backoff, retry logic, graceful degradation

### Constitutional Principles

This feature must comply with `.specify/memory/constitution.md`:

| Section | Requirement | Watcher Compliance |
|---------|-------------|-------------------|
| **Section 2: Source of Truth** | Obsidian vault is authoritative | ✅ Watchers write to vault, never modify existing files |
| **Section 3: Privacy First** | No PII in logs or public repos | ✅ PII redaction using detect-secrets |
| **Section 4: Frozen Control Plane** | No modifications to `src/control_plane/` | ✅ Watchers are additive in `src/watchers/` |
| **Section 8: Auditability** | All actions logged | ✅ P2 logging for all watcher events |
| **Section 9: Error Recovery** | Graceful degradation | ✅ Retry logic, exponential backoff |

### Hackathon Tier Alignment

| Tier | Watcher Requirements | Estimated Time |
|------|---------------------|----------------|
| **Bronze** | One working watcher (Gmail OR file system) | 4-6 hours |
| **Silver** | All three watchers (Gmail, WhatsApp, file system) | 8-12 hours |
| **Gold** | Advanced features (filtering, real-time, multi-account) | 12-16 hours |

---

## User Stories

### US1: Gmail Watcher (Bronze Tier)

**As a** system operator
**I want** the AI Employee to automatically detect new emails from Gmail
**So that** I don't have to manually copy emails into the Obsidian vault

**Acceptance Criteria:**
- [ ] Watcher authenticates with Gmail API using OAuth2
- [ ] New emails (unread, primary inbox only) are fetched every 30 seconds
- [ ] Each email is converted to Markdown with YAML frontmatter
- [ ] Emails are written to `/Inbox/<sender>_<timestamp>.md`
- [ ] PII (email addresses, phone numbers) is redacted from logs
- [ ] Attachments are downloaded to `/Attachments/<email-id>/`
- [ ] Watcher logs all activity to P2 logging infrastructure
- [ ] Watcher can be started/stopped via `fte watcher start gmail`

**Example Output:**

```markdown
---
source: gmail
message_id: 18d4a1b2c3d4e5f6
from: client@example.com
subject: "Urgent: Q4 Budget Review"
received_at: 2026-01-28T10:30:00Z
labels: [INBOX, IMPORTANT]
attachments: [Q4_Budget.xlsx]
status: needs_action
---

# Email from client@example.com

**Subject:** Urgent: Q4 Budget Review

**Body:**

Hi Team,

Please review the attached Q4 budget spreadsheet and provide feedback by EOD Friday. Pay special attention to the marketing allocation.

Thanks,
Client

**Attachments:**
- [Q4_Budget.xlsx](../../Attachments/18d4a1b2c3d4e5f6/Q4_Budget.xlsx)

---

**AI Employee Instructions:**
1. Download and analyze Q4_Budget.xlsx
2. Prepare summary of key changes vs Q3
3. Flag any anomalies in marketing allocation
4. Draft response email for approval
```

**Test Cases:**
1. **TC1.1**: Fetch 5 new unread emails, verify all written to `/Inbox`
2. **TC1.2**: Email with attachment → verify attachment downloaded
3. **TC1.3**: Email with phone number → verify PII redacted from logs
4. **TC1.4**: Gmail API rate limit → verify exponential backoff retry
5. **TC1.5**: Network failure → verify graceful degradation, no crash

---

### US2: File System Watcher (Bronze Tier)

**As a** system operator
**I want** the AI Employee to detect new files dropped into a monitored folder
**So that** I can trigger document processing workflows

**Acceptance Criteria:**
- [ ] Watcher monitors `/Input_Documents/` folder recursively
- [ ] New files trigger Markdown record creation in `/Inbox`
- [ ] File metadata (size, type, SHA256 hash) is captured
- [ ] Watcher uses `inotify` (Linux) or `FSEvents` (macOS) for efficiency
- [ ] File move/rename/delete events are logged but not actioned
- [ ] Watcher respects `.gitignore` patterns (ignore `.tmp`, `.swp`, etc.)
- [ ] Watcher can be started/stopped via `fte watcher start filesystem`

**Example Output:**

```markdown
---
source: filesystem
file_path: /Input_Documents/contracts/Service_Agreement_v3.pdf
file_name: Service_Agreement_v3.pdf
file_size: 524288
file_type: application/pdf
file_hash: a1b2c3d4e5f6...
detected_at: 2026-01-28T11:00:00Z
status: needs_action
---

# New File Detected: Service_Agreement_v3.pdf

**Location:** `/Input_Documents/contracts/`

**File Details:**
- Type: PDF
- Size: 512 KB
- SHA256: `a1b2c3d4e5f6...`

**AI Employee Instructions:**
1. Extract text from PDF using OCR if needed
2. Identify contract type (service agreement, NDA, etc.)
3. Extract key terms: parties, duration, payment, termination
4. Flag any unusual clauses for legal review
5. Move to `/Done/Contracts/` when complete
```

**Test Cases:**
1. **TC2.1**: Drop 10 files in `/Input_Documents/` → verify 10 Markdown files created
2. **TC2.2**: Drop `.tmp` file → verify ignored (no Markdown created)
3. **TC2.3**: File renamed → verify event logged, no duplicate Markdown
4. **TC2.4**: File deleted before processing → verify graceful handling
5. **TC2.5**: Large file (> 1GB) → verify watcher doesn't block on hash computation

---

### US3: WhatsApp Watcher (Silver Tier)

**As a** system operator
**I want** the AI Employee to monitor WhatsApp Business messages
**So that** customer inquiries are automatically processed

**Acceptance Criteria:**
- [ ] Watcher integrates with WhatsApp Business API (webhook mode)
- [ ] New messages trigger Markdown record creation in `/Inbox`
- [ ] Message metadata (sender phone, timestamp, message type) is captured
- [ ] Media messages (images, documents) are downloaded to `/Attachments`
- [ ] Phone numbers are redacted from logs (PII compliance)
- [ ] Watcher can be started/stopped via `fte watcher start whatsapp`
- [ ] Webhook endpoint secured with HMAC signature verification

**Example Output:**

```markdown
---
source: whatsapp
message_id: wamid.HBgNMTIzNDU2Nzg5MAARAgASC...
from: +1234567890
received_at: 2026-01-28T12:00:00Z
message_type: text
status: needs_action
---

# WhatsApp Message from +1234567890

**Message:**

Hi, I'd like to order 50 units of Product X for delivery next week. Can you confirm availability and pricing?

**AI Employee Instructions:**
1. Check inventory system for Product X availability
2. Look up pricing for bulk order (50 units)
3. Calculate delivery timeline for next week
4. Draft response with quote and delivery date
5. Submit for human approval before sending
```

**Test Cases:**
1. **TC3.1**: Receive 10 text messages → verify 10 Markdown files created
2. **TC3.2**: Receive image message → verify image downloaded to `/Attachments`
3. **TC3.3**: Receive message with phone number in logs → verify PII redacted
4. **TC3.4**: Webhook signature invalid → verify request rejected (403)
5. **TC3.5**: WhatsApp API down → verify exponential backoff retry

---

### US4: Process Management (Silver Tier)

**As a** system operator
**I want** watchers to auto-restart on failure and survive system reboots
**So that** the AI Employee maintains 24/7 perception capabilities

**Acceptance Criteria:**
- [ ] Watchers run as PM2 or supervisord managed processes
- [ ] Each watcher has individual start/stop/restart controls
- [ ] Watchers auto-restart on crash (max 3 retries in 1 minute)
- [ ] Watchers start on system boot (systemd/launchd integration)
- [ ] Process status visible via `fte watcher status`
- [ ] Logs aggregated via `fte watcher logs <name> --tail 50`

**Example PM2 Configuration:**

```javascript
// ecosystem.config.js
module.exports = {
  apps: [
    {
      name: 'watcher-gmail',
      script: 'python',
      args: '-m src.watchers.gmail',
      cwd: '/path/to/AI_Employee/',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '200M',
      env: {
        VAULT_PATH: '/path/to/AI_Employee_Vault',
        LOG_LEVEL: 'INFO',
      },
      error_file: '/var/log/fte/watcher-gmail-error.log',
      out_file: '/var/log/fte/watcher-gmail-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      min_uptime: '10s',
      max_restarts: 3,
    },
    {
      name: 'watcher-filesystem',
      script: 'python',
      args: '-m src.watchers.filesystem',
      // ... similar config
    },
    {
      name: 'watcher-whatsapp',
      script: 'python',
      args: '-m src.watchers.whatsapp',
      // ... similar config
    },
  ],
};
```

**Test Cases:**
1. **TC4.1**: Start all watchers → verify `fte watcher status` shows "running"
2. **TC4.2**: Kill watcher process (SIGKILL) → verify auto-restart within 10s
3. **TC4.3**: Reboot system → verify watchers auto-start on boot
4. **TC4.4**: Watcher crashes 3 times in 1 minute → verify permanent stop, alert logged
5. **TC4.5**: `fte watcher logs gmail --tail 50` → verify last 50 log entries displayed

---

### US5: Error Recovery and Retry Logic (Silver Tier)

**As a** system operator
**I want** watchers to gracefully handle transient failures
**So that** temporary network issues don't require manual intervention

**Acceptance Criteria:**
- [ ] Network failures trigger exponential backoff retry (1s, 2s, 4s, 8s, 16s, max 60s)
- [ ] API rate limits trigger backoff based on `Retry-After` header
- [ ] Permanent failures (401 auth error) stop watcher and alert operator
- [ ] Partial failures (1 email fails, others succeed) don't block entire batch
- [ ] Circuit breaker pattern prevents retry storms (open after 5 consecutive failures)
- [ ] All retries logged with retry count and reason

**Retry Logic Pseudocode:**

```python
from typing import Callable, TypeVar, Optional
import time
import logging

T = TypeVar('T')
logger = logging.get_logger(__name__)

def retry_with_backoff(
    func: Callable[[], T],
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    permanent_errors: tuple = (AuthenticationError,),
) -> Optional[T]:
    """
    Execute function with exponential backoff retry.

    Args:
        func: Function to retry
        max_retries: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        permanent_errors: Exceptions that should not be retried

    Returns:
        Function result or None if all retries exhausted
    """
    for attempt in range(max_retries):
        try:
            return func()
        except permanent_errors as e:
            logger.error(f"Permanent error, not retrying: {e}")
            raise
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Max retries exhausted: {e}")
                return None

            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning(
                f"Retry {attempt + 1}/{max_retries} after {delay}s: {e}",
                context={"error_type": type(e).__name__, "retry_delay": delay}
            )
            time.sleep(delay)

    return None
```

**Test Cases:**
1. **TC5.1**: Simulate network timeout → verify 5 retries with exponential backoff
2. **TC5.2**: Simulate API rate limit (429) → verify backoff based on `Retry-After` header
3. **TC5.3**: Simulate auth error (401) → verify immediate stop, no retries
4. **TC5.4**: Simulate 5 consecutive failures → verify circuit breaker opens
5. **TC5.5**: Circuit breaker open → verify periodic half-open attempts (every 5 minutes)

---

### US6: Advanced Filtering and Prioritization (Gold Tier)

**As a** system operator
**I want** watchers to filter and prioritize incoming data based on rules
**So that** the AI Employee focuses on high-priority tasks first

**Acceptance Criteria:**
- [ ] Gmail watcher supports label-based filtering (e.g., only process `IMPORTANT` label)
- [ ] File system watcher supports glob pattern filtering (e.g., only `.pdf` and `.docx`)
- [ ] WhatsApp watcher supports sender whitelist/blacklist
- [ ] Priority scoring based on configurable rules (sender, keywords, urgency)
- [ ] High-priority items written to `/Needs_Action`, others to `/Inbox`
- [ ] Filtering rules stored in `config/watcher_rules.yaml`

**Example Configuration:**

```yaml
# config/watcher_rules.yaml

gmail:
  filters:
    labels:
      include: [IMPORTANT, URGENT]
      exclude: [SPAM, PROMOTIONS]
    senders:
      whitelist:
        - ceo@company.com
        - legal@company.com
      blacklist:
        - noreply@*.com
    keywords:
      high_priority: [urgent, asap, critical, deadline]
      low_priority: [newsletter, update, fyi]

filesystem:
  filters:
    patterns:
      include: ["*.pdf", "*.docx", "*.xlsx"]
      exclude: ["*.tmp", "*.swp", "~*"]
    directories:
      watch: [/Input_Documents/contracts, /Input_Documents/reports]
      ignore: [/Input_Documents/archive]

whatsapp:
  filters:
    senders:
      whitelist: [+1234567890, +9876543210]
    keywords:
      high_priority: [order, quote, urgent]

priority_scoring:
  rules:
    - condition: sender in gmail.senders.whitelist
      score: +10
    - condition: any(keyword in subject for keyword in gmail.keywords.high_priority)
      score: +5
    - condition: label == "URGENT"
      score: +15
  thresholds:
    high: 15  # Write to /Needs_Action
    medium: 5  # Write to /Inbox
    low: 0    # Write to /Inbox/Low_Priority
```

**Test Cases:**
1. **TC6.1**: Email from whitelisted sender → verify written to `/Needs_Action`
2. **TC6.2**: Email with "urgent" keyword → verify priority score +5
3. **TC6.3**: File matching `*.tmp` pattern → verify ignored
4. **TC6.4**: WhatsApp from non-whitelisted sender → verify written to `/Inbox/Low_Priority`
5. **TC6.5**: Email with URGENT label from CEO → verify priority score 25, `/Needs_Action`

---

## Functional Requirements

### FR1: Gmail Watcher Core Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR1.1 | Authenticate with Gmail API using OAuth2 | P1 (Bronze) |
| FR1.2 | Fetch unread emails from primary inbox every 30s | P1 (Bronze) |
| FR1.3 | Parse email metadata (from, subject, date, labels) | P1 (Bronze) |
| FR1.4 | Convert email body (HTML → Markdown) | P1 (Bronze) |
| FR1.5 | Download attachments to `/Attachments/<message-id>/` | P1 (Bronze) |
| FR1.6 | Mark emails as read after processing | P2 (Silver) |
| FR1.7 | Support label-based filtering | P3 (Gold) |
| FR1.8 | Support multi-account monitoring | P4 (Future) |

### FR2: File System Watcher Core Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR2.1 | Monitor directory for new files using inotify/FSEvents | P1 (Bronze) |
| FR2.2 | Capture file metadata (size, type, SHA256) | P1 (Bronze) |
| FR2.3 | Respect `.gitignore` patterns | P1 (Bronze) |
| FR2.4 | Support recursive directory monitoring | P1 (Bronze) |
| FR2.5 | Handle file move/rename events | P2 (Silver) |
| FR2.6 | Support glob pattern filtering | P3 (Gold) |
| FR2.7 | Detect file modifications (not just creation) | P4 (Future) |

### FR3: WhatsApp Watcher Core Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR3.1 | Integrate with WhatsApp Business API (webhook) | P2 (Silver) |
| FR3.2 | Verify webhook HMAC signatures | P2 (Silver) |
| FR3.3 | Parse text messages | P2 (Silver) |
| FR3.4 | Download media messages (images, documents) | P2 (Silver) |
| FR3.5 | Support sender whitelist/blacklist | P3 (Gold) |
| FR3.6 | Support multi-number monitoring | P4 (Future) |

### FR4: Process Management Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR4.1 | Run watchers as PM2/supervisord managed processes | P2 (Silver) |
| FR4.2 | Auto-restart watchers on crash (max 3 retries/min) | P2 (Silver) |
| FR4.3 | Start watchers on system boot | P2 (Silver) |
| FR4.4 | Individual start/stop/restart controls via CLI | P2 (Silver) |
| FR4.5 | Aggregate logs via CLI | P2 (Silver) |

### FR5: Error Handling Functions

| ID | Requirement | Priority |
|----|-------------|----------|
| FR5.1 | Exponential backoff retry for transient failures | P2 (Silver) |
| FR5.2 | Respect API rate limits (`Retry-After` header) | P2 (Silver) |
| FR5.3 | Circuit breaker pattern (open after 5 failures) | P2 (Silver) |
| FR5.4 | Permanent error detection (stop, don't retry) | P2 (Silver) |
| FR5.5 | Partial failure isolation (batch processing) | P3 (Gold) |

---

## Non-Functional Requirements

### NFR1: Performance

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR1.1 | Gmail polling interval | 30s | Configurable via `config.yaml` |
| NFR1.2 | File system event latency | < 1s | inotify event → Markdown written |
| NFR1.3 | WhatsApp webhook response time | < 500ms | HTTP 200 response time |
| NFR1.4 | Memory footprint per watcher | < 100MB | RSS memory usage |
| NFR1.5 | CPU usage per watcher (idle) | < 1% | Average CPU over 1 hour |
| NFR1.6 | Markdown write latency | < 100ms | File write duration |

### NFR2: Reliability

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR2.1 | Uptime per watcher | 99.9% | (total_time - downtime) / total_time |
| NFR2.2 | Auto-recovery success rate | 95% | Successful restarts / total crashes |
| NFR2.3 | Data loss rate | 0% | Messages lost / total messages |
| NFR2.4 | Duplicate detection | 99.9% | Duplicates prevented / total attempts |

### NFR3: Security

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR3.1 | PII redaction in logs | 100% | Manual audit of 100 log entries |
| NFR3.2 | Credential storage | System keychain | No plaintext credentials in code/config |
| NFR3.3 | Webhook signature verification | 100% | All webhooks verified before processing |
| NFR3.4 | Least privilege file permissions | 0644 (Markdown), 0600 (credentials) | `ls -la` audit |

### NFR4: Observability

| ID | Requirement | Target | Measurement |
|----|-------------|--------|-------------|
| NFR4.1 | Structured logging (P2 infrastructure) | 100% | All watchers use `get_logger()` |
| NFR4.2 | Log levels (DEBUG, INFO, WARNING, ERROR) | 100% | Appropriate levels for all events |
| NFR4.3 | Trace correlation (trace IDs) | 100% | All logs include `trace_id` |
| NFR4.4 | Metrics emission (processed, failed, retried) | 100% | Prometheus metrics endpoint |

---

## Technical Architecture

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     External Data Sources                        │
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐     │
│  │  Gmail   │    │  File System │    │  WhatsApp API    │     │
│  │   API    │    │  (inotify)   │    │   (Webhook)      │     │
│  └────┬─────┘    └──────┬───────┘    └────────┬─────────┘     │
└───────┼─────────────────┼─────────────────────┼───────────────┘
        │                 │                     │
        │ OAuth2          │ inotify events      │ HTTPS POST
        │ Poll (30s)      │ Real-time           │ Webhook
        │                 │                     │
        ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Watcher Scripts Layer                       │
│                     (src/watchers/)                              │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐ │
│  │  Gmail Watcher   │  │ Filesystem       │  │  WhatsApp    │ │
│  │                  │  │ Watcher          │  │  Watcher     │ │
│  │  - OAuth2 client │  │ - inotify loop   │  │  - Flask app │ │
│  │  - Email parser  │  │ - File metadata  │  │  - HMAC auth │ │
│  │  - Attachment DL │  │ - Hash compute   │  │  - Media DL  │ │
│  │  - Retry logic   │  │ - Gitignore      │  │  - Retry     │ │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬───────┘ │
│           │                     │                    │          │
└───────────┼─────────────────────┼────────────────────┼──────────┘
            │                     │                    │
            │ Write Markdown      │ Write Markdown     │ Write Markdown
            │ P2 Logging          │ P2 Logging         │ P2 Logging
            ▼                     ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Obsidian Vault (File System)                  │
│                                                                  │
│  /Inbox/                                                         │
│  ├── gmail_client_2026-01-28T10-30-00.md                        │
│  ├── file_Service_Agreement_v3.md                               │
│  └── whatsapp_1234567890_2026-01-28T12-00-00.md                │
│                                                                  │
│  /Attachments/                                                   │
│  └── <message-id>/                                               │
│      ├── Q4_Budget.xlsx                                          │
│      └── image.png                                               │
└─────────────────────────────────────────────────────────────────┘
            │
            │ Read by Claude Code
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Reasoning Layer (Claude)                     │
└─────────────────────────────────────────────────────────────────┘
```

### Component Design

#### Gmail Watcher

**Technology Stack:**
- Python 3.10+
- `google-auth-oauthlib` (OAuth2 client)
- `google-api-python-client` (Gmail API)
- `beautifulsoup4` (HTML → Markdown)
- `markdownify` (HTML → Markdown conversion)

**Pseudocode:**

```python
# src/watchers/gmail.py

import time
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from markdownify import markdownify as md

from src.logging import get_logger
from src.watchers.base import BaseWatcher

logger = get_logger(__name__)


class GmailWatcher(BaseWatcher):
    """
    Gmail watcher that polls for new emails and writes to Obsidian vault.
    """

    def __init__(self, vault_path: Path, poll_interval: int = 30):
        super().__init__(vault_path, poll_interval)
        self.service = None

    def authenticate(self):
        """Authenticate with Gmail API using OAuth2."""
        # Load credentials from keychain
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail authentication successful")

    def fetch_new_emails(self) -> list:
        """Fetch unread emails from primary inbox."""
        results = self.service.users().messages().list(
            userId='me',
            labelIds=['INBOX', 'UNREAD'],
            maxResults=10
        ).execute()

        messages = results.get('messages', [])
        logger.info(f"Fetched {len(messages)} new emails")
        return messages

    def parse_email(self, message_id: str) -> dict:
        """Parse email and extract metadata."""
        msg = self.service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()

        headers = {h['name']: h['value'] for h in msg['payload']['headers']}

        # Extract body
        body_html = self._get_body(msg['payload'])
        body_markdown = md(body_html)

        return {
            'message_id': message_id,
            'from': headers.get('From'),
            'subject': headers.get('Subject'),
            'date': headers.get('Date'),
            'body': body_markdown,
            'labels': msg.get('labelIds', []),
        }

    def write_to_vault(self, email_data: dict):
        """Write email as Markdown to vault."""
        filename = self._sanitize_filename(
            f"gmail_{email_data['from']}_{email_data['date']}.md"
        )
        filepath = self.vault_path / "Inbox" / filename

        markdown_content = f"""---
source: gmail
message_id: {email_data['message_id']}
from: {email_data['from']}
subject: "{email_data['subject']}"
received_at: {email_data['date']}
labels: {email_data['labels']}
status: needs_action
---

# Email from {email_data['from']}

**Subject:** {email_data['subject']}

**Body:**

{email_data['body']}

---

**AI Employee Instructions:**
[Claude will analyze and determine actions]
"""

        # Atomic write
        filepath.write_text(markdown_content, encoding='utf-8')
        logger.info(f"Email written to {filepath}", context={
            'message_id': email_data['message_id'],
            'subject': email_data['subject']
        })

    def run(self):
        """Main polling loop."""
        logger.info("Starting Gmail watcher")
        self.authenticate()

        while True:
            try:
                messages = self.fetch_new_emails()

                for msg in messages:
                    email_data = self.parse_email(msg['id'])
                    self.write_to_vault(email_data)

                    # Mark as read
                    self.service.users().messages().modify(
                        userId='me',
                        id=msg['id'],
                        body={'removeLabelIds': ['UNREAD']}
                    ).execute()

                logger.debug(f"Sleeping for {self.poll_interval}s")
                time.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"Gmail watcher error: {e}", exc_info=True)
                self.retry_with_backoff(self.run)


if __name__ == "__main__":
    vault = Path("/path/to/AI_Employee_Vault")
    watcher = GmailWatcher(vault)
    watcher.run()
```

#### File System Watcher

**Technology Stack:**
- Python 3.10+
- `watchdog` (cross-platform file system events)
- `pathspec` (`.gitignore` pattern matching)
- `hashlib` (SHA256 computation)

**Pseudocode:**

```python
# src/watchers/filesystem.py

import hashlib
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.logging import get_logger

logger = get_logger(__name__)


class FilesystemWatcher(FileSystemEventHandler):
    """
    File system watcher that monitors directory for new files.
    """

    def __init__(self, vault_path: Path, watch_path: Path):
        self.vault_path = vault_path
        self.watch_path = watch_path
        self.gitignore_patterns = self._load_gitignore()

    def _load_gitignore(self) -> list:
        """Load .gitignore patterns."""
        gitignore_file = self.watch_path / ".gitignore"
        if gitignore_file.exists():
            return gitignore_file.read_text().splitlines()
        return []

    def _should_ignore(self, file_path: Path) -> bool:
        """Check if file matches .gitignore patterns."""
        import pathspec
        spec = pathspec.PathSpec.from_lines('gitwildmatch', self.gitignore_patterns)
        return spec.match_file(str(file_path.relative_to(self.watch_path)))

    def _compute_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with file_path.open('rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def on_created(self, event):
        """Handle file creation event."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check .gitignore
        if self._should_ignore(file_path):
            logger.debug(f"Ignoring file (gitignore): {file_path}")
            return

        # Compute metadata
        file_size = file_path.stat().st_size
        file_hash = self._compute_hash(file_path)
        file_type = self._detect_mime_type(file_path)

        logger.info(f"New file detected: {file_path}", context={
            'file_size': file_size,
            'file_hash': file_hash,
            'file_type': file_type
        })

        # Write to vault
        self._write_to_vault(file_path, file_size, file_hash, file_type)

    def _write_to_vault(self, file_path: Path, file_size: int, file_hash: str, file_type: str):
        """Write file detection as Markdown."""
        filename = f"file_{file_path.stem}_{int(time.time())}.md"
        markdown_path = self.vault_path / "Inbox" / filename

        markdown_content = f"""---
source: filesystem
file_path: {file_path}
file_name: {file_path.name}
file_size: {file_size}
file_type: {file_type}
file_hash: {file_hash}
detected_at: {datetime.now(timezone.utc).isoformat()}
status: needs_action
---

# New File Detected: {file_path.name}

**Location:** `{file_path.parent}/`

**File Details:**
- Type: {file_type}
- Size: {file_size} bytes
- SHA256: `{file_hash}`

**AI Employee Instructions:**
1. Analyze file content and determine processing steps
2. Extract key information or metadata
3. Move to appropriate /Done subdirectory when complete
"""

        markdown_path.write_text(markdown_content, encoding='utf-8')
        logger.info(f"File detection written to {markdown_path}")

    def run(self):
        """Start file system observer."""
        observer = Observer()
        observer.schedule(self, str(self.watch_path), recursive=True)
        observer.start()
        logger.info(f"Watching directory: {self.watch_path}")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


if __name__ == "__main__":
    vault = Path("/path/to/AI_Employee_Vault")
    watch = Path("/path/to/Input_Documents")
    watcher = FilesystemWatcher(vault, watch)
    watcher.run()
```

#### WhatsApp Watcher

**Technology Stack:**
- Python 3.10+
- `flask` (HTTP server for webhooks)
- `hmac` (signature verification)
- `requests` (WhatsApp API calls)

**Pseudocode:**

```python
# src/watchers/whatsapp.py

import hmac
import hashlib
from flask import Flask, request, jsonify
from pathlib import Path

from src.logging import get_logger

logger = get_logger(__name__)
app = Flask(__name__)

VAULT_PATH = Path("/path/to/AI_Employee_Vault")
WHATSAPP_VERIFY_TOKEN = "your-verify-token"
WHATSAPP_APP_SECRET = "your-app-secret"


@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Verify webhook endpoint (WhatsApp setup)."""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified")
        return challenge, 200
    else:
        logger.warning("Webhook verification failed")
        return 'Forbidden', 403


@app.route('/webhook', methods=['POST'])
def receive_message():
    """Receive incoming WhatsApp messages."""
    # Verify signature
    signature = request.headers.get('X-Hub-Signature-256')
    if not verify_signature(request.data, signature):
        logger.warning("Invalid webhook signature")
        return 'Forbidden', 403

    # Parse webhook payload
    data = request.json

    for entry in data.get('entry', []):
        for change in entry.get('changes', []):
            value = change.get('value', {})

            if 'messages' in value:
                for message in value['messages']:
                    process_message(message)

    return jsonify({'status': 'ok'}), 200


def verify_signature(payload: bytes, signature: str) -> bool:
    """Verify HMAC signature."""
    expected_signature = hmac.new(
        WHATSAPP_APP_SECRET.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Extract signature from "sha256=<signature>"
    received_signature = signature.split('=')[1] if signature else ''

    return hmac.compare_digest(expected_signature, received_signature)


def process_message(message: dict):
    """Process incoming WhatsApp message."""
    message_id = message['id']
    from_number = message['from']
    timestamp = message['timestamp']
    message_type = message['type']

    if message_type == 'text':
        text_body = message['text']['body']
        logger.info(f"Received WhatsApp message from {from_number}")

        write_to_vault({
            'message_id': message_id,
            'from': from_number,
            'timestamp': timestamp,
            'type': 'text',
            'body': text_body
        })

    elif message_type in ['image', 'document']:
        # Download media
        media_url = message[message_type]['url']
        download_media(media_url, message_id)


def write_to_vault(message_data: dict):
    """Write WhatsApp message as Markdown."""
    filename = f"whatsapp_{message_data['from']}_{message_data['timestamp']}.md"
    filepath = VAULT_PATH / "Inbox" / filename

    markdown_content = f"""---
source: whatsapp
message_id: {message_data['message_id']}
from: {message_data['from']}
received_at: {message_data['timestamp']}
message_type: {message_data['type']}
status: needs_action
---

# WhatsApp Message from {message_data['from']}

**Message:**

{message_data['body']}

**AI Employee Instructions:**
[Claude will analyze and determine actions]
"""

    filepath.write_text(markdown_content, encoding='utf-8')
    logger.info(f"WhatsApp message written to {filepath}")


if __name__ == "__main__":
    logger.info("Starting WhatsApp webhook server on port 5000")
    app.run(host='0.0.0.0', port=5000)
```

### Base Watcher Class

```python
# src/watchers/base.py

import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Optional

from src.logging import get_logger

logger = get_logger(__name__)


class BaseWatcher(ABC):
    """
    Abstract base class for all watchers.
    Provides common functionality: retry logic, logging, configuration.
    """

    def __init__(self, vault_path: Path, poll_interval: int = 30):
        self.vault_path = vault_path
        self.poll_interval = poll_interval
        self.max_retries = 5
        self.base_delay = 1.0
        self.max_delay = 60.0

    @abstractmethod
    def run(self):
        """Main watcher loop (must be implemented by subclasses)."""
        pass

    def retry_with_backoff(
        self,
        func: Callable,
        permanent_errors: tuple = (AuthenticationError,)
    ) -> Optional[any]:
        """
        Execute function with exponential backoff retry.
        """
        for attempt in range(self.max_retries):
            try:
                return func()
            except permanent_errors as e:
                logger.error(f"Permanent error, stopping watcher: {e}")
                raise
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Max retries exhausted, stopping watcher: {e}")
                    return None

                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                logger.warning(
                    f"Retry {attempt + 1}/{self.max_retries} after {delay}s: {e}",
                    context={'error_type': type(e).__name__, 'retry_delay': delay}
                )
                time.sleep(delay)

        return None

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for cross-platform compatibility."""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Truncate to 255 characters (filesystem limit)
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1)
            filename = name[:250] + '.' + ext

        return filename
```

---

## Data Models

### Markdown Output Format (All Watchers)

All watchers produce Markdown files with consistent YAML frontmatter:

```yaml
---
source: <gmail|filesystem|whatsapp>
message_id: <unique-id>
from: <sender-email|file-path|phone-number>
subject: <email-subject|file-name|message-preview>
received_at: <ISO8601-timestamp>
status: <needs_action|in_progress|done>
priority: <high|medium|low>  # Optional (Gold tier)
labels: [<label1>, <label2>]  # Optional (Gmail)
attachments: [<file1>, <file2>]  # Optional
---

# <Title>

<Body content in Markdown>

---

**AI Employee Instructions:**
<Task-specific guidance for Claude>
```

### Configuration Schema

```yaml
# config/watchers.yaml

vault_path: /path/to/AI_Employee_Vault
log_level: INFO

gmail:
  enabled: true
  poll_interval: 30  # seconds
  credentials_file: ~/.credentials/gmail_token.json
  filters:
    labels:
      include: [INBOX, IMPORTANT]
      exclude: [SPAM]

filesystem:
  enabled: true
  watch_path: /Input_Documents
  recursive: true
  gitignore: true
  patterns:
    include: ["*.pdf", "*.docx", "*.xlsx"]
    exclude: ["*.tmp", "*.swp"]

whatsapp:
  enabled: false  # Silver tier
  webhook_port: 5000
  verify_token: ${WHATSAPP_VERIFY_TOKEN}
  app_secret: ${WHATSAPP_APP_SECRET}

process_management:
  pm2_config: ecosystem.config.js
  auto_restart: true
  max_restarts: 3

logging:
  use_p2_infrastructure: true
  log_dir: /var/log/fte/watchers
```

---

## Security Considerations

### SEC1: Credential Management

**Risk:** Hardcoded credentials in code or config files

**Mitigation:**
1. Store OAuth2 tokens in system keychain (macOS Keychain, Linux Secret Service)
2. Use environment variables for API keys (`${WHATSAPP_APP_SECRET}`)
3. Never commit credentials to Git (`.gitignore` for `credentials/`, `*.token`, `*.key`)
4. Rotate credentials every 90 days

**Example:**

```python
import keyring

# Store credential
keyring.set_password("fte-gmail", "oauth-token", token_json)

# Retrieve credential
token = keyring.get_password("fte-gmail", "oauth-token")
```

### SEC2: PII Redaction

**Risk:** Email addresses, phone numbers logged in plaintext

**Mitigation:**
1. Use `detect-secrets` patterns for PII redaction
2. Redact before logging (never log raw email/phone)
3. Audit logs monthly for PII leaks

**Example:**

```python
import re

def redact_pii(text: str) -> str:
    """Redact email addresses and phone numbers."""
    # Redact emails
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)

    # Redact phone numbers
    text = re.sub(r'\+?1?\d{9,15}\b', '[PHONE_REDACTED]', text)

    return text

logger.info(f"Processing email from {redact_pii(sender_email)}")
```

### SEC3: Webhook Signature Verification

**Risk:** Unauthenticated webhook requests (replay attacks, spoofing)

**Mitigation:**
1. Verify HMAC signature on all WhatsApp webhooks
2. Use constant-time comparison (`hmac.compare_digest`)
3. Reject requests with invalid signatures (403)

**Example:** (See WhatsApp watcher pseudocode above)

### SEC4: File System Permissions

**Risk:** Unauthorized access to Obsidian vault or credentials

**Mitigation:**
1. Markdown files: `0644` (owner read/write, group/world read)
2. Credentials: `0600` (owner read/write only)
3. Directories: `0755` (owner rwx, group/world rx)
4. Run watchers as dedicated user (not root)

**Example:**

```bash
# Set permissions
chmod 0600 ~/.credentials/gmail_token.json
chmod 0644 AI_Employee_Vault/Inbox/*.md
chmod 0755 AI_Employee_Vault/

# Create dedicated user
sudo useradd -m -s /bin/bash fte-watcher
sudo -u fte-watcher python -m src.watchers.gmail
```

---

## Error Handling and Recovery

### Error Classification

| Error Type | Example | Recovery Strategy |
|------------|---------|-------------------|
| **Transient Network** | `ConnectionTimeout`, `503 Service Unavailable` | Exponential backoff retry (5 attempts) |
| **Rate Limiting** | `429 Too Many Requests` | Backoff based on `Retry-After` header |
| **Authentication** | `401 Unauthorized`, `403 Forbidden` | Stop watcher, alert operator (permanent) |
| **Malformed Data** | Invalid JSON, corrupt attachment | Skip item, log error, continue batch |
| **Disk Full** | `OSError: No space left on device` | Stop watcher, alert operator (critical) |
| **Process Crash** | `SIGSEGV`, `SIGKILL` | Auto-restart via PM2 (max 3 attempts) |

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    """Circuit breaker to prevent retry storms."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 300):
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

    def call(self, func: Callable) -> any:
        """Execute function with circuit breaker protection."""
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
                logger.info("Circuit breaker: HALF_OPEN (testing recovery)")
            else:
                raise CircuitBreakerOpen("Circuit breaker is OPEN")

        try:
            result = func()

            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
                logger.info("Circuit breaker: CLOSED (recovery successful)")

            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
                logger.error(f"Circuit breaker: OPEN (threshold {self.failure_threshold} reached)")

            raise
```

---

## Constitutional Compliance

| Constitutional Section | Requirement | Watcher Compliance |
|------------------------|-------------|-------------------|
| **Section 2: Source of Truth** | Obsidian vault is authoritative | ✅ Watchers write to vault, never modify |
| **Section 3: Privacy First** | No PII in logs | ✅ `redact_pii()` before logging |
| **Section 4: Frozen Control Plane** | No modifications to `src/control_plane/` | ✅ Watchers in `src/watchers/` (additive) |
| **Section 8: Auditability** | All actions logged | ✅ P2 logging for all events |
| **Section 9: Error Recovery** | Graceful degradation | ✅ Retry logic, circuit breaker |

---

## Implementation Phases

### Phase 1: Gmail Watcher (Bronze Tier) - 4-6 hours

**Deliverables:**
- [ ] `src/watchers/gmail.py` (Gmail watcher implementation)
- [ ] `src/watchers/base.py` (Base watcher class)
- [ ] OAuth2 authentication flow
- [ ] Email parsing (metadata, body, attachments)
- [ ] Markdown output to `/Inbox`
- [ ] PII redaction in logs
- [ ] CLI integration (`fte watcher start gmail`)

**Acceptance Test:**
```bash
# Start Gmail watcher
fte watcher start gmail

# Send test email to monitored account
# Subject: "Test: AI Employee Task"
# Body: "Please analyze Q4 budget report."

# Verify Markdown created in vault
ls AI_Employee_Vault/Inbox/
# Expected: gmail_sender@example.com_2026-01-28T*.md

# Verify logs (PII redacted)
fte watcher logs gmail --tail 20
# Expected: "Processing email from [EMAIL_REDACTED]"
```

### Phase 2: File System Watcher (Bronze Tier) - 2-3 hours

**Deliverables:**
- [ ] `src/watchers/filesystem.py` (File system watcher)
- [ ] inotify/FSEvents integration
- [ ] `.gitignore` pattern support
- [ ] SHA256 hash computation
- [ ] Markdown output to `/Inbox`
- [ ] CLI integration (`fte watcher start filesystem`)

**Acceptance Test:**
```bash
# Start filesystem watcher
fte watcher start filesystem

# Drop test file
cp ~/Documents/Contract_v2.pdf Input_Documents/contracts/

# Verify Markdown created
ls AI_Employee_Vault/Inbox/
# Expected: file_Contract_v2_*.md

# Verify file hash logged
fte watcher logs filesystem --tail 10
# Expected: "file_hash: a1b2c3d4..."
```

### Phase 3: Process Management (Silver Tier) - 2-3 hours

**Deliverables:**
- [ ] `ecosystem.config.js` (PM2 configuration)
- [ ] Auto-restart on crash
- [ ] System boot integration (systemd/launchd)
- [ ] CLI integration (`fte watcher status`, `fte watcher restart`)

**Acceptance Test:**
```bash
# Start all watchers
fte watcher start --all

# Check status
fte watcher status
# Expected:
# gmail       ✓ running   PID: 12345   Uptime: 2m
# filesystem  ✓ running   PID: 12346   Uptime: 2m

# Kill watcher process
kill -9 12345

# Wait 10 seconds
sleep 10

# Verify auto-restart
fte watcher status
# Expected:
# gmail       ✓ running   PID: 54321   Uptime: 5s  (restarted)
```

### Phase 4: Error Recovery (Silver Tier) - 2-3 hours

**Deliverables:**
- [ ] Exponential backoff retry logic
- [ ] Circuit breaker implementation
- [ ] Permanent error detection (401, 403)
- [ ] Partial failure isolation

**Acceptance Test:**
```bash
# Simulate network failure (disconnect WiFi)
# Watchers should retry with exponential backoff
fte watcher logs gmail --tail 20 --follow
# Expected:
# [WARN] Retry 1/5 after 1.0s: ConnectionTimeout
# [WARN] Retry 2/5 after 2.0s: ConnectionTimeout
# ...

# Reconnect WiFi after 30s
# Expected:
# [INFO] Gmail fetch successful (recovered after 3 retries)
```

### Phase 5: WhatsApp Watcher (Silver Tier) - 4-6 hours

**Deliverables:**
- [ ] `src/watchers/whatsapp.py` (WhatsApp watcher)
- [ ] Flask webhook server
- [ ] HMAC signature verification
- [ ] Media download (images, documents)
- [ ] CLI integration (`fte watcher start whatsapp`)

**Acceptance Test:**
```bash
# Start WhatsApp webhook server
fte watcher start whatsapp
# Expected: Flask server running on port 5000

# Configure WhatsApp webhook (via Meta dashboard)
# Webhook URL: https://your-domain.com/webhook
# Verify Token: <your-token>

# Send test WhatsApp message
# Verify Markdown created
ls AI_Employee_Vault/Inbox/
# Expected: whatsapp_1234567890_*.md
```

### Phase 6: Advanced Filtering (Gold Tier) - 3-4 hours

**Deliverables:**
- [ ] `config/watcher_rules.yaml` (Filtering rules)
- [ ] Label-based filtering (Gmail)
- [ ] Glob pattern filtering (Filesystem)
- [ ] Priority scoring algorithm
- [ ] High-priority → `/Needs_Action`, low → `/Inbox/Low_Priority`

**Acceptance Test:**
```yaml
# config/watcher_rules.yaml
gmail:
  filters:
    senders:
      whitelist: [ceo@company.com]

# Send email from CEO
# Expected: Written to /Needs_Action (high priority)

# Send email from random sender
# Expected: Written to /Inbox (normal priority)
```

---

## Success Metrics

### Bronze Tier (Minimum Viable)

- [ ] One watcher operational (Gmail OR Filesystem)
- [ ] Watchers write Markdown to vault successfully
- [ ] PII redaction functional (manual audit passes)
- [ ] CLI start/stop commands work
- [ ] Logs visible via `fte watcher logs`

### Silver Tier (Production Ready)

- [ ] All three watchers operational (Gmail, Filesystem, WhatsApp)
- [ ] Auto-restart on crash (< 10s recovery time)
- [ ] Exponential backoff retry (5 attempts, 60s max delay)
- [ ] Circuit breaker prevents retry storms
- [ ] 99% uptime over 7-day test period

### Gold Tier (Enterprise Grade)

- [ ] Advanced filtering rules operational
- [ ] Priority scoring correctly categorizes emails
- [ ] Multi-account support (Gmail, WhatsApp)
- [ ] Real-time monitoring dashboard (Grafana)
- [ ] < 1s latency for file system events
- [ ] Zero data loss over 30-day test period

---

## Open Questions

1. **Gmail API Quotas:**
   - Gmail API has quota limits (e.g., 250 requests/second per user). Should we implement request throttling?
   - **Recommendation:** Start with 30s polling, monitor quota usage, implement throttling if needed.

2. **Attachment Size Limits:**
   - Should watchers skip attachments > 10MB to prevent disk exhaustion?
   - **Recommendation:** Yes, skip large attachments, log warning, continue processing email.

3. **Duplicate Detection:**
   - How to handle duplicate emails (same message ID) caused by retries?
   - **Recommendation:** Track processed message IDs in SQLite DB, skip duplicates.

4. **WhatsApp Business API Access:**
   - Requires Meta Business account and app approval (can take days). Fallback plan?
   - **Recommendation:** Use Twilio WhatsApp Business API as alternative (faster setup).

5. **Process Management Choice:**
   - PM2 (Node.js) vs supervisord (Python) vs systemd (native)?
   - **Recommendation:** PM2 for ease of use, cross-platform, rich CLI.

---

## Appendix

### A1: Gmail API Scopes

```python
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'  # For marking as read
]
```

### A2: WhatsApp Webhook Payload Example

```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "1234567890",
              "phone_number_id": "PHONE_NUMBER_ID"
            },
            "contacts": [
              {
                "profile": {
                  "name": "John Doe"
                },
                "wa_id": "1234567890"
              }
            ],
            "messages": [
              {
                "from": "1234567890",
                "id": "wamid.HBgNMTIzNDU2Nzg5MAARAgASC...",
                "timestamp": "1643723400",
                "type": "text",
                "text": {
                  "body": "Hello, I need assistance"
                }
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}
```

### A3: PM2 Commands Reference

```bash
# Start all watchers
pm2 start ecosystem.config.js

# Stop specific watcher
pm2 stop watcher-gmail

# Restart watcher
pm2 restart watcher-gmail

# View logs
pm2 logs watcher-gmail --lines 50

# Monitor all processes
pm2 monit

# Save process list for auto-start on reboot
pm2 save

# Generate startup script
pm2 startup
```

### A4: Testing Checklist

```markdown
## Gmail Watcher Testing

- [ ] OAuth2 authentication successful
- [ ] Fetch 10 new emails successfully
- [ ] HTML → Markdown conversion correct
- [ ] Attachments downloaded to `/Attachments`
- [ ] Email addresses redacted from logs
- [ ] Retry on network timeout (3 attempts)
- [ ] Circuit breaker opens after 5 failures
- [ ] CLI commands work: start, stop, status, logs

## File System Watcher Testing

- [ ] inotify events detected within 1s
- [ ] `.gitignore` patterns respected
- [ ] SHA256 hash computed correctly
- [ ] Large files (> 1GB) handled gracefully
- [ ] File rename events logged (not duplicated)
- [ ] CLI commands work: start, stop, status, logs

## WhatsApp Watcher Testing

- [ ] Webhook verification successful (GET request)
- [ ] HMAC signature validation works
- [ ] Text messages parsed correctly
- [ ] Image messages downloaded
- [ ] Invalid signature rejected (403)
- [ ] Phone numbers redacted from logs
- [ ] CLI commands work: start, stop, status, logs

## Process Management Testing

- [ ] PM2 starts all watchers on boot
- [ ] Auto-restart on crash (< 10s)
- [ ] Max restart limit enforced (3 attempts/min)
- [ ] `fte watcher status` shows correct PID/uptime
- [ ] `fte watcher logs` aggregates all logs

## Error Recovery Testing

- [ ] Exponential backoff: 1s, 2s, 4s, 8s, 16s
- [ ] Rate limit (429) respects `Retry-After` header
- [ ] Auth error (401) stops watcher immediately
- [ ] Circuit breaker opens after 5 consecutive failures
- [ ] Partial failure (1 email fails) doesn't block batch
```

---

## Change Log

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2026-01-28 | v1.0 | AI Employee Team | Initial specification |

---

**Next Steps:**
1. Review spec with stakeholders
2. Generate implementation plan using `/sp.plan`
3. Generate task breakdown using `/sp.tasks`
4. Begin Bronze Tier implementation (Gmail OR Filesystem watcher)

---

*This specification is part of the Personal AI Employee Hackathon 0 project. For related specs, see:*
- *[P2: Logging Infrastructure](../002-logging-infrastructure/spec.md)*
- *[P3: CLI Integration Roadmap](../003-cli-integration-roadmap/spec.md)*
- *[P4: MCP Threat Model](../004-mcp-threat-model/spec.md)*

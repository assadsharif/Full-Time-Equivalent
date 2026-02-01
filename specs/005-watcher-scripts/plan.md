# Implementation Plan: Watcher Scripts (Perception Layer)

**Branch**: `005-watcher-scripts` | **Date**: 2026-01-28 | **Spec**: [specs/005-watcher-scripts/spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-watcher-scripts/spec.md`

## Summary

Implement daemon-based Watcher scripts that continuously monitor external data sources (Gmail, WhatsApp, file system) and convert incoming data into structured Markdown files in the Obsidian vault. Watchers provide the "perception layer" enabling the AI Employee to detect tasks autonomously without manual data entry.

**Key Approach**: Poll-based architecture with Python daemons managed by PM2/supervisord. Each Watcher runs independently, polls its data source, parses content, redacts PII, formats as Markdown, and writes atomically to vault `/Inbox` folder.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: google-auth>=2.23.0, google-api-python-client>=2.100.0, watchdog>=3.0.0, detect-secrets>=1.4.0, pyyaml>=6.0
**Storage**: Obsidian vault (file-based), checkpoint files for poll state
**Testing**: pytest>=7.4.0, pytest-asyncio for async tests, responses for API mocking
**Target Platform**: Linux/macOS (primary), Windows (secondary)
**Project Type**: Single project (daemon scripts)
**Performance Goals**: <5% CPU per watcher, <100MB RAM per watcher, 30s default poll interval
**Constraints**: ADDITIVE ONLY - no control plane modifications, privacy-preserving (PII redaction), graceful degradation on errors
**Scale/Scope**: 3 core watchers (Gmail, WhatsApp, FileSystem), support 100+ events/hour per watcher

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

✅ **Section 2 (Source of Truth)**: Watchers write to vault, vault is source of truth
✅ **Section 3 (Local-First & Privacy)**: PII redaction, credentials in OS keyring, no cloud storage
✅ **Section 4 (File-Driven Control Plane)**: Atomic file writes to `/Inbox`, respect folder state
✅ **Section 8 (Auditability)**: All watcher events logged via P2 infrastructure
✅ **Section 9 (Error Handling)**: Exponential backoff, retry logic, error logging
✅ **Section 11 (No Spec Drift)**: Implementation follows spec exactly, additive only

## Project Structure

### Documentation (this feature)

```text
specs/005-watcher-scripts/
├── plan.md              # This file
├── research.md          # Gmail API, WhatsApp API, inotify comparison
├── data-model.md        # Markdown format, YAML frontmatter schema
├── quickstart.md        # Watcher setup guide
└── contracts/           # Watcher API contracts
    ├── gmail-watcher.md
    ├── whatsapp-watcher.md
    └── filesystem-watcher.md
```

### Source Code (repository root)

```text
src/watchers/
├── __init__.py          # Watcher base class
├── base_watcher.py      # Abstract base for all watchers
├── gmail_watcher.py     # Gmail API integration
├── whatsapp_watcher.py  # WhatsApp Business API integration
├── filesystem_watcher.py # Inotify-based file watcher
├── markdown_formatter.py # Markdown + YAML formatter
├── pii_redactor.py      # PII detection and redaction
└── models.py            # Watcher data models

config/
├── watchers/
│   ├── gmail.yaml       # Gmail watcher config
│   ├── whatsapp.yaml    # WhatsApp watcher config
│   └── filesystem.yaml  # File watcher config
└── pii-patterns.yaml    # PII redaction patterns

scripts/
└── run_watcher.py       # Watcher entry point (PM2 runs this)

tests/watchers/
├── test_gmail_watcher.py
├── test_filesystem_watcher.py
├── test_pii_redactor.py
└── test_watcher_integration.py

.fte/
├── watchers/
│   ├── gmail.checkpoint.json     # Last processed email ID
│   └── filesystem.checkpoint.json # Last processed file timestamp
└── pm2.config.js        # PM2 process configuration
```

**Structure Decision**: New `src/watchers/` module with independent daemon scripts. Each watcher inherits from `BaseWatcher` for common functionality (logging, error handling, checkpointing).

## Complexity Tracking

> No constitutional violations - all gates passing.

## Phase 0: Research & Technology Selection

### Research Areas

1. **Gmail API Integration**
   - **Question**: OAuth2 vs Service Account vs API Key?
   - **Options**: OAuth2 (user consent), Service Account (server-to-server), API key (deprecated)
   - **Decision Criteria**: Security, user experience, refresh token handling
   - **Recommendation**: OAuth2 with refresh tokens stored in OS keyring

2. **File System Monitoring**
   - **Question**: Polling vs inotify vs watchdog library?
   - **Options**: Polling (cross-platform, inefficient), inotify (Linux-only, efficient), watchdog (cross-platform wrapper)
   - **Recommendation**: `watchdog` library (supports inotify on Linux, FSEvents on macOS, ReadDirectoryChangesW on Windows)

3. **WhatsApp Integration**
   - **Question**: WhatsApp Business API vs WhatsApp Web scraping?
   - **Options**: Official Business API (reliable, paid), Web scraping (unreliable, against TOS)
   - **Recommendation**: WhatsApp Business API (official, secure, constitutional compliance)

4. **Process Management**
   - **Question**: PM2 vs supervisord vs systemd?
   - **Options**: PM2 (Node.js, cross-platform), supervisord (Python, UNIX-only), systemd (Linux-only)
   - **Recommendation**: PM2 for development, systemd for production Linux deployments

5. **PII Redaction**
   - **Question**: Which PII patterns to detect (emails, phone numbers, SSNs)?
   - **Research**: GDPR requirements, detect-secrets patterns, custom regex
   - **Recommendation**: Use detect-secrets + custom patterns for domain-specific PII

### Research Deliverable: `research.md`

Document containing:
- Gmail API authentication flow (OAuth2 setup)
- File system monitoring comparison (inotify vs FSEvents vs polling)
- WhatsApp Business API pricing and setup
- Process management options (PM2 vs supervisord vs systemd)
- PII patterns and redaction strategies

## Phase 1: Design & Contracts

### Data Model (`data-model.md`)

**Markdown File Format** (Inbox task):
```markdown
---
id: gmail_user@example.com_2026-01-28T10-30-00
source: gmail
sender: client@company.com
subject: "Urgent: Q4 Report Needed"
received: 2026-01-28T10:30:00Z
priority: high
has_attachments: true
pii_redacted: true
---

# Task from Gmail: Urgent: Q4 Report Needed

**From**: client@company.com
**Received**: 2026-01-28 10:30 AM
**Subject**: Urgent: Q4 Report Needed

## Content

Hi [REDACTED_NAME],

Can you prepare the Q4 financial report by end of week? Please include:
- Revenue breakdown
- Customer acquisition metrics
- Expense analysis

Contact me at [REDACTED_PHONE] if you have questions.

## Attachments

- `Q3_template.xlsx` (saved to /Attachments/)

---

_Auto-generated by Gmail Watcher_
```

**YAML Frontmatter Schema**:
```yaml
id: string               # Unique task ID (source_sender_timestamp)
source: gmail|whatsapp|filesystem
sender: string           # Email address or phone number
subject: string          # Email subject or file name
received: ISO8601        # Timestamp of receipt
priority: low|medium|high|urgent
has_attachments: boolean
pii_redacted: boolean
checkpoint: string       # For idempotency (Gmail message ID, file hash)
```

**Watcher Checkpoint Format**:
```json
{
  "last_processed_id": "gmail_message_id_12345",
  "last_poll_time": "2026-01-28T10:30:00Z",
  "events_processed": 142,
  "errors_count": 2
}
```

### API Contracts (`contracts/`)

**gmail-watcher.md**:
```python
# Gmail Watcher Contract
class GmailWatcher(BaseWatcher):
    def poll(self) -> List[EmailMessage]:
        """
        Poll Gmail API for new messages since last checkpoint.

        Returns:
            List of unread emails in inbox

        Raises:
            AuthenticationError: OAuth token expired/invalid
            RateLimitError: Gmail API quota exceeded
        """

    def parse_message(self, message: EmailMessage) -> Dict[str, Any]:
        """
        Extract structured data from Gmail message.

        Returns:
            {sender, subject, body, attachments, timestamp}
        """

    def download_attachment(
        self,
        attachment_id: str,
        filename: str
    ) -> Path:
        """
        Download attachment to vault /Attachments folder.

        Returns:
            Path to saved attachment
        """
```

**filesystem-watcher.md**:
```python
# File System Watcher Contract
class FileSystemWatcher(BaseWatcher):
    def watch_directory(self, path: Path) -> None:
        """
        Start watching directory for file changes.

        Uses watchdog library with inotify backend on Linux.

        Events:
            - file_created
            - file_modified
            - file_deleted
        """

    def on_file_created(self, event: FileSystemEvent) -> None:
        """
        Handler for file creation events.

        Creates task in /Inbox with file metadata.
        """
```

**pii-redaction.md**:
```python
# PII Redaction Contract
class PIIRedactor:
    def redact(self, text: str) -> Tuple[str, List[str]]:
        """
        Redact PII from text using detect-secrets patterns.

        Returns:
            (redacted_text, list_of_redacted_patterns)

        Patterns:
            - Email addresses → [REDACTED_EMAIL]
            - Phone numbers → [REDACTED_PHONE]
            - SSN → [REDACTED_SSN]
            - Credit cards → [REDACTED_CC]
            - Names (NER) → [REDACTED_NAME]
        """
```

### Quickstart Guide (`quickstart.md`)

```markdown
# Watcher Scripts Quickstart

## Gmail Watcher Setup

### 1. Create OAuth2 Credentials

1. Go to https://console.cloud.google.com
2. Create new project "Digital FTE"
3. Enable Gmail API
4. Create OAuth2 credentials (Desktop app)
5. Download `credentials.json`

### 2. Authenticate

```bash
# Store credentials
fte security store gmail-watcher user@gmail.com --file credentials.json

# Test connection
fte watcher test gmail
```

### 3. Configure Watcher

Edit `config/watchers/gmail.yaml`:
```yaml
poll_interval: 30  # seconds
inbox_folder: /Inbox
redact_pii: true
download_attachments: true
max_attachment_size: 10485760  # 10MB
```

### 4. Start Watcher

```bash
# Start Gmail watcher
fte watcher start gmail

# Check status
fte watcher status

# View logs
fte watcher logs gmail --tail 50
```

## File System Watcher Setup

```bash
# Configure watched directories
fte watcher config filesystem --add-path ~/Documents/FTE_Tasks

# Start watcher
fte watcher start filesystem

# Test file detection
echo "Test task" > ~/Documents/FTE_Tasks/test.md
fte vault status  # Should show new task in Inbox
```
```

## Phase 2: Implementation Roadmap

### Bronze Tier (Week 1-2): Core Watcher Infrastructure

**Milestone**: Gmail and FileSystem watchers functional

**Tasks**:
1. Implement `BaseWatcher` abstract class
2. Create `GmailWatcher` with OAuth2 integration
3. Implement `FileSystemWatcher` with watchdog
4. Add `MarkdownFormatter` for task file generation
5. Implement `PIIRedactor` with detect-secrets
6. Create checkpoint system for idempotency
7. Write unit tests for each watcher
8. PM2 configuration for process management

**Deliverables**:
- Working Gmail watcher (OAuth2, PII redaction, attachments)
- Working file system watcher (recursive monitoring)
- Markdown task generation
- PM2 daemon configuration
- Test coverage >80%

### Silver Tier (Week 3-4): WhatsApp Integration & Error Handling

**Milestone**: WhatsApp watcher, robust error handling

**Tasks**:
1. Implement `WhatsAppWatcher` (Business API)
2. Add exponential backoff retry logic
3. Implement circuit breaker pattern
4. Add health check endpoints for each watcher
5. Integration with P2 logging infrastructure
6. CLI integration (`fte watcher` commands)
7. Comprehensive error recovery testing

**Deliverables**:
- WhatsApp watcher (Business API integration)
- Robust error handling (retries, circuit breakers)
- Health check API
- CLI watcher management commands
- Integration tests with mocked APIs

### Gold Tier (Week 5-6): Advanced Features & Monitoring

**Milestone**: Monitoring dashboard, advanced filtering

**Tasks**:
1. Add priority detection (urgent keywords, VIP senders)
2. Implement smart filtering (spam detection)
3. Create watcher monitoring dashboard
4. Add metrics collection (events/hour, errors, latency)
5. Implement watcher auto-recovery
6. Performance optimization (async operations)
7. Comprehensive documentation

**Deliverables**:
- Smart task prioritization
- Spam filtering
- Monitoring dashboard (`fte watcher dashboard`)
- Performance metrics
- Auto-recovery mechanisms
- Production deployment guide

## Testing Strategy

### Unit Tests
```python
def test_gmail_watcher_poll():
    watcher = GmailWatcher(config)
    with mock.patch('google.gmail.service') as mock_gmail:
        mock_gmail.messages().list.return_value = mock_messages
        messages = watcher.poll()
        assert len(messages) == 3

def test_pii_redactor_email():
    redactor = PIIRedactor()
    text = "Contact me at user@example.com"
    redacted, patterns = redactor.redact(text)
    assert "[REDACTED_EMAIL]" in redacted
    assert "email" in patterns
```

### Integration Tests
- Test with real Gmail API (test account)
- Test file system events with temporary directory
- Test checkpoint persistence across restarts
- Test error recovery scenarios

### Load Tests
- 100 emails/minute processing
- 1000 file events/minute
- Memory usage under sustained load
- CPU usage monitoring

## Risk Analysis

### Risk 1: Gmail API Quota Limits
**Impact**: High (watcher stops working)
**Mitigation**: Implement exponential backoff, increase poll interval during errors, upgrade to paid quota if needed

### Risk 2: OAuth Token Expiration
**Impact**: Medium (requires re-authentication)
**Mitigation**: Automatic refresh token handling, alert when manual re-auth needed

### Risk 3: File System Event Overflow
**Impact**: Medium (missed events)
**Mitigation**: Queue events, process in batches, alert on backlog

### Risk 4: PII Redaction False Positives/Negatives
**Impact**: Medium (privacy risk or over-redaction)
**Mitigation**: Configurable patterns, manual review option, audit logging

## Architectural Decision Records

### ADR-001: Polling vs Webhook Architecture

**Decision**: Use polling-based architecture for all watchers

**Rationale**:
- Simpler implementation (no webhook server required)
- Better for local-first architecture
- Easier to debug and monitor
- Gmail API doesn't support webhooks for personal accounts
- Constitutional compliance (local-first, no cloud dependencies)

**Alternatives Considered**:
- Webhooks: Requires public endpoint, complex NAT traversal, not local-first
- Real-time APIs: WhatsApp Web doesn't provide official API

**Trade-offs**:
- Higher latency (30s default vs real-time)
- More API calls (continuous polling)
- Acceptable for FTE use case (not time-critical)

### ADR-002: Watchdog Library for File Monitoring

**Decision**: Use `watchdog` library for cross-platform file system monitoring

**Rationale**:
- Cross-platform support (Linux/macOS/Windows)
- Uses efficient native APIs (inotify, FSEvents, ReadDirectoryChangesW)
- Well-maintained, widely adopted
- Pythonic API, easy to test

**Alternatives Considered**:
- Raw inotify: Linux-only, low-level API
- Polling: Inefficient, high CPU usage
- pyinotify: Linux-only, less actively maintained

### ADR-003: PM2 for Process Management

**Decision**: Use PM2 for watcher process management in development

**Rationale**:
- Excellent process monitoring dashboard
- Auto-restart on crashes
- Log aggregation
- Cross-platform (unlike systemd)
- Easy to configure and debug

**Alternatives Considered**:
- supervisord: Python-based but UNIX-only
- systemd: Linux-only, requires root access
- Custom solution: High maintenance, reinventing wheel

**Production Deployment**:
- Use systemd for Linux production deployments
- Provide systemd service files in docs
- Keep PM2 for development/macOS

## Integration Points

### P1 Control Plane
- **No modifications** to control plane code
- Watchers write to `/Inbox` folder (control plane picks up from there)

### P2 Logging Infrastructure
- All watcher events logged via `LoggerService`
- Query watcher logs: `fte logs query --module watchers`
- Integration with audit trail

### P3 CLI Integration
- `fte watcher` command group
- Start, stop, status, logs commands
- Configuration management

### P4 MCP Security
- OAuth tokens stored in OS keyring (same pattern as MCP credentials)
- PII redaction patterns shared with security module

### Obsidian Vault
- Write to `/Inbox` folder
- Atomic file operations
- YAML frontmatter format
- Attachment storage in `/Attachments`

## Success Metrics

### Functionality
- [ ] All 3 watchers implemented (Gmail, WhatsApp, FileSystem)
- [ ] PII redaction working (100% of test patterns caught)
- [ ] Atomic file writes (no corruption)
- [ ] Checkpoint system prevents duplicate processing

### Reliability
- [ ] 99.9% uptime over 30 days
- [ ] Auto-recovery from transient errors
- [ ] Zero data loss
- [ ] Graceful degradation on API failures

### Performance
- [ ] <5% CPU per watcher
- [ ] <100MB RAM per watcher
- [ ] Process 100+ events/hour without degradation
- [ ] <30s latency from external event to vault

### Privacy
- [ ] Zero PII in logs
- [ ] Credentials encrypted in OS keyring
- [ ] Redaction audit trail

---

**Next Steps**: Run `/sp.tasks` to generate actionable task breakdown.

# Implementation Plan: HITL Approval Workflows

**Branch**: `010-hitl-approval-workflows` | **Date**: 2026-01-28 | **Spec**: [specs/010-hitl-approval-workflows/spec.md](./spec.md)

## Summary

Implement Human-in-the-Loop (HITL) approval workflows that enforce manual approval for dangerous actions (payments, emails, deletions) before execution. Prevents autonomous AI Employee from executing sensitive operations without explicit human consent.

**Key Approach**: File-based approval system in `/Approvals` folder, approval file format with nonce for replay protection, CLI approval commands, file integrity verification, timeout mechanisms, audit trail integration.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: python-ulid>=2.0.0, hashlib (stdlib), pathlib (stdlib)
**Storage**: Obsidian vault `/Approvals` folder (file-based)
**Testing**: pytest>=7.4.0, approval workflow tests
**Target Platform**: Cross-platform
**Project Type**: Single project (approval system)
**Performance Goals**: <100ms approval check, <1s approval file creation
**Constraints**: ADDITIVE ONLY, zero approval bypasses allowed, complete audit trail
**Scale/Scope**: Support 100+ approvals/week, handle 10 approval types

## Constitution Check

✅ **Section 6-7 (Autonomy & HITL)**: Core requirement - dangerous actions require approval
✅ **Section 4 (File-Driven)**: Approvals are file-based (/Approvals folder)
✅ **Section 8 (Auditability)**: All approvals logged with nonce
✅ **Section 9 (Error Handling)**: No approval = action blocked (fail-safe)

## Project Structure

```text
src/approval/
├── __init__.py
├── approval_manager.py  # Approval creation and checking
├── nonce_generator.py   # Nonce-based replay protection
├── integrity_checker.py # File integrity verification
└── models.py            # Approval data models

AI_Employee_Vault/Approvals/
├── PAYMENT_Vendor_A_2026-01-28.md
├── EMAIL_Client_B_2026-01-28.md
└── ...

tests/approval/
├── test_approval_manager.py
├── test_nonce_generator.py
└── test_approval_workflow.py
```

## Approval File Format

```yaml
---
task_id: gmail_ceo_2026-01-28T10-00-00
approval_id: PAYMENT_Vendor_A_2026-01-28
nonce: 7a9b3c4d-5e6f-7890-ab12-3456789abcde
action_type: payment
risk_level: high
approval_status: pending  # pending, approved, rejected, timeout
created_at: 2026-01-28T10:00:00Z
expires_at: 2026-01-28T22:00:00Z
action:
  type: wire_transfer
  recipient: Vendor A
  amount: 5000.00
---

# Approval Request: Payment to Vendor A

**Action**: Wire Transfer
**Amount**: $5,000.00
**Recipient**: Vendor A

Please review and approve/reject this action using:

```bash
fte vault approve PAYMENT_Vendor_A_2026-01-28
# OR
fte vault reject PAYMENT_Vendor_A_2026-01-28
```

## Implementation Roadmap

### Bronze Tier (Week 1): Core Approval System
- Implement `ApprovalManager` class
- Create approval file format and templates
- Add nonce generation for replay protection
- CLI approval commands (`approve`, `reject`)
- Unit tests

### Silver Tier (Week 2): Security & Validation
- Implement file integrity verification
- Add timeout mechanism (12-hour expiry)
- Authorization checks (only vault owner can approve)
- Audit logging integration
- Integration tests

### Gold Tier (Week 3): Advanced Features
- Approval delegation (authorized approvers list)
- Multi-level approvals (payment tiers)
- Approval history dashboard
- Email notifications for pending approvals
- Comprehensive documentation

## Security Features

### Replay Protection
- Unique nonce per approval
- Nonce stored in approval file
- MCP checks nonce before execution
- Used nonces tracked in audit log

### File Integrity
- SHA256 hash of approval file content
- Hash verification before execution
- Tamper detection

### Authorization
- Only vault owner can approve
- Authorized approvers list (configurable)
- CLI user verification

### Timeout
- Default 12-hour expiration
- Configurable per action type
- Auto-reject on timeout

## Success Metrics

- [ ] Zero approval bypasses (100% enforcement)
- [ ] All dangerous actions require approval
- [ ] Nonce-based replay protection working
- [ ] File integrity verification passing
- [ ] Audit trail complete

---

**Next Steps**: Run `/sp.tasks` to generate actionable task breakdown.

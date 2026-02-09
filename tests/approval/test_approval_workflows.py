"""
HITL Approval Workflow tests (spec 010 — Bronze Tier).

Coverage map:
  TestNonceGenerator       — uniqueness, UUID format, record/check
  TestIntegrityChecker     — deterministic hash, tamper detection, body extraction
  TestApprovalManagerCreate — file creation, YAML frontmatter, risk classification
  TestApprovalManagerRead  — get by ID, find by task_id
  TestApprovalManagerLifecycle — approve, reject, nonce consumption, status guards
  TestApprovalManagerTimeout   — expired-approval reject, bulk expiry sweep
  TestApprovalIntegrity    — tampered-body blocks approve
  TestApprovalManagerOrchestratorBridge — ApprovalManager feeds is_approved correctly
                                          when wired into Orchestrator vault layout
"""

import shutil
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.approval.approval_manager import ApprovalManager
from src.approval.integrity_checker import IntegrityChecker
from src.approval.models import ApprovalRequest, ApprovalStatus
from src.approval.nonce_generator import NonceGenerator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def approvals_dir():
    d = Path(tempfile.mkdtemp())
    approvals = d / "Approvals"
    approvals.mkdir()
    yield approvals
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def audit_path(approvals_dir):
    return approvals_dir.parent / ".fte" / "approval_nonces.txt"


@pytest.fixture
def manager(approvals_dir, audit_path):
    return ApprovalManager(approvals_dir, audit_path)


# ===========================================================================
# NonceGenerator
# ===========================================================================


class TestNonceGenerator:
    def test_generate_unique(self, audit_path):
        gen = NonceGenerator(audit_path)
        assert len({gen.generate() for _ in range(200)}) == 200

    def test_generate_uuid_format(self, audit_path):
        gen = NonceGenerator(audit_path)
        parts = gen.generate().split("-")
        assert [len(p) for p in parts] == [8, 4, 4, 4, 12]

    def test_is_used_false_initially(self, audit_path):
        gen = NonceGenerator(audit_path)
        assert gen.is_used("anything") is False

    def test_record_then_is_used(self, audit_path):
        gen = NonceGenerator(audit_path)
        nonce = gen.generate()
        gen.record_used(nonce)
        assert gen.is_used(nonce) is True

    def test_unrecorded_nonce_not_used(self, audit_path):
        gen = NonceGenerator(audit_path)
        n1, n2 = gen.generate(), gen.generate()
        gen.record_used(n1)
        assert gen.is_used(n2) is False

    def test_multiple_record_idempotent(self, audit_path):
        gen = NonceGenerator(audit_path)
        nonce = gen.generate()
        gen.record_used(nonce)
        gen.record_used(nonce)  # duplicate write — should not break
        assert gen.is_used(nonce) is True


# ===========================================================================
# IntegrityChecker
# ===========================================================================


class TestIntegrityChecker:
    def test_hash_is_deterministic(self):
        assert IntegrityChecker.compute_hash("abc") == IntegrityChecker.compute_hash(
            "abc"
        )

    def test_hash_differs_on_change(self):
        assert IntegrityChecker.compute_hash("abc") != IntegrityChecker.compute_hash(
            "abd"
        )

    def test_verify_pass(self):
        h = IntegrityChecker.compute_hash("payload")
        assert IntegrityChecker.verify("payload", h) is True

    def test_verify_fail(self):
        h = IntegrityChecker.compute_hash("payload")
        assert IntegrityChecker.verify("tampered", h) is False

    def test_body_content_strips_frontmatter(self, approvals_dir):
        p = approvals_dir / "fm.md"
        p.write_text("---\nkey: val\n---\n\nBody here.\n")
        assert IntegrityChecker.body_content(p) == "Body here.\n"

    def test_body_content_passthrough_without_frontmatter(self, approvals_dir):
        p = approvals_dir / "nofm.md"
        p.write_text("plain text\n")
        assert IntegrityChecker.body_content(p) == "plain text\n"

    def test_extract_hash_present(self, approvals_dir):
        p = approvals_dir / "hash.md"
        p.write_text("---\nintegrity_hash: abc123\n---\nbody\n")
        assert IntegrityChecker.extract_hash(p) == "abc123"

    def test_extract_hash_absent(self, approvals_dir):
        p = approvals_dir / "nohash.md"
        p.write_text("---\ntitle: x\n---\nbody\n")
        assert IntegrityChecker.extract_hash(p) is None


# ===========================================================================
# ApprovalManager — creation
# ===========================================================================


class TestApprovalManagerCreate:
    def test_returns_approval_request(self, manager):
        req = manager.create(
            task_id="t-001",
            action_type="payment",
            keywords=["payment"],
            action_details={"recipient": "Vendor A", "amount": 500},
        )
        assert isinstance(req, ApprovalRequest)
        assert req.task_id == "t-001"
        assert req.status == ApprovalStatus.PENDING
        assert req.nonce
        assert req.integrity_hash

    def test_file_created_with_frontmatter(self, manager, approvals_dir):
        req = manager.create(
            task_id="t-002", action_type="email", keywords=["send email"]
        )
        p = approvals_dir / f"{req.approval_id}.md"
        assert p.exists()
        text = p.read_text()
        assert text.startswith("---")
        end = text.find("---", 3)
        assert end != -1
        assert "t-002" in text
        assert "send email" in text

    def test_risk_high_payment(self, manager):
        req = manager.create(
            task_id="r1",
            action_type="payment",
            keywords=["payment"],
            action_details={"amount": 500},
        )
        assert req.risk_level == "high"

    def test_risk_critical_large_payment(self, manager):
        req = manager.create(
            task_id="r2",
            action_type="wire",
            keywords=["wire"],
            action_details={"amount": 50_000},
        )
        assert req.risk_level == "critical"

    def test_risk_high_deploy(self, manager):
        req = manager.create(task_id="r3", action_type="deploy", keywords=["deploy"])
        assert req.risk_level == "high"

    def test_risk_high_delete(self, manager):
        req = manager.create(task_id="r4", action_type="delete", keywords=["delete"])
        assert req.risk_level == "high"

    def test_risk_medium_email(self, manager):
        req = manager.create(task_id="r5", action_type="email", keywords=["send email"])
        assert req.risk_level == "medium"

    def test_expiry_default_12h(self, manager):
        req = manager.create(task_id="r6", action_type="deploy", keywords=["deploy"])
        delta = (req.expires_at - req.created_at).total_seconds()
        assert abs(delta - 12 * 3600) < 2

    def test_custom_timeout(self, manager):
        req = manager.create(
            task_id="r7", action_type="deploy", keywords=["deploy"], timeout_hours=1
        )
        delta = (req.expires_at - req.created_at).total_seconds()
        assert abs(delta - 3600) < 2

    def test_action_details_in_body(self, manager, approvals_dir):
        req = manager.create(
            task_id="r8",
            action_type="payment",
            keywords=["payment"],
            action_details={"recipient": "ACME Corp", "amount": 1234},
        )
        body = (approvals_dir / f"{req.approval_id}.md").read_text()
        assert "ACME Corp" in body
        assert "1234" in body


# ===========================================================================
# ApprovalManager — read
# ===========================================================================


class TestApprovalManagerRead:
    def test_get_by_id(self, manager):
        created = manager.create(
            task_id="rd-1", action_type="deploy", keywords=["deploy"]
        )
        loaded = manager.get(created.approval_id)
        assert loaded is not None
        assert loaded.approval_id == created.approval_id
        assert loaded.task_id == "rd-1"

    def test_get_missing_returns_none(self, manager):
        assert manager.get("no-such-id") is None

    def test_find_for_task(self, manager):
        created = manager.create(
            task_id="find-me", action_type="deploy", keywords=["deploy"]
        )
        found = manager.find_for_task("find-me")
        assert found is not None
        assert found.approval_id == created.approval_id

    def test_find_for_task_missing(self, manager):
        assert manager.find_for_task("ghost") is None

    def test_find_for_task_returns_latest(self, manager):
        """When two requests exist for same task, the later one wins."""
        r1 = manager.create(task_id="latest", action_type="deploy", keywords=["deploy"])
        r2 = manager.create(task_id="latest", action_type="deploy", keywords=["deploy"])
        found = manager.find_for_task("latest")
        assert found is not None
        # r2 was created after r1
        assert found.approval_id == r2.approval_id


# ===========================================================================
# ApprovalManager — approve / reject lifecycle
# ===========================================================================


class TestApprovalManagerLifecycle:
    def test_approve_transitions_to_approved(self, manager):
        req = manager.create(task_id="lc-1", action_type="deploy", keywords=["deploy"])
        result = manager.approve(req.approval_id)
        assert result.status == ApprovalStatus.APPROVED

    def test_approve_records_nonce(self, manager, audit_path):
        req = manager.create(task_id="lc-2", action_type="deploy", keywords=["deploy"])
        manager.approve(req.approval_id)
        assert NonceGenerator(audit_path).is_used(req.nonce) is True

    def test_approve_already_approved_raises(self, manager):
        req = manager.create(task_id="lc-3", action_type="deploy", keywords=["deploy"])
        manager.approve(req.approval_id)
        with pytest.raises(ValueError, match="not pending"):
            manager.approve(req.approval_id)

    def test_approve_not_found_raises(self, manager):
        with pytest.raises(ValueError, match="not found"):
            manager.approve("phantom-id")

    def test_reject_transitions_to_rejected(self, manager):
        req = manager.create(
            task_id="lc-4", action_type="payment", keywords=["payment"]
        )
        result = manager.reject(req.approval_id, reason="Denied")
        assert result.status == ApprovalStatus.REJECTED

    def test_reject_writes_reason_to_file(self, manager, approvals_dir):
        req = manager.create(
            task_id="lc-5", action_type="payment", keywords=["payment"]
        )
        manager.reject(req.approval_id, reason="Budget exceeded")
        text = (approvals_dir / f"{req.approval_id}.md").read_text()
        assert "Budget exceeded" in text

    def test_reject_already_approved_raises(self, manager):
        req = manager.create(task_id="lc-6", action_type="deploy", keywords=["deploy"])
        manager.approve(req.approval_id)
        with pytest.raises(ValueError, match="not pending"):
            manager.reject(req.approval_id)

    def test_reject_not_found_raises(self, manager):
        with pytest.raises(ValueError, match="not found"):
            manager.reject("phantom-id")

    def test_is_approved_true_after_approve(self, manager):
        req = manager.create(task_id="lc-7", action_type="deploy", keywords=["deploy"])
        assert manager.is_approved("lc-7") is False
        manager.approve(req.approval_id)
        assert manager.is_approved("lc-7") is True

    def test_is_approved_false_after_reject(self, manager):
        req = manager.create(task_id="lc-8", action_type="deploy", keywords=["deploy"])
        manager.reject(req.approval_id)
        assert manager.is_approved("lc-8") is False


# ===========================================================================
# ApprovalManager — timeout / expiry
# ===========================================================================


def _expire_request(approvals_dir: Path, req: ApprovalRequest) -> None:
    """Helper: rewrite expires_at in the file to 1 hour in the past."""
    file_path = approvals_dir / f"{req.approval_id}.md"
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    file_path.write_text(
        file_path.read_text().replace(req.expires_at.isoformat(), past)
    )


class TestApprovalManagerTimeout:
    def test_approve_expired_raises(self, manager, approvals_dir):
        req = manager.create(task_id="exp-1", action_type="deploy", keywords=["deploy"])
        _expire_request(approvals_dir, req)
        with pytest.raises(ValueError, match="expired"):
            manager.approve(req.approval_id)

    def test_check_expired_marks_timeout(self, manager, approvals_dir):
        req = manager.create(task_id="exp-2", action_type="deploy", keywords=["deploy"])
        _expire_request(approvals_dir, req)
        expired = manager.check_expired()
        assert len(expired) == 1
        assert expired[0].status == ApprovalStatus.TIMEOUT

    def test_check_expired_ignores_non_pending(self, manager, approvals_dir):
        """Already-approved requests are NOT swept by check_expired."""
        req = manager.create(task_id="exp-3", action_type="deploy", keywords=["deploy"])
        manager.approve(req.approval_id)
        _expire_request(approvals_dir, req)
        expired = manager.check_expired()
        assert len(expired) == 0

    def test_is_approved_false_when_expired(self, manager, approvals_dir):
        req = manager.create(task_id="exp-4", action_type="deploy", keywords=["deploy"])
        manager.approve(req.approval_id)
        _expire_request(approvals_dir, req)
        assert manager.is_approved("exp-4") is False


# ===========================================================================
# Integrity verification blocks tampered approvals
# ===========================================================================


class TestApprovalIntegrity:
    def test_tampered_body_blocks_approve(self, manager, approvals_dir):
        req = manager.create(task_id="int-1", action_type="deploy", keywords=["deploy"])
        file_path = approvals_dir / f"{req.approval_id}.md"

        # Tamper: replace a word in the body only
        text = file_path.read_text()
        end = text.find("---", 3)
        fm, body = text[: end + 3], text[end + 3 :]
        body = body.replace("deploy", "HACKED")
        file_path.write_text(fm + body)

        with pytest.raises(ValueError, match="tampered"):
            manager.approve(req.approval_id)

    def test_untampered_body_passes(self, manager):
        """Sanity: approve works when body is pristine."""
        req = manager.create(task_id="int-2", action_type="deploy", keywords=["deploy"])
        manager.approve(req.approval_id)  # should not raise


# ===========================================================================
# Bridge: ApprovalManager fits into Orchestrator vault layout
# ===========================================================================


class TestApprovalManagerOrchestratorBridge:
    def test_vault_layout_create_and_approve(self):
        """Simulate the vault folder layout the Orchestrator expects."""
        vault = Path(tempfile.mkdtemp())
        try:
            approvals = vault / "Approvals"
            audit = vault / ".fte" / "approval_nonces.txt"
            mgr = ApprovalManager(approvals, audit)

            # Orchestrator detects a "deploy" keyword in a task
            req = mgr.create(
                task_id="deploy-prod-server",
                action_type="deploy",
                keywords=["deploy", "production"],
                action_details={"target": "prod-k8s", "image": "myapp:2.1"},
            )

            # Not yet approved
            assert mgr.is_approved("deploy-prod-server") is False

            # Human approves
            mgr.approve(req.approval_id)
            assert mgr.is_approved("deploy-prod-server") is True

            # File exists in /Approvals
            assert (approvals / f"{req.approval_id}.md").exists()

            # Replay blocked
            with pytest.raises(ValueError, match="not pending"):
                mgr.approve(req.approval_id)
        finally:
            shutil.rmtree(vault, ignore_errors=True)

    def test_rejected_task_stays_blocked(self):
        vault = Path(tempfile.mkdtemp())
        try:
            mgr = ApprovalManager(vault / "Approvals", vault / ".fte" / "nonces.txt")
            req = mgr.create(
                task_id="delete-data",
                action_type="delete",
                keywords=["delete"],
            )
            mgr.reject(req.approval_id, reason="Risky")
            assert mgr.is_approved("delete-data") is False
        finally:
            shutil.rmtree(vault, ignore_errors=True)

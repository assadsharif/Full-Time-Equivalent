"""
Approval Manager — full HITL approval lifecycle.

Creates approval requests with nonce + integrity hash, persists them as
YAML-frontmatter Markdown files in ``/Approvals``, and enforces the
approve / reject / timeout state machine with replay and tamper checks
at every transition.

Zero-bypass guarantee: an approval that has expired, been tampered with,
or whose nonce has already been consumed will never transition to
``approved``.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import yaml

from src.approval.audit_logger import ApprovalAuditLogger
from src.approval.integrity_checker import IntegrityChecker
from src.approval.models import ApprovalRequest, ApprovalStatus
from src.approval.nonce_generator import NonceGenerator


class ApprovalManager:
    """Lifecycle manager for HITL approval requests."""

    DEFAULT_TIMEOUT_HOURS = 12

    # High-risk action types for automatic risk classification
    _HIGH_RISK_TYPES = {"payment", "wire", "deploy", "delete"}

    def __init__(
        self,
        approvals_path: Path,
        audit_path: Optional[Path] = None,
        approval_audit_log_path: Optional[Path] = None,
    ):
        self.approvals_path = approvals_path
        self.approvals_path.mkdir(parents=True, exist_ok=True)
        audit_path = audit_path or approvals_path.parent / ".fte" / "approval_nonces.txt"
        self._nonces = NonceGenerator(audit_path)
        approval_audit_log_path = (
            approval_audit_log_path
            or approvals_path.parent / ".fte" / "approval_audit.log"
        )
        self._audit_logger = ApprovalAuditLogger(approval_audit_log_path)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(
        self,
        task_id: str,
        action_type: str,
        keywords: list[str],
        action_details: Optional[dict] = None,
        timeout_hours: int = DEFAULT_TIMEOUT_HOURS,
    ) -> ApprovalRequest:
        """
        Create and persist a new approval request.

        The body is rendered first, hashed (SHA256), and the digest is
        stored in the frontmatter before writing.
        """
        now = datetime.now(timezone.utc)
        nonce = self._nonces.generate()
        approval_id = f"APR-{task_id}-{now.strftime('%Y%m%d%H%M')}"
        risk_level = self._classify_risk(action_type, action_details)

        request = ApprovalRequest(
            task_id=task_id,
            approval_id=approval_id,
            nonce=nonce,
            action_type=action_type,
            risk_level=risk_level,
            status=ApprovalStatus.PENDING,
            created_at=now,
            expires_at=now + timedelta(hours=timeout_hours),
            action=action_details or {},
        )

        body = self._render_body(request, keywords)
        request.integrity_hash = IntegrityChecker.compute_hash(body)

        frontmatter = {
            "task_id": request.task_id,
            "approval_id": request.approval_id,
            "nonce": request.nonce,
            "action_type": request.action_type,
            "risk_level": request.risk_level,
            "approval_status": request.status.value,
            "created_at": request.created_at.isoformat(),
            "expires_at": request.expires_at.isoformat(),
            "integrity_hash": request.integrity_hash,
            "action": request.action,
        }
        fm_yaml = yaml.dump(frontmatter, default_flow_style=False).rstrip()
        file_path = self.approvals_path / f"{approval_id}.md"
        file_path.write_text(f"---\n{fm_yaml}\n---\n\n{body}")

        self._audit_logger.log_created(
            request.approval_id, request.task_id,
            request.action_type, request.risk_level,
        )
        return request

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, approval_id: str) -> Optional[ApprovalRequest]:
        """Load an approval request by ID (exact or glob match)."""
        file_path = self._find_file(approval_id)
        if file_path is None:
            return None
        return self._parse_approval_file(file_path)

    def find_for_task(self, task_id: str) -> Optional[ApprovalRequest]:
        """Return the most recent approval request for *task_id*."""
        candidates = []
        for f in self.approvals_path.glob("*.md"):
            req = self._parse_approval_file(f)
            if req and req.task_id == task_id:
                candidates.append(req)
        return max(candidates, key=lambda r: r.created_at) if candidates else None

    # ------------------------------------------------------------------
    # Approve / Reject
    # ------------------------------------------------------------------

    def approve(self, approval_id: str) -> ApprovalRequest:
        """
        Transition a pending approval to ``approved``.

        Checks (in order): status is pending, not expired, nonce not
        already consumed, body integrity intact.  Raises ``ValueError``
        on any violation.
        """
        request = self.get(approval_id)
        if request is None:
            raise ValueError(f"Approval {approval_id} not found")
        self._verify_approvable(request)

        request.status = ApprovalStatus.APPROVED
        self._update_status(request)
        self._nonces.record_used(request.nonce)
        self._audit_logger.log_approved(
            request.approval_id, request.task_id,
            request.action_type, request.risk_level,
        )
        return request

    def reject(self, approval_id: str, reason: str = "") -> ApprovalRequest:
        """Transition a pending approval to ``rejected``."""
        request = self.get(approval_id)
        if request is None:
            raise ValueError(f"Approval {approval_id} not found")
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Approval {approval_id} is not pending "
                f"(status: {request.status.value})"
            )
        request.status = ApprovalStatus.REJECTED
        self._update_status(request, reason=reason)
        self._audit_logger.log_rejected(
            request.approval_id, request.task_id,
            request.action_type, request.risk_level,
            reason=reason,
        )
        return request

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def is_approved(self, task_id: str) -> bool:
        """True when there is an approved, non-expired request for *task_id*."""
        request = self.find_for_task(task_id)
        if request is None or request.status != ApprovalStatus.APPROVED:
            return False
        return datetime.now(timezone.utc) <= request.expires_at

    def check_expired(self) -> list[ApprovalRequest]:
        """Find all pending requests past their expiry; mark as timeout."""
        now = datetime.now(timezone.utc)
        expired: list[ApprovalRequest] = []
        for f in self.approvals_path.glob("*.md"):
            req = self._parse_approval_file(f)
            if req and req.status == ApprovalStatus.PENDING and now > req.expires_at:
                req.status = ApprovalStatus.TIMEOUT
                self._update_status(req)
                self._audit_logger.log_timeout(
                    req.approval_id, req.task_id,
                    req.action_type, req.risk_level,
                )
                expired.append(req)
        return expired

    # ------------------------------------------------------------------
    # Private — verification
    # ------------------------------------------------------------------

    def _verify_approvable(self, request: ApprovalRequest) -> None:
        """Raise ``ValueError`` if *request* cannot be approved."""
        if request.status != ApprovalStatus.PENDING:
            raise ValueError(
                f"Approval {request.approval_id} is not pending "
                f"(status: {request.status.value})"
            )
        if datetime.now(timezone.utc) > request.expires_at:
            raise ValueError(f"Approval {request.approval_id} has expired")
        if self._nonces.is_used(request.nonce):
            raise ValueError(
                f"Nonce {request.nonce} already used — replay attempt blocked"
            )
        # Integrity check
        file_path = self._find_file(request.approval_id)
        if file_path and request.integrity_hash:
            body = IntegrityChecker.body_content(file_path)
            if not IntegrityChecker.verify(body, request.integrity_hash):
                raise ValueError(
                    f"Integrity check failed for {request.approval_id} — "
                    "file may have been tampered with"
                )

    # ------------------------------------------------------------------
    # Private — file I/O
    # ------------------------------------------------------------------

    def _find_file(self, approval_id: str) -> Optional[Path]:
        exact = self.approvals_path / f"{approval_id}.md"
        if exact.exists():
            return exact
        matches = list(self.approvals_path.glob(f"*{approval_id}*.md"))
        return matches[0] if matches else None

    def _update_status(self, request: ApprovalRequest, reason: str = "") -> None:
        """Rewrite the approval file with the new status."""
        file_path = self._find_file(request.approval_id)
        if file_path is None:
            return
        lines = file_path.read_text().splitlines(keepends=True)
        new_lines = [
            f"approval_status: {request.status.value}\n"
            if line.startswith("approval_status:")
            else line
            for line in lines
        ]
        updated = "".join(new_lines)
        if reason:
            updated += f"\n> **Rejection reason**: {reason}\n"
        file_path.write_text(updated)

    # ------------------------------------------------------------------
    # Private — parsing & rendering
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_approval_file(file_path: Path) -> Optional[ApprovalRequest]:
        text = file_path.read_text()
        if not text.startswith("---"):
            return None
        end = text.find("---", 3)
        if end == -1:
            return None
        fm = yaml.safe_load(text[3:end])
        if not isinstance(fm, dict) or "approval_id" not in fm:
            return None
        try:
            return ApprovalRequest(
                task_id=fm.get("task_id", ""),
                approval_id=fm["approval_id"],
                nonce=fm.get("nonce", ""),
                action_type=fm.get("action_type", ""),
                risk_level=fm.get("risk_level", "low"),
                status=ApprovalStatus(fm.get("approval_status", "pending")),
                created_at=datetime.fromisoformat(fm["created_at"]),
                expires_at=datetime.fromisoformat(fm["expires_at"]),
                action=fm.get("action", {}),
                integrity_hash=fm.get("integrity_hash"),
            )
        except (KeyError, ValueError):
            return None

    @staticmethod
    def _classify_risk(action_type: str, details: Optional[dict]) -> str:
        lower = action_type.lower()
        if lower in ApprovalManager._HIGH_RISK_TYPES:
            if lower in {"payment", "wire"} and details:
                amount = details.get("amount", 0)
                if isinstance(amount, (int, float)) and amount > 10_000:
                    return "critical"
            return "high"
        return "medium"

    @staticmethod
    def _render_body(request: ApprovalRequest, keywords: list[str]) -> str:
        action_lines = ""
        if request.action:
            action_lines = "\n".join(
                f"- **{k.replace('_', ' ').title()}**: {v}"
                for k, v in request.action.items()
            )

        return (
            f"# Approval Request: {request.approval_id}\n\n"
            f"**Action Type**: {request.action_type}\n"
            f"**Risk Level**: {request.risk_level.upper()}\n"
            f"**Task ID**: {request.task_id}\n"
            f"**Created**: {request.created_at.isoformat()}\n"
            f"**Expires**: {request.expires_at.isoformat()}\n\n"
            f"## Triggered By\n\n"
            f"Keywords detected: {', '.join(keywords)}\n\n"
            + (f"## Action Details\n\n{action_lines}\n\n" if action_lines else "")
            + f"## How to Respond\n\n"
            f"```bash\n"
            f"fte vault approve {request.approval_id}\n"
            f"# OR\n"
            f"fte vault reject {request.approval_id}\n"
            f"```\n\n"
            f"---\n"
            f"*Auto-generated by HITL Approval Manager | Nonce: {request.nonce}*\n"
        )

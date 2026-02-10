"""
MCP Security — Bronze tier unit tests (spec 004).

Coverage map:
  TestCredentialVault    — store/retrieve, overwrite, delete, missing, list, isolation
  TestAuditLogger        — mcp_action, credential_access, scan_result, query_recent,
                           empty log, append-only ordering
  TestSecretsScanner     — AWS key, password, clean text, scan_file, scan_directory,
                           redaction, no false positives on short strings
"""

import shutil
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_dir():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


# ===========================================================================
# CredentialVault
# ===========================================================================


class TestCredentialVault:
    def _vault(self, tmp: Path):
        from src.security.credential_vault import CredentialVault

        return CredentialVault(tmp)

    def test_store_and_retrieve(self, tmp_dir):
        vault = self._vault(tmp_dir)
        vault.store("gmail-mcp", "user@x.com", "secret-key-123")
        assert vault.retrieve("gmail-mcp", "user@x.com") == "secret-key-123"

    def test_overwrite_credential(self, tmp_dir):
        vault = self._vault(tmp_dir)
        vault.store("svc", "alice", "old")
        vault.store("svc", "alice", "new")
        assert vault.retrieve("svc", "alice") == "new"

    def test_delete_credential(self, tmp_dir):
        from src.security.credential_vault import CredentialNotFoundError

        vault = self._vault(tmp_dir)
        vault.store("svc", "bob", "val")
        vault.delete("svc", "bob")
        with pytest.raises(CredentialNotFoundError):
            vault.retrieve("svc", "bob")

    def test_retrieve_missing_raises(self, tmp_dir):
        from src.security.credential_vault import CredentialNotFoundError

        vault = self._vault(tmp_dir)
        with pytest.raises(CredentialNotFoundError):
            vault.retrieve("nonexistent", "nobody")

    def test_delete_missing_raises(self, tmp_dir):
        from src.security.credential_vault import CredentialNotFoundError

        vault = self._vault(tmp_dir)
        with pytest.raises(CredentialNotFoundError):
            vault.delete("no-svc", "no-user")

    def test_list_services(self, tmp_dir):
        vault = self._vault(tmp_dir)
        vault.store("alpha", "u1", "c1")
        vault.store("beta", "u2", "c2")
        services = vault.list_services()
        assert "alpha" in services
        assert "beta" in services

    def test_multiple_users_same_service(self, tmp_dir):
        vault = self._vault(tmp_dir)
        vault.store("svc", "alice", "a-secret")
        vault.store("svc", "bob", "b-secret")
        assert vault.retrieve("svc", "alice") == "a-secret"
        assert vault.retrieve("svc", "bob") == "b-secret"

    def test_delete_one_user_keeps_other(self, tmp_dir):
        vault = self._vault(tmp_dir)
        vault.store("svc", "alice", "a")
        vault.store("svc", "bob", "b")
        vault.delete("svc", "alice")
        assert vault.retrieve("svc", "bob") == "b"

    def test_delete_last_user_removes_service(self, tmp_dir):
        vault = self._vault(tmp_dir)
        vault.store("solo", "only", "val")
        vault.delete("solo", "only")
        assert "solo" not in vault.list_services()

    def test_encrypted_file_is_not_plaintext(self, tmp_dir):
        """The on-disk credential file must not contain the plaintext secret."""
        vault = self._vault(tmp_dir)
        vault.store("test-svc", "u", "SUPER_SECRET_VALUE_12345")
        enc_file = tmp_dir / ".fte" / "security" / "credentials.json.enc"
        raw = enc_file.read_bytes()
        assert b"SUPER_SECRET_VALUE_12345" not in raw


# ===========================================================================
# SecurityAuditLogger
# ===========================================================================


class TestAuditLogger:
    def _logger(self, tmp: Path):
        from src.security.audit_logger import SecurityAuditLogger

        return SecurityAuditLogger(tmp / "audit.log")

    def test_log_mcp_action(self, tmp_dir):
        from src.security.models import RiskLevel

        logger = self._logger(tmp_dir)
        logger.log_mcp_action(
            mcp_server="gmail-mcp",
            action="send_email",
            approved=True,
            risk_level=RiskLevel.HIGH,
            result="success",
            duration_ms=234,
        )
        events = logger.query_recent()
        assert len(events) == 1
        assert events[0]["event_type"] == "mcp_action"
        assert events[0]["mcp_server"] == "gmail-mcp"
        assert events[0]["approved"] is True
        assert events[0]["risk_level"] == "high"
        assert events[0]["duration_ms"] == 234

    def test_log_credential_access(self, tmp_dir):
        logger = self._logger(tmp_dir)
        logger.log_credential_access("gmail-mcp", "store", "user@x.com")
        events = logger.query_recent()
        assert len(events) == 1
        assert events[0]["event_type"] == "credential_access"
        assert events[0]["risk_level"] == "critical"
        assert events[0]["details"]["operation"] == "store"

    def test_log_scan_result_with_findings(self, tmp_dir):
        logger = self._logger(tmp_dir)
        findings = [{"type": "AWS Key", "line": 3}]
        logger.log_scan_result("vault/secret.md", findings)
        events = logger.query_recent()
        assert events[0]["risk_level"] == "high"
        assert events[0]["details"]["finding_count"] == 1

    def test_log_scan_result_no_findings(self, tmp_dir):
        logger = self._logger(tmp_dir)
        logger.log_scan_result("vault/clean.md", [])
        events = logger.query_recent()
        assert events[0]["risk_level"] == "low"
        assert events[0]["details"]["finding_count"] == 0

    def test_query_recent_empty_log(self, tmp_dir):
        logger = self._logger(tmp_dir)
        assert logger.query_recent() == []

    def test_append_only_ordering(self, tmp_dir):
        from src.security.models import RiskLevel

        logger = self._logger(tmp_dir)
        for i in range(5):
            logger.log_mcp_action("svc", f"action-{i}", True, RiskLevel.LOW)
        events = logger.query_recent()
        assert len(events) == 5
        # Actions appear in insertion order
        for i, ev in enumerate(events):
            assert ev["action"] == f"action-{i}"

    def test_query_recent_respects_limit(self, tmp_dir):
        from src.security.models import RiskLevel

        logger = self._logger(tmp_dir)
        for i in range(10):
            logger.log_mcp_action("svc", f"a{i}", True, RiskLevel.LOW)
        events = logger.query_recent(limit=3)
        assert len(events) == 3
        # Should be the last 3
        assert events[0]["action"] == "a7"


# ===========================================================================
# SecretsScanner
# ===========================================================================


class TestSecretsScanner:
    def _scanner(self):
        from src.security.secrets_scanner import SecretsScanner

        return SecretsScanner()

    def test_detects_aws_access_key(self):
        scanner = self._scanner()
        text = 'aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"\n'
        findings = scanner.scan_text(text)
        assert len(findings) >= 1
        assert any("AWS" in f.secret_type or "Key" in f.secret_type for f in findings)

    def test_detects_password(self):
        scanner = self._scanner()
        text = 'password = "hunter2supersecret"\n'
        findings = scanner.scan_text(text)
        assert len(findings) >= 1

    def test_clean_text_no_findings(self):
        scanner = self._scanner()
        text = "This is a normal line of text with no secrets.\nHello world.\n"
        findings = scanner.scan_text(text)
        assert findings == []

    def test_scan_file(self, tmp_dir):
        scanner = self._scanner()
        f = tmp_dir / "leaky.txt"
        f.write_text('API_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
        findings = scanner.scan_file(f)
        assert len(findings) >= 1
        assert findings[0].file_path == str(f)
        assert findings[0].line_number is not None

    def test_scan_missing_file_returns_empty(self, tmp_dir):
        scanner = self._scanner()
        assert scanner.scan_file(tmp_dir / "ghost.txt") == []

    def test_scan_directory(self, tmp_dir):
        scanner = self._scanner()
        (tmp_dir / "clean.md").write_text("# Hello\nJust a doc.\n")
        (tmp_dir / "leaky.md").write_text(
            'secret_key = "abcdefghijklmnopqrstuvwxyz1234"\n'
        )
        findings = scanner.scan_directory(tmp_dir, glob="*.md")
        # At least the leaky file should produce a finding
        assert len(findings) >= 1
        assert any("leaky.md" in (f.file_path or "") for f in findings)

    def test_redacted_context_hides_secret(self):
        scanner = self._scanner()
        text = 'API_KEY = "AKIAIOSFODNN7EXAMPLE"\n'
        findings = scanner.scan_text(text)
        for f in findings:
            assert "AKIAIOSFODNN7EXAMPLE" not in f.redacted_context

    def test_short_values_not_flagged_as_tokens(self):
        """Short identifiers like variable names must not trigger Token pattern."""
        scanner = self._scanner()
        text = "token = short\n"
        findings = scanner.scan_text(text)
        # "short" is only 5 chars — should not match any pattern
        token_findings = [f for f in findings if f.secret_type == "Token"]
        assert token_findings == []


# ===========================================================================
# MCPVerifier — Silver tier
# ===========================================================================


class TestMCPVerifier:
    def _verifier(self, tmp: Path):
        from src.security.mcp_verifier import MCPVerifier

        return MCPVerifier(tmp / "mcp-signatures.json")

    def test_calculate_signature_deterministic(self, tmp_dir):
        from src.security.mcp_verifier import MCPVerifier

        f = tmp_dir / "server.py"
        f.write_text("print('hello')\n")
        sig1 = MCPVerifier.calculate_signature(f)
        sig2 = MCPVerifier.calculate_signature(f)
        assert sig1 == sig2
        assert len(sig1) == 64  # SHA256 hex

    def test_calculate_signature_changes_on_edit(self, tmp_dir):
        from src.security.mcp_verifier import MCPVerifier

        f = tmp_dir / "server.py"
        f.write_text("v1\n")
        sig1 = MCPVerifier.calculate_signature(f)
        f.write_text("v2\n")
        sig2 = MCPVerifier.calculate_signature(f)
        assert sig1 != sig2

    def test_calculate_signature_missing_file(self, tmp_dir):
        from src.security.mcp_verifier import MCPVerifier

        with pytest.raises(FileNotFoundError):
            MCPVerifier.calculate_signature(tmp_dir / "ghost.py")

    def test_add_and_list_trusted(self, tmp_dir):
        v = self._verifier(tmp_dir)
        v.add_trusted("gmail-mcp", "abc123")
        v.add_trusted("slack-mcp", "def456")
        store = v.list_trusted()
        assert store == {"gmail-mcp": "abc123", "slack-mcp": "def456"}

    def test_remove_trusted(self, tmp_dir):
        v = self._verifier(tmp_dir)
        v.add_trusted("svc", "sig")
        v.remove_trusted("svc")
        assert v.list_trusted() == {}

    def test_verify_server_success(self, tmp_dir):
        from src.security.mcp_verifier import MCPVerifier

        v = self._verifier(tmp_dir)
        f = tmp_dir / "server.py"
        f.write_text("content\n")
        sig = MCPVerifier.calculate_signature(f)
        v.add_trusted("test-mcp", sig)
        assert v.verify_server("test-mcp", f) is True

    def test_verify_server_tampered(self, tmp_dir):
        from src.security.mcp_verifier import MCPVerifier, VerificationError

        v = self._verifier(tmp_dir)
        f = tmp_dir / "server.py"
        f.write_text("original\n")
        sig = MCPVerifier.calculate_signature(f)
        v.add_trusted("test-mcp", sig)

        # Tamper with the file
        f.write_text("tampered!\n")
        with pytest.raises(VerificationError):
            v.verify_server("test-mcp", f)

    def test_verify_server_not_in_store(self, tmp_dir):
        v = self._verifier(tmp_dir)
        with pytest.raises(KeyError):
            v.verify_server("unknown", tmp_dir / "any.py")

    def test_is_trusted_returns_false_for_unknown(self, tmp_dir):
        v = self._verifier(tmp_dir)
        assert v.is_trusted("unknown", tmp_dir / "any.py") is False

    def test_is_trusted_returns_false_for_tampered(self, tmp_dir):
        from src.security.mcp_verifier import MCPVerifier

        v = self._verifier(tmp_dir)
        f = tmp_dir / "server.py"
        f.write_text("original\n")
        v.add_trusted("svc", MCPVerifier.calculate_signature(f))
        f.write_text("tampered\n")
        assert v.is_trusted("svc", f) is False


# ===========================================================================
# RateLimiter — Silver tier
# ===========================================================================


class TestRateLimiter:
    def _limiter(self, tmp: Path, limits: dict = None):
        from src.security.rate_limiter import RateLimiter

        return RateLimiter(
            state_path=tmp / "rate_limits.json",
            default_limits=limits
            or {
                "email": {"per_minute": 10, "per_hour": 100},
                "payment": {"per_minute": 1, "per_hour": 10},
            },
        )

    def test_consume_succeeds_within_limit(self, tmp_dir):
        rl = self._limiter(tmp_dir)
        assert rl.consume("gmail", "email") is True

    def test_consume_exhausts_bucket(self, tmp_dir):
        from src.security.rate_limiter import RateLimitExceededError

        # Use a tiny bucket: max 3 tokens, 1/min refill
        rl = self._limiter(tmp_dir, {"action": {"per_minute": 1, "per_hour": 3}})
        rl.consume("svc", "action")
        rl.consume("svc", "action")
        rl.consume("svc", "action")
        with pytest.raises(RateLimitExceededError):
            rl.consume("svc", "action")

    def test_remaining_reflects_consumed(self, tmp_dir):
        rl = self._limiter(tmp_dir, {"pay": {"per_minute": 1, "per_hour": 10}})
        before = rl.remaining("svc", "pay")
        rl.consume("svc", "pay", tokens=3)
        after = rl.remaining("svc", "pay")
        assert after < before

    def test_unknown_action_uses_generous_default(self, tmp_dir):
        """Actions without explicit config get a permissive fallback."""
        rl = self._limiter(tmp_dir, {})  # no configured limits
        # Should not raise — default is 3600 tokens/hour
        assert rl.consume("svc", "unknown_action") is True

    def test_separate_buckets_per_server(self, tmp_dir):
        from src.security.rate_limiter import RateLimitExceededError

        rl = self._limiter(tmp_dir, {"pay": {"per_minute": 1, "per_hour": 1}})
        rl.consume("server-a", "pay")  # exhausts server-a's bucket
        with pytest.raises(RateLimitExceededError):
            rl.consume("server-a", "pay")
        # server-b still has a full bucket
        assert rl.consume("server-b", "pay") is True

    def test_add_limit_overrides_default(self, tmp_dir):
        rl = self._limiter(tmp_dir, {"email": {"per_minute": 10, "per_hour": 100}})
        rl.add_limit("email", per_minute=1, per_hour=2)
        # New bucket for a fresh server will use the updated limit
        rl.consume("new-svc", "email")
        rl.consume("new-svc", "email")
        from src.security.rate_limiter import RateLimitExceededError

        with pytest.raises(RateLimitExceededError):
            rl.consume("new-svc", "email")

    def test_state_persisted_to_disk(self, tmp_dir):
        rl = self._limiter(tmp_dir, {"pay": {"per_minute": 1, "per_hour": 10}})
        rl.consume("svc", "pay", tokens=5)

        state_file = tmp_dir / "rate_limits.json"
        assert state_file.exists()
        import json

        data = json.loads(state_file.read_text())
        assert "svc:pay" in data
        assert data["svc:pay"]["tokens"] == 5.0


# ===========================================================================
# CredentialVault.rotate — Gold tier
# ===========================================================================


class TestCredentialRotation:
    def _vault(self, tmp: Path):
        from src.security.credential_vault import CredentialVault

        return CredentialVault(tmp)

    def test_rotate_returns_old_credential(self, tmp_dir):
        vault = self._vault(tmp_dir)
        vault.store("svc", "user", "old-secret")
        old = vault.rotate("svc", "user", "new-secret")
        assert old == "old-secret"

    def test_rotate_stores_new_credential(self, tmp_dir):
        vault = self._vault(tmp_dir)
        vault.store("svc", "user", "original")
        vault.rotate("svc", "user", "rotated")
        assert vault.retrieve("svc", "user") == "rotated"

    def test_rotate_missing_raises(self, tmp_dir):
        from src.security.credential_vault import CredentialNotFoundError

        vault = self._vault(tmp_dir)
        with pytest.raises(CredentialNotFoundError):
            vault.rotate("ghost", "nobody", "val")


# ===========================================================================
# MCPGuard — Gold tier (composite gate)
# ===========================================================================


class TestMCPGuard:
    def _guard(self, tmp: Path):
        from src.security.audit_logger import SecurityAuditLogger
        from src.security.rate_limiter import RateLimiter
        from src.security.mcp_guard import MCPGuard

        rl = RateLimiter(
            state_path=tmp / "rate_limits.json",
            default_limits={"email": {"per_minute": 10, "per_hour": 100}},
        )
        audit = SecurityAuditLogger(tmp / "audit.log")
        return MCPGuard(
            rate_limiter=rl,
            audit_logger=audit,
            failure_threshold=2,
            recovery_timeout=0.1,
        )

    def test_successful_call_logged(self, tmp_dir):
        from src.security.audit_logger import SecurityAuditLogger
        from src.security.models import RiskLevel

        guard = self._guard(tmp_dir)
        result = guard.call("gmail", "email", lambda: "ok", risk_level=RiskLevel.MEDIUM)
        assert result == "ok"

        audit = SecurityAuditLogger(tmp_dir / "audit.log")
        events = audit.query_recent()
        assert len(events) == 1
        assert events[0]["result"] == "success"
        assert events[0]["mcp_server"] == "gmail"

    def test_exception_in_fn_is_logged_and_raised(self, tmp_dir):
        from src.security.audit_logger import SecurityAuditLogger

        guard = self._guard(tmp_dir)

        def boom():
            raise ValueError("explode")

        with pytest.raises(ValueError, match="explode"):
            guard.call("slack", "email", boom)

        audit = SecurityAuditLogger(tmp_dir / "audit.log")
        events = audit.query_recent()
        assert "ValueError" in events[0]["result"]

    def test_rate_limit_fires_and_is_logged(self, tmp_dir):
        from src.security.audit_logger import SecurityAuditLogger
        from src.security.rate_limiter import RateLimiter, RateLimitExceededError
        from src.security.mcp_guard import MCPGuard

        # Tiny bucket: 2 tokens max
        rl = RateLimiter(
            state_path=tmp_dir / "rate_limits.json",
            default_limits={"pay": {"per_minute": 1, "per_hour": 2}},
        )
        audit = SecurityAuditLogger(tmp_dir / "audit.log")
        guard = MCPGuard(rate_limiter=rl, audit_logger=audit)

        guard.call("svc", "pay", lambda: None)
        guard.call("svc", "pay", lambda: None)

        with pytest.raises(RateLimitExceededError):
            guard.call("svc", "pay", lambda: None)

        events = audit.query_recent()
        assert events[-1]["result"] == "rate_limit_exceeded"

    def test_circuit_breaker_opens_after_failures(self, tmp_dir):
        from watchers.circuit_breaker import CircuitBreakerError

        guard = self._guard(tmp_dir)  # failure_threshold=2

        # Two failures trip the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                guard.call(
                    "flaky",
                    "email",
                    lambda: (_ for _ in ()).throw(RuntimeError("fail")),
                )

        # Third call should hit open circuit
        with pytest.raises(CircuitBreakerError):
            guard.call("flaky", "email", lambda: None)

    def test_breaker_state_default_is_closed(self, tmp_dir):
        guard = self._guard(tmp_dir)
        assert guard.breaker_state("unknown-server") == "closed"

    def test_duration_ms_recorded(self, tmp_dir):
        import time as _time

        from src.security.audit_logger import SecurityAuditLogger

        guard = self._guard(tmp_dir)

        def slow():
            _time.sleep(0.05)
            return "done"

        guard.call("gmail", "email", slow)
        events = SecurityAuditLogger(tmp_dir / "audit.log").query_recent()
        assert events[0]["duration_ms"] >= 40  # ~50ms sleep, allow margin

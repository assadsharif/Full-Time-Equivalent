"""
Unit tests for CLI error module.

Covers the exception hierarchy, error-formatting helpers,
safe_execute, ErrorMetrics, and the error_context context manager.
"""

import sys

sys.path.insert(0, ".")

from cli.errors import (
    CLIError,
    VaultNotFoundError,
    VaultNotInitializedError,
    ConfigError,
    ConfigNotFoundError,
    ConfigValidationError,
    WatcherError,
    MCPError,
    ApprovalError,
    ApprovalExpiredError,
    ApprovalInvalidNonceError,
    ApprovalIntegrityError,
    BriefingError,
    BriefingNotFoundError,
    CheckpointError,
    CheckpointLoadError,
    CheckpointSaveError,
    safe_execute,
    get_error_context,
    format_error_for_user,
    ErrorMetrics,
)

# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------


def test_cli_error_defaults():
    e = CLIError("boom")
    assert e.message == "boom"
    assert e.exit_code == 1
    assert str(e) == "boom"


def test_cli_error_custom_exit_code():
    e = CLIError("oops", exit_code=42)
    assert e.exit_code == 42


def test_vault_not_found_error_default_message():
    e = VaultNotFoundError()
    assert "not found" in e.message.lower()
    assert e.exit_code == 1


def test_vault_not_found_error_custom_message():
    e = VaultNotFoundError("custom msg")
    assert e.message == "custom msg"


def test_vault_not_initialized_error():
    e = VaultNotInitializedError()
    assert "vault init" in e.message.lower()


def test_config_error_prefix():
    e = ConfigError("bad yaml")
    assert "Configuration error" in e.message


def test_config_not_found_error():
    e = ConfigNotFoundError("/etc/missing.yaml")
    assert "/etc/missing.yaml" in e.message


def test_config_validation_error():
    e = ConfigValidationError("field X missing")
    assert "field X missing" in e.message


def test_approval_expired_error():
    e = ApprovalExpiredError("A123", "2026-01-01T00:00:00Z")
    assert "A123" in e.message
    assert "2026-01-01" in e.message


def test_approval_invalid_nonce_error():
    e = ApprovalInvalidNonceError("A456")
    assert "A456" in e.message
    assert "nonce" in e.message.lower()


def test_approval_integrity_error():
    e = ApprovalIntegrityError("A789")
    assert "A789" in e.message
    assert "tampered" in e.message.lower()


def test_briefing_not_found_error():
    e = BriefingNotFoundError()
    assert "generate" in e.message.lower()


def test_checkpoint_load_error():
    e = CheckpointLoadError("/tmp/cp.json", "file locked")
    assert "/tmp/cp.json" in e.message
    assert "file locked" in e.message


def test_checkpoint_save_error():
    e = CheckpointSaveError("/tmp/cp.json", "disk full")
    assert "/tmp/cp.json" in e.message
    assert "disk full" in e.message


# ---------------------------------------------------------------------------
# Inheritance chains
# ---------------------------------------------------------------------------


def test_vault_errors_are_cli_errors():
    assert issubclass(VaultNotFoundError, CLIError)
    assert issubclass(VaultNotInitializedError, CLIError)


def test_config_errors_inherit():
    assert issubclass(ConfigNotFoundError, ConfigError)
    assert issubclass(ConfigValidationError, ConfigError)
    assert issubclass(ConfigError, CLIError)


def test_approval_errors_inherit():
    assert issubclass(ApprovalExpiredError, ApprovalError)
    assert issubclass(ApprovalInvalidNonceError, ApprovalError)
    assert issubclass(ApprovalIntegrityError, ApprovalError)
    assert issubclass(ApprovalError, CLIError)


def test_checkpoint_errors_inherit():
    assert issubclass(CheckpointLoadError, CheckpointError)
    assert issubclass(CheckpointSaveError, CheckpointError)
    assert issubclass(CheckpointError, CLIError)


# ---------------------------------------------------------------------------
# safe_execute
# ---------------------------------------------------------------------------


def test_safe_execute_success():
    called = []

    def ok_fn():
        called.append(True)

    success, err = safe_execute(ok_fn)
    assert success is True
    assert err is None
    assert called == [True]


def test_safe_execute_failure():
    def boom():
        raise ValueError("kaboom")

    success, err = safe_execute(boom)
    assert success is False
    assert isinstance(err, ValueError)
    assert "kaboom" in str(err)


# ---------------------------------------------------------------------------
# get_error_context
# ---------------------------------------------------------------------------


def test_get_error_context_cli_error():
    e = CLIError("test", exit_code=2)
    ctx = get_error_context(e)
    assert ctx["error_type"] == "CLIError"
    assert ctx["is_cli_error"] is True
    assert ctx["exit_code"] == 2
    assert ctx["error_message"] == "test"


def test_get_error_context_generic():
    e = RuntimeError("generic")
    ctx = get_error_context(e)
    assert ctx["error_type"] == "RuntimeError"
    assert ctx["is_cli_error"] is False
    assert ctx["exit_code"] == 1  # default


# ---------------------------------------------------------------------------
# format_error_for_user
# ---------------------------------------------------------------------------


def test_format_cli_error():
    e = CLIError("user-friendly msg")
    assert format_error_for_user(e) == "user-friendly msg"


def test_format_file_not_found():
    e = FileNotFoundError()
    e.filename = "/tmp/nope.txt"
    assert "/tmp/nope.txt" in format_error_for_user(e)


def test_format_permission_error():
    e = PermissionError()
    e.filename = "/root/secret"
    assert "/root/secret" in format_error_for_user(e)


def test_format_keyboard_interrupt():
    e = KeyboardInterrupt()
    assert "cancelled" in format_error_for_user(e).lower()


def test_format_unknown_error():
    e = RuntimeError("something weird")
    msg = format_error_for_user(e)
    assert "something weird" in msg
    assert "Unexpected" in msg


# ---------------------------------------------------------------------------
# ErrorMetrics
# ---------------------------------------------------------------------------


def test_error_metrics_empty():
    m = ErrorMetrics()
    stats = m.get_stats()
    assert stats["total_errors"] == 0
    assert stats["error_counts"] == {}
    assert stats["recent_errors"] == []


def test_error_metrics_record_and_count():
    m = ErrorMetrics()
    m.record_error(ValueError("v1"), command="status")
    m.record_error(ValueError("v2"), command="init")
    m.record_error(RuntimeError("r1"), command="status")

    stats = m.get_stats()
    assert stats["total_errors"] == 3
    assert stats["error_counts"]["ValueError"] == 2
    assert stats["error_counts"]["RuntimeError"] == 1


def test_error_metrics_recent_errors_capped():
    m = ErrorMetrics()
    for i in range(15):
        m.record_error(RuntimeError(str(i)))

    stats = m.get_stats()
    # recent_errors returns last 10
    assert len(stats["recent_errors"]) == 10


def test_error_metrics_clear():
    m = ErrorMetrics()
    m.record_error(ValueError("x"))
    m.clear()
    stats = m.get_stats()
    assert stats["total_errors"] == 0

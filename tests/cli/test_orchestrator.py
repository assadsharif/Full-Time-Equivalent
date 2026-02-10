"""
Unit tests for orchestrator CLI module.

Tests the _parse_since duration parser which is the core
pure-logic function in src/cli/orchestrator.py.
The Click commands themselves require vault + orchestrator
infrastructure and are covered by integration / e2e tests.
"""

import sys
import types

sys.path.insert(0, ".")

from datetime import datetime, timezone
import click

# ---------------------------------------------------------------------------
# Stub cli.utils before importing orchestrator to avoid the logging shadow.
# orchestrator.py does "from cli.utils import ..." which needs src/ on path,
# but that triggers src/logging/__init__.py.  Pre-seed stubs instead.
# ---------------------------------------------------------------------------
_cli_utils_stub = types.ModuleType("cli.utils")
_cli_utils_stub.display_error = lambda *a, **kw: None
_cli_utils_stub.display_info = lambda *a, **kw: None
_cli_utils_stub.resolve_vault_path = lambda *a, **kw: None
_cli_utils_stub.validate_vault_or_error = lambda *a, **kw: True
if "cli" not in sys.modules:
    sys.modules["cli"] = types.ModuleType("cli")
sys.modules["cli.utils"] = _cli_utils_stub

from cli.orchestrator import _parse_since

# ---------------------------------------------------------------------------
# _parse_since — valid inputs
# ---------------------------------------------------------------------------


def test_parse_since_hours():
    before = datetime.now(timezone.utc)
    result = _parse_since("24h")
    # Should be ~24 hours ago
    diff = (before - result).total_seconds()
    assert 86390 < diff < 86410  # 24*3600 ± 10 s tolerance


def test_parse_since_days():
    before = datetime.now(timezone.utc)
    result = _parse_since("7d")
    diff = (before - result).total_seconds()
    expected = 7 * 86400
    assert expected - 10 < diff < expected + 10


def test_parse_since_1h():
    before = datetime.now(timezone.utc)
    result = _parse_since("1h")
    diff = (before - result).total_seconds()
    assert 3590 < diff < 3610


def test_parse_since_30d():
    before = datetime.now(timezone.utc)
    result = _parse_since("30d")
    diff = (before - result).total_seconds()
    expected = 30 * 86400
    assert expected - 10 < diff < expected + 10


def test_parse_since_result_is_aware():
    result = _parse_since("1h")
    assert result.tzinfo is not None


# ---------------------------------------------------------------------------
# _parse_since — invalid inputs
# ---------------------------------------------------------------------------


def test_parse_since_empty_string_raises():
    try:
        _parse_since("")
        assert False, "should raise"
    except click.BadParameter:
        pass


def test_parse_since_unknown_unit_raises():
    try:
        _parse_since("5x")
        assert False, "should raise"
    except click.BadParameter as e:
        assert "x" in str(e)


def test_parse_since_non_numeric_raises():
    try:
        _parse_since("abch")
        assert False, "should raise"
    except click.BadParameter:
        pass


def test_parse_since_zero_raises():
    try:
        _parse_since("0h")
        assert False, "should raise"
    except click.BadParameter:
        pass


def test_parse_since_negative_raises():
    try:
        _parse_since("-3d")
        assert False, "should raise"
    except click.BadParameter:
        pass

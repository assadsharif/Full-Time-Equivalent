"""
Unit tests for security CLI module.

Tests the _parse_time_window helper which converts duration
strings ("1h", "24h", "7d", "30m") to integer hours.
The Click commands (alerts, scan, isolate, …) depend on vault
infrastructure and are covered by integration / e2e tests.
"""

import sys
import types

sys.path.insert(0, ".")


# ---------------------------------------------------------------------------
# Stub cli.config before importing security.py to avoid the logging shadow.
# security.py does "from cli.config import get_config" which needs src/ on
# path; pre-seeding sidesteps the circular import.
# ---------------------------------------------------------------------------
class _StubConfig:
    vault_path = "/tmp"


_cli_config_stub = types.ModuleType("cli.config")
_cli_config_stub.get_config = lambda: _StubConfig()
if "cli" not in sys.modules:
    sys.modules["cli"] = types.ModuleType("cli")
sys.modules["cli.config"] = _cli_config_stub

from cli.security import _parse_time_window

# ---------------------------------------------------------------------------
# _parse_time_window — hours
# ---------------------------------------------------------------------------


def test_parse_hours_1():
    assert _parse_time_window("1h") == 1


def test_parse_hours_24():
    assert _parse_time_window("24h") == 24


def test_parse_hours_100():
    assert _parse_time_window("100h") == 100


# ---------------------------------------------------------------------------
# _parse_time_window — days (converted to hours)
# ---------------------------------------------------------------------------


def test_parse_days_1():
    assert _parse_time_window("1d") == 24


def test_parse_days_7():
    assert _parse_time_window("7d") == 168


def test_parse_days_30():
    assert _parse_time_window("30d") == 720


# ---------------------------------------------------------------------------
# _parse_time_window — minutes (floored to hours, minimum 1)
# ---------------------------------------------------------------------------


def test_parse_minutes_60():
    # 60 min / 60 = 1 hour
    assert _parse_time_window("60m") == 1


def test_parse_minutes_30():
    # 30 // 60 = 0 → clamped to 1
    assert _parse_time_window("30m") == 1


def test_parse_minutes_120():
    # 120 // 60 = 2
    assert _parse_time_window("120m") == 2


def test_parse_minutes_1():
    # 1 // 60 = 0 → clamped to 1
    assert _parse_time_window("1m") == 1


# ---------------------------------------------------------------------------
# _parse_time_window — bare number (assumed hours)
# ---------------------------------------------------------------------------


def test_parse_bare_number():
    assert _parse_time_window("6") == 6


def test_parse_bare_number_large():
    assert _parse_time_window("168") == 168


# ---------------------------------------------------------------------------
# _parse_time_window — whitespace / case
# ---------------------------------------------------------------------------


def test_parse_with_leading_space():
    assert _parse_time_window(" 2h") == 2


def test_parse_with_trailing_space():
    assert _parse_time_window("3d ") == 72


def test_parse_uppercase():
    # The function calls .lower() so uppercase should work
    assert _parse_time_window("4H") == 4

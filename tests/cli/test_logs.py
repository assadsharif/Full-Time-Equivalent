"""
Unit tests for logs CLI module.

Tests _parse_time and _parse_relative_time helper functions.
The Click commands (tail, query, search) depend on src.logging
which shadows stdlib logging — those are covered by e2e tests.
We import only the two pure helpers via importlib to avoid
triggering the relative-import chain in logs.py.
"""

import importlib.util
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Isolated import of the two pure helpers without triggering
# src.logging (the shadow module).  We stub out the relative
# imports that logs.py needs at the top level.
# ---------------------------------------------------------------------------

_LOGS_PY = Path(__file__).resolve().parent.parent.parent / "src" / "cli" / "logs.py"


def _load_pure_helpers():
    """Load _parse_time and _parse_relative_time without the click/logging deps."""
    # Stub packages so the relative imports don't crash
    _stub_logging_models = types.ModuleType("src.logging.models")
    _stub_logging_models.LogLevel = type(
        "LogLevel", (), {"DEBUG": "DEBUG", "INFO": "INFO"}
    )
    _stub_logging_models.LogQuery = type("LogQuery", (), {})

    _stub_logging_query = types.ModuleType("src.logging.query_service")
    _stub_logging_query.QueryService = type("QueryService", (), {})

    # Pre-seed sys.modules so relative imports resolve
    originals = {}
    for name, mod in [
        ("src.logging", types.ModuleType("src.logging")),
        ("src.logging.models", _stub_logging_models),
        ("src.logging.query_service", _stub_logging_query),
    ]:
        originals[name] = sys.modules.get(name)
        sys.modules[name] = mod

    # Attach sub-modules
    sys.modules["src.logging"].models = _stub_logging_models
    sys.modules["src.logging"].query_service = _stub_logging_query

    try:
        spec = importlib.util.spec_from_file_location("_logs_helpers", str(_LOGS_PY))
        mod = importlib.util.module_from_spec(spec)
        # Set __package__ so relative imports work
        mod.__package__ = "src.cli"
        spec.loader.exec_module(mod)
        return mod._parse_time, mod._parse_relative_time
    finally:
        # Restore originals
        for name, orig in originals.items():
            if orig is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = orig


_parse_time, _parse_relative_time = _load_pure_helpers()


# ---------------------------------------------------------------------------
# _parse_relative_time
# ---------------------------------------------------------------------------


def test_relative_minutes():
    assert _parse_relative_time("30m") == timedelta(minutes=30)


def test_relative_hours():
    assert _parse_relative_time("2h") == timedelta(hours=2)


def test_relative_days():
    assert _parse_relative_time("3d") == timedelta(days=3)


def test_relative_weeks():
    assert _parse_relative_time("1w") == timedelta(weeks=1)


def test_relative_invalid_unit_raises():
    try:
        _parse_relative_time("5x")
        assert False, "should raise"
    except ValueError as e:
        assert "5x" in str(e)


def test_relative_non_numeric_raises():
    try:
        _parse_relative_time("abch")
        assert False, "should raise"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# _parse_time — relative strings (delegates to _parse_relative_time)
# ---------------------------------------------------------------------------


def test_parse_time_relative_1h():
    before = datetime.now(timezone.utc)
    result = _parse_time("1h")
    diff = (before - result).total_seconds()
    assert 3590 < diff < 3610


def test_parse_time_relative_2d():
    before = datetime.now(timezone.utc)
    result = _parse_time("2d")
    diff = (before - result).total_seconds()
    expected = 2 * 86400
    assert expected - 10 < diff < expected + 10


# ---------------------------------------------------------------------------
# _parse_time — ISO format
# ---------------------------------------------------------------------------


def test_parse_time_iso_with_tz():
    result = _parse_time("2026-01-15T10:30:00+00:00")
    assert result == datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


def test_parse_time_iso_naive():
    # Python 3.11+ fromisoformat accepts "YYYY-MM-DD HH:MM:SS" natively;
    # it returns a naive datetime (no tzinfo).  Verify the date/time values.
    result = _parse_time("2026-02-01 12:00:00")
    assert result.year == 2026
    assert result.month == 2
    assert result.day == 1
    assert result.hour == 12
    assert result.minute == 0


def test_parse_time_date_only():
    # fromisoformat also parses bare dates in 3.11+; returns naive.
    result = _parse_time("2026-03-15")
    assert result.year == 2026
    assert result.month == 3
    assert result.day == 15


# ---------------------------------------------------------------------------
# _parse_time — invalid
# ---------------------------------------------------------------------------


def test_parse_time_garbage_raises():
    try:
        _parse_time("not-a-time")
        assert False, "should raise"
    except ValueError as e:
        assert "Invalid time format" in str(e)

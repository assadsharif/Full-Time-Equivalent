"""
Unit tests for TDD state manager.

Covers load/save round-trip, phase transitions, run recording,
cycle history, reset, and invalid-phase rejection.
"""

import json
import sys

sys.path.insert(0, ".")

from pathlib import Path
from src.cli.tdd_state import TDDState, PHASES

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(tmp_path) -> TDDState:
    """Create a TDDState backed by a temp file."""
    return TDDState(state_path=tmp_path / "tdd_state.json")


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


def test_initial_phase_is_idle(tmp_path):
    s = _make_state(tmp_path)
    assert s.phase == "idle"
    assert s.target_test is None
    assert s.passed == 0
    assert s.failed == 0
    assert s.errors == 0
    assert s.cycle_history == []


# ---------------------------------------------------------------------------
# Save / load round-trip
# ---------------------------------------------------------------------------


def test_save_creates_file(tmp_path):
    s = _make_state(tmp_path)
    s.save()
    assert (tmp_path / "tdd_state.json").exists()


def test_save_load_round_trip(tmp_path):
    path = tmp_path / "tdd_state.json"
    s1 = TDDState(state_path=path)
    s1.set_phase("red", target_test="tests/test_foo.py")
    s1.record_run(passed=2, failed=1, errors=0)

    # Reload from disk
    s2 = TDDState(state_path=path)
    assert s2.phase == "red"
    assert s2.target_test == "tests/test_foo.py"
    assert s2.passed == 2
    assert s2.failed == 1
    assert s2.errors == 0


def test_load_from_missing_file_gives_defaults(tmp_path):
    s = TDDState(state_path=tmp_path / "nonexistent.json")
    assert s.phase == "idle"


def test_load_from_corrupt_json_gives_defaults(tmp_path):
    path = tmp_path / "tdd_state.json"
    path.write_text("not valid json {{{")
    s = TDDState(state_path=path)
    assert s.phase == "idle"


# ---------------------------------------------------------------------------
# Phase transitions
# ---------------------------------------------------------------------------


def test_set_phase_valid(tmp_path):
    s = _make_state(tmp_path)
    for phase in PHASES:
        s.set_phase(phase)
        assert s.phase == phase


def test_set_phase_invalid_raises(tmp_path):
    s = _make_state(tmp_path)
    try:
        s.set_phase("bogus")
        assert False, "should have raised ValueError"
    except ValueError as e:
        assert "bogus" in str(e)


def test_set_phase_updates_target(tmp_path):
    s = _make_state(tmp_path)
    s.set_phase("green", target_test="tests/test_bar.py")
    assert s.target_test == "tests/test_bar.py"


def test_set_phase_without_target_preserves_existing(tmp_path):
    s = _make_state(tmp_path)
    s.set_phase("red", target_test="tests/test_x.py")
    s.set_phase("green")  # no target_test arg
    assert s.target_test == "tests/test_x.py"


# ---------------------------------------------------------------------------
# Run recording
# ---------------------------------------------------------------------------


def test_record_run(tmp_path):
    s = _make_state(tmp_path)
    s.record_run(passed=5, failed=2, errors=1)
    assert s.passed == 5
    assert s.failed == 2
    assert s.errors == 1


# ---------------------------------------------------------------------------
# Cycle history
# ---------------------------------------------------------------------------


def test_record_cycle_appends(tmp_path):
    s = _make_state(tmp_path)
    s.set_phase("red", target_test="tests/test_a.py")
    s.record_cycle("completed")
    s.record_cycle("aborted")

    assert len(s.cycle_history) == 2
    assert s.cycle_history[0]["outcome"] == "completed"
    assert s.cycle_history[1]["outcome"] == "aborted"
    assert "timestamp" in s.cycle_history[0]
    assert s.cycle_history[0]["target_test"] == "tests/test_a.py"


def test_cycle_history_persists(tmp_path):
    path = tmp_path / "tdd_state.json"
    s1 = TDDState(state_path=path)
    s1.set_phase("red", target_test="t.py")
    s1.record_cycle("done")

    s2 = TDDState(state_path=path)
    assert len(s2.cycle_history) == 1
    assert s2.cycle_history[0]["outcome"] == "done"


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


def test_reset_clears_everything(tmp_path):
    s = _make_state(tmp_path)
    s.set_phase("green", target_test="tests/test_z.py")
    s.record_run(passed=3, failed=1, errors=0)
    s.record_cycle("ok")

    s.reset()
    assert s.phase == "idle"
    assert s.target_test is None
    assert s.passed == 0
    assert s.failed == 0
    assert s.errors == 0


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------


def test_to_dict_shape(tmp_path):
    s = _make_state(tmp_path)
    s.set_phase("refactor", target_test="t.py")
    s.record_run(1, 0, 0)
    s.record_cycle("x")

    d = s.to_dict()
    assert d["phase"] == "refactor"
    assert d["target_test"] == "t.py"
    assert d["passed"] == 1
    assert d["failed"] == 0
    assert d["errors"] == 0
    assert d["cycles_completed"] == 1

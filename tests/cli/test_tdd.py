"""
Tests for fte tdd CLI commands.

Tests each TDD sub-agent command using CliRunner with mocked subprocess calls.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.tdd import (
    _parse_pytest_summary,
    tdd_cycle,
    tdd_green,
    tdd_group,
    tdd_init,
    tdd_red,
    tdd_refactor,
    tdd_status,
    tdd_watch,
)
from cli.tdd_state import TDDState

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def state_file(tmp_path):
    """Return a path to a temporary tdd_state.json."""
    return tmp_path / ".fte" / "tdd_state.json"


@pytest.fixture
def mock_state(tmp_path):
    """Return a TDDState backed by a temp directory."""
    return TDDState(state_path=tmp_path / ".fte" / "tdd_state.json")


# ---------------------------------------------------------------------------
# TDD State Manager
# ---------------------------------------------------------------------------


class TestTDDState:
    """Test TDDState persistence and transitions."""

    def test_initial_state_is_idle(self, mock_state):
        assert mock_state.phase == "idle"
        assert mock_state.target_test is None
        assert mock_state.passed == 0

    def test_set_phase(self, mock_state):
        mock_state.set_phase("red", target_test="tests/test_foo.py")
        assert mock_state.phase == "red"
        assert mock_state.target_test == "tests/test_foo.py"

    def test_set_phase_invalid(self, mock_state):
        with pytest.raises(ValueError, match="Invalid phase"):
            mock_state.set_phase("invalid")

    def test_record_run(self, mock_state):
        mock_state.record_run(passed=3, failed=1, errors=0)
        assert mock_state.passed == 3
        assert mock_state.failed == 1

    def test_record_cycle(self, mock_state):
        mock_state.set_phase("red", target_test="test.py")
        mock_state.record_cycle("success")
        assert len(mock_state.cycle_history) == 1
        assert mock_state.cycle_history[0]["outcome"] == "success"

    def test_persistence_round_trip(self, tmp_path):
        path = tmp_path / ".fte" / "tdd_state.json"
        s1 = TDDState(state_path=path)
        s1.set_phase("green", target_test="tests/test_a.py")
        s1.record_run(5, 0, 0)

        s2 = TDDState(state_path=path)
        assert s2.phase == "green"
        assert s2.target_test == "tests/test_a.py"
        assert s2.passed == 5

    def test_reset(self, mock_state):
        mock_state.set_phase("red", target_test="x.py")
        mock_state.record_run(0, 1, 0)
        mock_state.reset()
        assert mock_state.phase == "idle"
        assert mock_state.target_test is None
        assert mock_state.failed == 0

    def test_to_dict(self, mock_state):
        d = mock_state.to_dict()
        assert "phase" in d
        assert "cycles_completed" in d


# ---------------------------------------------------------------------------
# Helper: _parse_pytest_summary
# ---------------------------------------------------------------------------


class TestParsePytestSummary:
    def test_parse_all_passed(self):
        p, f, e = _parse_pytest_summary("===== 5 passed in 0.10s =====")
        assert p == 5
        assert f == 0
        assert e == 0

    def test_parse_mixed(self):
        p, f, e = _parse_pytest_summary(
            "===== 3 passed, 2 failed, 1 error in 1.0s ====="
        )
        assert (p, f, e) == (3, 2, 1)

    def test_parse_empty(self):
        p, f, e = _parse_pytest_summary("")
        assert (p, f, e) == (0, 0, 0)


# ---------------------------------------------------------------------------
# fte tdd init
# ---------------------------------------------------------------------------


class TestTDDInit:
    def test_tdd_init_creates_structure(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Patch _get_state so the state file goes into this temp dir
            with patch("cli.tdd._get_state") as mock_gs:
                mock_gs.return_value = TDDState(
                    state_path=Path.cwd() / ".fte" / "tdd_state.json"
                )
                result = runner.invoke(tdd_init)

            assert result.exit_code == 0
            assert "initialized" in result.output.lower()
            assert (Path.cwd() / "tests").exists()
            assert (Path.cwd() / "conftest.py").exists()

    def test_tdd_init_idempotent(self, runner, tmp_path):
        with runner.isolated_filesystem(temp_dir=tmp_path):
            (Path.cwd() / "tests").mkdir()
            (Path.cwd() / "conftest.py").write_text("# exists\n")

            with patch("cli.tdd._get_state") as mock_gs:
                mock_gs.return_value = TDDState(
                    state_path=Path.cwd() / ".fte" / "tdd_state.json"
                )
                result = runner.invoke(tdd_init)

            assert result.exit_code == 0
            assert "already exists" in result.output.lower()


# ---------------------------------------------------------------------------
# fte tdd red
# ---------------------------------------------------------------------------


class TestTDDRed:
    @patch("cli.tdd._get_state")
    @patch("cli.tdd._run_pytest")
    def test_tdd_red_passes_when_tests_fail(
        self, mock_pytest, mock_gs, runner, mock_state
    ):
        mock_gs.return_value = mock_state
        mock_pytest.return_value = MagicMock(
            returncode=1,
            stdout="===== 0 passed, 2 failed in 0.5s =====",
            stderr="",
        )

        result = runner.invoke(tdd_red, ["tests/test_foo.py"])

        assert result.exit_code == 0
        assert "failed as expected" in result.output.lower()

    @patch("cli.tdd._get_state")
    @patch("cli.tdd._run_pytest")
    def test_tdd_red_warns_when_tests_pass(
        self, mock_pytest, mock_gs, runner, mock_state
    ):
        mock_gs.return_value = mock_state
        mock_pytest.return_value = MagicMock(
            returncode=0,
            stdout="===== 3 passed in 0.1s =====",
            stderr="",
        )

        result = runner.invoke(tdd_red, ["tests/test_foo.py"])

        assert result.exit_code == 1
        assert "tests passed" in result.output.lower()


# ---------------------------------------------------------------------------
# fte tdd green
# ---------------------------------------------------------------------------


class TestTDDGreen:
    @patch("cli.tdd._get_state")
    @patch("cli.tdd._run_pytest")
    def test_tdd_green_passes_when_tests_pass(
        self, mock_pytest, mock_gs, runner, mock_state
    ):
        mock_gs.return_value = mock_state
        mock_pytest.return_value = MagicMock(
            returncode=0,
            stdout="===== 3 passed in 0.1s =====",
            stderr="",
        )

        result = runner.invoke(tdd_green, ["tests/test_foo.py"])

        assert result.exit_code == 0
        assert "all tests passed" in result.output.lower()

    @patch("cli.tdd._get_state")
    @patch("cli.tdd._run_pytest")
    def test_tdd_green_warns_when_tests_fail(
        self, mock_pytest, mock_gs, runner, mock_state
    ):
        mock_gs.return_value = mock_state
        mock_pytest.return_value = MagicMock(
            returncode=1,
            stdout="===== 1 passed, 1 failed in 0.2s =====",
            stderr="",
        )

        result = runner.invoke(tdd_green, ["tests/test_foo.py"])

        assert result.exit_code == 1
        assert "still failing" in result.output.lower()


# ---------------------------------------------------------------------------
# fte tdd refactor
# ---------------------------------------------------------------------------


class TestTDDRefactor:
    @patch("cli.tdd._get_state")
    @patch("cli.tdd._run_pytest")
    def test_tdd_refactor_runs_all_tests(
        self, mock_pytest, mock_gs, runner, mock_state
    ):
        mock_gs.return_value = mock_state
        mock_pytest.return_value = MagicMock(
            returncode=0,
            stdout="===== 10 passed in 0.5s =====",
            stderr="",
        )

        result = runner.invoke(tdd_refactor)

        assert result.exit_code == 0
        assert "all tests green" in result.output.lower()
        # Verify pytest was called without a specific target
        mock_pytest.assert_called_once_with(extra_args=None)

    @patch("cli.tdd._get_state")
    @patch("cli.tdd._run_pytest")
    def test_tdd_refactor_detects_regressions(
        self, mock_pytest, mock_gs, runner, mock_state
    ):
        mock_gs.return_value = mock_state
        mock_pytest.return_value = MagicMock(
            returncode=1,
            stdout="===== 8 passed, 2 failed in 0.5s =====",
            stderr="",
        )

        result = runner.invoke(tdd_refactor)

        assert result.exit_code == 1
        assert "regressions" in result.output.lower()

    @patch("cli.tdd._get_state")
    @patch("cli.tdd._run_pytest")
    def test_tdd_refactor_with_coverage(self, mock_pytest, mock_gs, runner, mock_state):
        mock_gs.return_value = mock_state
        mock_pytest.return_value = MagicMock(
            returncode=0,
            stdout="===== 5 passed in 0.3s =====",
            stderr="",
        )

        result = runner.invoke(tdd_refactor, ["--cov"])

        assert result.exit_code == 0
        mock_pytest.assert_called_once_with(extra_args=["--cov"])


# ---------------------------------------------------------------------------
# fte tdd status
# ---------------------------------------------------------------------------


class TestTDDStatus:
    @patch("cli.tdd._get_state")
    def test_tdd_status_shows_state(self, mock_gs, runner, mock_state):
        mock_state.set_phase("green", target_test="tests/test_bar.py")
        mock_state.record_run(5, 0, 0)
        mock_gs.return_value = mock_state

        result = runner.invoke(tdd_status)

        assert result.exit_code == 0
        assert "GREEN" in result.output
        assert "tests/test_bar.py" in result.output
        assert "5" in result.output

    @patch("cli.tdd._get_state")
    def test_tdd_status_idle(self, mock_gs, runner, mock_state):
        mock_gs.return_value = mock_state

        result = runner.invoke(tdd_status)

        assert result.exit_code == 0
        assert "IDLE" in result.output


# ---------------------------------------------------------------------------
# fte tdd cycle
# ---------------------------------------------------------------------------


class TestTDDCycle:
    @patch("cli.tdd._get_state")
    @patch("cli.tdd._run_pytest")
    @patch("click.pause")
    def test_tdd_cycle_enforces_order(
        self, mock_pause, mock_pytest, mock_gs, runner, mock_state
    ):
        mock_gs.return_value = mock_state

        # RED: tests fail, GREEN: tests pass, REFACTOR: tests pass
        mock_pytest.side_effect = [
            MagicMock(
                returncode=1, stdout="===== 0 passed, 1 failed in 0.1s =====", stderr=""
            ),
            MagicMock(returncode=0, stdout="===== 1 passed in 0.1s =====", stderr=""),
            MagicMock(returncode=0, stdout="===== 10 passed in 0.5s =====", stderr=""),
        ]

        result = runner.invoke(tdd_cycle, ["tests/test_foo.py"])

        assert result.exit_code == 0
        assert "cycle complete" in result.output.lower()
        assert mock_pytest.call_count == 3

    @patch("cli.tdd._get_state")
    @patch("cli.tdd._run_pytest")
    @patch("click.pause")
    def test_tdd_cycle_aborts_on_red_pass(
        self, mock_pause, mock_pytest, mock_gs, runner, mock_state
    ):
        mock_gs.return_value = mock_state

        # RED phase: tests pass (wrong)
        mock_pytest.return_value = MagicMock(
            returncode=0,
            stdout="===== 1 passed in 0.1s =====",
            stderr="",
        )

        result = runner.invoke(tdd_cycle, ["tests/test_foo.py"])

        assert result.exit_code == 1
        assert "expects failures" in result.output.lower()

    @patch("cli.tdd._get_state")
    @patch("cli.tdd._run_pytest")
    @patch("click.pause")
    def test_tdd_cycle_aborts_on_green_fail(
        self, mock_pause, mock_pytest, mock_gs, runner, mock_state
    ):
        mock_gs.return_value = mock_state

        mock_pytest.side_effect = [
            # RED: tests fail (correct)
            MagicMock(
                returncode=1, stdout="===== 0 passed, 1 failed in 0.1s =====", stderr=""
            ),
            # GREEN: tests still fail (wrong)
            MagicMock(
                returncode=1, stdout="===== 0 passed, 1 failed in 0.1s =====", stderr=""
            ),
        ]

        result = runner.invoke(tdd_cycle, ["tests/test_foo.py"])

        assert result.exit_code == 1
        assert "still failing" in result.output.lower()


# ---------------------------------------------------------------------------
# fte tdd watch
# ---------------------------------------------------------------------------


class TestTDDWatch:
    @patch("cli.tdd.subprocess.run")
    def test_tdd_watch_starts(self, mock_run, runner):
        mock_run.return_value = MagicMock(returncode=0)

        result = runner.invoke(tdd_watch, ["tests"])

        assert result.exit_code == 0
        mock_run.assert_called_once()

    @patch("cli.tdd.subprocess.run", side_effect=FileNotFoundError)
    def test_tdd_watch_not_installed(self, mock_run, runner):
        result = runner.invoke(tdd_watch, ["tests"])

        assert result.exit_code == 1
        assert "pytest-watch not installed" in result.output.lower()


# ---------------------------------------------------------------------------
# fte tdd group
# ---------------------------------------------------------------------------


class TestTDDGroup:
    def test_tdd_group_help(self, runner):
        result = runner.invoke(tdd_group, ["--help"])

        assert result.exit_code == 0
        assert "tdd" in result.output.lower()
        assert "init" in result.output
        assert "red" in result.output
        assert "green" in result.output
        assert "refactor" in result.output
        assert "cycle" in result.output
        assert "status" in result.output
        assert "watch" in result.output

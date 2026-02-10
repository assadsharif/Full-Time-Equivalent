"""
Unit tests for shared TDD helpers.

Covers parse_pytest_summary across all result shapes and
run_pytest subprocess invocation (via mock).
"""

import sys

sys.path.insert(0, ".")

from unittest.mock import patch, MagicMock
from cli.tdd_helpers import run_pytest, parse_pytest_summary

# ---------------------------------------------------------------------------
# parse_pytest_summary
# ---------------------------------------------------------------------------


def test_parse_all_passed():
    output = "======================== 7 passed in 0.12s ========================"
    passed, failed, errors = parse_pytest_summary(output)
    assert passed == 7
    assert failed == 0
    assert errors == 0


def test_parse_mixed():
    output = "====== 3 failed, 5 passed, 1 error in 1.23s ======"
    passed, failed, errors = parse_pytest_summary(output)
    assert passed == 5
    assert failed == 3
    assert errors == 1


def test_parse_only_failures():
    output = "======================== 2 failed in 0.08s ========================"
    passed, failed, errors = parse_pytest_summary(output)
    assert passed == 0
    assert failed == 2
    assert errors == 0


def test_parse_only_errors():
    output = "======================== 1 error in 0.05s ========================="
    passed, failed, errors = parse_pytest_summary(output)
    assert passed == 0
    assert failed == 0
    assert errors == 1


def test_parse_empty_output():
    passed, failed, errors = parse_pytest_summary("")
    assert passed == 0
    assert failed == 0
    assert errors == 0


def test_parse_no_summary_line():
    output = "collecting ...\ntest_foo.py::test_bar PASSED\n"
    passed, failed, errors = parse_pytest_summary(output)
    assert passed == 0  # no summary line to parse


def test_parse_warnings_line_ignored():
    # Warnings line should not confuse the parser
    output = (
        "test_foo.py 1 passed\n"
        "2 warnings summary\n"
        "======= 1 passed, 1 warning in 0.01s ======="
    )
    passed, failed, errors = parse_pytest_summary(output)
    assert passed == 1


def test_parse_large_numbers():
    output = (
        "=============== 1234 passed, 56 failed, 7 errors in 42.00s ==============="
    )
    passed, failed, errors = parse_pytest_summary(output)
    assert passed == 1234
    assert failed == 56
    assert errors == 7


# ---------------------------------------------------------------------------
# run_pytest (subprocess mocked)
# ---------------------------------------------------------------------------


@patch("src.cli.tdd_helpers.subprocess.run")
def test_run_pytest_default_args(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
    result = run_pytest()

    args = mock_run.call_args
    cmd = args[0][0]  # first positional arg is the command list
    assert cmd[-2] == "-v"
    assert cmd[-1] == "--tb=short"
    assert cmd[1] == "-m"  # sys.executable -m pytest
    assert cmd[2] == "pytest"


@patch("src.cli.tdd_helpers.subprocess.run")
def test_run_pytest_with_target(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    run_pytest(target="tests/test_foo.py")

    cmd = mock_run.call_args[0][0]
    assert "tests/test_foo.py" in cmd


@patch("src.cli.tdd_helpers.subprocess.run")
def test_run_pytest_with_extra_args(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    run_pytest(extra_args=["--cov", "--no-header"])

    cmd = mock_run.call_args[0][0]
    assert "--cov" in cmd
    assert "--no-header" in cmd


@patch("src.cli.tdd_helpers.subprocess.run")
def test_run_pytest_with_cwd(mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    run_pytest(cwd="/tmp/project")

    kwargs = mock_run.call_args[1]
    assert kwargs["cwd"] == "/tmp/project"

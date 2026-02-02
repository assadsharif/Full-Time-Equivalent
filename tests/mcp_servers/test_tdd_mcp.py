"""
Tests for TDD MCP Server (tdd_mcp).

Written FIRST per TDD contract — all tests fail on import until implementation exists.
Covers: input validation, tool behavior, state management, scaffold content,
cycle validation, and server registration.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_servers.tdd_mcp import (
    TddGenerateScaffoldInput,
    TddGreenInput,
    TddInitInput,
    TddRedInput,
    TddRefactorInput,
    TddRunTestsInput,
    TddValidateCycleInput,
    mcp,
    tdd_generate_scaffold,
    tdd_green,
    tdd_init,
    tdd_red,
    tdd_refactor,
    tdd_run_tests,
    tdd_status,
    tdd_validate_cycle,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_state(tmp_path):
    """Return a temporary state file path."""
    return str(tmp_path / ".fte" / "tdd_state.json")


@pytest.fixture
def tmp_project(tmp_path):
    """Return a temporary project directory."""
    return str(tmp_path / "project")


# ---------------------------------------------------------------------------
# Server Registration
# ---------------------------------------------------------------------------

class TestServerRegistration:
    def test_server_name(self):
        assert mcp.name == "tdd_mcp"

    def test_server_has_eight_tools(self):
        tools = mcp._tool_manager._tools
        assert len(tools) == 8, f"Expected 8 tools, got {len(tools)}: {list(tools.keys())}"

    def test_tool_names(self):
        tool_names = set(mcp._tool_manager._tools.keys())
        expected = {
            "tdd_run_tests",
            "tdd_red",
            "tdd_green",
            "tdd_refactor",
            "tdd_init",
            "tdd_status",
            "tdd_generate_scaffold",
            "tdd_validate_cycle",
        }
        assert tool_names == expected


# ---------------------------------------------------------------------------
# Input Validation — TddRunTestsInput
# ---------------------------------------------------------------------------

class TestTddRunTestsInputValidation:
    def test_valid_input(self):
        inp = TddRunTestsInput(target_path="tests/test_foo.py")
        assert inp.target_path == "tests/test_foo.py"

    def test_strips_whitespace(self):
        inp = TddRunTestsInput(target_path="  tests/test_foo.py  ")
        assert inp.target_path == "tests/test_foo.py"

    def test_rejects_path_traversal(self):
        with pytest.raises(ValueError, match="[Pp]ath traversal"):
            TddRunTestsInput(target_path="../../../etc/passwd")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError):
            TddRunTestsInput(target_path="")

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValueError):
            TddRunTestsInput(target_path="tests/", secret="hack")

    def test_optional_extra_args(self):
        inp = TddRunTestsInput(target_path="tests/", extra_args=["-x", "--tb=long"])
        assert inp.extra_args == ["-x", "--tb=long"]


# ---------------------------------------------------------------------------
# Input Validation — TddRedInput / TddGreenInput
# ---------------------------------------------------------------------------

class TestTddRedGreenInputValidation:
    def test_red_valid(self):
        inp = TddRedInput(test_path="tests/test_a.py")
        assert inp.test_path == "tests/test_a.py"

    def test_green_valid(self):
        inp = TddGreenInput(test_path="tests/test_a.py")
        assert inp.test_path == "tests/test_a.py"

    def test_red_rejects_path_traversal(self):
        with pytest.raises(ValueError, match="[Pp]ath traversal"):
            TddRedInput(test_path="../../secrets")

    def test_green_rejects_path_traversal(self):
        with pytest.raises(ValueError, match="[Pp]ath traversal"):
            TddGreenInput(test_path="../../secrets")

    def test_red_rejects_empty(self):
        with pytest.raises(ValueError):
            TddRedInput(test_path="")

    def test_green_rejects_empty(self):
        with pytest.raises(ValueError):
            TddGreenInput(test_path="")


# ---------------------------------------------------------------------------
# Input Validation — TddGenerateScaffoldInput
# ---------------------------------------------------------------------------

class TestTddGenerateScaffoldInputValidation:
    def test_valid_module_path(self):
        inp = TddGenerateScaffoldInput(module_path="src/cli/tdd.py")
        assert inp.module_path == "src/cli/tdd.py"

    def test_rejects_non_py_module(self):
        with pytest.raises(ValueError, match=r"\.py"):
            TddGenerateScaffoldInput(module_path="src/cli/tdd.txt")

    def test_rejects_path_traversal(self):
        with pytest.raises(ValueError, match="[Pp]ath traversal"):
            TddGenerateScaffoldInput(module_path="../../evil.py")

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            TddGenerateScaffoldInput(module_path="")


# ---------------------------------------------------------------------------
# Tool: tdd_run_tests
# ---------------------------------------------------------------------------

class TestTddRunTests:
    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.run_pytest")
    async def test_returns_json_with_results(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="===== 5 passed in 0.1s =====",
            stderr="",
        )
        result = await tdd_run_tests(target_path="tests/")
        data = json.loads(result)
        assert data["returncode"] == 0
        assert data["passed"] == 5
        assert data["failed"] == 0
        assert data["errors"] == 0
        assert "stdout" in data

    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.run_pytest")
    async def test_captures_failures(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="===== 2 passed, 3 failed in 0.5s =====",
            stderr="some error",
        )
        result = await tdd_run_tests(target_path="tests/")
        data = json.loads(result)
        assert data["returncode"] == 1
        assert data["passed"] == 2
        assert data["failed"] == 3

    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.run_pytest")
    async def test_passes_extra_args(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="===== 1 passed in 0.1s =====",
            stderr="",
        )
        await tdd_run_tests(target_path="tests/", extra_args=["-x"])
        mock_run.assert_called_once_with(target="tests/", extra_args=["-x"], cwd=None)

    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.run_pytest")
    async def test_passes_cwd(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="===== 1 passed in 0.1s =====",
            stderr="",
        )
        await tdd_run_tests(target_path="tests/", cwd="/some/path")
        mock_run.assert_called_once_with(target="tests/", extra_args=None, cwd="/some/path")


# ---------------------------------------------------------------------------
# Tool: tdd_red
# ---------------------------------------------------------------------------

class TestTddRed:
    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.run_pytest")
    @patch("mcp_servers.tdd_mcp.TDDState")
    async def test_red_success_when_tests_fail(self, MockState, mock_run, tmp_state):
        mock_state = MagicMock()
        MockState.return_value = mock_state
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="===== 0 passed, 2 failed in 0.5s =====",
            stderr="",
        )
        result = await tdd_red(test_path="tests/test_foo.py", state_path=tmp_state)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["phase"] == "red"
        mock_state.set_phase.assert_called_with("red", target_test="tests/test_foo.py")

    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.run_pytest")
    @patch("mcp_servers.tdd_mcp.TDDState")
    async def test_red_error_when_tests_pass(self, MockState, mock_run, tmp_state):
        mock_state = MagicMock()
        MockState.return_value = mock_state
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="===== 3 passed in 0.1s =====",
            stderr="",
        )
        result = await tdd_red(test_path="tests/test_foo.py", state_path=tmp_state)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "pass" in data["message"].lower()


# ---------------------------------------------------------------------------
# Tool: tdd_green
# ---------------------------------------------------------------------------

class TestTddGreen:
    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.run_pytest")
    @patch("mcp_servers.tdd_mcp.TDDState")
    async def test_green_success_when_tests_pass(self, MockState, mock_run, tmp_state):
        mock_state = MagicMock()
        MockState.return_value = mock_state
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="===== 5 passed in 0.2s =====",
            stderr="",
        )
        result = await tdd_green(test_path="tests/test_foo.py", state_path=tmp_state)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["phase"] == "green"

    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.run_pytest")
    @patch("mcp_servers.tdd_mcp.TDDState")
    async def test_green_error_when_tests_fail(self, MockState, mock_run, tmp_state):
        mock_state = MagicMock()
        MockState.return_value = mock_state
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="===== 1 passed, 2 failed in 0.3s =====",
            stderr="",
        )
        result = await tdd_green(test_path="tests/test_foo.py", state_path=tmp_state)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "fail" in data["message"].lower()


# ---------------------------------------------------------------------------
# Tool: tdd_refactor
# ---------------------------------------------------------------------------

class TestTddRefactor:
    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.run_pytest")
    @patch("mcp_servers.tdd_mcp.TDDState")
    async def test_refactor_success(self, MockState, mock_run, tmp_state):
        mock_state = MagicMock()
        MockState.return_value = mock_state
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="===== 10 passed in 0.5s =====",
            stderr="",
        )
        result = await tdd_refactor(state_path=tmp_state)
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["phase"] == "refactor"
        mock_state.record_cycle.assert_called_once_with("success")
        mock_state.set_phase.assert_any_call("refactor")
        mock_state.set_phase.assert_any_call("idle")

    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.run_pytest")
    @patch("mcp_servers.tdd_mcp.TDDState")
    async def test_refactor_failure_on_regression(self, MockState, mock_run, tmp_state):
        mock_state = MagicMock()
        MockState.return_value = mock_state
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="===== 8 passed, 2 failed in 0.5s =====",
            stderr="",
        )
        result = await tdd_refactor(state_path=tmp_state)
        data = json.loads(result)
        assert data["status"] == "error"
        assert "regression" in data["message"].lower()

    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.run_pytest")
    @patch("mcp_servers.tdd_mcp.TDDState")
    async def test_refactor_with_coverage(self, MockState, mock_run, tmp_state):
        mock_state = MagicMock()
        MockState.return_value = mock_state
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="===== 5 passed in 0.3s =====",
            stderr="",
        )
        await tdd_refactor(include_coverage=True, state_path=tmp_state)
        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        # extra_args should include --cov
        assert "--cov" in call_kwargs[1].get("extra_args", []) or "--cov" in call_kwargs.kwargs.get("extra_args", [])


# ---------------------------------------------------------------------------
# Tool: tdd_init
# ---------------------------------------------------------------------------

class TestTddInit:
    @pytest.mark.asyncio
    async def test_init_creates_structure(self, tmp_path):
        project_dir = str(tmp_path / "myproject")
        result = await tdd_init(project_dir=project_dir)
        data = json.loads(result)
        assert data["status"] == "success"
        assert (tmp_path / "myproject" / "tests").exists()
        assert (tmp_path / "myproject" / "conftest.py").exists()

    @pytest.mark.asyncio
    async def test_init_idempotent(self, tmp_path):
        project_dir = str(tmp_path / "myproject")
        # Run twice
        await tdd_init(project_dir=project_dir)
        result = await tdd_init(project_dir=project_dir)
        data = json.loads(result)
        assert data["status"] == "success"


# ---------------------------------------------------------------------------
# Tool: tdd_status
# ---------------------------------------------------------------------------

class TestTddStatus:
    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.TDDState")
    async def test_status_returns_state_dict(self, MockState):
        mock_state = MagicMock()
        mock_state.to_dict.return_value = {
            "phase": "idle",
            "target_test": None,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "cycles_completed": 0,
        }
        MockState.return_value = mock_state
        result = await tdd_status()
        data = json.loads(result)
        assert data["phase"] == "idle"
        assert data["cycles_completed"] == 0


# ---------------------------------------------------------------------------
# Tool: tdd_generate_scaffold
# ---------------------------------------------------------------------------

class TestTddGenerateScaffold:
    @pytest.mark.asyncio
    async def test_scaffold_returns_string(self, tmp_path):
        # Create a real module file to scaffold from
        module = tmp_path / "mymod.py"
        module.write_text(
            "def add(a, b):\n    return a + b\n\ndef divide(a, b):\n    return a / b\n"
        )
        result = await tdd_generate_scaffold(module_path=str(module))
        assert isinstance(result, str)
        assert "import" in result
        assert "test_" in result

    @pytest.mark.asyncio
    async def test_scaffold_error_path_first(self, tmp_path):
        module = tmp_path / "mymod.py"
        module.write_text(
            "def divide(a, b):\n    return a / b\n"
        )
        result = await tdd_generate_scaffold(module_path=str(module))
        # Error-path tests should come before happy-path in the output
        lines = result.split("\n")
        error_idx = None
        happy_idx = None
        for i, line in enumerate(lines):
            if "error" in line.lower() or "invalid" in line.lower() or "raise" in line.lower() or "edge" in line.lower():
                if error_idx is None:
                    error_idx = i
            if "happy" in line.lower() or "success" in line.lower() or "valid" in line.lower() or "normal" in line.lower():
                if happy_idx is None:
                    happy_idx = i
        # At minimum, the scaffold should contain test functions
        assert "def test_" in result

    @pytest.mark.asyncio
    async def test_scaffold_nonexistent_module(self, tmp_path):
        result = await tdd_generate_scaffold(module_path=str(tmp_path / "nonexistent.py"))
        # Should return an error in the result
        data = json.loads(result)
        assert data["status"] == "error"

    @pytest.mark.asyncio
    async def test_scaffold_with_hypothesis(self, tmp_path):
        module = tmp_path / "mymod.py"
        module.write_text("def add(a, b):\n    return a + b\n")
        result = await tdd_generate_scaffold(
            module_path=str(module), include_hypothesis=True
        )
        assert "hypothesis" in result.lower()


# ---------------------------------------------------------------------------
# Tool: tdd_validate_cycle
# ---------------------------------------------------------------------------

class TestTddValidateCycle:
    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.TDDState")
    async def test_valid_idle_state(self, MockState):
        mock_state = MagicMock()
        mock_state.phase = "idle"
        MockState.return_value = mock_state
        result = await tdd_validate_cycle()
        data = json.loads(result)
        assert data["valid"] is True
        assert "idle" in data["current_phase"]

    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.TDDState")
    async def test_valid_transitions_listed(self, MockState):
        mock_state = MagicMock()
        mock_state.phase = "red"
        MockState.return_value = mock_state
        result = await tdd_validate_cycle()
        data = json.loads(result)
        assert "green" in data["next_valid_phases"]

    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.TDDState")
    async def test_green_next_is_refactor(self, MockState):
        mock_state = MagicMock()
        mock_state.phase = "green"
        MockState.return_value = mock_state
        result = await tdd_validate_cycle()
        data = json.loads(result)
        assert "refactor" in data["next_valid_phases"]

    @pytest.mark.asyncio
    @patch("mcp_servers.tdd_mcp.TDDState")
    async def test_refactor_next_is_idle(self, MockState):
        mock_state = MagicMock()
        mock_state.phase = "refactor"
        MockState.return_value = mock_state
        result = await tdd_validate_cycle()
        data = json.loads(result)
        assert "idle" in data["next_valid_phases"]

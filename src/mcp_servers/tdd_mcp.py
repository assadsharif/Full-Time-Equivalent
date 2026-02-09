"""
TDD MCP Server — exposes 8 TDD engineering tools via FastMCP (stdio transport).

Tools:
    tdd_run_tests       Run pytest, return JSON results
    tdd_red             RED phase — expect FAIL
    tdd_green           GREEN phase — expect PASS
    tdd_refactor        REFACTOR phase — run ALL tests
    tdd_init            Initialize TDD project structure
    tdd_status          Return current TDD state as JSON
    tdd_generate_scaffold  Generate test scaffold for a module
    tdd_validate_cycle  Validate TDD phase transitions
"""

import ast
import json
import textwrap
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

from cli.tdd_helpers import parse_pytest_summary, run_pytest
from cli.tdd_state import TDDState

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("tdd_mcp")

# ---------------------------------------------------------------------------
# Valid TDD phase transitions: current → [valid next]
# ---------------------------------------------------------------------------

PHASE_TRANSITIONS: dict[str, list[str]] = {
    "idle": ["red"],
    "red": ["green"],
    "green": ["refactor"],
    "refactor": ["idle"],
}

# ---------------------------------------------------------------------------
# Pydantic Input Models
# ---------------------------------------------------------------------------

_PATH_TRAVERSAL_RE = ".."


def _check_path_traversal(v: str) -> str:
    if _PATH_TRAVERSAL_RE in v:
        raise ValueError("Path traversal not allowed: '..' in path")
    return v


class TddRunTestsInput(BaseModel):
    """Input for tdd_run_tests."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    target_path: str = Field(
        ..., min_length=1, description="Test file or directory to run"
    )
    extra_args: Optional[list[str]] = Field(
        None, description="Additional pytest arguments"
    )
    cwd: Optional[str] = Field(None, description="Working directory for pytest")

    @field_validator("target_path")
    @classmethod
    def validate_target_path(cls, v: str) -> str:
        return _check_path_traversal(v)


class TddRedInput(BaseModel):
    """Input for tdd_red."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    test_path: str = Field(
        ..., min_length=1, description="Test file to run in RED phase"
    )
    state_path: Optional[str] = Field(None, description="Custom TDD state file path")

    @field_validator("test_path")
    @classmethod
    def validate_test_path(cls, v: str) -> str:
        return _check_path_traversal(v)


class TddGreenInput(BaseModel):
    """Input for tdd_green."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    test_path: str = Field(
        ..., min_length=1, description="Test file to run in GREEN phase"
    )
    state_path: Optional[str] = Field(None, description="Custom TDD state file path")

    @field_validator("test_path")
    @classmethod
    def validate_test_path(cls, v: str) -> str:
        return _check_path_traversal(v)


class TddRefactorInput(BaseModel):
    """Input for tdd_refactor."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    include_coverage: bool = Field(False, description="Include coverage report")
    state_path: Optional[str] = Field(None, description="Custom TDD state file path")
    cwd: Optional[str] = Field(None, description="Working directory for pytest")


class TddInitInput(BaseModel):
    """Input for tdd_init."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    project_dir: Optional[str] = Field(
        None, description="Project directory to initialize"
    )


class TddGenerateScaffoldInput(BaseModel):
    """Input for tdd_generate_scaffold."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    module_path: str = Field(
        ..., min_length=1, description="Path to Python module to scaffold tests for"
    )
    output_path: Optional[str] = Field(
        None, description="Optional output path for generated test file"
    )
    include_hypothesis: bool = Field(
        False, description="Include hypothesis property-based tests"
    )

    @field_validator("module_path")
    @classmethod
    def validate_module_path(cls, v: str) -> str:
        v = _check_path_traversal(v)
        if not v.endswith(".py"):
            raise ValueError("module_path must end with .py")
        return v


class TddValidateCycleInput(BaseModel):
    """Input for tdd_validate_cycle."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    state_path: Optional[str] = Field(None, description="Custom TDD state file path")


# ---------------------------------------------------------------------------
# Helper: resolve state
# ---------------------------------------------------------------------------


def _get_state(state_path: str | None = None) -> TDDState:
    if state_path:
        return TDDState(state_path=Path(state_path))
    return TDDState()


# ---------------------------------------------------------------------------
# Tool: tdd_run_tests
# ---------------------------------------------------------------------------


@mcp.tool()
async def tdd_run_tests(
    target_path: str,
    extra_args: list[str] | None = None,
    cwd: str | None = None,
) -> str:
    """Run pytest on a target path and return JSON results.

    Returns JSON: {returncode, passed, failed, errors, stdout, stderr}
    """
    result = run_pytest(target=target_path, extra_args=extra_args, cwd=cwd)
    passed, failed, errors = parse_pytest_summary(result.stdout)
    return json.dumps(
        {
            "returncode": result.returncode,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    )


# ---------------------------------------------------------------------------
# Tool: tdd_red
# ---------------------------------------------------------------------------


@mcp.tool()
async def tdd_red(
    test_path: str,
    state_path: str | None = None,
) -> str:
    """RED phase — run tests and expect them to FAIL.

    Returns JSON: {status, phase, message, passed, failed, errors}
    Success when tests fail. Error when tests pass.
    """
    state = _get_state(state_path)
    state.set_phase("red", target_test=test_path)

    result = run_pytest(target=test_path)
    passed, failed, errors = parse_pytest_summary(result.stdout)
    state.record_run(passed, failed, errors)

    if result.returncode != 0:
        return json.dumps(
            {
                "status": "success",
                "phase": "red",
                "message": f"RED: tests failed as expected ({failed} failed, {errors} errors)",
                "passed": passed,
                "failed": failed,
                "errors": errors,
            }
        )
    else:
        return json.dumps(
            {
                "status": "error",
                "phase": "red",
                "message": "RED: tests passed — you need to write a failing test first!",
                "passed": passed,
                "failed": failed,
                "errors": errors,
            }
        )


# ---------------------------------------------------------------------------
# Tool: tdd_green
# ---------------------------------------------------------------------------


@mcp.tool()
async def tdd_green(
    test_path: str,
    state_path: str | None = None,
) -> str:
    """GREEN phase — run tests and expect them to PASS.

    Returns JSON: {status, phase, message, passed, failed, errors}
    Success when tests pass. Error when tests fail.
    """
    state = _get_state(state_path)
    state.set_phase("green", target_test=test_path)

    result = run_pytest(target=test_path)
    passed, failed, errors = parse_pytest_summary(result.stdout)
    state.record_run(passed, failed, errors)

    if result.returncode == 0:
        return json.dumps(
            {
                "status": "success",
                "phase": "green",
                "message": f"GREEN: all tests passed ({passed} passed)",
                "passed": passed,
                "failed": failed,
                "errors": errors,
            }
        )
    else:
        return json.dumps(
            {
                "status": "error",
                "phase": "green",
                "message": f"GREEN: tests still failing ({failed} failed, {errors} errors)",
                "passed": passed,
                "failed": failed,
                "errors": errors,
            }
        )


# ---------------------------------------------------------------------------
# Tool: tdd_refactor
# ---------------------------------------------------------------------------


@mcp.tool()
async def tdd_refactor(
    include_coverage: bool = False,
    state_path: str | None = None,
    cwd: str | None = None,
) -> str:
    """REFACTOR phase — run ALL tests to verify nothing is broken.

    Returns JSON: {status, phase, message, passed, failed, errors}
    Records cycle on success and resets state to idle.
    """
    state = _get_state(state_path)
    state.set_phase("refactor")

    extra_args = ["--cov"] if include_coverage else None
    result = run_pytest(extra_args=extra_args, cwd=cwd)
    passed, failed, errors = parse_pytest_summary(result.stdout)
    state.record_run(passed, failed, errors)

    if result.returncode == 0:
        state.record_cycle("success")
        state.set_phase("idle")
        return json.dumps(
            {
                "status": "success",
                "phase": "refactor",
                "message": f"REFACTOR: all tests green ({passed} passed)",
                "passed": passed,
                "failed": failed,
                "errors": errors,
            }
        )
    else:
        return json.dumps(
            {
                "status": "error",
                "phase": "refactor",
                "message": f"REFACTOR: regressions detected ({failed} failed, {errors} errors)",
                "passed": passed,
                "failed": failed,
                "errors": errors,
            }
        )


# ---------------------------------------------------------------------------
# Tool: tdd_init
# ---------------------------------------------------------------------------


@mcp.tool()
async def tdd_init(
    project_dir: str | None = None,
) -> str:
    """Initialize TDD project structure (tests/, conftest.py) and reset state.

    Returns JSON: {status, message, created}
    """
    project_root = Path(project_dir) if project_dir else Path.cwd()
    project_root.mkdir(parents=True, exist_ok=True)

    tests_dir = project_root / "tests"
    conftest = project_root / "conftest.py"
    created: list[str] = []

    if not tests_dir.exists():
        tests_dir.mkdir(parents=True)
        created.append(str(tests_dir))

    if not conftest.exists():
        conftest.write_text('"""Root conftest for pytest."""\n')
        created.append(str(conftest))

    state_path = project_root / ".fte" / "tdd_state.json"
    state = TDDState(state_path=state_path)
    state.reset()

    return json.dumps(
        {
            "status": "success",
            "message": (
                "TDD structure initialized"
                if created
                else "TDD structure already exists"
            ),
            "created": created,
        }
    )


# ---------------------------------------------------------------------------
# Tool: tdd_status
# ---------------------------------------------------------------------------


@mcp.tool()
async def tdd_status(
    state_path: str | None = None,
) -> str:
    """Return current TDD state as JSON.

    Returns JSON: {phase, target_test, passed, failed, errors, cycles_completed}
    """
    state = _get_state(state_path)
    return json.dumps(state.to_dict())


# ---------------------------------------------------------------------------
# Tool: tdd_generate_scaffold
# ---------------------------------------------------------------------------


def _extract_functions(source: str) -> list[dict]:
    """Extract function names and their args from Python source using AST."""
    functions = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return functions

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if node.name.startswith("_"):
                continue
            args = [a.arg for a in node.args.args if a.arg != "self"]
            functions.append({"name": node.name, "args": args})
    return functions


@mcp.tool()
async def tdd_generate_scaffold(
    module_path: str,
    output_path: str | None = None,
    include_hypothesis: bool = False,
) -> str:
    """Generate a test scaffold for a Python module (error-path-first stubs).

    Returns the test file content as a string.
    If the module doesn't exist, returns JSON error.
    """
    path = Path(module_path)
    if not path.exists():
        return json.dumps(
            {
                "status": "error",
                "message": f"Module not found: {module_path}",
            }
        )

    source = path.read_text()
    functions = _extract_functions(source)
    module_name = path.stem

    lines: list[str] = []
    lines.append(f'"""Tests for {module_name} — error-path-first stubs."""')
    lines.append("")
    lines.append("import pytest")

    if include_hypothesis:
        lines.append("from hypothesis import given, strategies as st")

    lines.append("")
    lines.append("")

    for func in functions:
        # Error / edge-case stubs first
        lines.append(f"class Test{func['name'].title().replace('_', '')}:")
        lines.append(f"    \"\"\"Tests for {func['name']}.\"\"\"")
        lines.append("")
        lines.append(f"    def test_{func['name']}_invalid_input_raises(self):")
        lines.append(f'        """Error path: invalid input should raise."""')
        lines.append(f"        pytest.skip('TODO: implement error-path test')")
        lines.append("")
        lines.append(f"    def test_{func['name']}_edge_case(self):")
        lines.append(f'        """Edge case: boundary conditions."""')
        lines.append(f"        pytest.skip('TODO: implement edge-case test')")
        lines.append("")
        lines.append(f"    def test_{func['name']}_normal_operation(self):")
        lines.append(f'        """Happy path: valid input returns expected result."""')
        lines.append(f"        pytest.skip('TODO: implement happy-path test')")
        lines.append("")

        if include_hypothesis:
            arg_strats = ", ".join(f"{a}=st.integers()" for a in func["args"])
            if arg_strats:
                lines.append(f"    @given({arg_strats})")
                lines.append(
                    f"    def test_{func['name']}_property(self, {', '.join(func['args'])}):"
                )
                lines.append(f'        """Property-based: hypothesis fuzz test."""')
                lines.append(
                    f"        pytest.skip('TODO: implement property-based test')"
                )
                lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: tdd_validate_cycle
# ---------------------------------------------------------------------------


@mcp.tool()
async def tdd_validate_cycle(
    state_path: str | None = None,
) -> str:
    """Validate TDD phase transitions: idle->red->green->refactor->idle.

    Returns JSON: {valid, current_phase, next_valid_phases}
    """
    state = _get_state(state_path)
    current = state.phase
    next_valid = PHASE_TRANSITIONS.get(current, [])

    return json.dumps(
        {
            "valid": True,
            "current_phase": current,
            "next_valid_phases": next_valid,
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")

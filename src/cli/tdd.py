"""
TDD Sub-Agent CLI Commands

Orchestrates Red-Green-Refactor cycles, runs pytest, tracks TDD state,
and enforces TDD-Skill rules via the ``fte tdd`` command group.
"""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from cli.tdd_helpers import parse_pytest_summary as _parse_pytest_summary
from cli.tdd_helpers import run_pytest as _run_pytest
from cli.tdd_state import TDDState
from cli.utils import display_error, display_info, display_success, display_warning

console = Console()


def _get_state() -> TDDState:
    return TDDState()


# ---------------------------------------------------------------------------
# CLI Group
# ---------------------------------------------------------------------------


@click.group(name="tdd")
def tdd_group():
    """TDD sub-agent — Red/Green/Refactor cycle management."""
    pass


# ---------------------------------------------------------------------------
# fte tdd init
# ---------------------------------------------------------------------------


@tdd_group.command(name="init")
@click.pass_context
def tdd_init(ctx: click.Context):
    """Initialize pytest + TDD structure in the current project.

    Creates conftest.py and tests/ directory if they do not already exist,
    and resets TDD state to idle.
    """
    try:
        project_root = Path.cwd()
        tests_dir = project_root / "tests"
        conftest = project_root / "conftest.py"

        created: list[str] = []

        if not tests_dir.exists():
            tests_dir.mkdir(parents=True)
            created.append(str(tests_dir))

        if not conftest.exists():
            conftest.write_text('"""Root conftest for pytest."""\n')
            created.append(str(conftest))

        state = _get_state()
        state.reset()

        if created:
            for item in created:
                display_success(f"Created {item}")
        else:
            display_info("TDD structure already exists")

        display_success("TDD state initialized (idle)")

    except SystemExit:
        raise
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# fte tdd red
# ---------------------------------------------------------------------------


@tdd_group.command(name="red")
@click.argument("test_path")
@click.pass_context
def tdd_red(ctx: click.Context, test_path: str):
    """RED phase — run target tests and verify they FAIL.

    Exits 0 when tests fail (expected). Exits 1 when tests pass (unexpected).
    """
    try:
        state = _get_state()
        state.set_phase("red", target_test=test_path)

        console.print("[bold red]RED[/bold red] phase — expecting failures...")
        result = _run_pytest(test_path)

        console.print(result.stdout)
        if result.stderr:
            console.print(result.stderr)

        passed, failed, errors = _parse_pytest_summary(result.stdout)
        state.record_run(passed, failed, errors)

        if result.returncode != 0:
            # Tests failed — correct for RED
            display_success(
                f"RED: tests failed as expected ({failed} failed, {errors} errors)"
            )
        else:
            # Tests passed — wrong for RED
            display_warning(
                "RED: tests passed — you need to write a failing test first!"
            )
            raise SystemExit(1)

    except SystemExit:
        raise
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# fte tdd green
# ---------------------------------------------------------------------------


@tdd_group.command(name="green")
@click.argument("test_path")
@click.pass_context
def tdd_green(ctx: click.Context, test_path: str):
    """GREEN phase — run target tests and verify they PASS.

    Exits 0 when tests pass. Exits 1 when tests fail.
    """
    try:
        state = _get_state()
        state.set_phase("green", target_test=test_path)

        console.print("[bold green]GREEN[/bold green] phase — expecting passes...")
        result = _run_pytest(test_path)

        console.print(result.stdout)
        if result.stderr:
            console.print(result.stderr)

        passed, failed, errors = _parse_pytest_summary(result.stdout)
        state.record_run(passed, failed, errors)

        if result.returncode == 0:
            display_success(f"GREEN: all tests passed ({passed} passed)")
        else:
            display_warning(
                f"GREEN: tests still failing ({failed} failed, {errors} errors)"
            )
            raise SystemExit(1)

    except SystemExit:
        raise
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# fte tdd refactor
# ---------------------------------------------------------------------------


@tdd_group.command(name="refactor")
@click.option("--cov", is_flag=True, help="Run with coverage report")
@click.pass_context
def tdd_refactor(ctx: click.Context, cov: bool):
    """REFACTOR phase — run ALL tests to verify nothing is broken.

    Optionally include a coverage report with --cov.
    """
    try:
        state = _get_state()
        state.set_phase("refactor")

        console.print(
            "[bold blue]REFACTOR[/bold blue] phase — running full test suite..."
        )
        extra = ["--cov"] if cov else None
        result = _run_pytest(extra_args=extra)

        console.print(result.stdout)
        if result.stderr:
            console.print(result.stderr)

        passed, failed, errors = _parse_pytest_summary(result.stdout)
        state.record_run(passed, failed, errors)

        if result.returncode == 0:
            display_success(f"REFACTOR: all tests green ({passed} passed)")
            state.record_cycle("success")
            state.set_phase("idle")
        else:
            display_warning(
                f"REFACTOR: regressions detected ({failed} failed, {errors} errors)"
            )
            raise SystemExit(1)

    except SystemExit:
        raise
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# fte tdd cycle
# ---------------------------------------------------------------------------


@tdd_group.command(name="cycle")
@click.argument("test_path")
@click.pass_context
def tdd_cycle(ctx: click.Context, test_path: str):
    """Interactive full TDD cycle — RED -> GREEN -> REFACTOR.

    Guides you through each phase, pausing between steps.
    """
    try:
        state = _get_state()
        state.set_phase("red", target_test=test_path)

        # --- RED ---
        console.print("\n[bold red]═══ RED PHASE ═══[/bold red]")
        console.print("Write a failing test, then press Enter to run it.")
        click.pause("Press Enter to run RED phase...")

        red_result = _run_pytest(test_path)
        console.print(red_result.stdout)
        passed, failed, errors = _parse_pytest_summary(red_result.stdout)
        state.record_run(passed, failed, errors)

        if red_result.returncode == 0:
            display_warning(
                "Tests passed — RED phase expects failures. Aborting cycle."
            )
            raise SystemExit(1)

        display_success(f"RED: tests failed as expected ({failed} failed)")

        # --- GREEN ---
        state.set_phase("green", target_test=test_path)
        console.print("\n[bold green]═══ GREEN PHASE ═══[/bold green]")
        console.print("Write the minimum code to make the test pass, then press Enter.")
        click.pause("Press Enter to run GREEN phase...")

        green_result = _run_pytest(test_path)
        console.print(green_result.stdout)
        passed, failed, errors = _parse_pytest_summary(green_result.stdout)
        state.record_run(passed, failed, errors)

        if green_result.returncode != 0:
            display_warning(f"Tests still failing ({failed} failed). Fix and re-run.")
            raise SystemExit(1)

        display_success(f"GREEN: all tests passed ({passed} passed)")

        # --- REFACTOR ---
        state.set_phase("refactor")
        console.print("\n[bold blue]═══ REFACTOR PHASE ═══[/bold blue]")
        console.print("Refactor as needed, then press Enter to run full suite.")
        click.pause("Press Enter to run REFACTOR phase...")

        refactor_result = _run_pytest()
        console.print(refactor_result.stdout)
        passed, failed, errors = _parse_pytest_summary(refactor_result.stdout)
        state.record_run(passed, failed, errors)

        if refactor_result.returncode != 0:
            display_warning(
                f"Regressions detected ({failed} failed). Fix before continuing."
            )
            raise SystemExit(1)

        display_success(f"REFACTOR: all tests green ({passed} passed)")
        state.record_cycle("success")
        state.set_phase("idle")
        console.print("\n[bold]TDD cycle complete![/bold]")

    except SystemExit:
        raise
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# fte tdd status
# ---------------------------------------------------------------------------


@tdd_group.command(name="status")
@click.pass_context
def tdd_status(ctx: click.Context):
    """Show current TDD state, test counts, and pass/fail summary."""
    try:
        state = _get_state()
        info = state.to_dict()

        phase_colors = {
            "idle": "dim",
            "red": "red",
            "green": "green",
            "refactor": "blue",
        }
        color = phase_colors.get(info["phase"], "white")

        table = Table(title="TDD Status", show_header=True, header_style="bold cyan")
        table.add_column("Field", style="bold")
        table.add_column("Value")

        table.add_row("Phase", f"[{color}]{info['phase'].upper()}[/{color}]")
        table.add_row("Target test", info["target_test"] or "-")
        table.add_row("Passed", str(info["passed"]))
        table.add_row("Failed", str(info["failed"]))
        table.add_row("Errors", str(info["errors"]))
        table.add_row("Cycles completed", str(info["cycles_completed"]))

        console.print(table)

    except SystemExit:
        raise
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# fte tdd watch
# ---------------------------------------------------------------------------


@tdd_group.command(name="watch")
@click.argument("path", default="tests")
@click.pass_context
def tdd_watch(ctx: click.Context, path: str):
    """Start pytest-watch for continuous TDD feedback.

    Defaults to watching the 'tests' directory.
    """
    try:
        display_info(f"Starting pytest-watch on {path} (Ctrl+C to stop)...")
        subprocess.run(
            [sys.executable, "-m", "pytest_watch", path],
        )
    except FileNotFoundError:
        display_warning(
            "pytest-watch not installed. Install with: pip install pytest-watch"
        )
        raise SystemExit(1)
    except KeyboardInterrupt:
        display_info("Stopped watching.")
    except SystemExit:
        raise
    except Exception as e:
        display_error(e, verbose=ctx.obj.get("verbose", False) if ctx.obj else False)
        raise SystemExit(1)

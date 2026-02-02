"""
Shared TDD helpers — used by both CLI (tdd.py) and MCP server (tdd_mcp.py).

Provides pytest execution and output parsing utilities.
"""

import re
import subprocess
import sys


def run_pytest(
    target: str | None = None,
    extra_args: list[str] | None = None,
    cwd: str | None = None,
) -> subprocess.CompletedProcess:
    """Run pytest and return the CompletedProcess.

    Args:
        target: Specific test file/directory to run.
        extra_args: Additional pytest arguments.
        cwd: Working directory for subprocess.
    """
    cmd = [sys.executable, "-m", "pytest"]
    if target:
        cmd.append(target)
    if extra_args:
        cmd.extend(extra_args)
    cmd.extend(["-v", "--tb=short"])
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def parse_pytest_summary(output: str) -> tuple[int, int, int]:
    """Parse passed/failed/error counts from pytest output.

    Returns (passed, failed, errors).
    """
    passed = failed = errors = 0
    for line in output.splitlines():
        low = line.lower()
        if "passed" in low or "failed" in low or "error" in low:
            m_passed = re.search(r"(\d+)\s+passed", low)
            m_failed = re.search(r"(\d+)\s+failed", low)
            m_errors = re.search(r"(\d+)\s+error", low)
            if m_passed:
                passed = int(m_passed.group(1))
            if m_failed:
                failed = int(m_failed.group(1))
            if m_errors:
                errors = int(m_errors.group(1))
    return passed, failed, errors

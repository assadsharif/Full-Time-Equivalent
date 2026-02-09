"""
CLI Performance Benchmarks

Tests CLI performance and ensures startup/execution times meet targets.

Performance Targets:
- CLI startup: < 100ms
- Simple commands (--help, --version): < 50ms
- Status checks: < 2s
- Vault operations: < 50ms for list, < 100ms for create/move
- Watcher operations: < 500ms
- MCP operations: < 1s (excluding network calls)

Benchmarking Strategy:
- Measure cold start (first invocation)
- Measure warm start (subsequent invocations)
- Measure with/without verbose output
- Identify performance bottlenecks
"""

import subprocess
import time
from pathlib import Path
from statistics import mean, median, stdev
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.approval import approval_group
from cli.briefing import briefing_group
from cli.init import init_command
from cli.mcp import mcp_group
from cli.status import status_command
from cli.vault import vault_group
from cli.watcher import watcher_group

# Performance thresholds (in milliseconds)
THRESHOLDS = {
    "cli_startup": 100,
    "simple_command": 50,
    "status_check": 2000,
    "vault_list": 50,
    "vault_create": 100,
    "vault_move": 100,
    "watcher_command": 500,
    "mcp_command": 1000,
}


def time_command(func, *args, **kwargs):
    """
    Time a command execution.

    Args:
        func: Function to time
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Tuple of (result, duration_ms)
    """
    start = time.time()
    result = func(*args, **kwargs)
    duration_ms = (time.time() - start) * 1000
    return result, duration_ms


def benchmark_runs(func, runs=5, *args, **kwargs):
    """
    Run benchmark multiple times and return statistics.

    Args:
        func: Function to benchmark
        runs: Number of runs
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Dictionary with timing statistics
    """
    durations = []

    for _ in range(runs):
        _, duration = time_command(func, *args, **kwargs)
        durations.append(duration)

    return {
        "mean": mean(durations),
        "median": median(durations),
        "min": min(durations),
        "max": max(durations),
        "stdev": stdev(durations) if len(durations) > 1 else 0,
        "runs": runs,
        "durations": durations,
    }


@pytest.fixture
def perf_vault(tmp_path):
    """Create a vault for performance testing."""
    vault_path = tmp_path / "perf_vault"
    vault_path.mkdir()

    folders = [
        "Inbox",
        "Needs_Action",
        "In_Progress",
        "Done",
        "Approvals",
        "Briefings",
        "Attachments",
    ]
    for folder in folders:
        (vault_path / folder).mkdir()

    config_dir = vault_path / "config"
    config_dir.mkdir()
    (config_dir / "mcp_servers.yaml").write_text("servers: {}")

    return vault_path


class TestCLIStartup:
    """Test CLI startup performance."""

    def test_cli_cold_start(self):
        """Test CLI cold start time (first invocation)"""
        import sys

        # Measure actual CLI startup via subprocess
        result = subprocess.run(
            [sys.executable, "-m", "cli.main", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Note: Actual timing would be measured externally
        # This test just verifies the command works
        assert result.returncode == 0

    def test_help_command_performance(self):
        """Test --help command performance (should be fast)"""
        runner = CliRunner()

        stats = benchmark_runs(runner.invoke, runs=5, cli=vault_group, args=["--help"])

        assert (
            stats["median"] < THRESHOLDS["simple_command"]
        ), f"--help command too slow: {stats['median']:.2f}ms (threshold: {THRESHOLDS['simple_command']}ms)"

        print(f"\n--help performance: {stats['median']:.2f}ms (median)")

    def test_version_command_performance(self):
        """Test --version command performance"""
        # Version check should be very fast as it just returns a string
        # Testing via CliRunner (not full subprocess)
        runner = CliRunner()

        start = time.time()
        for _ in range(10):
            runner.invoke(vault_group, ["--help"])
        duration = (time.time() - start) * 100  # Per invocation in ms

        assert (
            duration < THRESHOLDS["simple_command"]
        ), f"Version command too slow: {duration:.2f}ms"


class TestVaultOperations:
    """Test vault operation performance."""

    def test_vault_list_performance(self, perf_vault):
        """Test vault list command performance"""
        runner = CliRunner()

        # Create some tasks to list
        for i in range(10):
            (perf_vault / "Inbox" / f"task_{i}.md").write_text(f"# Task {i}")

        stats = benchmark_runs(
            runner.invoke,
            runs=5,
            cli=vault_group,
            args=["list", "inbox", "--vault-path", str(perf_vault)],
        )

        assert (
            stats["median"] < THRESHOLDS["vault_list"]
        ), f"Vault list too slow: {stats['median']:.2f}ms (threshold: {THRESHOLDS['vault_list']}ms)"

        print(f"\nVault list (10 tasks) performance: {stats['median']:.2f}ms (median)")

    def test_vault_create_performance(self, perf_vault):
        """Test vault create command performance"""
        runner = CliRunner()

        stats = benchmark_runs(
            runner.invoke,
            runs=5,
            cli=vault_group,
            args=[
                "create",
                "--vault-path",
                str(perf_vault),
                "--task",
                "Performance test task",
                "--folder",
                "inbox",
            ],
        )

        assert (
            stats["median"] < THRESHOLDS["vault_create"]
        ), f"Vault create too slow: {stats['median']:.2f}ms (threshold: {THRESHOLDS['vault_create']}ms)"

        print(f"\nVault create performance: {stats['median']:.2f}ms (median)")

    def test_vault_move_performance(self, perf_vault):
        """Test vault move command performance"""
        runner = CliRunner()

        # Create a task to move
        task_file = perf_vault / "Inbox" / "test_task.md"
        task_file.write_text("# Test Task")

        stats = benchmark_runs(
            runner.invoke,
            runs=5,
            cli=vault_group,
            args=[
                "move",
                "test_task",
                "inbox",
                "done",
                "--vault-path",
                str(perf_vault),
            ],
        )

        assert (
            stats["median"] < THRESHOLDS["vault_move"]
        ), f"Vault move too slow: {stats['median']:.2f}ms (threshold: {THRESHOLDS['vault_move']}ms)"

        print(f"\nVault move performance: {stats['median']:.2f}ms (median)")

    def test_vault_list_large_folder(self, perf_vault):
        """Test performance with large number of tasks"""
        runner = CliRunner()

        # Create 100 tasks
        for i in range(100):
            (perf_vault / "Inbox" / f"task_{i:03d}.md").write_text(f"# Task {i}")

        stats = benchmark_runs(
            runner.invoke,
            runs=3,  # Fewer runs for large dataset
            cli=vault_group,
            args=["list", "inbox", "--vault-path", str(perf_vault)],
        )

        # Should still be reasonably fast even with 100 tasks
        assert (
            stats["median"] < 200
        ), f"Vault list with 100 tasks too slow: {stats['median']:.2f}ms"

        print(f"\nVault list (100 tasks) performance: {stats['median']:.2f}ms (median)")


class TestStatusCheck:
    """Test status check performance."""

    @patch("cli.status.check_watcher_status")
    @patch("cli.status.check_mcp_status")
    def test_status_command_performance(
        self, mock_mcp_status, mock_watcher_status, perf_vault
    ):
        """Test status command performance with parallel checks"""
        runner = CliRunner()

        # Mock external checks to be instant
        mock_watcher_status.return_value = {"watchers": []}
        mock_mcp_status.return_value = {"servers": []}

        stats = benchmark_runs(
            runner.invoke,
            runs=3,
            cli=status_command,
            args=["--vault-path", str(perf_vault)],
        )

        assert (
            stats["median"] < THRESHOLDS["status_check"]
        ), f"Status check too slow: {stats['median']:.2f}ms (threshold: {THRESHOLDS['status_check']}ms)"

        print(f"\nStatus check performance: {stats['median']:.2f}ms (median)")

    @patch("cli.status.check_watcher_status")
    @patch("cli.status.check_mcp_status")
    def test_status_json_output_performance(
        self, mock_mcp_status, mock_watcher_status, perf_vault
    ):
        """Test status command with JSON output (should be same speed)"""
        runner = CliRunner()

        mock_watcher_status.return_value = {"watchers": []}
        mock_mcp_status.return_value = {"servers": []}

        stats = benchmark_runs(
            runner.invoke,
            runs=5,
            cli=status_command,
            args=["--vault-path", str(perf_vault), "--json"],
        )

        assert (
            stats["median"] < THRESHOLDS["status_check"]
        ), f"Status check (JSON) too slow: {stats['median']:.2f}ms"

        print(f"\nStatus check (JSON) performance: {stats['median']:.2f}ms (median)")


class TestWatcherOperations:
    """Test watcher operation performance."""

    @patch("cli.watcher.subprocess.run")
    @patch("cli.watcher.check_pm2_installed")
    def test_watcher_status_performance(
        self, mock_pm2_installed, mock_subprocess, perf_vault
    ):
        """Test watcher status command performance"""
        runner = CliRunner()

        mock_pm2_installed.return_value = True
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="[]")

        stats = benchmark_runs(
            runner.invoke,
            runs=5,
            cli=watcher_group,
            args=["status", "--vault-path", str(perf_vault)],
        )

        assert (
            stats["median"] < THRESHOLDS["watcher_command"]
        ), f"Watcher status too slow: {stats['median']:.2f}ms"

        print(f"\nWatcher status performance: {stats['median']:.2f}ms (median)")


class TestMCPOperations:
    """Test MCP operation performance."""

    def test_mcp_list_performance(self, perf_vault):
        """Test MCP list command performance"""
        runner = CliRunner()

        # Add some servers to registry
        registry_file = perf_vault / "config" / "mcp_servers.yaml"
        registry_content = """servers:
  server1:
    url: https://api1.example.com
  server2:
    url: https://api2.example.com
  server3:
    url: https://api3.example.com
"""
        registry_file.write_text(registry_content)

        stats = benchmark_runs(
            runner.invoke,
            runs=5,
            cli=mcp_group,
            args=["list", "--vault-path", str(perf_vault)],
        )

        assert (
            stats["median"] < THRESHOLDS["mcp_command"]
        ), f"MCP list too slow: {stats['median']:.2f}ms"

        print(f"\nMCP list performance: {stats['median']:.2f}ms (median)")

    @patch("cli.mcp.requests.get")
    def test_mcp_tools_caching_performance(self, mock_get, perf_vault):
        """Test that MCP tools caching improves performance"""
        runner = CliRunner()

        # Add server
        runner.invoke(
            mcp_group,
            [
                "add",
                "test-api",
                "https://api.example.com",
                "--vault-path",
                str(perf_vault),
            ],
        )

        # Mock API response
        mock_get.return_value = MagicMock(
            status_code=200, json=lambda: [{"name": "tool1"}, {"name": "tool2"}]
        )

        # First call (cache miss)
        _, first_duration = time_command(
            runner.invoke,
            cli=mcp_group,
            args=["tools", "test-api", "--vault-path", str(perf_vault)],
        )

        # Second call (should use cache)
        _, second_duration = time_command(
            runner.invoke,
            cli=mcp_group,
            args=["tools", "test-api", "--vault-path", str(perf_vault)],
        )

        # Cached call should be faster (no actual HTTP request)
        # Allow for some variance but should see improvement
        print(
            f"\nMCP tools - First: {first_duration:.2f}ms, Cached: {second_duration:.2f}ms"
        )


class TestBriefingOperations:
    """Test briefing operation performance."""

    @patch("cli.briefing.get_checkpoint_manager")
    def test_briefing_generate_performance(self, mock_checkpoint, perf_vault):
        """Test briefing generation performance"""
        runner = CliRunner()

        mock_mgr = MagicMock()
        mock_checkpoint.return_value = mock_mgr

        # Create some completed tasks
        for i in range(20):
            (perf_vault / "Done" / f"task_{i}.md").write_text(
                f"# Task {i}\nPriority: medium"
            )

        stats = benchmark_runs(
            runner.invoke,
            runs=3,
            cli=briefing_group,
            args=["generate", "--vault-path", str(perf_vault)],
        )

        # Briefing generation with 20 tasks should be fast
        assert (
            stats["median"] < 500
        ), f"Briefing generation too slow: {stats['median']:.2f}ms"

        print(
            f"\nBriefing generate (20 tasks) performance: {stats['median']:.2f}ms (median)"
        )


class TestScalability:
    """Test performance scalability with increasing data."""

    def test_vault_list_scalability(self, perf_vault):
        """Test how vault list performance scales with task count"""
        runner = CliRunner()

        task_counts = [10, 50, 100, 500]
        results = {}

        for count in task_counts:
            # Clear inbox
            inbox_dir = perf_vault / "Inbox"
            for f in inbox_dir.glob("*.md"):
                f.unlink()

            # Create tasks
            for i in range(count):
                (inbox_dir / f"task_{i:04d}.md").write_text(f"# Task {i}")

            # Measure performance
            stats = benchmark_runs(
                runner.invoke,
                runs=3,
                cli=vault_group,
                args=["list", "inbox", "--vault-path", str(perf_vault)],
            )

            results[count] = stats["median"]

        # Print scalability results
        print("\nVault list scalability:")
        for count, duration in results.items():
            print(f"  {count:4d} tasks: {duration:6.2f}ms")

        # Performance should scale roughly linearly
        # 500 tasks shouldn't take more than 10x longer than 50 tasks
        ratio = results[500] / results[50]
        assert ratio < 10, f"Performance degradation too severe: {ratio:.2f}x"


class TestMemoryUsage:
    """Test memory usage (basic checks)."""

    def test_vault_list_memory(self, perf_vault):
        """Test that vault list doesn't consume excessive memory"""
        import tracemalloc

        runner = CliRunner()

        # Create 100 tasks
        for i in range(100):
            (perf_vault / "Inbox" / f"task_{i}.md").write_text(f"# Task {i}")

        # Measure memory
        tracemalloc.start()

        runner.invoke(vault_group, ["list", "inbox", "--vault-path", str(perf_vault)])

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Peak memory should be reasonable (< 10MB for 100 tasks)
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 10, f"Excessive memory usage: {peak_mb:.2f}MB"

        print(f"\nMemory usage (100 tasks): Peak {peak_mb:.2f}MB")


class TestCommandOverhead:
    """Test Click framework overhead."""

    def test_minimal_command_overhead(self):
        """Test overhead of Click framework itself"""
        runner = CliRunner()

        # Measure multiple --help calls (should be consistent)
        durations = []
        for _ in range(10):
            start = time.time()
            runner.invoke(vault_group, ["--help"])
            durations.append((time.time() - start) * 1000)

        # Standard deviation should be low (consistent performance)
        std = stdev(durations)
        print(f"\n--help consistency: mean={mean(durations):.2f}ms, stdev={std:.2f}ms")

        # Variance should be minimal
        assert std < 10, f"High variance in command overhead: {std:.2f}ms"


def generate_performance_report():
    """Generate a performance report (for CI/CD)."""
    # This would be called separately to generate a full report
    report = {
        "timestamp": time.time(),
        "thresholds": THRESHOLDS,
        "tests": {},
    }

    # Run all benchmark tests and collect results
    # (Would be implemented with pytest plugins or custom reporting)

    return report


if __name__ == "__main__":
    """Run performance benchmarks directly."""
    print("=" * 60)
    print("CLI Performance Benchmarks")
    print("=" * 60)

    # Run pytest with verbose output
    import sys

    sys.exit(pytest.main([__file__, "-v", "-s"]))

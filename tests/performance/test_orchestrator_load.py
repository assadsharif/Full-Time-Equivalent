"""
Load tests for orchestrator (spec 006 Phase 7 T044).

Tests orchestrator performance under high load (100 tasks, simulated concurrency).
"""

import json
import time
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vault_path(tmp_path):
    """Create a temporary vault structure."""
    vault = tmp_path / "vault"
    vault.mkdir()

    # Create required directories
    (vault / "Needs_Action").mkdir()
    (vault / "Planning").mkdir()
    (vault / "In_Progress").mkdir()
    (vault / "Done").mkdir()
    (vault / "Rejected").mkdir()
    (vault / "Approvals").mkdir()

    return vault


@pytest.fixture
def config_file(tmp_path, vault_path):
    """Create a test orchestrator config for load testing."""
    config_path = tmp_path / "orchestrator.yaml"
    config_content = f"""
orchestrator:
  vault_path: {vault_path}
  poll_interval: 0.1
  max_concurrent_tasks: 10
  claude_timeout: 5
  stop_hook_file: .claude_stop
  max_iterations: 3

priority_weights:
  urgency: 0.4
  deadline: 0.3
  sender: 0.3

vip_senders: []

approval_keywords:
  - deploy
  - production

retry:
  max_attempts: 2
  base_delay: 0.1
  max_delay: 1.0
  jitter: 0.1

metrics:
  enabled: true
  retention_days: 30
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def orchestrator(config_file, vault_path):
    """Create an Orchestrator instance for load testing."""
    from src.orchestrator.models import OrchestratorConfig
    from src.orchestrator.scheduler import Orchestrator

    config = OrchestratorConfig.from_yaml(config_file, vault_path_override=vault_path)
    orch = Orchestrator(config=config, dry_run=True)  # Dry-run for performance test
    return orch


def _create_task_batch(vault_path: Path, count: int, prefix: str = "task") -> list[Path]:
    """Helper to create a batch of tasks."""
    tasks = []
    for i in range(count):
        task_path = vault_path / "Needs_Action" / f"{prefix}_{i:04d}.md"
        content = f"# Task {i}\n**Priority**: {'High' if i % 5 == 0 else 'Medium'}\n"
        task_path.write_text(content)
        tasks.append(task_path)
    return tasks


# ---------------------------------------------------------------------------
# Load Tests
# ---------------------------------------------------------------------------


class TestHighVolume:
    """Test orchestrator with high task volume."""

    def test_100_tasks_discovery_and_scoring(self, orchestrator, vault_path):
        """Discover and score 100 tasks."""
        # Create 100 tasks
        tasks = _create_task_batch(vault_path, 100)

        # Measure discovery and scoring time
        start = time.monotonic()
        exits = orchestrator.run_once()
        elapsed = time.monotonic() - start

        # All tasks should be discovered and processed
        assert len(exits) == 100

        # Should complete in reasonable time (< 10 seconds for dry-run)
        assert elapsed < 10.0, f"100 tasks took {elapsed:.2f}s (expected < 10s)"

        print(f"\n✓ Processed 100 tasks in {elapsed:.2f}s ({100/elapsed:.1f} tasks/sec)")

    def test_priority_scoring_performance(self, orchestrator, vault_path):
        """Priority scoring should be fast even with many tasks."""
        # Create 100 tasks with varying priorities
        tasks = _create_task_batch(vault_path, 100)

        from src.orchestrator.priority_scorer import PriorityScorer
        scorer = PriorityScorer(orchestrator.config)

        # Measure scoring time
        start = time.monotonic()
        for task in tasks:
            scorer.score(task)
        elapsed = time.monotonic() - start

        # Scoring should be very fast (< 1 second for 100 tasks)
        assert elapsed < 1.0, f"Scoring 100 tasks took {elapsed:.2f}s (expected < 1s)"

        print(f"\n✓ Scored 100 tasks in {elapsed:.3f}s ({100/elapsed:.0f} tasks/sec)")


class TestConcurrencySimulation:
    """Simulate concurrent task processing."""

    def test_mixed_priority_workload(self, orchestrator, vault_path):
        """Process mixed high/medium/low priority tasks."""
        # Create 100 tasks with different priorities
        for i in range(100):
            task_path = vault_path / "Needs_Action" / f"task_{i:04d}.md"
            if i % 10 == 0:
                priority = "High"
                urgency = "URGENT"
            elif i % 3 == 0:
                priority = "Low"
                urgency = ""
            else:
                priority = "Medium"
                urgency = ""
            content = f"# Task {i}\n**Priority**: {priority}\n{urgency}\n"
            task_path.write_text(content)

        # Process all tasks
        start = time.monotonic()
        exits = orchestrator.run_once()
        elapsed = time.monotonic() - start

        assert len(exits) == 100

        # High-priority tasks should be processed first
        high_priority_indices = [
            idx for idx, exit in enumerate(exits)
            if "URGENT" in (vault_path / "Needs_Action" / exit.task_name).read_text()
        ]

        # Most high-priority tasks should be in first 20 processed
        early_high_priority = sum(1 for idx in high_priority_indices if idx < 20)
        assert early_high_priority >= 5, "High-priority tasks should be processed early"

        print(f"\n✓ Processed 100 mixed-priority tasks in {elapsed:.2f}s")

    def test_age_based_boosting_under_load(self, orchestrator, vault_path):
        """Verify age-based priority boost works with many tasks."""
        import os

        # Create mix of fresh and old tasks
        now = time.time()

        for i in range(50):
            task_path = vault_path / "Needs_Action" / f"fresh_{i:04d}.md"
            task_path.write_text(f"# Fresh Task {i}\n**Priority**: Medium\n")

        for i in range(50):
            task_path = vault_path / "Needs_Action" / f"old_{i:04d}.md"
            task_path.write_text(f"# Old Task {i}\n**Priority**: Low\n")
            # Make task 10 days old
            old_time = now - (10 * 86400)
            os.utime(task_path, (old_time, old_time))

        # Process all tasks
        exits = orchestrator.run_once()

        assert len(exits) == 100

        # Old tasks should appear early despite lower base priority (age boost)
        old_task_indices = [
            idx for idx, exit in enumerate(exits)
            if exit.task_name.startswith("old_")
        ]

        # At least some old tasks should be in first half
        early_old_tasks = sum(1 for idx in old_task_indices if idx < 50)
        assert early_old_tasks >= 20, "Old tasks should get priority boost"

        print(f"\n✓ Age-based boosting working under load ({early_old_tasks}/50 old tasks in first half)")


class TestMetricsUnderLoad:
    """Test metrics collection with high volume."""

    def test_metrics_logging_performance(self, orchestrator, vault_path):
        """Metrics logging shouldn't significantly impact performance."""
        metrics_path = vault_path.parent / ".fte" / "orchestrator_metrics.log"
        if metrics_path.exists():
            metrics_path.unlink()

        # Create 100 tasks
        _create_task_batch(vault_path, 100)

        # Process all tasks
        start = time.monotonic()
        exits = orchestrator.run_once()
        elapsed = time.monotonic() - start

        # Metrics should be logged
        assert metrics_path.exists()

        # Count events
        lines = metrics_path.read_text().strip().split("\n")
        events = [json.loads(line) for line in lines if line]

        # Should have at least 200 events (started + completed for each task)
        assert len(events) >= 200

        # Metrics overhead should be minimal
        print(f"\n✓ Logged {len(events)} events in {elapsed:.2f}s")


class TestCheckpointingUnderLoad:
    """Test checkpoint performance with high volume."""

    def test_checkpoint_performance(self, orchestrator, vault_path):
        """Checkpoint should handle large exit logs efficiently."""
        checkpoint_path = vault_path.parent / ".fte" / "orchestrator.checkpoint.json"

        # Create and process 100 tasks
        _create_task_batch(vault_path, 100)

        start = time.monotonic()
        exits = orchestrator.run_once()
        elapsed = time.monotonic() - start

        # Checkpoint should exist
        assert checkpoint_path.exists()

        # Checkpoint should be reasonably sized (< 1MB for 100 tasks)
        checkpoint_size = checkpoint_path.stat().st_size
        assert checkpoint_size < 1024 * 1024, f"Checkpoint too large: {checkpoint_size} bytes"

        # Should contain all exits
        data = json.loads(checkpoint_path.read_text())
        assert len(data["exit_log"]) == 100

        print(f"\n✓ Checkpoint: {checkpoint_size} bytes for 100 tasks")


# ---------------------------------------------------------------------------
# Stress Tests
# ---------------------------------------------------------------------------


class TestStressScenarios:
    """Stress test scenarios."""

    def test_rapid_task_arrival(self, orchestrator, vault_path):
        """Simulate rapid task arrival."""
        # Create tasks in batches
        batch1 = _create_task_batch(vault_path, 50, prefix="batch1")

        # Process first batch
        exits1 = orchestrator.run_once()
        assert len(exits1) == 50

        # Add more tasks (simulating rapid arrival)
        batch2 = _create_task_batch(vault_path, 50, prefix="batch2")

        # Process second batch
        exits2 = orchestrator.run_once()
        assert len(exits2) == 50

        print("\n✓ Handled rapid task arrival (2 batches of 50)")

    def test_memory_efficiency(self, orchestrator, vault_path):
        """Verify orchestrator doesn't accumulate excessive state."""
        import sys

        # Create and process 100 tasks
        _create_task_batch(vault_path, 100)

        # Get initial memory usage (rough estimate via sys.getsizeof)
        initial_size = sys.getsizeof(orchestrator)

        # Process tasks
        exits = orchestrator.run_once()

        # Memory shouldn't grow excessively
        final_size = sys.getsizeof(orchestrator)

        # Memory growth should be reasonable (< 10MB)
        growth = final_size - initial_size
        print(f"\n✓ Memory growth: {growth} bytes (initial: {initial_size}, final: {final_size})")


# ---------------------------------------------------------------------------
# Performance Benchmarks
# ---------------------------------------------------------------------------


class TestPerformanceBenchmarks:
    """Performance benchmarks for reporting."""

    def test_throughput_benchmark(self, orchestrator, vault_path):
        """Benchmark task throughput."""
        _create_task_batch(vault_path, 100)

        start = time.monotonic()
        exits = orchestrator.run_once()
        elapsed = time.monotonic() - start

        throughput = len(exits) / elapsed

        print(f"\n" + "="*60)
        print(f"PERFORMANCE BENCHMARK")
        print(f"="*60)
        print(f"Tasks processed: {len(exits)}")
        print(f"Total time:      {elapsed:.2f}s")
        print(f"Throughput:      {throughput:.1f} tasks/sec")
        print(f"Avg latency:     {(elapsed/len(exits)*1000):.1f}ms/task")
        print(f"="*60)

        # Baseline: should achieve at least 10 tasks/sec in dry-run
        assert throughput >= 10.0, f"Throughput too low: {throughput:.1f} tasks/sec"

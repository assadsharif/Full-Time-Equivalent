"""
Performance benchmark: Sync vs Async Logging

Tests logging throughput and latency for sync and async modes.
Validates performance requirements from spec.md (< 5μs overhead for async).

Constitutional compliance: Section 9 (performance requirements).
"""

import asyncio
import statistics
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from src.logging import init_logging, get_logger
from src.logging.models import LogLevel


class PerformanceMetrics:
    """Container for performance test results."""

    def __init__(self, name: str):
        self.name = name
        self.latencies_us = []  # Microseconds per log call
        self.total_time_s = 0.0
        self.total_logs = 0

    @property
    def throughput_per_sec(self) -> float:
        """Logs per second."""
        if self.total_time_s == 0:
            return 0.0
        return self.total_logs / self.total_time_s

    @property
    def mean_latency_us(self) -> float:
        """Mean latency in microseconds."""
        return statistics.mean(self.latencies_us) if self.latencies_us else 0.0

    @property
    def p50_latency_us(self) -> float:
        """Median (p50) latency in microseconds."""
        return statistics.median(self.latencies_us) if self.latencies_us else 0.0

    @property
    def p95_latency_us(self) -> float:
        """p95 latency in microseconds."""
        if not self.latencies_us:
            return 0.0
        sorted_latencies = sorted(self.latencies_us)
        index = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[index]

    @property
    def p99_latency_us(self) -> float:
        """p99 latency in microseconds."""
        if not self.latencies_us:
            return 0.0
        sorted_latencies = sorted(self.latencies_us)
        index = int(len(sorted_latencies) * 0.99)
        return sorted_latencies[index]

    @property
    def max_latency_us(self) -> float:
        """Maximum latency in microseconds."""
        return max(self.latencies_us) if self.latencies_us else 0.0

    def __str__(self) -> str:
        """Pretty print metrics."""
        return (
            f"\n{'=' * 60}\n"
            f"{self.name}\n"
            f"{'=' * 60}\n"
            f"Total logs:        {self.total_logs:,}\n"
            f"Total time:        {self.total_time_s:.3f}s\n"
            f"Throughput:        {self.throughput_per_sec:,.0f} logs/sec\n"
            f"\n"
            f"Latency (per log call):\n"
            f"  Mean:            {self.mean_latency_us:.2f} μs\n"
            f"  Median (p50):    {self.p50_latency_us:.2f} μs\n"
            f"  p95:             {self.p95_latency_us:.2f} μs\n"
            f"  p99:             {self.p99_latency_us:.2f} μs\n"
            f"  Max:             {self.max_latency_us:.2f} μs\n"
            f"{'=' * 60}\n"
        )


@pytest.fixture
def temp_log_dir():
    """Temporary directory for log files."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


async def benchmark_async_logging(log_dir: Path, num_logs: int = 10000) -> PerformanceMetrics:
    """
    Benchmark async logging performance.

    Args:
        log_dir: Directory for log files
        num_logs: Number of log entries to generate

    Returns:
        PerformanceMetrics with results
    """
    metrics = PerformanceMetrics("Async Logging (async_enabled=True)")

    # Initialize async logger
    logger_service = init_logging(
        log_dir=log_dir,
        level=LogLevel.INFO,
        async_enabled=True,
    )
    await logger_service.start_async_writer()
    logger = get_logger("benchmark")

    # Warm-up phase (not counted)
    for _ in range(100):
        logger.info("Warmup log")
    await logger_service.flush()

    # Benchmark phase
    start_time = time.perf_counter()

    for i in range(num_logs):
        # Measure individual log call latency
        log_start = time.perf_counter()

        logger.info(
            "Benchmark log entry",
            context={
                "iteration": i,
                "user_id": f"user-{i % 1000}",
                "request_id": f"req-{i}",
            },
        )

        log_end = time.perf_counter()
        latency_us = (log_end - log_start) * 1_000_000  # Convert to microseconds
        metrics.latencies_us.append(latency_us)

    # Wait for all logs to be written
    await logger_service.flush()

    end_time = time.perf_counter()
    metrics.total_time_s = end_time - start_time
    metrics.total_logs = num_logs

    # Cleanup
    await logger_service.stop_async_writer()

    return metrics


async def benchmark_sync_logging(log_dir: Path, num_logs: int = 10000) -> PerformanceMetrics:
    """
    Benchmark sync logging performance.

    Args:
        log_dir: Directory for log files
        num_logs: Number of log entries to generate

    Returns:
        PerformanceMetrics with results
    """
    metrics = PerformanceMetrics("Sync Logging (async_enabled=False)")

    # Initialize sync logger
    logger_service = init_logging(
        log_dir=log_dir,
        level=LogLevel.INFO,
        async_enabled=False,
    )
    logger = get_logger("benchmark")

    # Warm-up phase (not counted)
    for _ in range(100):
        logger.info("Warmup log")

    # Benchmark phase
    start_time = time.perf_counter()

    for i in range(num_logs):
        # Measure individual log call latency
        log_start = time.perf_counter()

        logger.info(
            "Benchmark log entry",
            context={
                "iteration": i,
                "user_id": f"user-{i % 1000}",
                "request_id": f"req-{i}",
            },
        )

        log_end = time.perf_counter()
        latency_us = (log_end - log_start) * 1_000_000  # Convert to microseconds
        metrics.latencies_us.append(latency_us)

    end_time = time.perf_counter()
    metrics.total_time_s = end_time - start_time
    metrics.total_logs = num_logs

    return metrics


@pytest.mark.asyncio
async def test_async_vs_sync_performance(temp_log_dir):
    """
    Compare async vs sync logging performance.

    Validates that async logging meets performance requirements:
    - Async latency < 5μs (p95)
    - Async throughput > 100,000 logs/sec
    - Async is significantly faster than sync
    """
    num_logs = 10000

    # Benchmark async logging
    async_metrics = await benchmark_async_logging(temp_log_dir, num_logs)
    print(async_metrics)

    # Benchmark sync logging
    sync_metrics = await benchmark_sync_logging(temp_log_dir, num_logs)
    print(sync_metrics)

    # Print comparison
    print("\n" + "=" * 60)
    print("COMPARISON")
    print("=" * 60)
    print(f"Throughput improvement: {async_metrics.throughput_per_sec / sync_metrics.throughput_per_sec:.1f}x")
    print(f"Latency reduction (p95): {sync_metrics.p95_latency_us / async_metrics.p95_latency_us:.1f}x")
    print("=" * 60 + "\n")

    # Assertions: Async performance requirements
    assert async_metrics.p95_latency_us < 5.0, (
        f"Async p95 latency {async_metrics.p95_latency_us:.2f}μs exceeds requirement of < 5μs"
    )

    assert async_metrics.throughput_per_sec > 100_000, (
        f"Async throughput {async_metrics.throughput_per_sec:,.0f} logs/sec "
        f"is below requirement of > 100,000 logs/sec"
    )

    # Assertions: Async must be faster than sync
    assert async_metrics.throughput_per_sec > sync_metrics.throughput_per_sec, (
        "Async logging should have higher throughput than sync"
    )

    assert async_metrics.p95_latency_us < sync_metrics.p95_latency_us, (
        "Async logging should have lower latency than sync"
    )


@pytest.mark.asyncio
async def test_async_logging_under_load(temp_log_dir):
    """
    Test async logging under sustained load.

    Validates that async logging maintains performance under high load:
    - 50,000 logs with consistent latency
    - No memory leaks or queue saturation
    """
    num_logs = 50000

    metrics = await benchmark_async_logging(temp_log_dir, num_logs)
    print(metrics)

    # Validate sustained performance
    assert metrics.p95_latency_us < 10.0, (
        f"Under load, p95 latency {metrics.p95_latency_us:.2f}μs exceeds 10μs"
    )

    assert metrics.throughput_per_sec > 50_000, (
        f"Under load, throughput {metrics.throughput_per_sec:,.0f} logs/sec is below 50,000"
    )

    # Check latency consistency (p99 should not be too far from p95)
    latency_ratio = metrics.p99_latency_us / metrics.p95_latency_us
    assert latency_ratio < 5.0, (
        f"Latency distribution is inconsistent (p99/p95 = {latency_ratio:.1f}x)"
    )


@pytest.mark.asyncio
async def test_trace_correlation_overhead(temp_log_dir):
    """
    Test performance overhead of trace correlation.

    Validates that trace ID binding adds minimal overhead.
    """
    num_logs = 5000

    # Initialize logger
    logger_service = init_logging(
        log_dir=temp_log_dir,
        level=LogLevel.INFO,
        async_enabled=True,
    )
    await logger_service.start_async_writer()
    logger = get_logger("benchmark")

    # Benchmark without trace ID
    metrics_no_trace = PerformanceMetrics("Without Trace Correlation")
    start = time.perf_counter()

    for i in range(num_logs):
        log_start = time.perf_counter()
        logger.info("Log without trace", context={"iteration": i})
        log_end = time.perf_counter()
        metrics_no_trace.latencies_us.append((log_end - log_start) * 1_000_000)

    await logger_service.flush()
    metrics_no_trace.total_time_s = time.perf_counter() - start
    metrics_no_trace.total_logs = num_logs

    # Benchmark with trace ID
    metrics_with_trace = PerformanceMetrics("With Trace Correlation")
    start = time.perf_counter()

    for i in range(num_logs):
        with logger.bind_trace_id():
            log_start = time.perf_counter()
            logger.info("Log with trace", context={"iteration": i})
            log_end = time.perf_counter()
            metrics_with_trace.latencies_us.append((log_end - log_start) * 1_000_000)

    await logger_service.flush()
    metrics_with_trace.total_time_s = time.perf_counter() - start
    metrics_with_trace.total_logs = num_logs

    # Cleanup
    await logger_service.stop_async_writer()

    # Print results
    print(metrics_no_trace)
    print(metrics_with_trace)

    # Trace overhead should be < 1μs
    overhead_us = metrics_with_trace.p95_latency_us - metrics_no_trace.p95_latency_us
    print(f"\nTrace correlation overhead (p95): {overhead_us:.2f} μs\n")

    assert overhead_us < 1.0, f"Trace correlation overhead {overhead_us:.2f}μs exceeds 1μs"


@pytest.mark.asyncio
async def test_context_binding_overhead(temp_log_dir):
    """
    Test performance overhead of context binding.

    Validates that context binding adds minimal overhead.
    """
    num_logs = 5000

    # Initialize logger
    logger_service = init_logging(
        log_dir=temp_log_dir,
        level=LogLevel.INFO,
        async_enabled=True,
    )
    await logger_service.start_async_writer()
    logger = get_logger("benchmark")

    # Benchmark without context binding
    metrics_no_context = PerformanceMetrics("Without Context Binding")
    start = time.perf_counter()

    for i in range(num_logs):
        log_start = time.perf_counter()
        logger.info("Log without context", context={"iteration": i})
        log_end = time.perf_counter()
        metrics_no_context.latencies_us.append((log_end - log_start) * 1_000_000)

    await logger_service.flush()
    metrics_no_context.total_time_s = time.perf_counter() - start
    metrics_no_context.total_logs = num_logs

    # Benchmark with context binding
    metrics_with_context = PerformanceMetrics("With Context Binding")
    start = time.perf_counter()

    with logger.bind_context(user="test_user", session="sess-123"):
        for i in range(num_logs):
            log_start = time.perf_counter()
            logger.info("Log with context", context={"iteration": i})
            log_end = time.perf_counter()
            metrics_with_context.latencies_us.append((log_end - log_start) * 1_000_000)

    await logger_service.flush()
    metrics_with_context.total_time_s = time.perf_counter() - start
    metrics_with_context.total_logs = num_logs

    # Cleanup
    await logger_service.stop_async_writer()

    # Print results
    print(metrics_no_context)
    print(metrics_with_context)

    # Context binding overhead should be < 0.5μs
    overhead_us = metrics_with_context.p95_latency_us - metrics_no_context.p95_latency_us
    print(f"\nContext binding overhead (p95): {overhead_us:.2f} μs\n")

    assert overhead_us < 0.5, f"Context binding overhead {overhead_us:.2f}μs exceeds 0.5μs"


if __name__ == "__main__":
    """Run benchmarks standalone."""
    import sys

    async def main():
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            print("\n🚀 Running Performance Benchmarks...\n")

            # Run main comparison
            async_metrics = await benchmark_async_logging(log_dir, 10000)
            print(async_metrics)

            sync_metrics = await benchmark_sync_logging(log_dir, 10000)
            print(sync_metrics)

            # Print comparison
            print("\n" + "=" * 60)
            print("COMPARISON SUMMARY")
            print("=" * 60)
            print(f"Throughput improvement: {async_metrics.throughput_per_sec / sync_metrics.throughput_per_sec:.1f}x")
            print(f"Latency reduction (p95): {sync_metrics.p95_latency_us / async_metrics.p95_latency_us:.1f}x")

            # Check performance requirements
            print("\n" + "=" * 60)
            print("PERFORMANCE REQUIREMENTS CHECK")
            print("=" * 60)

            # Async p95 < 5μs
            if async_metrics.p95_latency_us < 5.0:
                print(f"✅ Async p95 latency: {async_metrics.p95_latency_us:.2f}μs < 5μs")
            else:
                print(f"❌ Async p95 latency: {async_metrics.p95_latency_us:.2f}μs >= 5μs")

            # Async throughput > 100k/sec
            if async_metrics.throughput_per_sec > 100_000:
                print(f"✅ Async throughput: {async_metrics.throughput_per_sec:,.0f} logs/sec > 100,000")
            else:
                print(f"❌ Async throughput: {async_metrics.throughput_per_sec:,.0f} logs/sec <= 100,000")

            print("=" * 60 + "\n")

    asyncio.run(main())

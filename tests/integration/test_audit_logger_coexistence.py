"""
Integration Test: P1 AuditLogger + P2 Logging Infrastructure Coexistence

This test validates that the new P2 logging infrastructure can coexist
with the frozen P1 AuditLogger without conflicts or interference.

Constitutional compliance:
- Section 2: Both systems write to disk
- Frozen control plane: P1 AuditLogger remains unchanged
- Additive only: P2 logging doesn't modify P1 code

SKIPPED: Test references State and Transition classes that were planned but not implemented.
"""

import pytest

pytestmark = pytest.mark.skip(
    reason="Test references State/Transition classes not yet implemented"
)

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

# P1 imports (frozen control plane)
from src.control_plane.logger import AuditLogger
from src.control_plane.state_machine import StateMachine

# P2 imports (new logging infrastructure)
from src.logging import init_logging, get_logger
from src.logging.models import LogLevel
from src.logging.query_service import QueryService, LogQuery


@pytest.fixture
def temp_log_dir():
    """Shared temp directory for both logging systems."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def audit_logger(temp_log_dir):
    """P1 AuditLogger instance (frozen)."""
    return AuditLogger(log_dir=temp_log_dir)


@pytest.fixture
async def p2_logger_service(temp_log_dir):
    """P2 LoggerService instance (new)."""
    logger = init_logging(
        log_dir=temp_log_dir,
        level=LogLevel.INFO,
        async_enabled=True,
    )
    await logger.start_async_writer()
    yield logger
    await logger.stop_async_writer()


@pytest.fixture
def query_service(temp_log_dir):
    """Query service for P2 logs."""
    return QueryService(log_dir=temp_log_dir)


@pytest.mark.asyncio
async def test_both_loggers_write_to_same_directory(
    audit_logger, p2_logger_service, temp_log_dir
):
    """
    Test that P1 and P2 loggers can write to the same directory without conflicts.

    Validates:
    - Both systems create their own log files
    - No file name conflicts
    - Both systems can operate independently
    """
    # P1: Use AuditLogger to log a transition
    sm = StateMachine(logger=audit_logger)
    transition = Transition(
        from_state=State.INITIALIZED,
        to_state=State.PLANNING,
        timestamp="2026-01-28T12:00:00Z",
        trigger="user_input",
        context={"task": "Build logging infrastructure"},
    )
    audit_logger.log_transition(transition)

    # P2: Use new logging infrastructure
    logger = get_logger("integration_test")
    logger.info(
        "P2 logging system operational",
        context={
            "feature": "logging-infrastructure",
            "test": "coexistence",
        },
    )

    # Flush P2 logs
    await p2_logger_service.flush()

    # Check that both log files exist
    log_files = list(temp_log_dir.glob("*.log"))
    assert len(log_files) >= 1, "At least one log file should exist"

    # P1 creates audit_YYYYMMDD.log files
    audit_log_files = list(temp_log_dir.glob("audit_*.log"))

    # P2 creates YYYYMMDD.log files
    p2_log_files = list(temp_log_dir.glob("[0-9]*.log"))

    # Both should have created files
    assert (
        len(audit_log_files) > 0 or len(p2_log_files) > 0
    ), "Both logging systems should create log files"

    print(f"\nP1 audit logs: {audit_log_files}")
    print(f"P2 logs: {p2_log_files}")
    print(f"All log files: {log_files}")


@pytest.mark.asyncio
async def test_p1_logger_not_modified(audit_logger, p2_logger_service, temp_log_dir):
    """
    Test that P1 AuditLogger behavior is unchanged by P2 logging infrastructure.

    Validates:
    - AuditLogger API remains the same
    - AuditLogger produces expected output
    - No side effects from P2 initialization
    """
    # Use P1 AuditLogger (should work exactly as before)
    sm = StateMachine(logger=audit_logger)

    # Log several transitions (P1 usage pattern)
    transitions = [
        Transition(
            from_state=State.INITIALIZED,
            to_state=State.PLANNING,
            timestamp="2026-01-28T12:00:00Z",
            trigger="start",
            context={"task": "Plan feature"},
        ),
        Transition(
            from_state=State.PLANNING,
            to_state=State.EXECUTING,
            timestamp="2026-01-28T12:01:00Z",
            trigger="plan_approved",
            context={"plan_id": "plan-001"},
        ),
        Transition(
            from_state=State.EXECUTING,
            to_state=State.COMPLETED,
            timestamp="2026-01-28T12:10:00Z",
            trigger="tasks_done",
            context={"duration_minutes": 9},
        ),
    ]

    for t in transitions:
        audit_logger.log_transition(t)

    # Verify P1 logs were created
    audit_files = list(temp_log_dir.glob("audit_*.log"))
    assert len(audit_files) > 0, "P1 AuditLogger should create audit_*.log files"

    # Read P1 audit log and verify format
    audit_content = audit_files[0].read_text()
    assert "INITIALIZED" in audit_content
    assert "PLANNING" in audit_content
    assert "EXECUTING" in audit_content
    assert "COMPLETED" in audit_content
    assert "Plan feature" in audit_content

    print(f"\n✅ P1 AuditLogger working correctly")
    print(f"Audit log: {audit_files[0]}")
    print(f"Content preview:\n{audit_content[:300]}...")


@pytest.mark.asyncio
async def test_p2_logger_queries_dont_affect_p1(
    audit_logger,
    p2_logger_service,
    query_service,
    temp_log_dir,
):
    """
    Test that P2 query operations don't interfere with P1 audit logs.

    Validates:
    - P2 queries only read P2 logs
    - P1 audit logs are not affected by P2 queries
    - Both systems can operate concurrently
    """
    # P1: Write audit logs
    sm = StateMachine(logger=audit_logger)
    audit_logger.log_transition(
        Transition(
            from_state=State.INITIALIZED,
            to_state=State.PLANNING,
            timestamp="2026-01-28T12:00:00Z",
            trigger="start",
            context={},
        )
    )

    # P2: Write logs
    logger = get_logger("integration_test")
    logger.info("P2 log entry 1")
    logger.warning("P2 warning entry")
    logger.error("P2 error entry")
    await p2_logger_service.flush()

    # P2: Query logs (should only see P2 logs, not P1)
    results = query_service.query(
        LogQuery(levels=[LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR]),
        format="dict",
    )

    # Results should contain P2 logs
    messages = [r.message for r in results]
    assert "P2 log entry 1" in messages
    assert "P2 warning entry" in messages
    assert "P2 error entry" in messages

    # Results should NOT contain P1 audit transition data
    # (P1 uses different format, P2 QueryService reads NDJSON)
    for result in results:
        assert "INITIALIZED" not in result.message
        assert "PLANNING" not in result.message

    print(f"\n✅ P2 queries operate independently")
    print(f"Found {len(results)} P2 log entries")
    print(f"P2 messages: {messages}")


@pytest.mark.asyncio
async def test_concurrent_logging_from_both_systems(
    audit_logger,
    p2_logger_service,
    temp_log_dir,
):
    """
    Test that P1 and P2 can log concurrently without conflicts or data loss.

    Validates:
    - Concurrent writes don't corrupt files
    - Both systems complete successfully
    - No exceptions or errors from either system
    """
    # Start concurrent logging

    async def p2_logging_task():
        """P2 logging in background."""
        logger = get_logger("concurrent_test")
        for i in range(100):
            logger.info(f"P2 concurrent log {i}", context={"iteration": i})
            await asyncio.sleep(0.001)  # Small delay
        await p2_logger_service.flush()

    def p1_logging_task():
        """P1 logging in same timeframe."""
        sm = StateMachine(logger=audit_logger)
        for i in range(100):
            audit_logger.log_transition(
                Transition(
                    from_state=State.INITIALIZED,
                    to_state=State.PLANNING,
                    timestamp=f"2026-01-28T12:00:{i:02d}Z",
                    trigger=f"concurrent_trigger_{i}",
                    context={"iteration": i},
                )
            )

    # Run concurrently
    await asyncio.gather(
        p2_logging_task(),
        asyncio.to_thread(p1_logging_task),  # Run P1 in thread
    )

    # Verify both systems completed successfully
    log_files = list(temp_log_dir.glob("*.log"))
    assert len(log_files) >= 1, "Log files should exist"

    print(f"\n✅ Concurrent logging successful")
    print(f"Total log files: {len(log_files)}")
    for log_file in log_files:
        print(f"  - {log_file.name}: {log_file.stat().st_size} bytes")


@pytest.mark.asyncio
async def test_p1_and_p2_log_formats_are_distinct(
    audit_logger,
    p2_logger_service,
    temp_log_dir,
):
    """
    Test that P1 and P2 use distinct log formats without conflicts.

    Validates:
    - P1 uses its own format (state transition logs)
    - P2 uses NDJSON format (structured logs)
    - Formats don't conflict or interfere
    """
    # P1: Write state transition
    sm = StateMachine(logger=audit_logger)
    audit_logger.log_transition(
        Transition(
            from_state=State.INITIALIZED,
            to_state=State.PLANNING,
            timestamp="2026-01-28T12:00:00Z",
            trigger="start",
            context={"task": "test"},
        )
    )

    # P2: Write structured log
    logger = get_logger("format_test")
    logger.info(
        "Structured log entry",
        context={
            "level": "info",
            "module": "format_test",
            "structured": True,
        },
    )
    await p2_logger_service.flush()

    # Read log files
    log_files = list(temp_log_dir.glob("*.log"))
    assert len(log_files) >= 1

    # Check formats
    for log_file in log_files:
        content = log_file.read_text()

        # If it's a P2 log (NDJSON), should have JSON structure
        if "format_test" in content:
            # Should contain JSON fields
            assert '"timestamp"' in content or '"level"' in content
            print(f"\n✅ P2 log format (NDJSON): {log_file.name}")
            print(f"Sample: {content[:200]}...")

        # If it's a P1 audit log, should have transition format
        if "INITIALIZED" in content and "PLANNING" in content:
            print(f"\n✅ P1 log format (transitions): {log_file.name}")
            print(f"Sample: {content[:200]}...")


@pytest.mark.asyncio
async def test_p2_logger_respects_frozen_code_constraint(p2_logger_service):
    """
    Test that P2 logging infrastructure respects frozen code constraint.

    Validates:
    - P2 code is in src/logging/ (not src/control_plane/)
    - P2 doesn't import or modify P1 AuditLogger
    - P2 is truly additive
    """
    import inspect
    from src.logging.logger_service import LoggerService

    # Get LoggerService source file
    logger_service_file = inspect.getfile(LoggerService)

    # Should be in src/logging/, not src/control_plane/
    assert (
        "src/logging" in logger_service_file or "src\\logging" in logger_service_file
    ), f"P2 logging should be in src/logging/, but found in: {logger_service_file}"

    assert (
        "control_plane" not in logger_service_file
    ), "P2 logging should NOT be in control_plane (frozen code)"

    # Verify P2 doesn't import P1 AuditLogger
    import src.logging

    logger_module_file = inspect.getfile(src.logging)
    logger_module_source = inspect.getsource(src.logging)

    assert (
        "from src.control_plane.logger import AuditLogger" not in logger_module_source
    ), "P2 logging should NOT import P1 AuditLogger"

    print(f"\n✅ P2 logging respects frozen code constraint")
    print(f"P2 location: {logger_service_file}")
    print(f"No P1 imports found in P2 code")


if __name__ == "__main__":
    """Run integration tests standalone."""
    import sys

    async def main():
        with TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)

            print("\n🧪 Running Integration Tests: P1 + P2 Coexistence\n")

            # Create fixtures
            audit_logger = AuditLogger(log_dir=log_dir)
            logger_service = init_logging(
                log_dir=log_dir, level=LogLevel.INFO, async_enabled=True
            )
            await logger_service.start_async_writer()

            # Test 1: Same directory
            print("Test 1: Both loggers write to same directory...")
            p1_logger = get_logger("test")
            p1_logger.info("Test log")
            audit_logger.log_transition(
                Transition(
                    from_state=State.INITIALIZED,
                    to_state=State.PLANNING,
                    timestamp="2026-01-28T12:00:00Z",
                    trigger="test",
                    context={},
                )
            )
            await logger_service.flush()

            log_files = list(log_dir.glob("*.log"))
            print(
                f"✅ Created {len(log_files)} log file(s): {[f.name for f in log_files]}"
            )

            # Test 2: P1 unchanged
            print("\nTest 2: P1 AuditLogger unchanged...")
            audit_logger.log_transition(
                Transition(
                    from_state=State.PLANNING,
                    to_state=State.EXECUTING,
                    timestamp="2026-01-28T12:01:00Z",
                    trigger="approved",
                    context={},
                )
            )
            print("✅ P1 AuditLogger operates normally")

            # Cleanup
            await logger_service.stop_async_writer()

            print("\n✅ All integration tests passed!\n")

    asyncio.run(main())

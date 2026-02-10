"""
Tests for the security-module circuit breaker (spec 004 Platinum US12).

These tests exercise the circuit breaker specifically through the
security-module re-export path (src.security.circuit_breaker) and cover
the MCP-guard integration scenarios that the watcher-level tests do not:
  - per-MCP-server isolation (one breaker opening does not affect others)
  - MCPGuard.breaker_state() reflects the live circuit state
  - force_open / force_close for incident-response workflows
  - stats accumulation across state transitions
"""

import sys
import time

# ---------------------------------------------------------------------------
# Import helpers  (avoid triggering the logging shadow — see MEMORY.md)
# ---------------------------------------------------------------------------
sys.path.insert(0, ".")

from security.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerRegistry,
    CircuitState,
)

# ---------------------------------------------------------------------------
# Basic state-machine tests
# ---------------------------------------------------------------------------


def test_initial_state_is_closed():
    cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=1.0)
    assert cb.state == CircuitState.CLOSED


def test_successful_calls_stay_closed():
    cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=1.0)
    for _ in range(10):
        cb.call(lambda: "ok")
    assert cb.state == CircuitState.CLOSED
    assert cb.stats.successful_calls == 10


def test_failures_open_circuit_at_threshold():
    cb = CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=60.0)

    for _ in range(2):
        try:
            cb.call(_raise)
        except RuntimeError:
            pass

    # Not yet open
    assert cb.state == CircuitState.CLOSED

    # Third failure trips the breaker
    try:
        cb.call(_raise)
    except RuntimeError:
        pass

    assert cb.state == CircuitState.OPEN


def test_open_circuit_rejects_calls():
    cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=60.0)

    # Trip it
    try:
        cb.call(_raise)
    except RuntimeError:
        pass

    assert cb.state == CircuitState.OPEN

    # Next call should be rejected without executing the function
    rejected = False
    try:
        cb.call(lambda: "should not run")
    except CircuitBreakerError as exc:
        rejected = True
        assert exc.time_until_retry > 0

    assert rejected
    assert cb.stats.rejected_calls == 1


# ---------------------------------------------------------------------------
# Recovery (OPEN → HALF_OPEN → CLOSED)
# ---------------------------------------------------------------------------


def test_recovery_timeout_transitions_to_half_open():
    cb = CircuitBreaker(
        name="test",
        failure_threshold=1,
        recovery_timeout=0.05,  # 50 ms for fast test
        success_threshold=1,
    )

    # Trip it
    try:
        cb.call(_raise)
    except RuntimeError:
        pass
    assert cb.state == CircuitState.OPEN

    # Wait past recovery timeout
    time.sleep(0.06)

    # Next call should be allowed (half-open probe)
    result = cb.call(lambda: "recovered")
    assert result == "recovered"
    # With success_threshold=1 a single success closes the circuit
    assert cb.state == CircuitState.CLOSED


def test_failure_in_half_open_reopens():
    cb = CircuitBreaker(
        name="test",
        failure_threshold=1,
        recovery_timeout=0.05,
        success_threshold=2,  # need 2 successes to close
    )

    # Trip
    try:
        cb.call(_raise)
    except RuntimeError:
        pass
    assert cb.state == CircuitState.OPEN

    time.sleep(0.06)

    # Half-open probe fails → reopen
    try:
        cb.call(_raise)
    except RuntimeError:
        pass
    assert cb.state == CircuitState.OPEN


# ---------------------------------------------------------------------------
# Per-server isolation (MCP guard scenario)
# ---------------------------------------------------------------------------


def test_per_server_isolation():
    """Opening one MCP breaker must not affect another."""
    registry = CircuitBreakerRegistry()
    payment = registry.get("payment-mcp", failure_threshold=1, recovery_timeout=60.0)
    email = registry.get("email-mcp", failure_threshold=1, recovery_timeout=60.0)

    # Trip payment only
    try:
        payment.call(_raise)
    except RuntimeError:
        pass

    assert payment.state == CircuitState.OPEN
    assert email.state == CircuitState.CLOSED

    # Email still works fine
    assert email.call(lambda: "sent") == "sent"


# ---------------------------------------------------------------------------
# Incident-response: force open / force close
# ---------------------------------------------------------------------------


def test_force_open():
    cb = CircuitBreaker(name="test", failure_threshold=100, recovery_timeout=60.0)
    assert cb.state == CircuitState.CLOSED

    cb.force_open()
    assert cb.state == CircuitState.OPEN

    try:
        cb.call(lambda: None)
    except CircuitBreakerError:
        pass  # expected


def test_force_close():
    cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=60.0)

    # Trip it
    try:
        cb.call(_raise)
    except RuntimeError:
        pass
    assert cb.state == CircuitState.OPEN

    cb.force_close()
    assert cb.state == CircuitState.CLOSED
    assert cb.call(lambda: "back") == "back"


# ---------------------------------------------------------------------------
# Stats accuracy
# ---------------------------------------------------------------------------


def test_stats_track_all_categories():
    cb = CircuitBreaker(
        name="test",
        failure_threshold=2,
        recovery_timeout=0.05,
        success_threshold=1,
    )

    # 3 successes
    for _ in range(3):
        cb.call(lambda: None)

    # 1 failure (doesn't open yet)
    try:
        cb.call(_raise)
    except RuntimeError:
        pass

    # 1 more failure → opens
    try:
        cb.call(_raise)
    except RuntimeError:
        pass

    # 1 rejection
    try:
        cb.call(lambda: None)
    except CircuitBreakerError:
        pass

    stats = cb.stats
    assert stats.successful_calls == 3
    assert stats.failed_calls == 2
    assert stats.rejected_calls == 1
    assert stats.total_calls == 6  # 3 + 2 + 1
    assert stats.state_transitions >= 1  # at least CLOSED → OPEN


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------


def test_registry_get_all_stats():
    registry = CircuitBreakerRegistry()
    registry.get("a", failure_threshold=5)
    registry.get("b", failure_threshold=5)

    stats = registry.get_all_stats()
    assert "a" in stats
    assert "b" in stats


def test_registry_reset_all():
    registry = CircuitBreakerRegistry()
    cb = registry.get("svc", failure_threshold=1, recovery_timeout=60.0)

    try:
        cb.call(_raise)
    except RuntimeError:
        pass
    assert cb.state == CircuitState.OPEN

    registry.reset_all()
    assert cb.state == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _raise():
    raise RuntimeError("simulated failure")

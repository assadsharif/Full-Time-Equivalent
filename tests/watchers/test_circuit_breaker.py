"""Tests for Circuit Breaker."""

import time
from unittest import mock

import pytest

from src.watchers.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerRegistry,
    CircuitState,
    get_circuit_breaker,
)


class TestCircuitBreaker:
    """Test suite for CircuitBreaker."""

    def test_initial_state_closed(self):
        """Test circuit starts in CLOSED state."""
        breaker = CircuitBreaker(name="test")
        assert breaker.state == CircuitState.CLOSED

    def test_successful_calls_stay_closed(self):
        """Test successful calls keep circuit CLOSED."""
        breaker = CircuitBreaker(name="test", failure_threshold=3)

        for _ in range(10):
            result = breaker.call(lambda: "success")
            assert result == "success"

        assert breaker.state == CircuitState.CLOSED
        assert breaker.stats.successful_calls == 10
        assert breaker.stats.failed_calls == 0

    def test_failures_open_circuit(self):
        """Test consecutive failures open the circuit."""
        breaker = CircuitBreaker(name="test", failure_threshold=3)

        def failing_func():
            raise ValueError("test error")

        # First 2 failures - still CLOSED
        for i in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)
        assert breaker.state == CircuitState.CLOSED

        # Third failure - opens circuit
        with pytest.raises(ValueError):
            breaker.call(failing_func)
        assert breaker.state == CircuitState.OPEN

    def test_open_circuit_rejects_calls(self):
        """Test OPEN circuit rejects calls immediately."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=60,
        )

        def failing_func():
            raise ValueError("test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Next call should be rejected
        with pytest.raises(CircuitBreakerError) as exc_info:
            breaker.call(lambda: "should not execute")

        assert "OPEN" in str(exc_info.value)
        assert breaker.stats.rejected_calls == 1

    def test_recovery_timeout_transitions_to_half_open(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=0.1,  # 100ms for testing
        )

        def failing_func():
            raise ValueError("test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)

        # Next call should transition to HALF_OPEN and execute
        result = breaker.call(lambda: "success")
        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN

    def test_half_open_success_closes_circuit(self):
        """Test successful calls in HALF_OPEN close the circuit."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=0.1,
            success_threshold=2,
        )

        def failing_func():
            raise ValueError("test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        # Wait and transition to HALF_OPEN
        time.sleep(0.15)
        breaker.call(lambda: "success")  # First success
        assert breaker.state == CircuitState.HALF_OPEN

        # Second success should close
        breaker.call(lambda: "success")
        assert breaker.state == CircuitState.CLOSED

    def test_half_open_failure_reopens_circuit(self):
        """Test failure in HALF_OPEN reopens the circuit."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=0.1,
        )

        def failing_func():
            raise ValueError("test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        # Wait and transition to HALF_OPEN with success
        time.sleep(0.15)
        breaker.call(lambda: "success")
        assert breaker.state == CircuitState.HALF_OPEN

        # Failure should reopen
        with pytest.raises(ValueError):
            breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        """Test successful call resets consecutive failure count."""
        breaker = CircuitBreaker(name="test", failure_threshold=3)

        def failing_func():
            raise ValueError("test error")

        # Two failures
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        # Success resets count
        breaker.call(lambda: "success")

        # Two more failures - should not open (count reset)
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        assert breaker.state == CircuitState.CLOSED

    def test_reset(self):
        """Test circuit reset."""
        breaker = CircuitBreaker(name="test", failure_threshold=2)

        def failing_func():
            raise ValueError("test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Reset
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED

        # Should allow calls again
        result = breaker.call(lambda: "success")
        assert result == "success"

    def test_force_open(self):
        """Test forcing circuit open."""
        breaker = CircuitBreaker(name="test")
        assert breaker.state == CircuitState.CLOSED

        breaker.force_open()
        assert breaker.state == CircuitState.OPEN

        with pytest.raises(CircuitBreakerError):
            breaker.call(lambda: "should fail")

    def test_force_close(self):
        """Test forcing circuit closed."""
        breaker = CircuitBreaker(name="test", failure_threshold=2)

        def failing_func():
            raise ValueError("test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        assert breaker.state == CircuitState.OPEN

        # Force close
        breaker.force_close()
        assert breaker.state == CircuitState.CLOSED

    def test_stats_tracking(self):
        """Test statistics are tracked correctly."""
        breaker = CircuitBreaker(name="test", failure_threshold=3)

        def failing_func():
            raise ValueError("test error")

        # 5 successes
        for _ in range(5):
            breaker.call(lambda: "success")

        # 2 failures
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        stats = breaker.stats
        assert stats.total_calls == 7
        assert stats.successful_calls == 5
        assert stats.failed_calls == 2
        assert stats.consecutive_failures == 2

    def test_time_until_retry(self):
        """Test time_until_retry in CircuitBreakerError."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=2,
            recovery_timeout=10,
        )

        def failing_func():
            raise ValueError("test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        # Check time until retry
        with pytest.raises(CircuitBreakerError) as exc_info:
            breaker.call(lambda: "should fail")

        # Should be close to 10 seconds
        assert exc_info.value.time_until_retry > 9
        assert exc_info.value.time_until_retry <= 10


class TestCircuitBreakerRegistry:
    """Test suite for CircuitBreakerRegistry."""

    def test_get_creates_new_breaker(self):
        """Test get creates new circuit breaker."""
        registry = CircuitBreakerRegistry()
        breaker = registry.get("test", failure_threshold=5)

        assert breaker.name == "test"
        assert breaker.failure_threshold == 5

    def test_get_returns_existing_breaker(self):
        """Test get returns same instance for same name."""
        registry = CircuitBreakerRegistry()
        breaker1 = registry.get("test")
        breaker2 = registry.get("test")

        assert breaker1 is breaker2

    def test_get_all_stats(self):
        """Test getting stats for all breakers."""
        registry = CircuitBreakerRegistry()
        registry.get("breaker1")
        registry.get("breaker2")

        # Make some calls
        registry.get("breaker1").call(lambda: "success")

        stats = registry.get_all_stats()
        assert "breaker1" in stats
        assert "breaker2" in stats
        assert stats["breaker1"].successful_calls == 1

    def test_reset_all(self):
        """Test resetting all breakers."""
        registry = CircuitBreakerRegistry()

        def failing_func():
            raise ValueError("test")

        # Open breaker1
        b1 = registry.get("breaker1", failure_threshold=1)
        with pytest.raises(ValueError):
            b1.call(failing_func)
        assert b1.state == CircuitState.OPEN

        # Reset all
        registry.reset_all()
        assert b1.state == CircuitState.CLOSED


class TestGlobalRegistry:
    """Test global circuit breaker registry function."""

    def test_get_circuit_breaker(self):
        """Test global get_circuit_breaker function."""
        breaker = get_circuit_breaker("global_test", failure_threshold=3)
        assert breaker.name == "global_test"
        assert breaker.failure_threshold == 3

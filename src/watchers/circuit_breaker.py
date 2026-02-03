"""
Circuit Breaker Pattern for Watcher Error Recovery.

Prevents retry storms by opening the circuit after consecutive failures,
allowing time for external services to recover.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Circuit tripped, all requests fail immediately
- HALF_OPEN: Testing recovery, limited requests allowed

Constitutional Compliance:
- Section 9: Graceful error handling and recovery
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any, Callable, Optional, TypeVar

# Try to import the logging module, fall back to standard logging
try:
    from src.logging import get_logger
except ImportError:
    import logging

    def get_logger(name: str):
        return logging.getLogger(name)


logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit tripped, failing fast
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, message: str, time_until_retry: float = 0):
        super().__init__(message)
        self.time_until_retry = time_until_retry


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0  # Calls rejected while OPEN
    state_transitions: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


@dataclass
class CircuitBreaker:
    """
    Circuit Breaker for protecting external service calls.

    Opens after `failure_threshold` consecutive failures, preventing
    further calls for `recovery_timeout` seconds. After timeout,
    enters HALF_OPEN state to test if service has recovered.

    Example:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        try:
            result = breaker.call(lambda: external_api_call())
        except CircuitBreakerError as e:
            # Circuit is open, handle gracefully
            logger.warning(f"Circuit open, retry in {e.time_until_retry}s")

    Thread-safe implementation using locks.
    """

    name: str = "default"
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 3  # Max calls in HALF_OPEN before deciding
    success_threshold: int = 2  # Successes needed to close from HALF_OPEN

    # Internal state (initialized in __post_init__)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _last_failure_time: Optional[float] = field(default=None, init=False)
    _failure_count: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)
    _half_open_calls: int = field(default=0, init=False)
    _lock: Lock = field(default_factory=Lock, init=False)
    _stats: CircuitBreakerStats = field(default_factory=CircuitBreakerStats, init=False)

    def __post_init__(self):
        """Initialize mutable defaults."""
        self._lock = Lock()
        self._stats = CircuitBreakerStats()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            return self._state

    @property
    def stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics."""
        with self._lock:
            return CircuitBreakerStats(
                total_calls=self._stats.total_calls,
                successful_calls=self._stats.successful_calls,
                failed_calls=self._stats.failed_calls,
                rejected_calls=self._stats.rejected_calls,
                state_transitions=self._stats.state_transitions,
                last_failure_time=self._stats.last_failure_time,
                last_success_time=self._stats.last_success_time,
                consecutive_failures=self._failure_count,
                consecutive_successes=self._success_count,
            )

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state (must hold lock)."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            self._stats.state_transitions += 1

            logger.info(
                f"Circuit breaker '{self.name}': {old_state.value} -> {new_state.value}",
                context={
                    "circuit_name": self.name,
                    "old_state": old_state.value,
                    "new_state": new_state.value,
                    "failure_count": self._failure_count,
                },
            )

            # Reset counters on state change
            if new_state == CircuitState.HALF_OPEN:
                self._half_open_calls = 0
                self._success_count = 0
            elif new_state == CircuitState.CLOSED:
                self._failure_count = 0

    def _should_attempt(self) -> bool:
        """
        Check if a call should be attempted (must hold lock).

        Returns:
            True if call should proceed, False if should fail fast
        """
        now = time.time()

        if self._state == CircuitState.CLOSED:
            return True

        elif self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self._last_failure_time is None:
                return True

            time_since_failure = now - self._last_failure_time
            if time_since_failure >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)
                return True

            return False

        elif self._state == CircuitState.HALF_OPEN:
            # Allow limited calls to test recovery
            if self._half_open_calls < self.half_open_max_calls:
                return True
            return False

        return False

    def _record_success(self) -> None:
        """Record a successful call (must hold lock)."""
        self._stats.successful_calls += 1
        self._stats.last_success_time = datetime.now(timezone.utc)
        self._failure_count = 0
        self._success_count += 1

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._success_count >= self.success_threshold:
                self._transition_to(CircuitState.CLOSED)

    def _record_failure(self, error: Exception) -> None:
        """Record a failed call (must hold lock)."""
        self._stats.failed_calls += 1
        self._stats.last_failure_time = datetime.now(timezone.utc)
        self._last_failure_time = time.time()
        self._failure_count += 1
        self._success_count = 0

        if self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)

        elif self._state == CircuitState.HALF_OPEN:
            # Any failure in HALF_OPEN reopens the circuit
            self._transition_to(CircuitState.OPEN)

    def call(self, func: Callable[[], T]) -> T:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Function to execute

        Returns:
            Function result

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Original exception if call fails
        """
        with self._lock:
            self._stats.total_calls += 1

            if not self._should_attempt():
                self._stats.rejected_calls += 1
                time_until_retry = 0.0
                if self._last_failure_time:
                    time_until_retry = max(
                        0,
                        self.recovery_timeout - (time.time() - self._last_failure_time),
                    )

                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is OPEN",
                    time_until_retry=time_until_retry,
                )

        # Execute function outside lock
        try:
            result = func()

            with self._lock:
                self._record_success()

            return result

        except Exception as e:
            with self._lock:
                self._record_failure(e)
            raise

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            self._last_failure_time = None

            logger.info(f"Circuit breaker '{self.name}' reset to CLOSED")

    def force_open(self) -> None:
        """Force circuit breaker to OPEN state (for testing/maintenance)."""
        with self._lock:
            self._transition_to(CircuitState.OPEN)
            self._last_failure_time = time.time()

    def force_close(self) -> None:
        """Force circuit breaker to CLOSED state."""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._failure_count = 0


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Provides centralized access to circuit breakers by name,
    useful when multiple services need protection.

    Example:
        registry = CircuitBreakerRegistry()
        gmail_breaker = registry.get("gmail", failure_threshold=5)
        api_breaker = registry.get("external_api", failure_threshold=3)
    """

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = Lock()

    def get(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        **kwargs,
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker by name.

        Args:
            name: Circuit breaker name
            failure_threshold: Failures before opening
            recovery_timeout: Seconds before attempting recovery
            **kwargs: Additional CircuitBreaker arguments

        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    **kwargs,
                )
            return self._breakers[name]

    def get_all_stats(self) -> dict[str, CircuitBreakerStats]:
        """Get stats for all registered circuit breakers."""
        with self._lock:
            return {name: breaker.stats for name, breaker in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()


# Global registry for convenience
_global_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
) -> CircuitBreaker:
    """
    Get a circuit breaker from the global registry.

    Args:
        name: Circuit breaker name
        failure_threshold: Failures before opening
        recovery_timeout: Seconds before attempting recovery

    Returns:
        CircuitBreaker instance
    """
    return _global_registry.get(name, failure_threshold, recovery_timeout)

"""
Circuit Breaker — security-module public surface (spec 004 Platinum US12).

The canonical implementation lives in ``src.watchers.circuit_breaker``,
written for the watcher error-recovery use case.  This module re-exports
the full public API so that MCPGuard and other security consumers can
import from a single package without reaching across module boundaries.

Usage::

    from src.security.circuit_breaker import CircuitBreaker, CircuitBreakerError

    breaker = CircuitBreaker(name="payment-mcp", failure_threshold=3, recovery_timeout=60)
    try:
        result = breaker.call(lambda: make_payment(...))
    except CircuitBreakerError as exc:
        logger.warning("payment-mcp circuit open — retry in %ss", exc.time_until_retry)
"""

from watchers.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerRegistry,
    CircuitBreakerStats,
    CircuitState,
    get_circuit_breaker,
)

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerError",
    "CircuitBreakerRegistry",
    "CircuitBreakerStats",
    "CircuitState",
    "get_circuit_breaker",
]

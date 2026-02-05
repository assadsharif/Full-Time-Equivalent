"""
MCP Guard — composite security gate for MCP server calls (spec 004 Gold).

Wraps every outbound MCP call with:
    1. Rate-limit check (token bucket)
    2. Circuit-breaker protection (reuses watchers.circuit_breaker)
    3. Append-only audit log entry

All three checks happen before the callable is invoked.  If any guard
fires, the call is rejected and the failure is logged.
"""

import time
from typing import Callable, TypeVar

from src.security.audit_logger import SecurityAuditLogger
from src.security.models import RiskLevel
from src.security.rate_limiter import RateLimiter, RateLimitExceededError
from src.security.circuit_breaker import CircuitBreaker, CircuitBreakerError

T = TypeVar("T")


class MCPGuard:
    """
    Composite security gate.

    Args:
        rate_limiter: shared RateLimiter instance.
        audit_logger: shared SecurityAuditLogger instance.
        failure_threshold: consecutive failures before a per-server circuit opens.
        recovery_timeout: seconds the circuit stays open before half-open probe.
    """

    def __init__(
        self,
        rate_limiter: RateLimiter,
        audit_logger: SecurityAuditLogger,
        failure_threshold: int = 3,
        recovery_timeout: float = 60.0,
    ):
        self._rate_limiter = rate_limiter
        self._audit = audit_logger
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._breakers: dict[str, CircuitBreaker] = {}

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def call(
        self,
        server: str,
        action_type: str,
        fn: Callable[[], T],
        *,
        approved: bool = True,
        risk_level: RiskLevel = RiskLevel.LOW,
        approval_id: str | None = None,
        nonce: str | None = None,
    ) -> T:
        """
        Execute *fn* through the full security gate.

        Raises:
            RateLimitExceededError: rate limit exhausted.
            CircuitBreakerError: circuit is open for this server.
            Any exception raised by *fn* (propagated after logging).
        """
        # 1. Rate limit
        try:
            self._rate_limiter.consume(server, action_type)
        except RateLimitExceededError:
            self._audit.log_mcp_action(
                server, action_type, approved, risk_level,
                approval_id=approval_id, nonce=nonce,
                result="rate_limit_exceeded",
            )
            raise

        # 2. Circuit-breaker wrapped execution
        breaker = self._get_breaker(server)
        start = time.monotonic()
        try:
            result: T = breaker.call(fn)
        except CircuitBreakerError:
            self._audit.log_mcp_action(
                server, action_type, approved, risk_level,
                approval_id=approval_id, nonce=nonce,
                result="circuit_open",
            )
            raise
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            self._audit.log_mcp_action(
                server, action_type, approved, risk_level,
                approval_id=approval_id, nonce=nonce,
                result=f"error:{type(exc).__name__}",
                duration_ms=duration_ms,
            )
            raise

        # 3. Success path
        duration_ms = int((time.monotonic() - start) * 1000)
        self._audit.log_mcp_action(
            server, action_type, approved, risk_level,
            approval_id=approval_id, nonce=nonce,
            result="success",
            duration_ms=duration_ms,
        )
        return result

    def breaker_state(self, server: str) -> str:
        """Return the current circuit state for a server (or 'closed' if unseen)."""
        if server in self._breakers:
            return self._breakers[server].state.value
        return "closed"

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_breaker(self, server: str) -> CircuitBreaker:
        if server not in self._breakers:
            self._breakers[server] = CircuitBreaker(
                name=f"mcp:{server}",
                failure_threshold=self._failure_threshold,
                recovery_timeout=self._recovery_timeout,
            )
        return self._breakers[server]

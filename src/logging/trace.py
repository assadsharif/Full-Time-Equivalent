"""
Trace ID generation and context management for logging infrastructure (P2).

Uses ULID for sortable, timestamp-embedded trace IDs.
Constitutional compliance: Section 8 (trace correlation for auditability).
"""

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Optional

from ulid import ULID


# Context variable for storing current trace ID
_trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


def new_trace_id() -> str:
    """
    Generate a new ULID-based trace ID.

    ULIDs are:
    - Sortable (timestamp prefix)
    - Unique (128-bit randomness)
    - URL-safe (Base32 encoded)
    - 26 characters long

    Returns:
        New trace ID as string

    Example:
        >>> trace_id = new_trace_id()
        >>> len(trace_id)
        26
        >>> trace_id  # doctest: +SKIP
        '01HQ8Z9X0ABCDEFGHIJKLMNOPQ'
    """
    return str(ULID())


def get_trace_id() -> Optional[str]:
    """
    Get the current trace ID from context.

    Returns:
        Current trace ID if set, None otherwise

    Example:
        >>> get_trace_id()  # No trace ID set
        None
        >>> with bind_trace_id("01HQ8Z9X0ABCDEFGHIJKLMNOPQ"):
        ...     get_trace_id()
        '01HQ8Z9X0ABCDEFGHIJKLMNOPQ'
    """
    return _trace_id_var.get()


@contextmanager
def bind_trace_id(trace_id: Optional[str] = None):
    """
    Context manager to bind a trace ID to the current execution context.

    If no trace_id provided, generates a new one automatically.
    Restores previous trace ID when context exits.

    Args:
        trace_id: Trace ID to bind (or None to auto-generate)

    Yields:
        The bound trace ID

    Example:
        >>> with bind_trace_id() as trace_id:
        ...     print(f"Trace ID: {trace_id}")
        ...     assert get_trace_id() == trace_id
        Trace ID: 01HQ8Z9X0ABCDEFGHIJKLMNOPQ

        >>> # Explicit trace ID
        >>> with bind_trace_id("custom-trace-123") as trace_id:
        ...     assert trace_id == "custom-trace-123"
    """
    if trace_id is None:
        trace_id = new_trace_id()

    # Save previous trace ID
    token = _trace_id_var.set(trace_id)

    try:
        yield trace_id
    finally:
        # Restore previous trace ID
        _trace_id_var.reset(token)

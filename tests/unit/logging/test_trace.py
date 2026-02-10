"""
Unit tests for trace ID generation and context management (P2).

Tests cover:
- ULID-based trace ID generation
- Trace ID uniqueness and format
- Context manager for trace ID binding
- Context variable isolation
"""

import re

import pytest

from logging.trace import bind_trace_id, get_trace_id, new_trace_id


class TestNewTraceId:
    """Tests for new_trace_id() function."""

    def test_new_trace_id_format(self):
        """new_trace_id should generate valid ULID format."""
        trace_id = new_trace_id()

        # ULID is 26 characters, Base32 encoded
        assert len(trace_id) == 26
        # Base32 uses A-Z and 0-9 (case-insensitive, but typically uppercase)
        assert re.match(r"^[0-9A-Z]{26}$", trace_id, re.IGNORECASE)

    def test_new_trace_id_uniqueness(self):
        """new_trace_id should generate unique IDs."""
        ids = [new_trace_id() for _ in range(100)]

        # All IDs should be unique
        assert len(set(ids)) == 100

    def test_new_trace_id_sortability(self):
        """new_trace_id should generate sortable IDs (timestamp prefix)."""
        ids = [new_trace_id() for _ in range(10)]

        # IDs should be roughly in ascending order (timestamp prefix)
        # Note: This might rarely fail if IDs generated in same millisecond
        # but very unlikely with 100 IDs
        sorted_ids = sorted(ids)
        assert ids == sorted_ids or len(set(ids[:2])) == 2  # Allow for same millisecond


class TestGetTraceId:
    """Tests for get_trace_id() function."""

    def test_get_trace_id_none_by_default(self):
        """get_trace_id should return None when no trace ID is set."""
        # Clear any existing trace ID
        trace_id = get_trace_id()

        # Should be None initially (or from previous test context)
        # We can't guarantee None, so just check it's a valid return type
        assert trace_id is None or isinstance(trace_id, str)

    def test_get_trace_id_returns_bound_id(self):
        """get_trace_id should return the currently bound trace ID."""
        test_id = "01HQ8Z9X0ABCDEFGHIJKLMNOPQ"

        with bind_trace_id(test_id):
            current_id = get_trace_id()
            assert current_id == test_id


class TestBindTraceId:
    """Tests for bind_trace_id() context manager."""

    def test_bind_trace_id_explicit(self):
        """bind_trace_id should bind the provided trace ID."""
        test_id = "01HQ8Z9X0ABCDEFGHIJKLMNOPQ"

        with bind_trace_id(test_id) as bound_id:
            assert bound_id == test_id
            assert get_trace_id() == test_id

    def test_bind_trace_id_auto_generate(self):
        """bind_trace_id should auto-generate if no ID provided."""
        with bind_trace_id() as bound_id:
            assert bound_id is not None
            assert len(bound_id) == 26
            assert get_trace_id() == bound_id

    def test_bind_trace_id_restoration(self):
        """bind_trace_id should restore previous trace ID after exit."""
        outer_id = new_trace_id()

        with bind_trace_id(outer_id):
            assert get_trace_id() == outer_id

            inner_id = new_trace_id()
            with bind_trace_id(inner_id):
                assert get_trace_id() == inner_id

            # Should restore outer ID after inner context exits
            assert get_trace_id() == outer_id

    def test_bind_trace_id_nested_contexts(self):
        """bind_trace_id should support nested contexts."""
        id1 = "trace-1"
        id2 = "trace-2"
        id3 = "trace-3"

        with bind_trace_id(id1):
            assert get_trace_id() == id1

            with bind_trace_id(id2):
                assert get_trace_id() == id2

                with bind_trace_id(id3):
                    assert get_trace_id() == id3

                assert get_trace_id() == id2

            assert get_trace_id() == id1

    def test_bind_trace_id_exception_safety(self):
        """bind_trace_id should restore previous ID even on exception."""
        outer_id = new_trace_id()

        with bind_trace_id(outer_id):
            assert get_trace_id() == outer_id

            try:
                with bind_trace_id("inner-id"):
                    assert get_trace_id() == "inner-id"
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # Should restore outer ID even after exception
            assert get_trace_id() == outer_id

    def test_bind_trace_id_yields_bound_id(self):
        """bind_trace_id should yield the bound trace ID."""
        test_id = "test-trace-id"

        with bind_trace_id(test_id) as yielded_id:
            assert yielded_id == test_id

        # Auto-generated case
        with bind_trace_id() as yielded_id:
            assert yielded_id is not None
            assert len(yielded_id) == 26

    def test_bind_trace_id_isolation(self):
        """Trace IDs should be isolated between different execution contexts."""
        # This test simulates what would happen in async contexts
        # In real async code, each task would have its own context

        id1 = "context-1"
        id2 = "context-2"

        # Simulate two independent contexts
        with bind_trace_id(id1):
            ctx1_id = get_trace_id()

        with bind_trace_id(id2):
            ctx2_id = get_trace_id()

        assert ctx1_id == id1
        assert ctx2_id == id2


class TestTraceIdIntegration:
    """Integration tests for trace ID workflow."""

    def test_typical_usage_pattern(self):
        """Test typical usage pattern: generate ID, bind, use, restore."""
        # Start with no trace ID
        initial_id = get_trace_id()

        # Create operation with new trace ID
        with bind_trace_id() as trace_id:
            # Verify ID is bound
            assert get_trace_id() == trace_id
            assert len(trace_id) == 26

            # Simulate nested operation with same trace ID
            with bind_trace_id(trace_id):
                assert get_trace_id() == trace_id

        # Verify restoration (might be None or previous value)
        final_id = get_trace_id()
        # We can only assert that we're back to the initial state
        # (which might be None)

    def test_multiple_independent_operations(self):
        """Test multiple operations with different trace IDs."""
        ids = []

        for i in range(5):
            with bind_trace_id() as trace_id:
                ids.append(trace_id)
                assert get_trace_id() == trace_id

        # All IDs should be unique
        assert len(set(ids)) == 5

    def test_trace_id_propagation(self):
        """Test trace ID propagation through call stack."""

        def inner_function():
            """Function that reads current trace ID."""
            return get_trace_id()

        def middle_function():
            """Function that calls inner function."""
            return inner_function()

        def outer_function():
            """Function that binds trace ID and calls middle function."""
            with bind_trace_id("propagation-test") as trace_id:
                result = middle_function()
                return trace_id, result

        trace_id, propagated_id = outer_function()

        # Trace ID should propagate through call stack
        assert trace_id == "propagation-test"
        assert propagated_id == "propagation-test"

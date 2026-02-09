"""
Token-Bucket Rate Limiter — per-server, per-action-type throttling (spec 004 Silver).

Each (server, action_type) pair has its own bucket.  Bucket state is
persisted to a JSON file so that limits survive process restarts.

Algorithm:
    tokens += elapsed_seconds * refill_rate        (capped at max_tokens)
    consume(n) succeeds when tokens >= n

The default limits are loaded from ``config/security.yaml`` but can be
overridden programmatically via ``add_limit()``.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class BucketState:
    """Mutable state for one token bucket."""

    max_tokens: int
    refill_per_minute: int  # tokens added per 60 s
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self):
        self.tokens = float(self.max_tokens)  # start full
        self.last_refill = time.monotonic()

    @classmethod
    def from_dict(cls, data: dict) -> "BucketState":
        obj = cls(
            max_tokens=data["max_tokens"], refill_per_minute=data["refill_per_minute"]
        )
        obj.tokens = data["tokens"]
        obj.last_refill = data["last_refill"]
        return obj

    def to_dict(self) -> dict:
        return {
            "max_tokens": self.max_tokens,
            "refill_per_minute": self.refill_per_minute,
            "tokens": self.tokens,
            "last_refill": self.last_refill,
        }


class RateLimitExceededError(Exception):
    """Raised when a consume() call would exceed the rate limit."""


class RateLimiter:
    """
    Token-bucket rate limiter with per-(server, action) buckets.

    Args:
        state_path: JSON file for persisting bucket state across restarts.
        default_limits: mapping of action_type → {"per_minute": N, "per_hour": M}.
                        ``per_minute`` is used as ``refill_per_minute``; ``per_hour``
                        is used as ``max_tokens``.
    """

    def __init__(
        self,
        state_path: Path,
        default_limits: Optional[dict[str, dict[str, int]]] = None,
    ):
        self._state_path = state_path
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._default_limits = default_limits or {
            "email": {"per_minute": 10, "per_hour": 100},
            "payment": {"per_minute": 1, "per_hour": 10},
            "deploy": {"per_minute": 2, "per_hour": 20},
        }
        self._buckets: dict[str, BucketState] = {}
        self._load_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def consume(self, server: str, action_type: str, tokens: int = 1) -> bool:
        """
        Attempt to consume *tokens* from the bucket.

        Returns True on success.  Raises RateLimitExceededError if the
        bucket does not have enough tokens after refilling.
        """
        key = f"{server}:{action_type}"
        bucket = self._get_or_create(key, action_type)
        self._refill(bucket)

        if bucket.tokens < tokens:
            raise RateLimitExceededError(
                f"Rate limit exceeded for {key}: "
                f"{bucket.tokens:.1f}/{bucket.max_tokens} tokens available"
            )
        bucket.tokens -= tokens
        self._save_state()
        return True

    def remaining(self, server: str, action_type: str) -> float:
        """Return current token count after refill (non-destructive)."""
        key = f"{server}:{action_type}"
        bucket = self._get_or_create(key, action_type)
        self._refill(bucket)
        return bucket.tokens

    def add_limit(self, action_type: str, per_minute: int, per_hour: int) -> None:
        """Register or update a limit for an action type."""
        self._default_limits[action_type] = {
            "per_minute": per_minute,
            "per_hour": per_hour,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_or_create(self, key: str, action_type: str) -> BucketState:
        if key not in self._buckets:
            limits = self._default_limits.get(
                action_type, {"per_minute": 60, "per_hour": 3600}
            )
            self._buckets[key] = BucketState(
                max_tokens=limits["per_hour"],
                refill_per_minute=limits["per_minute"],
            )
        return self._buckets[key]

    @staticmethod
    def _refill(bucket: BucketState) -> None:
        now = time.monotonic()
        elapsed = now - bucket.last_refill
        if elapsed > 0:
            refill_rate = bucket.refill_per_minute / 60.0  # tokens per second
            bucket.tokens = min(
                bucket.max_tokens,
                bucket.tokens + elapsed * refill_rate,
            )
            bucket.last_refill = now

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_state(self) -> None:
        if not self._state_path.exists():
            return
        raw = json.loads(self._state_path.read_text())
        for key, data in raw.items():
            self._buckets[key] = BucketState.from_dict(data)

    def _save_state(self) -> None:
        raw = {key: b.to_dict() for key, b in self._buckets.items()}
        self._state_path.write_text(json.dumps(raw, indent=2))

"""Security data models — enums, events, and config (spec 004)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import total_ordering
from typing import Optional


@total_ordering
class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __lt__(self, other):
        if not isinstance(other, RiskLevel):
            return NotImplemented
        order = {
            RiskLevel.LOW: 0,
            RiskLevel.MEDIUM: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }
        return order[self] < order[other]


@dataclass
class SecurityEvent:
    """A single auditable security event."""

    event_type: str  # mcp_action | credential_access | scan_result | rate_limit
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    mcp_server: Optional[str] = None
    action: Optional[str] = None
    approved: Optional[bool] = None
    approval_id: Optional[str] = None
    nonce: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.LOW
    result: Optional[str] = None
    duration_ms: Optional[int] = None
    details: Optional[dict] = None

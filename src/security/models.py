"""Security data models — enums, events, and config (spec 004)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


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

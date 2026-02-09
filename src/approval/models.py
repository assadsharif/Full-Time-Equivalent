"""Approval data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class ApprovalRequest:
    """Single approval lifecycle record."""

    task_id: str
    approval_id: str
    nonce: str
    action_type: str
    risk_level: str  # low | medium | high | critical
    status: ApprovalStatus
    created_at: datetime
    expires_at: datetime
    action: dict = field(default_factory=dict)
    integrity_hash: Optional[str] = None

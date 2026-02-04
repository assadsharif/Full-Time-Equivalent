"""Security module — credential vault, audit logging, secrets scanning,
MCP verification, and rate limiting."""

from src.security.credential_vault import CredentialVault, CredentialNotFoundError
from src.security.audit_logger import SecurityAuditLogger
from src.security.secrets_scanner import SecretsScanner, ScanFinding
from src.security.mcp_verifier import MCPVerifier, VerificationError
from src.security.rate_limiter import RateLimiter, RateLimitExceededError
from src.security.mcp_guard import MCPGuard
from src.security.models import RiskLevel, SecurityEvent

__all__ = [
    "CredentialVault",
    "CredentialNotFoundError",
    "SecurityAuditLogger",
    "SecretsScanner",
    "ScanFinding",
    "MCPVerifier",
    "VerificationError",
    "RateLimiter",
    "RateLimitExceededError",
    "MCPGuard",
    "RiskLevel",
    "SecurityEvent",
]

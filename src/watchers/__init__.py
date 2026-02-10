"""
Watcher Scripts - Perception Layer for Digital FTE.

This module provides daemon-based watchers that monitor external data sources
(Gmail, WhatsApp, file system) and convert incoming data into structured
Markdown files in the Obsidian vault.

Constitutional Compliance:
- Section 2: Watchers write to vault (source of truth)
- Section 3: PII redaction before logging
- Section 4: Additive only (no control plane modifications)
- Section 8: All events logged via P2 infrastructure
- Section 9: Graceful error recovery with retries
"""

from .base_watcher import BaseWatcher, PermanentError, TransientError
from .pii_redactor import PIIRedactor
from .markdown_formatter import MarkdownFormatter
from .checkpoint import CheckpointManager
from .models import WatcherEvent, EmailMessage, FileEvent, WhatsAppMessage
from .filesystem_watcher import FileSystemWatcher
from .gmail_watcher import GmailWatcher, GmailAuthenticationError
from .whatsapp_watcher import WhatsAppWatcher, WhatsAppAuthenticationError
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerRegistry,
    CircuitState,
    get_circuit_breaker,
)

__all__ = [
    # Base classes
    "BaseWatcher",
    "PermanentError",
    "TransientError",
    # Utilities
    "PIIRedactor",
    "MarkdownFormatter",
    "CheckpointManager",
    # Models
    "WatcherEvent",
    "EmailMessage",
    "FileEvent",
    "WhatsAppMessage",
    # Watchers
    "FileSystemWatcher",
    "GmailWatcher",
    "GmailAuthenticationError",
    "WhatsAppWatcher",
    "WhatsAppAuthenticationError",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerError",
    "CircuitBreakerRegistry",
    "CircuitState",
    "get_circuit_breaker",
]

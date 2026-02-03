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

from src.watchers.base_watcher import BaseWatcher, PermanentError, TransientError
from src.watchers.pii_redactor import PIIRedactor
from src.watchers.markdown_formatter import MarkdownFormatter
from src.watchers.checkpoint import CheckpointManager
from src.watchers.models import WatcherEvent, EmailMessage, FileEvent, WhatsAppMessage
from src.watchers.filesystem_watcher import FileSystemWatcher
from src.watchers.gmail_watcher import GmailWatcher, GmailAuthenticationError

__all__ = [
    "BaseWatcher",
    "PermanentError",
    "TransientError",
    "PIIRedactor",
    "MarkdownFormatter",
    "CheckpointManager",
    "WatcherEvent",
    "EmailMessage",
    "FileEvent",
    "WhatsAppMessage",
    "FileSystemWatcher",
    "GmailWatcher",
    "GmailAuthenticationError",
]

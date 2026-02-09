"""
Watcher data models.

Pydantic models for watcher events, emails, and file system events.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class WatcherEvent(BaseModel):
    """Base model for all watcher events."""

    id: str = Field(..., description="Unique event identifier")
    source: str = Field(..., description="Event source: gmail, whatsapp, filesystem")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp in UTC",
    )
    priority: str = Field(
        default="medium", description="Priority: low, medium, high, urgent"
    )
    pii_redacted: bool = Field(default=False, description="Whether PII was redacted")


class EmailMessage(WatcherEvent):
    """Model for email messages from Gmail watcher."""

    source: str = "gmail"
    message_id: str = Field(..., description="Gmail message ID")
    sender: str = Field(..., description="Sender email address")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(default="", description="Email body in Markdown format")
    labels: list[str] = Field(default_factory=list, description="Gmail labels")
    has_attachments: bool = Field(
        default=False, description="Whether email has attachments"
    )
    attachments: list[str] = Field(
        default_factory=list, description="List of attachment filenames"
    )
    attachment_paths: list[Path] = Field(
        default_factory=list, description="Paths to downloaded attachments"
    )

    def generate_id(self) -> str:
        """Generate unique ID from message details."""
        safe_sender = self.sender.replace("@", "_at_").replace(".", "_")
        timestamp_str = self.timestamp.strftime("%Y-%m-%dT%H-%M-%S")
        return f"gmail_{safe_sender}_{timestamp_str}"


class FileEvent(WatcherEvent):
    """Model for file system events from filesystem watcher."""

    source: str = "filesystem"
    file_path: Path = Field(..., description="Full path to the file")
    file_name: str = Field(..., description="File name")
    file_size: int = Field(..., description="File size in bytes")
    file_type: str = Field(default="application/octet-stream", description="MIME type")
    file_hash: str = Field(default="", description="SHA256 hash of file content")
    event_type: str = Field(
        default="created", description="Event type: created, modified, deleted"
    )

    def generate_id(self) -> str:
        """Generate unique ID from file details."""
        safe_name = self.file_name.replace(" ", "_").replace(".", "_")
        timestamp_str = self.timestamp.strftime("%Y-%m-%dT%H-%M-%S")
        return f"file_{safe_name}_{timestamp_str}"


class WhatsAppMessage(WatcherEvent):
    """Model for WhatsApp messages from WhatsApp watcher."""

    source: str = "whatsapp"
    message_id: str = Field(..., description="WhatsApp message ID")
    sender_phone: str = Field(..., description="Sender phone number")
    message_type: str = Field(
        default="text", description="Message type: text, image, document"
    )
    body: str = Field(default="", description="Message body")
    has_media: bool = Field(default=False, description="Whether message has media")
    media_path: Optional[Path] = Field(
        default=None, description="Path to downloaded media"
    )

    def generate_id(self) -> str:
        """Generate unique ID from message details."""
        safe_phone = self.sender_phone.replace("+", "").replace("-", "")
        timestamp_str = self.timestamp.strftime("%Y-%m-%dT%H-%M-%S")
        return f"whatsapp_{safe_phone}_{timestamp_str}"


class CheckpointData(BaseModel):
    """Model for watcher checkpoint state."""

    watcher_name: str = Field(..., description="Name of the watcher")
    last_processed_id: Optional[str] = Field(
        default=None, description="ID of last processed item"
    )
    last_poll_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of last poll",
    )
    events_processed: int = Field(default=0, description="Total events processed")
    errors_count: int = Field(default=0, description="Total errors encountered")

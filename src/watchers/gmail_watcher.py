"""
Gmail Watcher.

Monitors Gmail inbox for new emails and creates Markdown tasks in the vault.
Uses OAuth2 for authentication with Gmail API.

Constitutional Compliance:
- Section 2: Writes to vault (source of truth)
- Section 3: PII redaction before logging
- Section 4: Additive only (no control plane modifications)
- Section 8: All events logged
"""

import base64
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Optional

# Try to import Google API libraries
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None
    HttpError = Exception

# Try HTML to Markdown conversion
try:
    from markdownify import markdownify as html_to_md
except ImportError:
    html_to_md = None

# Try to import the logging module, fall back to standard logging
try:
    from src.fte_logging import get_logger
except ImportError:
    import logging

    def get_logger(name: str):
        return logging.getLogger(name)


from .base_watcher import BaseWatcher, PermanentError
from .markdown_formatter import MarkdownFormatter
from .models import EmailMessage
from .pii_redactor import PIIRedactor

logger = get_logger(__name__)

# Gmail API scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",  # For marking as read
]


class GmailAuthenticationError(PermanentError):
    """Gmail OAuth2 authentication failed."""

    pass


class GmailWatcher(BaseWatcher):
    """
    Gmail Watcher that polls for new emails and creates Markdown tasks.

    Uses OAuth2 for authentication. Requires:
    1. Google Cloud project with Gmail API enabled
    2. OAuth2 credentials (credentials.json)
    3. User authorization (generates token.json)

    Example:
        watcher = GmailWatcher(
            vault_path=Path("./vault"),
            credentials_file=Path("~/.credentials/gmail_credentials.json"),
        )
        watcher.run()
    """

    def __init__(
        self,
        vault_path: Path,
        credentials_file: Path,
        token_file: Path | None = None,
        poll_interval: int = 30,
        max_results: int = 10,
        mark_as_read: bool = True,
        download_attachments: bool = True,
        max_attachment_size: int = 10 * 1024 * 1024,  # 10MB
        labels_include: list[str] | None = None,
        labels_exclude: list[str] | None = None,
        priority_keywords: dict[str, list[str]] | None = None,
        **kwargs,
    ):
        """
        Initialize GmailWatcher.

        Args:
            vault_path: Path to Obsidian vault root
            credentials_file: Path to OAuth2 credentials JSON
            token_file: Path to store OAuth2 token (default: next to credentials)
            poll_interval: Seconds between polls (default: 30)
            max_results: Maximum emails to fetch per poll (default: 10)
            mark_as_read: Mark emails as read after processing (default: True)
            download_attachments: Download email attachments (default: True)
            max_attachment_size: Skip attachments larger than this (default: 10MB)
            labels_include: Gmail labels to include (default: ["INBOX", "UNREAD"])
            labels_exclude: Gmail labels to exclude (default: ["SPAM", "TRASH"])
            priority_keywords: Keywords for priority detection
            **kwargs: Additional arguments for BaseWatcher
        """
        super().__init__(
            vault_path,
            watcher_name="gmail",
            poll_interval=poll_interval,
            **kwargs,
        )

        self.credentials_file = Path(credentials_file).expanduser()
        self.token_file = (
            Path(token_file).expanduser()
            if token_file
            else self.credentials_file.parent / "gmail_token.json"
        )
        self.max_results = max_results
        self.mark_as_read = mark_as_read
        self.download_attachments = download_attachments
        self.max_attachment_size = max_attachment_size
        self.labels_include = labels_include or ["INBOX", "UNREAD"]
        self.labels_exclude = labels_exclude or ["SPAM", "TRASH"]
        self.priority_keywords = priority_keywords or {
            "urgent": ["urgent", "asap", "critical", "emergency"],
            "high": ["important", "priority", "deadline"],
        }

        # Initialize helpers
        self.formatter = MarkdownFormatter()
        self.pii_redactor = PIIRedactor()

        # Gmail service (initialized on authenticate)
        self._service = None

        # Track processed message IDs
        self._processed_ids: set[str] = set()

    def authenticate(self) -> None:
        """
        Authenticate with Gmail API using OAuth2.

        Raises:
            GmailAuthenticationError: If authentication fails
            ImportError: If Google API libraries not installed
        """
        if not GOOGLE_API_AVAILABLE:
            raise ImportError(
                "Google API libraries required for Gmail watcher. "
                "Install with: pip install google-auth-oauthlib google-api-python-client"
            )

        creds = None

        # Load existing token
        if self.token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self.token_file), SCOPES
                )
                logger.debug("Loaded existing OAuth2 token")
            except Exception as e:
                logger.warning(f"Failed to load token: {e}")

        # Refresh or get new token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed OAuth2 token")
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}")
                    creds = None

            if not creds:
                if not self.credentials_file.exists():
                    raise GmailAuthenticationError(
                        f"Credentials file not found: {self.credentials_file}\n"
                        "Download OAuth2 credentials from Google Cloud Console."
                    )

                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("OAuth2 authorization completed")
                except Exception as e:
                    raise GmailAuthenticationError(f"OAuth2 flow failed: {e}")

            # Save token for future use
            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            self.token_file.write_text(creds.to_json())
            logger.info(f"Saved OAuth2 token to {self.token_file}")

        # Build Gmail service
        try:
            self._service = build("gmail", "v1", credentials=creds)
            logger.info("Gmail API authentication successful")
        except Exception as e:
            raise GmailAuthenticationError(f"Failed to build Gmail service: {e}")

    def poll(self) -> list[dict]:
        """
        Poll Gmail API for new unread emails.

        Returns:
            List of message metadata dictionaries
        """
        if not self._service:
            raise GmailAuthenticationError(
                "Not authenticated. Call authenticate() first."
            )

        try:
            # Build query for unread emails in inbox
            query_parts = []
            for label in self.labels_include:
                if label == "UNREAD":
                    query_parts.append("is:unread")
                elif label == "INBOX":
                    query_parts.append("in:inbox")
                else:
                    query_parts.append(f"label:{label}")

            query = " ".join(query_parts)

            # Fetch message list
            results = (
                self._service.users()
                .messages()
                .list(userId="me", q=query, maxResults=self.max_results)
                .execute()
            )

            messages = results.get("messages", [])

            # Filter out already processed messages
            new_messages = [
                msg for msg in messages if msg["id"] not in self._processed_ids
            ]

            logger.info(
                f"Polled Gmail: {len(new_messages)} new emails",
                context={"total_found": len(messages), "new": len(new_messages)},
            )

            return new_messages

        except HttpError as e:
            if e.resp.status == 401:
                raise GmailAuthenticationError("OAuth2 token expired or invalid")
            elif e.resp.status == 429:
                # Rate limited - let retry_with_backoff handle it
                retry_after = e.resp.headers.get("Retry-After", 60)
                logger.warning(f"Gmail API rate limited, retry after {retry_after}s")
                raise
            else:
                logger.error(f"Gmail API error: {e}")
                raise

    def parse_message(self, message_id: str) -> EmailMessage:
        """
        Fetch and parse a Gmail message.

        Args:
            message_id: Gmail message ID

        Returns:
            EmailMessage model with parsed data
        """
        if not self._service:
            raise GmailAuthenticationError("Not authenticated")

        # Fetch full message
        msg = (
            self._service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        # Extract headers
        headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}

        sender = headers.get("from", "unknown@unknown.com")
        subject = headers.get("subject", "(No Subject)")
        date_str = headers.get("date", "")

        # Parse date
        try:
            if date_str:
                received_at = parsedate_to_datetime(date_str)
                if received_at.tzinfo is None:
                    received_at = received_at.replace(tzinfo=timezone.utc)
            else:
                received_at = datetime.now(timezone.utc)
        except Exception:
            received_at = datetime.now(timezone.utc)

        # Extract body
        body = self._extract_body(msg["payload"])

        # Get labels
        labels = msg.get("labelIds", [])

        # Check for attachments
        attachments = self._get_attachment_list(msg["payload"])
        has_attachments = len(attachments) > 0

        # Detect priority
        priority = self._detect_priority(subject, body)

        # Create EmailMessage model
        email = EmailMessage(
            id="",  # Will be generated
            message_id=message_id,
            sender=sender,
            subject=subject,
            body=body,
            timestamp=received_at,
            labels=labels,
            has_attachments=has_attachments,
            attachments=[a["filename"] for a in attachments],
            priority=priority,
        )
        email.id = email.generate_id()

        logger.debug(
            f"Parsed email: {subject[:50]}...",
            context={
                "message_id": message_id,
                "sender": self.pii_redactor.redact(sender).text,
                "has_attachments": has_attachments,
            },
        )

        return email, attachments

    def _extract_body(self, payload: dict) -> str:
        """Extract email body from payload, preferring plain text."""
        body = ""

        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        elif "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")

                if mime_type == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )
                    break
                elif mime_type == "text/html" and part.get("body", {}).get("data"):
                    html_body = base64.urlsafe_b64decode(part["body"]["data"]).decode(
                        "utf-8"
                    )
                    if html_to_md:
                        body = html_to_md(html_body, strip=["script", "style"])
                    else:
                        # Basic HTML stripping fallback
                        import re

                        body = re.sub(r"<[^>]+>", "", html_body)
                elif mime_type.startswith("multipart/"):
                    # Recursively extract from nested parts
                    body = self._extract_body(part)
                    if body:
                        break

        return body.strip()

    def _get_attachment_list(self, payload: dict) -> list[dict]:
        """Get list of attachments from payload."""
        attachments = []

        def process_parts(parts):
            for part in parts:
                filename = part.get("filename", "")
                if filename and part.get("body", {}).get("attachmentId"):
                    attachments.append(
                        {
                            "filename": filename,
                            "attachment_id": part["body"]["attachmentId"],
                            "mime_type": part.get(
                                "mimeType", "application/octet-stream"
                            ),
                            "size": part.get("body", {}).get("size", 0),
                        }
                    )
                if "parts" in part:
                    process_parts(part["parts"])

        if "parts" in payload:
            process_parts(payload["parts"])

        return attachments

    def _detect_priority(self, subject: str, body: str) -> str:
        """Detect email priority based on keywords."""
        text = f"{subject} {body}".lower()

        for priority, keywords in self.priority_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    return priority

        return "medium"

    def download_attachment(
        self, message_id: str, attachment: dict, email_id: str
    ) -> Optional[Path]:
        """
        Download an email attachment.

        Args:
            message_id: Gmail message ID
            attachment: Attachment metadata dict
            email_id: Generated email ID for folder naming

        Returns:
            Path to downloaded file, or None if skipped/failed
        """
        if not self._service:
            raise GmailAuthenticationError("Not authenticated")

        filename = attachment["filename"]
        size = attachment.get("size", 0)

        # Skip large attachments
        if self.max_attachment_size > 0 and size > self.max_attachment_size:
            logger.warning(
                f"Skipping large attachment: {filename} ({size} bytes)",
                context={"message_id": message_id, "size": size},
            )
            return None

        try:
            # Fetch attachment content
            att_data = (
                self._service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment["attachment_id"])
                .execute()
            )

            # Decode content
            content = base64.urlsafe_b64decode(att_data["data"])

            # Create attachment directory
            att_dir = self.attachments_path / email_id
            att_dir.mkdir(parents=True, exist_ok=True)

            # Sanitize filename and save
            safe_filename = self._sanitize_filename(filename)
            file_path = att_dir / safe_filename

            file_path.write_bytes(content)

            logger.info(
                f"Downloaded attachment: {filename}",
                context={"message_id": message_id, "size": len(content)},
            )

            return file_path

        except Exception as e:
            logger.error(f"Failed to download attachment {filename}: {e}")
            return None

    def mark_as_read(self, message_id: str) -> bool:
        """Mark an email as read in Gmail."""
        if not self._service:
            return False

        try:
            self._service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            return True
        except Exception as e:
            logger.warning(f"Failed to mark message as read: {e}")
            return False

    def process_email(self, message_meta: dict) -> bool:
        """
        Process a single email: parse, download attachments, create task.

        Args:
            message_meta: Message metadata from poll()

        Returns:
            True if processed successfully
        """
        message_id = message_meta["id"]

        try:
            # Parse email
            email, attachments = self.parse_message(message_id)

            # Download attachments
            if self.download_attachments and attachments:
                downloaded_paths = []
                for att in attachments:
                    path = self.download_attachment(message_id, att, email.id)
                    if path:
                        downloaded_paths.append(path)
                email.attachment_paths = downloaded_paths

            # Apply PII redaction to body for logging (keep original for task)
            email.pii_redacted = self.pii_redactor.contains_pii(email.body)

            # Format as Markdown
            markdown_content = self.formatter.format_email(email)

            # Write to vault
            output_filename = self._sanitize_filename(f"{email.id}.md")
            output_path = self.inbox_path / output_filename
            self.formatter.write_to_file(markdown_content, output_path)

            # Mark as read in Gmail
            if self.mark_as_read:
                self.mark_as_read(message_id)

            # Track as processed
            self._processed_ids.add(message_id)

            # Update checkpoint
            checkpoint = self.load_checkpoint()
            checkpoint.last_processed_id = message_id
            self.increment_events_processed(checkpoint)

            logger.info(
                f"Processed email: {email.subject[:50]}...",
                context={
                    "email_id": email.id,
                    "priority": email.priority,
                    "attachments": len(email.attachments),
                },
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to process email {message_id}: {e}",
                context={"message_id": message_id},
            )
            checkpoint = self.load_checkpoint()
            self.increment_errors(checkpoint)
            return False

    def run(self) -> None:
        """
        Main polling loop.

        Authenticates, then polls for new emails at poll_interval.
        """
        if not GOOGLE_API_AVAILABLE:
            raise ImportError(
                "Google API libraries required. Install with:\n"
                "pip install google-auth-oauthlib google-api-python-client"
            )

        logger.info(f"Starting Gmail watcher (poll interval: {self.poll_interval}s)")

        # Authenticate
        self.authenticate()

        self._running = True

        while self._running:
            try:
                # Poll for new emails
                messages = self.retry_with_backoff(self.poll)

                if messages is None:
                    logger.error("Polling failed after retries, waiting before retry")
                    time.sleep(self.poll_interval * 2)
                    continue

                # Process each email
                for msg in messages:
                    if not self._running:
                        break
                    self.process_email(msg)

                # Sleep until next poll
                logger.debug(f"Sleeping for {self.poll_interval}s")
                time.sleep(self.poll_interval)

            except GmailAuthenticationError as e:
                logger.error(f"Authentication error: {e}")
                raise
            except KeyboardInterrupt:
                logger.info("Gmail watcher interrupted")
                break
            except Exception as e:
                logger.error(f"Unexpected error in Gmail watcher: {e}")
                time.sleep(self.poll_interval)

        logger.info("Gmail watcher stopped")


def main():
    """Entry point for Gmail watcher."""
    import argparse

    parser = argparse.ArgumentParser(description="Gmail Watcher for Digital FTE")
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=Path("./vault"),
        help="Path to Obsidian vault",
    )
    parser.add_argument(
        "--credentials",
        type=Path,
        default=Path("~/.credentials/gmail_credentials.json"),
        help="OAuth2 credentials file",
    )
    parser.add_argument(
        "--token",
        type=Path,
        default=None,
        help="OAuth2 token file (default: next to credentials)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Poll interval in seconds",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum emails per poll",
    )

    args = parser.parse_args()

    watcher = GmailWatcher(
        vault_path=args.vault_path,
        credentials_file=args.credentials,
        token_file=args.token,
        poll_interval=args.poll_interval,
        max_results=args.max_results,
    )
    watcher.run()


if __name__ == "__main__":
    main()

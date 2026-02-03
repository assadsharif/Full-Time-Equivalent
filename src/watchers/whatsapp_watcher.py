"""
WhatsApp Watcher.

Receives WhatsApp Business API webhooks and creates Markdown tasks in the vault.
Uses Flask for webhook server with HMAC signature verification.

Constitutional Compliance:
- Section 2: Writes to vault (source of truth)
- Section 3: PII redaction (phone numbers) before logging
- Section 4: Additive only (no control plane modifications)
- Section 8: All events logged
"""

import hashlib
import hmac
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread
from typing import Any, Optional

# Try to import Flask
try:
    from flask import Flask, request, jsonify

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Flask = None

# Try requests for media download
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

# Try to import the logging module, fall back to standard logging
try:
    from src.logging import get_logger
except ImportError:
    import logging

    def get_logger(name: str):
        return logging.getLogger(name)


from src.watchers.base_watcher import BaseWatcher, PermanentError
from src.watchers.markdown_formatter import MarkdownFormatter
from src.watchers.models import WhatsAppMessage
from src.watchers.pii_redactor import PIIRedactor

logger = get_logger(__name__)


class WhatsAppAuthenticationError(PermanentError):
    """WhatsApp webhook authentication failed."""

    pass


class WhatsAppWatcher(BaseWatcher):
    """
    WhatsApp Watcher that receives webhook messages and creates Markdown tasks.

    Uses WhatsApp Business API webhooks. Requires:
    1. Meta Business account with WhatsApp Business API access
    2. Webhook URL configured in Meta dashboard
    3. Verify token and app secret for signature verification

    Example:
        watcher = WhatsAppWatcher(
            vault_path=Path("./vault"),
            verify_token="your-verify-token",
            app_secret="your-app-secret",
            port=5000,
        )
        watcher.run()
    """

    def __init__(
        self,
        vault_path: Path,
        verify_token: str | None = None,
        app_secret: str | None = None,
        access_token: str | None = None,
        port: int = 5000,
        host: str = "0.0.0.0",
        download_media: bool = True,
        max_media_size: int = 10 * 1024 * 1024,  # 10MB
        sender_whitelist: list[str] | None = None,
        sender_blacklist: list[str] | None = None,
        **kwargs,
    ):
        """
        Initialize WhatsAppWatcher.

        Args:
            vault_path: Path to Obsidian vault root
            verify_token: Webhook verification token (from env if not provided)
            app_secret: App secret for HMAC verification (from env if not provided)
            access_token: Access token for media download (from env if not provided)
            port: Webhook server port (default: 5000)
            host: Webhook server host (default: 0.0.0.0)
            download_media: Download media messages (default: True)
            max_media_size: Skip media larger than this (default: 10MB)
            sender_whitelist: Only process messages from these numbers
            sender_blacklist: Ignore messages from these numbers
            **kwargs: Additional arguments for BaseWatcher
        """
        super().__init__(
            vault_path,
            watcher_name="whatsapp",
            **kwargs,
        )

        # Get credentials from environment if not provided
        self.verify_token = verify_token or os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
        self.app_secret = app_secret or os.environ.get("WHATSAPP_APP_SECRET", "")
        self.access_token = access_token or os.environ.get("WHATSAPP_ACCESS_TOKEN", "")

        self.port = port
        self.host = host
        self.download_media = download_media
        self.max_media_size = max_media_size
        # Normalize phone numbers on storage so comparison with normalized input works
        def _normalize(number: str) -> str:
            return number.lstrip("+").replace("-", "").replace(" ", "")

        self.sender_whitelist = set(_normalize(n) for n in sender_whitelist) if sender_whitelist else None
        self.sender_blacklist = set(_normalize(n) for n in sender_blacklist) if sender_blacklist else set()

        # Initialize helpers
        self.formatter = MarkdownFormatter()
        self.pii_redactor = PIIRedactor()

        # Flask app (initialized in run())
        self._app: Optional[Flask] = None
        self._server_thread: Optional[Thread] = None

        # Track processed message IDs
        self._processed_ids: set[str] = set()

    def _verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook HMAC signature.

        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value

        Returns:
            True if signature is valid
        """
        if not self.app_secret:
            logger.warning("No app secret configured, skipping signature verification")
            return True

        if not signature:
            return False

        # Extract signature from "sha256=<signature>"
        if signature.startswith("sha256="):
            signature = signature[7:]

        expected = hmac.new(
            self.app_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def _should_process_sender(self, phone_number: str) -> bool:
        """Check if sender should be processed based on whitelist/blacklist."""
        # Normalize phone number
        normalized = phone_number.lstrip("+").replace("-", "").replace(" ", "")

        # Check blacklist
        if normalized in self.sender_blacklist:
            logger.debug(f"Sender {self.pii_redactor.redact(phone_number).text} is blacklisted")
            return False

        # Check whitelist (if configured)
        if self.sender_whitelist:
            if normalized not in self.sender_whitelist:
                logger.debug(f"Sender {self.pii_redactor.redact(phone_number).text} not in whitelist")
                return False

        return True

    def _download_media(self, media_id: str, mime_type: str, message_id: str) -> Optional[Path]:
        """
        Download media from WhatsApp API.

        Args:
            media_id: WhatsApp media ID
            mime_type: MIME type of media
            message_id: Message ID for folder naming

        Returns:
            Path to downloaded file, or None if failed
        """
        if not REQUESTS_AVAILABLE:
            logger.warning("requests library not installed, skipping media download")
            return None

        if not self.access_token:
            logger.warning("No access token configured, skipping media download")
            return None

        try:
            # Get media URL
            url_response = requests.get(
                f"https://graph.facebook.com/v18.0/{media_id}",
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )
            url_response.raise_for_status()
            media_url = url_response.json().get("url")

            if not media_url:
                logger.warning(f"No URL in media response for {media_id}")
                return None

            # Download media
            media_response = requests.get(
                media_url,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=30,
                stream=True,
            )
            media_response.raise_for_status()

            # Check size
            content_length = int(media_response.headers.get("content-length", 0))
            if self.max_media_size > 0 and content_length > self.max_media_size:
                logger.warning(f"Media too large: {content_length} bytes")
                return None

            # Determine extension from mime type
            ext_map = {
                "image/jpeg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "video/mp4": ".mp4",
                "audio/ogg": ".ogg",
                "audio/mpeg": ".mp3",
                "application/pdf": ".pdf",
                "application/vnd.ms-excel": ".xls",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
            }
            ext = ext_map.get(mime_type, ".bin")

            # Save to attachments
            media_dir = self.attachments_path / message_id
            media_dir.mkdir(parents=True, exist_ok=True)

            filename = f"media_{media_id[:8]}{ext}"
            file_path = media_dir / filename

            with file_path.open("wb") as f:
                for chunk in media_response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(
                f"Downloaded media: {filename}",
                context={"media_id": media_id, "size": content_length},
            )

            return file_path

        except Exception as e:
            logger.error(f"Failed to download media {media_id}: {e}")
            return None

    def _process_message(self, message: dict, metadata: dict) -> bool:
        """
        Process a single WhatsApp message.

        Args:
            message: Message object from webhook
            metadata: Metadata from webhook entry

        Returns:
            True if processed successfully
        """
        message_id = message.get("id", "")

        # Skip if already processed
        if message_id in self._processed_ids:
            logger.debug(f"Skipping already processed message: {message_id}")
            return True

        sender_phone = message.get("from", "")
        timestamp = message.get("timestamp", "")
        message_type = message.get("type", "text")

        # Check sender whitelist/blacklist
        if not self._should_process_sender(sender_phone):
            return True

        try:
            # Parse timestamp
            try:
                received_at = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
            except (ValueError, TypeError):
                received_at = datetime.now(timezone.utc)

            # Extract message content
            body = ""
            has_media = False
            media_path = None

            if message_type == "text":
                body = message.get("text", {}).get("body", "")

            elif message_type == "image":
                has_media = True
                image_data = message.get("image", {})
                body = image_data.get("caption", "[Image]")
                if self.download_media:
                    media_path = self._download_media(
                        image_data.get("id", ""),
                        image_data.get("mime_type", "image/jpeg"),
                        message_id,
                    )

            elif message_type == "document":
                has_media = True
                doc_data = message.get("document", {})
                body = doc_data.get("caption", f"[Document: {doc_data.get('filename', 'unknown')}]")
                if self.download_media:
                    media_path = self._download_media(
                        doc_data.get("id", ""),
                        doc_data.get("mime_type", "application/octet-stream"),
                        message_id,
                    )

            elif message_type == "audio":
                has_media = True
                audio_data = message.get("audio", {})
                body = "[Audio Message]"
                if self.download_media:
                    media_path = self._download_media(
                        audio_data.get("id", ""),
                        audio_data.get("mime_type", "audio/ogg"),
                        message_id,
                    )

            elif message_type == "video":
                has_media = True
                video_data = message.get("video", {})
                body = video_data.get("caption", "[Video]")
                if self.download_media:
                    media_path = self._download_media(
                        video_data.get("id", ""),
                        video_data.get("mime_type", "video/mp4"),
                        message_id,
                    )

            elif message_type == "location":
                loc = message.get("location", {})
                body = f"[Location: {loc.get('latitude')}, {loc.get('longitude')}]"

            elif message_type == "contacts":
                contacts = message.get("contacts", [])
                body = f"[Contacts: {len(contacts)} shared]"

            else:
                body = f"[{message_type.title()} Message]"

            # Create WhatsAppMessage model
            wa_message = WhatsAppMessage(
                id="",  # Will be generated
                message_id=message_id,
                sender_phone=sender_phone,
                message_type=message_type,
                body=body,
                timestamp=received_at,
                has_media=has_media,
                media_path=media_path,
            )
            wa_message.id = wa_message.generate_id()

            # Check for PII in body
            wa_message.pii_redacted = self.pii_redactor.contains_pii(body)

            # Format as Markdown
            markdown_content = self.formatter.format_whatsapp(wa_message)

            # Write to vault
            output_filename = self._sanitize_filename(f"{wa_message.id}.md")
            output_path = self.inbox_path / output_filename
            self.formatter.write_to_file(markdown_content, output_path)

            # Mark as processed
            self._processed_ids.add(message_id)

            # Update checkpoint
            checkpoint = self.load_checkpoint()
            checkpoint.last_processed_id = message_id
            self.increment_events_processed(checkpoint)

            logger.info(
                f"Processed WhatsApp message",
                context={
                    "message_id": message_id,
                    "type": message_type,
                    "has_media": has_media,
                    "sender": self.pii_redactor.redact(sender_phone).text,
                },
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to process WhatsApp message {message_id}: {e}",
                context={"message_id": message_id},
            )
            checkpoint = self.load_checkpoint()
            self.increment_errors(checkpoint)
            return False

    def _create_flask_app(self) -> Flask:
        """Create and configure Flask app for webhook."""
        app = Flask(__name__)

        @app.route("/webhook", methods=["GET"])
        def verify_webhook():
            """Webhook verification endpoint (GET)."""
            mode = request.args.get("hub.mode")
            token = request.args.get("hub.verify_token")
            challenge = request.args.get("hub.challenge")

            if mode == "subscribe" and token == self.verify_token:
                logger.info("Webhook verified successfully")
                return challenge, 200
            else:
                logger.warning("Webhook verification failed")
                return "Forbidden", 403

        @app.route("/webhook", methods=["POST"])
        def receive_webhook():
            """Receive incoming WhatsApp messages."""
            # Verify signature
            signature = request.headers.get("X-Hub-Signature-256", "")
            if not self._verify_signature(request.data, signature):
                logger.warning("Invalid webhook signature")
                return jsonify({"error": "Invalid signature"}), 403

            # Parse payload
            try:
                data = request.json
            except Exception as e:
                logger.error(f"Failed to parse webhook payload: {e}")
                return jsonify({"error": "Invalid JSON"}), 400

            # Process entries
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    metadata = value.get("metadata", {})

                    # Process messages
                    for message in value.get("messages", []):
                        self._process_message(message, metadata)

            return jsonify({"status": "ok"}), 200

        @app.route("/health", methods=["GET"])
        def health_check():
            """Health check endpoint."""
            checkpoint = self.load_checkpoint()
            return jsonify({
                "status": "healthy",
                "watcher": "whatsapp",
                "events_processed": checkpoint.events_processed,
                "errors_count": checkpoint.errors_count,
                "last_poll_time": checkpoint.last_poll_time.isoformat()
                if checkpoint.last_poll_time
                else None,
            })

        return app

    def poll(self) -> list:
        """
        Poll is not used for WhatsApp (webhook-based).

        Returns empty list as messages come via webhook.
        """
        return []

    def run(self) -> None:
        """
        Start webhook server.

        Runs Flask server to receive WhatsApp webhooks.
        """
        if not FLASK_AVAILABLE:
            raise ImportError(
                "Flask required for WhatsApp watcher. "
                "Install with: pip install flask"
            )

        if not self.verify_token:
            raise WhatsAppAuthenticationError(
                "No verify token configured. Set WHATSAPP_VERIFY_TOKEN environment variable."
            )

        self._running = True
        self._app = self._create_flask_app()

        logger.info(
            f"Starting WhatsApp webhook server on {self.host}:{self.port}",
            context={
                "host": self.host,
                "port": self.port,
                "vault_path": str(self.vault_path),
            },
        )

        # Run Flask server
        try:
            self._app.run(
                host=self.host,
                port=self.port,
                debug=False,
                use_reloader=False,
            )
        except KeyboardInterrupt:
            logger.info("WhatsApp watcher interrupted")
        finally:
            self._running = False
            logger.info("WhatsApp watcher stopped")

    def stop(self) -> None:
        """Stop the webhook server."""
        super().stop()
        # Flask doesn't have a clean shutdown method
        # In production, use gunicorn or similar with proper signal handling


def main():
    """Entry point for WhatsApp watcher."""
    import argparse

    parser = argparse.ArgumentParser(description="WhatsApp Watcher for Digital FTE")
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=Path("./vault"),
        help="Path to Obsidian vault",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Webhook server port (default: 5000)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Webhook server host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--verify-token",
        default=None,
        help="Webhook verify token (or set WHATSAPP_VERIFY_TOKEN)",
    )

    args = parser.parse_args()

    watcher = WhatsAppWatcher(
        vault_path=args.vault_path,
        verify_token=args.verify_token,
        port=args.port,
        host=args.host,
    )
    watcher.run()


if __name__ == "__main__":
    main()

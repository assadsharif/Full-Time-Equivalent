"""Tests for WhatsAppWatcher."""

import hashlib
import hmac
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

from src.watchers.whatsapp_watcher import WhatsAppWatcher, WhatsAppAuthenticationError
from src.watchers.models import WhatsAppMessage

try:
    from flask import Flask

    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False


class TestWhatsAppWatcher:
    """Test suite for WhatsAppWatcher."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.vault_path = Path(self.temp_dir) / "vault"
        self.vault_path.mkdir()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """Test watcher initialization."""
        watcher = WhatsAppWatcher(
            vault_path=self.vault_path,
            verify_token="test-token",
            app_secret="test-secret",
            port=8080,
        )

        assert watcher.vault_path == self.vault_path
        assert watcher.verify_token == "test-token"
        assert watcher.app_secret == "test-secret"
        assert watcher.port == 8080
        assert watcher.watcher_name == "whatsapp"

    def test_verify_signature_valid(self):
        """Test valid HMAC signature verification."""
        app_secret = "test-secret"
        watcher = WhatsAppWatcher(
            vault_path=self.vault_path,
            verify_token="test-token",
            app_secret=app_secret,
        )

        payload = b'{"test": "data"}'
        expected_sig = hmac.new(
            app_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        assert watcher._verify_signature(payload, f"sha256={expected_sig}") is True

    def test_verify_signature_invalid(self):
        """Test invalid HMAC signature rejection."""
        watcher = WhatsAppWatcher(
            vault_path=self.vault_path,
            verify_token="test-token",
            app_secret="test-secret",
        )

        payload = b'{"test": "data"}'
        assert watcher._verify_signature(payload, "sha256=invalid") is False

    def test_verify_signature_no_secret(self):
        """Test signature verification without secret (skip)."""
        watcher = WhatsAppWatcher(
            vault_path=self.vault_path,
            verify_token="test-token",
            app_secret="",  # No secret
        )

        payload = b'{"test": "data"}'
        # Should return True (skip verification)
        assert watcher._verify_signature(payload, "sha256=anything") is True

    def test_should_process_sender_no_filters(self):
        """Test sender processing without filters."""
        watcher = WhatsAppWatcher(
            vault_path=self.vault_path,
            verify_token="test-token",
        )

        assert watcher._should_process_sender("+1234567890") is True

    def test_should_process_sender_whitelist(self):
        """Test sender whitelist filtering."""
        watcher = WhatsAppWatcher(
            vault_path=self.vault_path,
            verify_token="test-token",
            sender_whitelist=["+1234567890", "+9876543210"],
        )

        assert watcher._should_process_sender("+1234567890") is True
        assert watcher._should_process_sender("+9876543210") is True
        assert watcher._should_process_sender("+1111111111") is False

    def test_should_process_sender_blacklist(self):
        """Test sender blacklist filtering."""
        watcher = WhatsAppWatcher(
            vault_path=self.vault_path,
            verify_token="test-token",
            sender_blacklist=["+1234567890"],
        )

        assert watcher._should_process_sender("+1234567890") is False
        assert watcher._should_process_sender("+9876543210") is True

    def test_should_process_sender_normalized(self):
        """Test phone number normalization in filtering."""
        watcher = WhatsAppWatcher(
            vault_path=self.vault_path,
            verify_token="test-token",
            sender_whitelist=["1234567890"],  # Without +
        )

        # Should match with various formats
        assert watcher._should_process_sender("+1234567890") is True
        assert watcher._should_process_sender("1234567890") is True
        assert watcher._should_process_sender("+1-234-567-890") is True

    def test_process_text_message(self):
        """Test processing a text message."""
        watcher = WhatsAppWatcher(
            vault_path=self.vault_path,
            verify_token="test-token",
        )

        message = {
            "id": "wamid.test123",
            "from": "+1234567890",
            "timestamp": str(int(datetime.now(timezone.utc).timestamp())),
            "type": "text",
            "text": {
                "body": "Hello, this is a test message",
            },
        }

        result = watcher._process_message(message, {})
        assert result is True

        # Check file was created
        inbox_files = list((self.vault_path / "Inbox").glob("*.md"))
        assert len(inbox_files) == 1

        # Check content
        content = inbox_files[0].read_text()
        assert "source: whatsapp" in content
        assert "Hello, this is a test message" in content

    def test_process_image_message(self):
        """Test processing an image message."""
        watcher = WhatsAppWatcher(
            vault_path=self.vault_path,
            verify_token="test-token",
            download_media=False,  # Skip download for test
        )

        message = {
            "id": "wamid.img123",
            "from": "+1234567890",
            "timestamp": str(int(datetime.now(timezone.utc).timestamp())),
            "type": "image",
            "image": {
                "id": "media123",
                "mime_type": "image/jpeg",
                "caption": "Check out this photo",
            },
        }

        result = watcher._process_message(message, {})
        assert result is True

        # Check file was created
        inbox_files = list((self.vault_path / "Inbox").glob("*.md"))
        assert len(inbox_files) == 1

        content = inbox_files[0].read_text()
        assert "has_media: true" in content
        assert "Check out this photo" in content

    def test_process_location_message(self):
        """Test processing a location message."""
        watcher = WhatsAppWatcher(
            vault_path=self.vault_path,
            verify_token="test-token",
        )

        message = {
            "id": "wamid.loc123",
            "from": "+1234567890",
            "timestamp": str(int(datetime.now(timezone.utc).timestamp())),
            "type": "location",
            "location": {
                "latitude": 37.7749,
                "longitude": -122.4194,
            },
        }

        result = watcher._process_message(message, {})
        assert result is True

        inbox_files = list((self.vault_path / "Inbox").glob("*.md"))
        content = inbox_files[0].read_text()
        assert "Location" in content
        assert "37.7749" in content

    def test_duplicate_message_skipped(self):
        """Test duplicate messages are skipped."""
        watcher = WhatsAppWatcher(
            vault_path=self.vault_path,
            verify_token="test-token",
        )

        message = {
            "id": "wamid.dup123",
            "from": "+1234567890",
            "timestamp": str(int(datetime.now(timezone.utc).timestamp())),
            "type": "text",
            "text": {"body": "Duplicate test"},
        }

        # Process twice
        result1 = watcher._process_message(message, {})
        result2 = watcher._process_message(message, {})

        assert result1 is True
        assert result2 is True  # Returns True but skips processing

        # Only one file created
        inbox_files = list((self.vault_path / "Inbox").glob("*.md"))
        assert len(inbox_files) == 1

    @pytest.mark.skipif(not HAS_FLASK, reason="Flask library not installed")
    def test_create_flask_app(self):
        """Test Flask app creation."""
        watcher = WhatsAppWatcher(
            vault_path=self.vault_path,
            verify_token="test-verify-token",
            app_secret="test-secret",
        )

        app = watcher._create_flask_app()
        assert app is not None

        # Test with Flask test client
        client = app.test_client()

        # Test webhook verification
        response = client.get(
            "/webhook?hub.mode=subscribe&hub.verify_token=test-verify-token&hub.challenge=test-challenge"
        )
        assert response.status_code == 200
        assert response.data == b"test-challenge"

        # Test verification failure
        response = client.get(
            "/webhook?hub.mode=subscribe&hub.verify_token=wrong-token&hub.challenge=test"
        )
        assert response.status_code == 403

        # Test health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert data["watcher"] == "whatsapp"


class TestWhatsAppMessage:
    """Test suite for WhatsAppMessage model."""

    def test_generate_id(self):
        """Test ID generation."""
        message = WhatsAppMessage(
            id="",
            message_id="wamid.test123",
            sender_phone="+1234567890",
            body="Test message",
        )

        msg_id = message.generate_id()
        assert msg_id.startswith("whatsapp_1234567890_")
        assert len(msg_id) > 25

    def test_model_fields(self):
        """Test model field defaults."""
        message = WhatsAppMessage(
            id="test-id",
            message_id="wamid.test",
            sender_phone="+1234567890",
            body="Test",
        )

        assert message.source == "whatsapp"
        assert message.message_type == "text"
        assert message.has_media is False
        assert message.media_path is None
        assert message.pii_redacted is False

    def test_model_with_media(self):
        """Test model with media."""
        message = WhatsAppMessage(
            id="test-id",
            message_id="wamid.test",
            sender_phone="+1234567890",
            body="Image caption",
            message_type="image",
            has_media=True,
            media_path=Path("/attachments/image.jpg"),
        )

        assert message.has_media is True
        assert message.media_path == Path("/attachments/image.jpg")
        assert message.message_type == "image"

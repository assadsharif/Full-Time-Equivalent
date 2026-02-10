"""Tests for GmailWatcher."""

import base64
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

from watchers.gmail_watcher import GmailWatcher, GmailAuthenticationError
from watchers.models import EmailMessage


class TestGmailWatcher:
    """Test suite for GmailWatcher."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.vault_path = Path(self.temp_dir) / "vault"
        self.credentials_file = Path(self.temp_dir) / "credentials.json"
        self.vault_path.mkdir()

        # Create dummy credentials file
        self.credentials_file.write_text('{"installed": {"client_id": "test"}}')

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """Test watcher initialization."""
        watcher = GmailWatcher(
            vault_path=self.vault_path,
            credentials_file=self.credentials_file,
            poll_interval=60,
            max_results=5,
        )

        assert watcher.vault_path == self.vault_path
        assert watcher.credentials_file == self.credentials_file
        assert watcher.poll_interval == 60
        assert watcher.max_results == 5
        assert watcher.watcher_name == "gmail"

    def test_init_default_labels(self):
        """Test default label configuration."""
        watcher = GmailWatcher(
            vault_path=self.vault_path,
            credentials_file=self.credentials_file,
        )

        assert "INBOX" in watcher.labels_include
        assert "UNREAD" in watcher.labels_include
        assert "SPAM" in watcher.labels_exclude

    def test_detect_priority_urgent(self):
        """Test urgent priority detection."""
        watcher = GmailWatcher(
            vault_path=self.vault_path,
            credentials_file=self.credentials_file,
        )

        test_cases = [
            ("URGENT: Please review", "", "urgent"),
            ("Meeting request", "This is ASAP needed", "urgent"),
            ("Critical issue found", "", "urgent"),
        ]

        for subject, body, expected in test_cases:
            priority = watcher._detect_priority(subject, body)
            assert priority == expected, f"Failed for subject: {subject}"

    def test_detect_priority_high(self):
        """Test high priority detection."""
        watcher = GmailWatcher(
            vault_path=self.vault_path,
            credentials_file=self.credentials_file,
        )

        test_cases = [
            ("Important announcement", "", "high"),
            ("Meeting", "Priority task list attached", "high"),
            ("Deadline approaching", "", "high"),
        ]

        for subject, body, expected in test_cases:
            priority = watcher._detect_priority(subject, body)
            assert priority == expected, f"Failed for subject: {subject}"

    def test_detect_priority_medium(self):
        """Test default medium priority."""
        watcher = GmailWatcher(
            vault_path=self.vault_path,
            credentials_file=self.credentials_file,
        )

        priority = watcher._detect_priority("Regular update", "Just an FYI")
        assert priority == "medium"

    def test_extract_body_plain_text(self):
        """Test plain text body extraction."""
        watcher = GmailWatcher(
            vault_path=self.vault_path,
            credentials_file=self.credentials_file,
        )

        text_content = "Hello, this is a test email."
        encoded = base64.urlsafe_b64encode(text_content.encode()).decode()

        payload = {
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": encoded},
                }
            ]
        }

        body = watcher._extract_body(payload)
        assert body == text_content

    def test_extract_body_direct(self):
        """Test direct body extraction (no parts)."""
        watcher = GmailWatcher(
            vault_path=self.vault_path,
            credentials_file=self.credentials_file,
        )

        text_content = "Direct body content"
        encoded = base64.urlsafe_b64encode(text_content.encode()).decode()

        payload = {
            "body": {"data": encoded},
        }

        body = watcher._extract_body(payload)
        assert body == text_content

    def test_get_attachment_list(self):
        """Test attachment list extraction."""
        watcher = GmailWatcher(
            vault_path=self.vault_path,
            credentials_file=self.credentials_file,
        )

        payload = {
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": "dGVzdA=="},
                },
                {
                    "filename": "document.pdf",
                    "mimeType": "application/pdf",
                    "body": {
                        "attachmentId": "att-123",
                        "size": 1024,
                    },
                },
                {
                    "filename": "image.png",
                    "mimeType": "image/png",
                    "body": {
                        "attachmentId": "att-456",
                        "size": 2048,
                    },
                },
            ]
        }

        attachments = watcher._get_attachment_list(payload)

        assert len(attachments) == 2
        assert attachments[0]["filename"] == "document.pdf"
        assert attachments[0]["attachment_id"] == "att-123"
        assert attachments[1]["filename"] == "image.png"

    def test_get_attachment_list_nested(self):
        """Test attachment extraction from nested multipart."""
        watcher = GmailWatcher(
            vault_path=self.vault_path,
            credentials_file=self.credentials_file,
        )

        payload = {
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {
                            "filename": "nested.docx",
                            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            "body": {
                                "attachmentId": "att-nested",
                                "size": 512,
                            },
                        }
                    ],
                }
            ]
        }

        attachments = watcher._get_attachment_list(payload)
        assert len(attachments) == 1
        assert attachments[0]["filename"] == "nested.docx"

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        watcher = GmailWatcher(
            vault_path=self.vault_path,
            credentials_file=self.credentials_file,
        )

        test_cases = [
            ("normal.pdf", "normal.pdf"),
            ("file with spaces.pdf", "file_with_spaces.pdf"),
            ("file:with:colons.pdf", "file_with_colons.pdf"),
            ("file<with>brackets.pdf", "file_with_brackets.pdf"),
        ]

        for input_name, expected in test_cases:
            result = watcher._sanitize_filename(input_name)
            assert result == expected, f"Failed for {input_name}"

    @pytest.mark.skipif(True, reason="Requires Google API mocking")
    def test_authenticate_missing_credentials(self):
        """Test authentication with missing credentials file."""
        watcher = GmailWatcher(
            vault_path=self.vault_path,
            credentials_file=Path("/nonexistent/credentials.json"),
        )

        with pytest.raises(GmailAuthenticationError):
            watcher.authenticate()

    def test_process_email_mock(self):
        """Test email processing with mocked service."""
        watcher = GmailWatcher(
            vault_path=self.vault_path,
            credentials_file=self.credentials_file,
            download_attachments=False,
            mark_as_read=False,
        )

        # Mock the service
        mock_service = mock.MagicMock()
        watcher._service = mock_service

        # Create mock message response
        text_content = "Hello, this is the email body."
        encoded_body = base64.urlsafe_b64encode(text_content.encode()).decode()

        mock_message = {
            "id": "msg-123",
            "payload": {
                "headers": [
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "Subject", "value": "Test Subject"},
                    {"name": "Date", "value": "Mon, 28 Jan 2026 10:30:00 +0000"},
                ],
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": encoded_body},
                    }
                ],
            },
            "labelIds": ["INBOX", "UNREAD"],
        }

        mock_service.users().messages().get().execute.return_value = mock_message

        # Process
        result = watcher.process_email({"id": "msg-123"})

        assert result is True

        # Check that file was created
        inbox_files = list((self.vault_path / "Inbox").glob("*.md"))
        assert len(inbox_files) == 1

        # Check content
        content = inbox_files[0].read_text()
        assert "Test Subject" in content
        assert "sender@example.com" in content
        assert "source: gmail" in content


class TestEmailMessage:
    """Test suite for EmailMessage model."""

    def test_generate_id(self):
        """Test ID generation."""
        email = EmailMessage(
            id="",
            message_id="gmail-123",
            sender="user@example.com",
            subject="Test Email",
        )

        email_id = email.generate_id()
        assert email_id.startswith("gmail_user_at_example_com_")
        assert len(email_id) > 30

    def test_model_fields(self):
        """Test model field defaults."""
        email = EmailMessage(
            id="test-id",
            message_id="gmail-123",
            sender="user@example.com",
            subject="Test",
        )

        assert email.source == "gmail"
        assert email.body == ""
        assert email.labels == []
        assert email.has_attachments is False
        assert email.pii_redacted is False

    def test_model_with_attachments(self):
        """Test model with attachments."""
        email = EmailMessage(
            id="test-id",
            message_id="gmail-123",
            sender="user@example.com",
            subject="With Attachments",
            has_attachments=True,
            attachments=["doc.pdf", "image.png"],
        )

        assert email.has_attachments is True
        assert len(email.attachments) == 2
        assert "doc.pdf" in email.attachments

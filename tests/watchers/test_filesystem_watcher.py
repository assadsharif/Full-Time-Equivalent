"""Tests for FileSystemWatcher."""

import tempfile
import time
from pathlib import Path
from unittest import mock

import pytest

from src.watchers.filesystem_watcher import FileSystemWatcher
from src.watchers.models import FileEvent

try:
    import pathspec
    HAS_PATHSPEC = True
except ImportError:
    HAS_PATHSPEC = False


class TestFileSystemWatcher:
    """Test suite for FileSystemWatcher."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.vault_path = Path(self.temp_dir) / "vault"
        self.watch_path = Path(self.temp_dir) / "watch"
        self.vault_path.mkdir()
        self.watch_path.mkdir()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init(self):
        """Test watcher initialization."""
        watcher = FileSystemWatcher(
            vault_path=self.vault_path,
            watch_path=self.watch_path,
        )

        assert watcher.vault_path == self.vault_path
        assert watcher.watch_path == self.watch_path
        assert watcher.recursive is True
        assert watcher.watcher_name == "filesystem"

    def test_should_ignore_exclude_patterns(self):
        """Test file exclusion patterns."""
        watcher = FileSystemWatcher(
            vault_path=self.vault_path,
            watch_path=self.watch_path,
            exclude_patterns=["*.tmp", "*.swp"],
        )

        # Create test files
        tmp_file = self.watch_path / "test.tmp"
        swp_file = self.watch_path / "test.swp"
        pdf_file = self.watch_path / "test.pdf"

        tmp_file.touch()
        swp_file.touch()
        pdf_file.touch()

        assert watcher._should_ignore(tmp_file) is True
        assert watcher._should_ignore(swp_file) is True
        assert watcher._should_ignore(pdf_file) is False

    def test_should_ignore_include_patterns(self):
        """Test file inclusion patterns."""
        watcher = FileSystemWatcher(
            vault_path=self.vault_path,
            watch_path=self.watch_path,
            include_patterns=["*.pdf", "*.docx"],
            exclude_patterns=[],
        )

        pdf_file = self.watch_path / "test.pdf"
        txt_file = self.watch_path / "test.txt"

        pdf_file.touch()
        txt_file.touch()

        assert watcher._should_ignore(pdf_file) is False
        assert watcher._should_ignore(txt_file) is True

    def test_compute_hash(self):
        """Test SHA256 hash computation."""
        watcher = FileSystemWatcher(
            vault_path=self.vault_path,
            watch_path=self.watch_path,
        )

        # Create test file with known content
        test_file = self.watch_path / "test.txt"
        test_file.write_text("Hello, World!")

        file_hash = watcher._compute_hash(test_file)

        # SHA256 of "Hello, World!" is known
        expected_hash = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        assert file_hash == expected_hash

    def test_compute_hash_large_file_skip(self):
        """Test hash computation is skipped for large files."""
        watcher = FileSystemWatcher(
            vault_path=self.vault_path,
            watch_path=self.watch_path,
            max_hash_size=100,  # Very small limit
        )

        # Create file larger than limit
        test_file = self.watch_path / "large.txt"
        test_file.write_text("x" * 200)

        file_hash = watcher._compute_hash(test_file)
        assert file_hash == ""

    def test_detect_mime_type(self):
        """Test MIME type detection."""
        watcher = FileSystemWatcher(
            vault_path=self.vault_path,
            watch_path=self.watch_path,
        )

        test_cases = [
            ("test.pdf", "application/pdf"),
            ("test.txt", "text/plain"),
            ("test.json", "application/json"),
            ("test.unknown", "application/octet-stream"),
        ]

        for filename, expected_mime in test_cases:
            file_path = self.watch_path / filename
            file_path.touch()
            mime_type = watcher._detect_mime_type(file_path)
            assert mime_type == expected_mime, f"Failed for {filename}"

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        watcher = FileSystemWatcher(
            vault_path=self.vault_path,
            watch_path=self.watch_path,
        )

        test_cases = [
            ("normal.txt", "normal.txt"),
            ("with spaces.txt", "with_spaces.txt"),
            ("with:colons.txt", "with_colons.txt"),
            ("with<brackets>.txt", "with_brackets_.txt"),
            ("  leading_trailing  .txt", "leading_trailing.txt"),
        ]

        for input_name, expected in test_cases:
            result = watcher._sanitize_filename(input_name)
            assert result == expected, f"Failed for {input_name}"

    @pytest.mark.skipif(not HAS_PATHSPEC, reason="pathspec library not installed")
    def test_load_gitignore(self):
        """Test .gitignore loading."""
        # Create .gitignore file
        gitignore_path = self.watch_path / ".gitignore"
        gitignore_path.write_text("*.log\n*.cache\n# Comment\n\n")

        watcher = FileSystemWatcher(
            vault_path=self.vault_path,
            watch_path=self.watch_path,
        )

        assert watcher._gitignore_spec is not None

        # Test pattern matching
        log_file = self.watch_path / "test.log"
        log_file.touch()
        assert watcher._should_ignore(log_file) is True

    @pytest.mark.skipif(
        True,  # Skip in CI - requires watchdog
        reason="Integration test requires watchdog observer"
    )
    def test_on_created_event(self):
        """Test file creation event handling."""
        watcher = FileSystemWatcher(
            vault_path=self.vault_path,
            watch_path=self.watch_path,
        )

        # Create a test file
        test_file = self.watch_path / "new_document.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        # Simulate file created event
        from watchdog.events import FileCreatedEvent
        event = FileCreatedEvent(str(test_file))
        watcher.on_created(event)

        # Check that Markdown was created in vault
        inbox_files = list((self.vault_path / "Inbox").glob("*.md"))
        assert len(inbox_files) == 1

        # Check content
        content = inbox_files[0].read_text()
        assert "new_document.pdf" in content
        assert "source: filesystem" in content


class TestFileEvent:
    """Test suite for FileEvent model."""

    def test_generate_id(self):
        """Test ID generation."""
        event = FileEvent(
            id="",
            file_path=Path("/test/document.pdf"),
            file_name="document.pdf",
            file_size=1024,
        )

        event_id = event.generate_id()
        assert event_id.startswith("file_document_pdf_")
        assert len(event_id) > 20

    def test_model_fields(self):
        """Test model field defaults."""
        event = FileEvent(
            id="test-id",
            file_path=Path("/test/file.txt"),
            file_name="file.txt",
            file_size=100,
        )

        assert event.source == "filesystem"
        assert event.file_type == "application/octet-stream"
        assert event.file_hash == ""
        assert event.event_type == "created"
        assert event.pii_redacted is False

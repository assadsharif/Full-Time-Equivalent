"""Tests for PIIRedactor."""

import pytest

from src.watchers.pii_redactor import PIIRedactor, RedactionResult


class TestPIIRedactor:
    """Test suite for PIIRedactor."""

    def setup_method(self):
        """Set up test fixtures."""
        self.redactor = PIIRedactor()

    def test_redact_email(self):
        """Test email address redaction."""
        text = "Contact me at user@example.com for more info"
        result = self.redactor.redact(text)

        assert isinstance(result, RedactionResult)
        assert "[REDACTED_EMAIL]" in result.text
        assert "user@example.com" not in result.text
        assert "email" in result.patterns_found
        assert result.redaction_count == 1

    def test_redact_multiple_emails(self):
        """Test redaction of multiple email addresses."""
        text = "Email alice@test.com or bob@company.org"
        result = self.redactor.redact(text)

        assert result.text.count("[REDACTED_EMAIL]") == 2
        assert result.redaction_count == 2

    def test_redact_phone_us(self):
        """Test US phone number redaction."""
        test_cases = [
            "Call me at 555-123-4567",
            "Phone: (555) 123-4567",
            "Contact: 555.123.4567",
            "Tel: +1-555-123-4567",
            "Mobile: 1 555 123 4567",
        ]

        for text in test_cases:
            result = self.redactor.redact(text)
            assert "[REDACTED_PHONE]" in result.text, f"Failed for: {text}"

    def test_redact_international_phone(self):
        """Test international phone number redaction."""
        text = "Reach me at +44 20 7946 0958"
        result = self.redactor.redact(text)

        assert "[REDACTED_PHONE]" in result.text

    def test_redact_ssn(self):
        """Test SSN redaction."""
        test_cases = [
            "SSN: 123-45-6789",
            "Social: 123 45 6789",
            "ID: 123.45.6789",
        ]

        for text in test_cases:
            result = self.redactor.redact(text)
            assert "[REDACTED_SSN]" in result.text, f"Failed for: {text}"

    def test_redact_credit_card(self):
        """Test credit card number redaction."""
        test_cases = [
            "Card: 4111-1111-1111-1111",
            "CC: 4111 1111 1111 1111",
            "Payment: 4111.1111.1111.1111",
        ]

        for text in test_cases:
            result = self.redactor.redact(text)
            assert "[REDACTED_CC]" in result.text, f"Failed for: {text}"

    def test_redact_ip_address(self):
        """Test IP address redaction."""
        text = "Server IP: 192.168.1.100"
        result = self.redactor.redact(text)

        assert "[REDACTED_IP]" in result.text
        assert "192.168.1.100" not in result.text

    def test_no_pii(self):
        """Test text without PII remains unchanged."""
        text = "This is a normal message without any PII"
        result = self.redactor.redact(text)

        assert result.text == text
        assert result.patterns_found == []
        assert result.redaction_count == 0

    def test_redact_dict(self):
        """Test dictionary redaction."""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "555-123-4567",
            "nested": {
                "contact": "alice@test.com",
            },
        }

        result = self.redactor.redact_dict(data)

        assert result["email"] == "[REDACTED_EMAIL]"
        assert result["phone"] == "[REDACTED_PHONE]"
        assert result["nested"]["contact"] == "[REDACTED_EMAIL]"
        assert result["name"] == "John Doe"  # No PII pattern

    def test_contains_pii(self):
        """Test PII detection."""
        assert self.redactor.contains_pii("user@example.com") is True
        assert self.redactor.contains_pii("555-123-4567") is True
        assert self.redactor.contains_pii("Hello world") is False

    def test_add_custom_pattern(self):
        """Test adding custom patterns."""
        self.redactor.add_pattern(
            name="employee_id",
            pattern=r"EMP-\d{6}",
            replacement="[REDACTED_EMPID]",
        )

        text = "Employee ID: EMP-123456"
        result = self.redactor.redact(text)

        assert "[REDACTED_EMPID]" in result.text
        assert "EMP-123456" not in result.text

    def test_non_string_input(self):
        """Test handling of non-string input."""
        result = self.redactor.redact(12345)
        assert result.text == "12345"

        result = self.redactor.redact(None)
        assert result.text == "None"

    def test_mixed_pii(self):
        """Test text with multiple PII types."""
        text = "Contact user@example.com or call 555-123-4567"
        result = self.redactor.redact(text)

        assert "[REDACTED_EMAIL]" in result.text
        assert "[REDACTED_PHONE]" in result.text
        assert result.redaction_count >= 2

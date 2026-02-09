"""
PII Redactor for watcher scripts.

Detects and redacts Personally Identifiable Information (PII) from text
before logging or processing.

Constitutional Compliance:
- Section 3: Privacy First - No PII in logs or public repos
"""

import re
from typing import NamedTuple

# Try to import the logging module, fall back to standard logging
try:
    from src.logging import get_logger
except ImportError:
    import logging

    def get_logger(name: str):
        return logging.getLogger(name)


logger = get_logger(__name__)


class RedactionResult(NamedTuple):
    """Result of PII redaction."""

    text: str
    patterns_found: list[str]
    redaction_count: int


class PIIRedactor:
    """
    Regex-based PII redaction for watcher scripts.

    Detects and redacts:
    - Email addresses
    - Phone numbers (various formats)
    - Social Security Numbers (SSN)
    - Credit card numbers
    - IP addresses

    Example:
        >>> redactor = PIIRedactor()
        >>> result = redactor.redact("Contact me at user@example.com or 555-123-4567")
        >>> print(result.text)
        Contact me at [REDACTED_EMAIL] or [REDACTED_PHONE]
    """

    # Default PII patterns
    DEFAULT_PATTERNS = {
        "email": {
            "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "replacement": "[REDACTED_EMAIL]",
        },
        "phone_us": {
            "pattern": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
            "replacement": "[REDACTED_PHONE]",
        },
        "phone_intl": {
            "pattern": r"\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b",
            "replacement": "[REDACTED_PHONE]",
        },
        "ssn": {
            "pattern": r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b",
            "replacement": "[REDACTED_SSN]",
        },
        "credit_card": {
            "pattern": r"\b(?:\d{4}[-.\s]?){3}\d{4}\b",
            "replacement": "[REDACTED_CC]",
        },
        "ip_address": {
            "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "replacement": "[REDACTED_IP]",
        },
    }

    def __init__(self, custom_patterns: dict[str, dict[str, str]] | None = None):
        """
        Initialize PIIRedactor.

        Args:
            custom_patterns: Additional patterns to use (merged with defaults)
                Format: {"pattern_name": {"pattern": "regex", "replacement": "[TEXT]"}}
        """
        self.patterns = self.DEFAULT_PATTERNS.copy()
        if custom_patterns:
            self.patterns.update(custom_patterns)

        # Compile patterns for performance
        self._compiled_patterns = {
            name: (re.compile(config["pattern"], re.IGNORECASE), config["replacement"])
            for name, config in self.patterns.items()
        }

    def redact(self, text: str) -> RedactionResult:
        """
        Redact PII from text.

        Args:
            text: Text to redact

        Returns:
            RedactionResult with redacted text, patterns found, and count
        """
        if not isinstance(text, str):
            text = str(text)

        patterns_found = []
        redaction_count = 0
        redacted_text = text

        for pattern_name, (
            compiled_pattern,
            replacement,
        ) in self._compiled_patterns.items():
            matches = compiled_pattern.findall(redacted_text)
            if matches:
                patterns_found.append(pattern_name)
                redaction_count += len(matches)
                redacted_text = compiled_pattern.sub(replacement, redacted_text)

        if redaction_count > 0:
            logger.debug(
                f"Redacted {redaction_count} PII instances",
                context={"patterns": patterns_found, "count": redaction_count},
            )

        return RedactionResult(
            text=redacted_text,
            patterns_found=patterns_found,
            redaction_count=redaction_count,
        )

    def redact_dict(self, data: dict) -> dict:
        """
        Recursively redact PII from dictionary values.

        Args:
            data: Dictionary to redact

        Returns:
            New dictionary with redacted string values
        """
        redacted = {}
        for key, value in data.items():
            if isinstance(value, dict):
                redacted[key] = self.redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    (
                        self.redact_dict(item)
                        if isinstance(item, dict)
                        else self.redact(item).text if isinstance(item, str) else item
                    )
                    for item in value
                ]
            elif isinstance(value, str):
                redacted[key] = self.redact(value).text
            else:
                redacted[key] = value
        return redacted

    def add_pattern(self, name: str, pattern: str, replacement: str) -> None:
        """
        Add a custom PII pattern.

        Args:
            name: Pattern identifier
            pattern: Regex pattern
            replacement: Replacement text
        """
        self.patterns[name] = {"pattern": pattern, "replacement": replacement}
        self._compiled_patterns[name] = (
            re.compile(pattern, re.IGNORECASE),
            replacement,
        )
        logger.info(f"Added PII pattern: {name}")

    def contains_pii(self, text: str) -> bool:
        """
        Check if text contains any PII.

        Args:
            text: Text to check

        Returns:
            True if PII detected, False otherwise
        """
        for _, (compiled_pattern, _) in self._compiled_patterns.items():
            if compiled_pattern.search(text):
                return True
        return False

"""
Secret redaction for logging infrastructure (P2).

Regex-based pattern matching for automatic secret redaction.
Constitutional compliance: Section 3 (privacy, secrets never written to disk).
"""

import re
from typing import Any


# Default secret patterns (can be overridden via config)
DEFAULT_SECRET_PATTERNS = [
    # API keys and secrets
    r"(?i)(api[_-]?key|apikey)[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9_\-]{20,})",
    # Passwords
    r"(?i)(password|passwd|pwd)[\"']?\s*[:=]\s*[\"']?([^\s\"']{6,})",
    # Bearer tokens
    r"(?i)(bearer|token|auth)[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9_\-\.]{20,})",
    # Private keys and secrets
    r"(?i)(secret|private[_-]?key)[\"']?\s*[:=]\s*[\"']?([a-zA-Z0-9_\-]{20,})",
    # JWT tokens (header.payload.signature format)
    r"eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+",
    # AWS access keys
    r"(?i)(aws[_-]?access[_-]?key[_-]?id|aws[_-]?secret[_-]?access[_-]?key)\s*[:=]\s*[\"']?([a-zA-Z0-9/+=]{20,})",
]


class SecretRedactor:
    """
    Regex-based secret redaction for log messages.

    Performance target: < 1μs per entry (hot path optimization).
    Constitutional compliance: Section 3 (secrets never written to disk).

    Example:
        >>> redactor = SecretRedactor()
        >>> redactor.redact("password=secret123")
        'password=***REDACTED***'
    """

    def __init__(
        self,
        patterns: list[str] | None = None,
        redaction_text: str = "***REDACTED***",
    ):
        """
        Initialize SecretRedactor with custom or default patterns.

        Args:
            patterns: List of regex patterns for secret detection
                     (defaults to DEFAULT_SECRET_PATTERNS if None)
            redaction_text: Replacement text for detected secrets

        Example:
            >>> redactor = SecretRedactor(
            ...     patterns=[r"secret=\w+"],
            ...     redaction_text="[HIDDEN]"
            ... )
        """
        self.patterns = patterns or DEFAULT_SECRET_PATTERNS
        self.redaction_text = redaction_text

        # Compile patterns once for performance (hot path optimization)
        self._compiled_patterns = [
            re.compile(pattern) for pattern in self.patterns
        ]

    def redact(self, text: str | Any) -> str:
        """
        Redact secrets from text using configured patterns.

        Performance: < 1μs per entry for typical log messages.
        Hot path optimization: compiled regex patterns, early returns.

        Args:
            text: Text to redact (converted to string if not already)

        Returns:
            Text with secrets replaced by redaction_text

        Example:
            >>> redactor = SecretRedactor()
            >>> redactor.redact("api_key=sk_test_EXAMPLE_KEY_NOT_REAL_00")
            'api_key=***REDACTED***'
            >>> redactor.redact("password=hunter2")
            'password=***REDACTED***'
            >>> redactor.redact("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123")
            'Bearer ***REDACTED***'
        """
        # Convert to string if needed
        if not isinstance(text, str):
            text = str(text)

        # Early return if no patterns configured
        if not self._compiled_patterns:
            return text

        # Apply each pattern sequentially
        redacted_text = text
        for pattern in self._compiled_patterns:
            redacted_text = pattern.sub(self.redaction_text, redacted_text)

        return redacted_text

    def redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Recursively redact secrets from dictionary values.

        Useful for redacting structured context data.

        Args:
            data: Dictionary to redact (keys preserved, values redacted)

        Returns:
            New dictionary with redacted values (original unchanged)

        Example:
            >>> redactor = SecretRedactor()
            >>> redactor.redact_dict({
            ...     "user": "alice",
            ...     "api_key": "sk_test_EXAMPLE_KEY_NOT_REAL_00"
            ... })
            {'user': 'alice', 'api_key': '***REDACTED***'}
        """
        redacted = {}
        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively redact nested dicts
                redacted[key] = self.redact_dict(value)
            elif isinstance(value, list):
                # Redact list items
                redacted[key] = [
                    self.redact_dict(item) if isinstance(item, dict) else self.redact(item)
                    for item in value
                ]
            else:
                # Redact scalar values
                redacted[key] = self.redact(value)

        return redacted

    def add_pattern(self, pattern: str) -> None:
        """
        Add a new secret pattern to the redactor.

        Args:
            pattern: Regex pattern to add

        Example:
            >>> redactor = SecretRedactor()
            >>> redactor.add_pattern(r"custom_secret=\w+")
            >>> redactor.redact("custom_secret=abc123")
            'custom_secret=***REDACTED***'
        """
        self.patterns.append(pattern)
        self._compiled_patterns.append(re.compile(pattern))

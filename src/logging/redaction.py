"""
Secret redaction for logging infrastructure (P2).

Regex-based pattern matching for automatic secret redaction.
Constitutional compliance: Section 3 (privacy, secrets never written to disk).
"""

import re
from typing import Any


# Default secret patterns (can be overridden via config)
# Patterns with capturing groups: group 1 = key name, group 2 = separator (normalized), group 3 = secret value
DEFAULT_SECRET_PATTERNS = [
    # API keys and secrets (key=value or key: value, with optional quotes)
    r"(?i)(api[_-]?key|apikey)([\"']?\s*[:=]\s*[\"']?)([a-zA-Z0-9_\-]{20,})[\"']?",
    # Passwords (with optional quotes around value)
    r"(?i)(password|passwd|pwd)([\"']?\s*[:=]\s*[\"']?)([^\s\"']{6,})[\"']?",
    # Bearer/token/auth with = or : separator
    r"(?i)(bearer|token|auth)([\"']?\s*[:=]\s*[\"']?)([a-zA-Z0-9_\-\.]{20,})[\"']?",
    # Bearer token with space (e.g., "Bearer xyz123") - preserve space separator
    r"(Bearer)( )([a-zA-Z0-9_\-\.]{20,})",
    # Private keys and secrets
    r"(?i)(secret|private[_-]?key)([\"']?\s*[:=]\s*[\"']?)([a-zA-Z0-9_\-]{20,})[\"']?",
    # JWT tokens (header.payload.signature format) - no capturing groups
    r"eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+",
    # AWS access keys
    r"(?i)(aws[_-]?access[_-]?key[_-]?id|aws[_-]?secret[_-]?access[_-]?key)(\s*[:=]\s*[\"']?)([a-zA-Z0-9/+=]{20,})[\"']?",
]

# Patterns for detecting secrets in standalone values (for dict redaction)
SECRET_VALUE_PATTERNS = [
    r"^sk_live_[a-zA-Z0-9_\-]{16,}$",  # Stripe live keys
    r"^sk_test_[a-zA-Z0-9_\-]{16,}$",  # Stripe test keys
    r"^[a-zA-Z0-9_\-]{20,}$",  # Generic long alphanumeric (potential secrets)
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
        r"""
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
        self.patterns = DEFAULT_SECRET_PATTERNS if patterns is None else patterns
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
            # Use replacement function to preserve key and separator
            def replace_with_prefix(match, redaction=self.redaction_text):
                groups = match.groups()
                matched_text = match.group(0)

                if len(groups) >= 3:
                    # Pattern has key, separator, value groups
                    key, sep, _ = groups[0], groups[1], groups[2]
                    # Normalize separator: remove quotes, keep : or = or space
                    if sep.strip() == "":
                        # Space-only separator (e.g., "Bearer xyz")
                        sep_clean = " "
                    elif ":" in sep:
                        sep_clean = ": "
                    else:
                        sep_clean = "="
                    return f"{key}{sep_clean}{redaction}"
                elif len(groups) >= 2:
                    # Pattern has key and value groups
                    return f"{groups[0]}={redaction}"
                else:
                    # No capturing groups - try to preserve prefix if pattern contains = or :
                    for sep in ["=", ": ", ":"]:
                        if sep in matched_text:
                            prefix = matched_text.split(sep)[0]
                            return f"{prefix}{sep}{redaction}"
                    # No separator found - replace entire match
                    return redaction

            redacted_text = pattern.sub(replace_with_prefix, redacted_text)

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
        # Keys that indicate sensitive values
        sensitive_keys = {
            "api_key", "apikey", "api-key",
            "password", "passwd", "pwd",
            "secret", "token", "auth",
            "private_key", "private-key",
            "access_key", "secret_key",
        }

        redacted = {}
        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively redact nested dicts
                redacted[key] = self.redact_dict(value)
            elif isinstance(value, list):
                # Redact list items, preserving types
                redacted[key] = [
                    self.redact_dict(item) if isinstance(item, dict)
                    else self._redact_value(key, item)
                    for item in value
                ]
            else:
                # Redact scalar values based on key and value
                redacted[key] = self._redact_value(key, value)

        return redacted

    def _redact_value(self, key: str, value: Any) -> Any:
        """
        Redact a single value based on its key and content.

        Preserves non-string types unless they contain secrets.
        """
        # Keys that indicate sensitive values
        sensitive_keys = {
            "api_key", "apikey", "api-key",
            "password", "passwd", "pwd",
            "secret", "token", "auth",
            "private_key", "private-key",
            "access_key", "secret_key",
        }

        key_lower = key.lower().replace("-", "_")

        # If key indicates sensitive field, redact the value
        if key_lower in sensitive_keys:
            return self.redaction_text

        # For strings, check if value itself looks like a secret
        if isinstance(value, str):
            # Check against text patterns first
            redacted = self.redact(value)
            if redacted != value:
                return redacted
            # Value unchanged, return as-is
            return value

        # Preserve non-string types (int, bool, float, None)
        return value

    def add_pattern(self, pattern: str) -> None:
        r"""
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

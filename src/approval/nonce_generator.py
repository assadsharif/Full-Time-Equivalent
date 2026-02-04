"""
Nonce Generator — replay-attack prevention.

Each approval is assigned a UUID4 nonce at creation.  When the approval
is acted on (approve / reject), the nonce is written to a line-based
audit file.  Any subsequent attempt to re-use the same nonce is caught
before the action executes.
"""

import uuid
from pathlib import Path


class NonceGenerator:
    """Generate and track single-use nonces."""

    def __init__(self, audit_path: Path):
        self._audit = audit_path

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def generate(self) -> str:
        """Return a fresh UUID4 nonce."""
        return str(uuid.uuid4())

    def record_used(self, nonce: str) -> None:
        """Append *nonce* to the audit file (creates parents if needed)."""
        self._audit.parent.mkdir(parents=True, exist_ok=True)
        with self._audit.open("a") as fh:
            fh.write(f"{nonce}\n")

    def is_used(self, nonce: str) -> bool:
        """True if *nonce* appears in the audit file."""
        if not self._audit.exists():
            return False
        return nonce in set(self._audit.read_text().splitlines())

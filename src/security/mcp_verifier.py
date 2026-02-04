"""
MCP Server Verifier — SHA256 signature verification (spec 004 Silver).

Calculates SHA256 digests of MCP server files and compares them against
a persisted trust store (.fte/mcp-signatures.json).  A server is considered
trusted only when its current digest matches the recorded signature.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional


class VerificationError(Exception):
    """Raised when a server signature does not match."""


class MCPVerifier:
    """Verify MCP server integrity via SHA256 checksums."""

    def __init__(self, trust_store_path: Path):
        self._store_path = trust_store_path
        self._store_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Signature calculation
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_signature(server_path: Path) -> str:
        """Return the hex-encoded SHA256 digest of a file."""
        if not server_path.exists():
            raise FileNotFoundError(f"Server file not found: {server_path}")
        h = hashlib.sha256()
        with open(server_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    # ------------------------------------------------------------------
    # Trust store management
    # ------------------------------------------------------------------

    def add_trusted(self, server_name: str, signature: str) -> None:
        """Record a trusted signature for a named server."""
        store = self._load_store()
        store[server_name] = signature
        self._save_store(store)

    def remove_trusted(self, server_name: str) -> None:
        """Remove a server from the trust store."""
        store = self._load_store()
        store.pop(server_name, None)
        self._save_store(store)

    def list_trusted(self) -> dict[str, str]:
        """Return {server_name: signature} for all trusted servers."""
        return self._load_store()

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    def verify_server(self, server_name: str, server_path: Path) -> bool:
        """
        Verify a server file against its trusted signature.

        Returns True if the current digest matches the stored signature.
        Raises VerificationError on mismatch.
        Raises KeyError if the server is not in the trust store.
        """
        store = self._load_store()
        if server_name not in store:
            raise KeyError(f"Server '{server_name}' not in trust store")
        current = self.calculate_signature(server_path)
        expected = store[server_name]
        if current != expected:
            raise VerificationError(
                f"Signature mismatch for '{server_name}': "
                f"expected {expected[:16]}… got {current[:16]}…"
            )
        return True

    def is_trusted(self, server_name: str, server_path: Path) -> bool:
        """Non-raising convenience: True if verified, False otherwise."""
        try:
            return self.verify_server(server_name, server_path)
        except (KeyError, VerificationError, FileNotFoundError):
            return False

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_store(self) -> dict[str, str]:
        if not self._store_path.exists():
            return {}
        return json.loads(self._store_path.read_text())

    def _save_store(self, store: dict[str, str]) -> None:
        self._store_path.write_text(json.dumps(store, indent=2))

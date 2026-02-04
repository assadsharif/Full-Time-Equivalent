"""
Credential Vault — secure credential storage (spec 004 Bronze).

Tries OS keyring first.  If keyring is unavailable, falls back to a
Fernet-encrypted JSON store under <vault>/.fte/security/ and emits a
one-time warning.  The encryption key lives in a 0o600 file next to the
ciphertext; this is deliberately weaker than keyring but still prevents
casual plaintext exposure.
"""

import json
import os
import warnings
from pathlib import Path

from cryptography.fernet import Fernet

try:
    import keyring as _keyring

    _KEYRING_AVAILABLE = True
except ImportError:
    _KEYRING_AVAILABLE = False


class CredentialNotFoundError(Exception):
    """Raised when a requested credential does not exist."""


class CredentialVault:
    """Store and retrieve credentials securely."""

    _SERVICE_PREFIX = "fte-mcp:"

    def __init__(self, vault_dir: Path):
        self._security_dir = vault_dir / ".fte" / "security"
        self._security_dir.mkdir(parents=True, exist_ok=True)
        self._cred_file = self._security_dir / "credentials.json.enc"
        self._key_file = self._security_dir / ".vault_key"

        if not _KEYRING_AVAILABLE:
            warnings.warn(
                "keyring not installed — credentials stored in encrypted file. "
                "Install 'keyring' for OS-native secure storage.",
                stacklevel=2,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(self, service: str, username: str, credential: str) -> None:
        """Store a credential for the given service / username."""
        if _KEYRING_AVAILABLE:
            _keyring.set_password(self._SERVICE_PREFIX + service, username, credential)
        else:
            self._store_fallback(service, username, credential)

    def retrieve(self, service: str, username: str) -> str:
        """Retrieve a credential.  Raises CredentialNotFoundError if missing."""
        if _KEYRING_AVAILABLE:
            value = _keyring.get_password(self._SERVICE_PREFIX + service, username)
            if value is None:
                raise CredentialNotFoundError(f"No credential for {service}/{username}")
            return value
        return self._retrieve_fallback(service, username)

    def delete(self, service: str, username: str) -> None:
        """Delete a credential.  Raises CredentialNotFoundError if missing."""
        if _KEYRING_AVAILABLE:
            _keyring.delete_password(self._SERVICE_PREFIX + service, username)
        else:
            self._delete_fallback(service, username)

    def list_services(self) -> list[str]:
        """Return all service names in the fallback store.

        Note: OS keyring does not expose a list API — returns empty when
        keyring is the active backend.
        """
        if _KEYRING_AVAILABLE:
            return []
        return list(self._load_store().keys())

    # ------------------------------------------------------------------
    # Fallback — Fernet-encrypted JSON file
    # ------------------------------------------------------------------

    def _get_key(self) -> bytes:
        if self._key_file.exists():
            return self._key_file.read_bytes()
        key = Fernet.generate_key()
        self._key_file.write_bytes(key)
        os.chmod(self._key_file, 0o600)
        return key

    def _load_store(self) -> dict:
        if not self._cred_file.exists():
            return {}
        fernet = Fernet(self._get_key())
        return json.loads(fernet.decrypt(self._cred_file.read_bytes()))

    def _save_store(self, store: dict) -> None:
        fernet = Fernet(self._get_key())
        self._cred_file.write_bytes(fernet.encrypt(json.dumps(store).encode()))

    def _store_fallback(self, service: str, username: str, credential: str) -> None:
        store = self._load_store()
        store.setdefault(service, {})[username] = credential
        self._save_store(store)

    def _retrieve_fallback(self, service: str, username: str) -> str:
        store = self._load_store()
        if service not in store or username not in store[service]:
            raise CredentialNotFoundError(f"No credential for {service}/{username}")
        return store[service][username]

    def _delete_fallback(self, service: str, username: str) -> None:
        store = self._load_store()
        if service not in store or username not in store[service]:
            raise CredentialNotFoundError(f"No credential for {service}/{username}")
        del store[service][username]
        if not store[service]:
            del store[service]
        self._save_store(store)

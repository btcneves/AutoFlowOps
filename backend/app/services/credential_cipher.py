"""Fernet-based credential encryption for notification channel configs.

Key hierarchy:
- NOTIFICATION_ENCRYPTION_KEY env var (production) — a URL-safe base64 Fernet key.
  Generate via: from cryptography.fernet import Fernet; Fernet.generate_key()
- If the key is absent, a key is derived from APP_SECRET_KEY via SHA-256.
  This provides consistent encryption in dev/test but is NOT suitable for production
  because the derived key is tied to APP_SECRET_KEY, which is less protected.
  A WARNING is logged in this case.

On read, legacy plain-JSON values (from v0.5.0 before encryption was introduced)
are decrypted transparently: if the ciphertext starts with '{', it is assumed to be
plain JSON, parsed, and re-saved as an encrypted token on the next write.
"""

import base64
import hashlib
import json
import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)

_fernet_instance: Fernet | None = None
_warned = False


def _get_fernet() -> Fernet:
    global _fernet_instance, _warned  # noqa: PLW0603
    if _fernet_instance is not None:
        return _fernet_instance

    raw_key = settings.notification_encryption_key.strip()
    if raw_key:
        try:
            key_bytes = raw_key.encode()
            # Validate the key is a proper Fernet key by instantiating
            fernet = Fernet(key_bytes)
            _fernet_instance = fernet
            return _fernet_instance
        except Exception as exc:
            raise ValueError(
                "NOTIFICATION_ENCRYPTION_KEY is set but is not a valid Fernet key. "
                "Generate one with Fernet.generate_key().decode()."
            ) from exc

    if not _warned:
        logger.warning(
            "NOTIFICATION_ENCRYPTION_KEY is not set. "
            "Credentials are encrypted using a key derived from APP_SECRET_KEY. "
            "Set NOTIFICATION_ENCRYPTION_KEY before deploying to production."
        )
        _warned = True

    derived = hashlib.sha256(settings.app_secret_key.encode()).digest()
    key_bytes = base64.urlsafe_b64encode(derived)
    _fernet_instance = Fernet(key_bytes)
    return _fernet_instance


def encrypt_config(config: dict[str, Any]) -> str:
    """Serialize config to JSON and encrypt it with Fernet."""
    plaintext = json.dumps(config, sort_keys=True).encode()
    return _get_fernet().encrypt(plaintext).decode()


def decrypt_config(ciphertext: str) -> dict[str, Any]:
    """Decrypt a Fernet ciphertext and parse it as JSON.

    Legacy plain-JSON values (v0.5.0 records written before encryption was
    introduced) are detected by the leading '{' character and parsed directly.
    """
    if ciphertext.startswith("{"):
        # Legacy: plain JSON stored before encryption was introduced.
        return json.loads(ciphertext)

    try:
        plaintext = _get_fernet().decrypt(ciphertext.encode())
        return json.loads(plaintext.decode())
    except InvalidToken as exc:
        raise ValueError(
            "Failed to decrypt channel config. "
            "Ensure NOTIFICATION_ENCRYPTION_KEY matches the key used at creation."
        ) from exc


def reset_fernet_cache() -> None:
    """Reset the cached Fernet instance. Used in tests to reload config."""
    global _fernet_instance, _warned  # noqa: PLW0603
    _fernet_instance = None
    _warned = False

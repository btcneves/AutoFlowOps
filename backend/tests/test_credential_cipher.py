"""Tests for the credential_cipher module."""

import json

import pytest

from app.services.credential_cipher import (
    decrypt_config,
    encrypt_config,
    reset_fernet_cache,
)


@pytest.fixture(autouse=True)
def reset_cipher():
    reset_fernet_cache()
    yield
    reset_fernet_cache()


def test_encrypt_decrypt_roundtrip() -> None:
    config = {"webhook_url": "https://hooks.example.com/secret-path/token"}
    ciphertext = encrypt_config(config)
    assert isinstance(ciphertext, str)
    assert "secret-path" not in ciphertext
    assert "token" not in ciphertext
    recovered = decrypt_config(ciphertext)
    assert recovered == config


def test_encrypt_produces_fernet_token() -> None:
    config = {"bot_token": "1234567890:ABCDEFGHIJKLMNabcdefghijklmn", "chat_id": "-100"}
    ciphertext = encrypt_config(config)
    # Fernet tokens are base64-encoded and start with 'g' (URL-safe base64 of 0x80)
    assert not ciphertext.startswith("{")
    assert len(ciphertext) > 20


def test_decrypt_legacy_plain_json() -> None:
    """Legacy records from v0.5.0 stored plain JSON — must be handled transparently."""
    config = {"webhook_url": "https://discord.com/api/webhooks/123/abc"}
    plain_json = json.dumps(config, sort_keys=True)
    recovered = decrypt_config(plain_json)
    assert recovered == config


def test_encrypt_secrets_not_in_ciphertext() -> None:
    config = {
        "bot_token": "9999999999:AAABBBCCC",
        "chat_id": "-100987654321",
    }
    ciphertext = encrypt_config(config)
    assert "AAABBBCCC" not in ciphertext
    assert "9999999999" not in ciphertext
    assert "-100987654321" not in ciphertext


def test_nested_dict_encrypted() -> None:
    config = {
        "url": "https://example.com/hook",
        "headers": {"Authorization": "Bearer super-secret"},
    }
    ciphertext = encrypt_config(config)
    assert "super-secret" not in ciphertext
    recovered = decrypt_config(ciphertext)
    assert recovered["headers"]["Authorization"] == "Bearer super-secret"


def test_different_configs_produce_different_ciphertexts() -> None:
    c1 = encrypt_config({"url": "https://a.example.com"})
    c2 = encrypt_config({"url": "https://b.example.com"})
    # Fernet includes a random IV, so even identical plaintexts produce different tokens
    assert c1 != c2

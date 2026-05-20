"""Masks sensitive fields in headers and JSON bodies before storing."""

import json
from typing import Any

SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "authorization",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "api_key",
        "apikey",
        "password",
        "passwd",
        "pwd",
        "cookie",
        "set-cookie",
        "private_key",
        "credential",
        "x-api-key",
        "x-auth-token",
    }
)

_MASK = "***"


def mask_sensitive_headers(headers: dict[str, str]) -> dict[str, str]:
    return {k: _MASK if k.lower() in SENSITIVE_KEYS else v for k, v in headers.items()}


def _mask_recursive(obj: Any, depth: int = 0) -> Any:
    if depth > 10:
        return obj
    if isinstance(obj, dict):
        return {
            k: _MASK if k.lower() in SENSITIVE_KEYS else _mask_recursive(v, depth + 1)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_mask_recursive(item, depth + 1) for item in obj]
    return obj


def mask_sensitive_body(body: str | None) -> str | None:
    if body is None:
        return None
    try:
        parsed = json.loads(body)
        return json.dumps(_mask_recursive(parsed))
    except (json.JSONDecodeError, TypeError):
        return body

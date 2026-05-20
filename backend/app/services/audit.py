"""Async helper for persisting audit log entries."""

import logging
import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = {
    "password", "password_hash", "secret", "token", "api_key",
    "webhook_url", "bot_token", "smtp_password", "encryption_key",
    "config", "config_encrypted", "config_masked",
}


def _mask_metadata(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            k: "***" if k in _SENSITIVE_KEYS else _mask_metadata(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_mask_metadata(item) for item in data]
    return data


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def log_action(
    session: AsyncSession,
    *,
    action: str,
    status: str = "success",
    user_id: uuid.UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata_=_mask_metadata(metadata) if metadata else None,
        )
        session.add(entry)
        await session.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to persist audit log entry: %s", exc)

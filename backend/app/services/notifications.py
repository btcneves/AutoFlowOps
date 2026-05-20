"""Notification channel delivery with masked persistence."""

import asyncio
import json
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.alert import Alert
from app.models.notification import NotificationChannel, NotificationDelivery
from app.schemas.notification import NotificationChannelRead
from app.services.masking import mask_sensitive_headers
from app.services.ssrf_guard import check_url

_MASK = "***"
_MAX_ATTEMPTS = 2


def load_channel_config(channel: NotificationChannel) -> dict[str, Any]:
    return json.loads(channel.config_encrypted)


def dump_channel_config(config: dict[str, Any]) -> str:
    return json.dumps(config, sort_keys=True)


def mask_url(url: str) -> str:
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return _MASK
    return urlunsplit((parsed.scheme, parsed.netloc, "/***", "", ""))


def mask_channel_config(channel_type: str, config: dict[str, Any]) -> dict[str, Any]:
    if channel_type == "discord_webhook":
        return {"webhook_url": mask_url(str(config.get("webhook_url", "")))}
    if channel_type == "smtp_email":
        return {
            "host": config.get("host"),
            "port": config.get("port"),
            "username": _MASK if config.get("username") else None,
            "password": _MASK if config.get("password") else None,
            "from_email": config.get("from_email"),
            "to_email": config.get("to_email"),
            "use_tls": bool(config.get("use_tls", True)),
            "use_ssl": bool(config.get("use_ssl", False)),
        }
    if channel_type == "custom_webhook":
        return {
            "url": mask_url(str(config.get("url", ""))),
            "method": "POST",
            "headers": mask_sensitive_headers(config.get("headers", {}) or {}),
        }
    return {}


def channel_to_read(channel: NotificationChannel) -> NotificationChannelRead:
    config = load_channel_config(channel)
    return NotificationChannelRead(
        id=channel.id,
        name=channel.name,
        type=channel.type,
        status=channel.status,
        config_masked=mask_channel_config(channel.type, config),
        created_at=channel.created_at,
        updated_at=channel.updated_at,
        last_tested_at=channel.last_tested_at,
    )


def _alert_payload(alert: Alert | None, *, test: bool = False) -> dict[str, str]:
    if alert is None:
        return {
            "title": "AutoFlowOps notification test",
            "severity": "info",
            "message": "This channel can receive AutoFlowOps notifications.",
            "alert_id": "test",
            "source_type": "test",
            "source_id": "test",
        }
    return {
        "title": alert.title,
        "severity": alert.severity,
        "message": alert.message,
        "alert_id": str(alert.id),
        "source_type": alert.source_type or "",
        "source_id": str(alert.source_id) if alert.source_id else "",
    }


async def send_channel_notification(
    session: AsyncSession,
    channel: NotificationChannel,
    alert: Alert | None = None,
    *,
    test: bool = False,
) -> NotificationDelivery:
    config = load_channel_config(channel)
    delivery = NotificationDelivery(
        alert_id=alert.id if alert else None,
        channel_id=channel.id,
        channel_name=channel.name,
        channel_type=channel.type,
        status="failed",
    )

    error: str | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            await _send_channel(channel.type, config, _alert_payload(alert, test=test))
            delivery.status = "success"
            delivery.sent_at = datetime.now(UTC)
            error = None
            break
        except Exception as exc:  # noqa: BLE001
            error = _mask_error(str(exc), config)
            if attempt + 1 < _MAX_ATTEMPTS:
                await asyncio.sleep(0.1)

    delivery.error_message = error
    if test:
        channel.last_tested_at = datetime.now(UTC)
        session.add(channel)
    session.add(delivery)
    await session.commit()
    await session.refresh(delivery)
    return delivery


async def dispatch_alert_notifications(
    session: AsyncSession,
    alert: Alert,
) -> list[NotificationDelivery]:
    if alert.severity != "error":
        return []

    result = await session.execute(
        select(NotificationChannel)
        .where(NotificationChannel.status == "active")
        .order_by(NotificationChannel.created_at.asc())
    )
    deliveries: list[NotificationDelivery] = []
    for channel in result.scalars().all():
        delivery = await send_channel_notification(session, channel, alert)
        deliveries.append(delivery)
    return deliveries


async def _send_channel(
    channel_type: str,
    config: dict[str, Any],
    payload: dict[str, str],
) -> None:
    if channel_type == "discord_webhook":
        await _send_discord(config, payload)
        return
    if channel_type == "smtp_email":
        await _send_smtp(config, payload)
        return
    if channel_type == "custom_webhook":
        await _send_custom_webhook(config, payload)
        return
    raise ValueError("Unsupported notification channel type")


async def _send_discord(config: dict[str, Any], payload: dict[str, str]) -> None:
    url = str(config["webhook_url"])
    _check_http_target(url)
    body = {
        "content": None,
        "embeds": [
            {
                "title": payload["title"],
                "description": payload["message"],
                "fields": [
                    {"name": "Severity", "value": payload["severity"], "inline": True},
                    {"name": "Alert", "value": payload["alert_id"], "inline": True},
                ],
            }
        ],
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(url, json=body)
        response.raise_for_status()


async def _send_custom_webhook(config: dict[str, Any], payload: dict[str, str]) -> None:
    url = str(config["url"])
    _check_http_target(url)
    headers = config.get("headers", {}) or {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()


async def _send_smtp(config: dict[str, Any], payload: dict[str, str]) -> None:
    await asyncio.to_thread(_send_smtp_sync, config, payload)


def _send_smtp_sync(config: dict[str, Any], payload: dict[str, str]) -> None:
    message = EmailMessage()
    message["Subject"] = (
        f"[AutoFlowOps] {payload['severity'].upper()}: {payload['title']}"
    )
    message["From"] = str(config["from_email"])
    message["To"] = str(config["to_email"])
    message.set_content(
        "\n".join(
            [
                payload["title"],
                "",
                f"Severity: {payload['severity']}",
                f"Message: {payload['message']}",
                f"Alert: {payload['alert_id']}",
                f"Source: {payload['source_type']} {payload['source_id']}".strip(),
            ]
        )
    )

    host = str(config["host"])
    port = int(config["port"])
    use_ssl = bool(config.get("use_ssl", False))
    use_tls = bool(config.get("use_tls", True))
    smtp_cls = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
    with smtp_cls(host, port, timeout=10) as smtp:
        if use_tls and not use_ssl:
            smtp.starttls()
        username = config.get("username")
        password = config.get("password")
        if username and password:
            smtp.login(str(username), str(password))
        smtp.send_message(message)


def _check_http_target(url: str) -> None:
    if settings.enable_ssrf_protection and not settings.allow_private_network_targets:
        check_url(url)


def _mask_error(error: str, config: dict[str, Any]) -> str:
    masked = error
    values: list[str] = []
    for value in config.values():
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, dict):
            values.extend(str(v) for v in value.values() if isinstance(v, str))
    for value in values:
        if value:
            masked = masked.replace(value, _MASK)
    return masked[:500]

"""Notification channel delivery with masked persistence and Fernet encryption."""

import asyncio
import json
import logging
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
from app.models.notification_template import NotificationTemplate
from app.schemas.notification import NotificationChannelRead
from app.services.credential_cipher import decrypt_config, encrypt_config
from app.services.masking import mask_sensitive_headers
from app.services.ssrf_guard import check_url

logger = logging.getLogger(__name__)

_MASK = "***"
_MAX_ATTEMPTS = 2


# ---------------------------------------------------------------------------
# Config persistence helpers (replaces plain JSON from v0.5.0)
# ---------------------------------------------------------------------------


def load_channel_config(channel: NotificationChannel) -> dict[str, Any]:
    """Decrypt channel config. Transparently handles legacy plain-JSON values."""
    return decrypt_config(channel.config_encrypted)


def dump_channel_config(config: dict[str, Any]) -> str:
    """Encrypt config with Fernet and return the ciphertext string."""
    return encrypt_config(config)


# ---------------------------------------------------------------------------
# Masking helpers (never expose secrets in API responses)
# ---------------------------------------------------------------------------


def mask_url(url: str) -> str:
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return _MASK
    return urlunsplit((parsed.scheme, parsed.netloc, "/***", "", ""))


def mask_channel_config(channel_type: str, config: dict[str, Any]) -> dict[str, Any]:
    if channel_type == "discord_webhook":
        return {"webhook_url": mask_url(str(config.get("webhook_url", "")))}
    if channel_type == "slack_webhook":
        return {"webhook_url": mask_url(str(config.get("webhook_url", "")))}
    if channel_type == "telegram_message":
        raw_token = str(config.get("bot_token", ""))
        # Show only the numeric bot-id prefix (before the colon), mask the rest
        token_prefix = raw_token.split(":")[0] if ":" in raw_token else _MASK
        return {
            "bot_token": f"{token_prefix}:{_MASK}",
            "chat_id": config.get("chat_id"),
        }
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
        masked: dict[str, Any] = {
            "url": mask_url(str(config.get("url", ""))),
            "method": "POST",
            "headers": mask_sensitive_headers(config.get("headers", {}) or {}),
        }
        if config.get("payload_template") is not None:
            masked["payload_template"] = config["payload_template"]
        return masked
    if channel_type == "pagerduty":
        masked = {"routing_key": _MASK}
        if config.get("dedup_key_template") is not None:
            masked["dedup_key_template"] = config["dedup_key_template"]
        return masked
    if channel_type == "opsgenie":
        masked = {
            "api_key": _MASK,
            "region": config.get("region", "us"),
            "responders": config.get("responders"),
        }
        if config.get("priority") is not None:
            masked["priority"] = config["priority"]
        return masked
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


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------


_BUILTIN_TITLE = "{title}"
_BUILTIN_BODY = "{title}\n\nSeverity: {severity}\n{message}"


def _build_template_vars(payload: dict[str, str]) -> dict[str, str]:
    return {
        "title": payload.get("title", ""),
        "severity": payload.get("severity", ""),
        "message": payload.get("message", ""),
        "alert_id": payload.get("alert_id", ""),
        "source_type": payload.get("source_type", ""),
        "source_id": payload.get("source_id", ""),
    }


async def _resolve_template(
    session: AsyncSession, severity: str
) -> tuple[str, str]:
    """Return (title_template, body_template) for the given severity."""
    # 1. Exact match on severity_filter
    result = await session.execute(
        select(NotificationTemplate)
        .where(NotificationTemplate.severity_filter == severity)
        .order_by(NotificationTemplate.created_at.desc())
        .limit(1)
    )
    tmpl = result.scalar_one_or_none()
    if tmpl:
        return tmpl.title_template, tmpl.body_template

    # 2. Catch-all template (severity_filter IS NULL)
    result = await session.execute(
        select(NotificationTemplate)
        .where(NotificationTemplate.severity_filter.is_(None))
        .order_by(
            NotificationTemplate.is_default.desc(),
            NotificationTemplate.created_at.desc(),
        )
        .limit(1)
    )
    tmpl = result.scalar_one_or_none()
    if tmpl:
        return tmpl.title_template, tmpl.body_template

    # 3. Built-in fallback
    return _BUILTIN_TITLE, _BUILTIN_BODY


def _render(title_tmpl: str, body_tmpl: str, vars_: dict[str, str]) -> tuple[str, str]:
    try:
        return title_tmpl.format(**vars_), body_tmpl.format(**vars_)
    except KeyError:
        return vars_["title"], _BUILTIN_BODY.format(**vars_)


# ---------------------------------------------------------------------------
# Alert payload helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------


async def send_channel_notification(
    session: AsyncSession,
    channel: NotificationChannel,
    alert: Alert | None = None,
    *,
    test: bool = False,
) -> NotificationDelivery:
    config = load_channel_config(channel)
    payload = _alert_payload(alert, test=test)

    # Resolve template for rendering rich title/body (used by Slack/Telegram/SMTP)
    title_tmpl, body_tmpl = await _resolve_template(
        session, payload.get("severity", "info")
    )
    vars_ = _build_template_vars(payload)
    rendered_title, rendered_body = _render(title_tmpl, body_tmpl, vars_)
    # Extend payload with rendered versions for channel senders
    enriched = {
        **payload,
        "rendered_title": rendered_title,
        "rendered_body": rendered_body,
    }

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
            await _send_channel(channel.type, config, enriched)
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
    """Dispatch alert to notification channels.

    If active escalation policies exist, uses escalation dispatch (step 0 only
    for immediate channels; deferred steps are handled by the escalation scheduler).
    Falls back to dispatching all active channels when no policies are configured.
    """
    if alert.severity != "error":
        return []

    from app.services.escalation import dispatch_via_escalation_policies

    used_escalation = await dispatch_via_escalation_policies(session, alert)
    if used_escalation is not None:
        return used_escalation

    # No active escalation policies — dispatch to all active channels directly
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


# ---------------------------------------------------------------------------
# Channel senders
# ---------------------------------------------------------------------------


async def _send_channel(
    channel_type: str,
    config: dict[str, Any],
    payload: dict[str, str],
) -> None:
    if channel_type == "discord_webhook":
        await _send_discord(config, payload)
        return
    if channel_type == "slack_webhook":
        await _send_slack(config, payload)
        return
    if channel_type == "telegram_message":
        await _send_telegram(config, payload)
        return
    if channel_type == "smtp_email":
        await _send_smtp(config, payload)
        return
    if channel_type == "custom_webhook":
        await _send_custom_webhook(config, payload)
        return
    if channel_type == "pagerduty":
        await _send_pagerduty(config, payload)
        return
    if channel_type == "opsgenie":
        await _send_opsgenie(config, payload)
        return
    raise ValueError("Unsupported notification channel type")


async def _send_discord(config: dict[str, Any], payload: dict[str, str]) -> None:
    url = str(config["webhook_url"])
    _check_http_target(url)
    title = payload.get("rendered_title") or payload["title"]
    body = payload.get("rendered_body") or payload["message"]
    discord_body = {
        "content": None,
        "embeds": [
            {
                "title": title,
                "description": body,
                "fields": [
                    {"name": "Severity", "value": payload["severity"], "inline": True},
                    {"name": "Alert", "value": payload["alert_id"], "inline": True},
                ],
            }
        ],
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(url, json=discord_body)
        response.raise_for_status()


async def _send_slack(config: dict[str, Any], payload: dict[str, str]) -> None:
    url = str(config["webhook_url"])
    _check_http_target(url)
    title = payload.get("rendered_title") or payload["title"]
    body = payload.get("rendered_body") or payload["message"]
    severity = payload["severity"]
    if severity == "error":
        color = "#cc0000"
    elif severity == "warning":
        color = "#e8a800"
    else:
        color = "#36a64f"
    slack_body = {
        "attachments": [
            {
                "color": color,
                "title": title,
                "text": body,
                "fields": [
                    {"title": "Severity", "value": severity, "short": True},
                    {"title": "Alert ID", "value": payload["alert_id"], "short": True},
                ],
                "footer": "AutoFlowOps",
            }
        ]
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(url, json=slack_body)
        response.raise_for_status()


async def _send_telegram(config: dict[str, Any], payload: dict[str, str]) -> None:
    bot_token = str(config["bot_token"])
    chat_id = str(config["chat_id"])
    title = payload.get("rendered_title") or payload["title"]
    body = payload.get("rendered_body") or payload["message"]
    severity = payload["severity"]
    text = f"*{title}*\n\nSeverity: {severity}\n{body}"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    _check_http_target("https://api.telegram.org")
    telegram_body = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(url, json=telegram_body)
        response.raise_for_status()


async def _send_custom_webhook(config: dict[str, Any], payload: dict[str, str]) -> None:
    url = str(config["url"])
    _check_http_target(url)
    headers = config.get("headers", {}) or {}
    payload_template = config.get("payload_template")
    if payload_template:
        rendered = payload_template.format_map(payload)
        send_payload = json.loads(rendered)
    else:
        send_payload = {
            k: v for k, v in payload.items() if not k.startswith("rendered_")
        }
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(url, json=send_payload, headers=headers)
        response.raise_for_status()


async def _send_pagerduty(config: dict[str, Any], payload: dict[str, str]) -> None:
    routing_key = str(config["routing_key"])
    url = "https://events.pagerduty.com/v2/enqueue"
    _check_http_target(url)
    title = payload.get("rendered_title") or payload["title"]
    body = payload.get("rendered_body") or payload["message"]
    severity_map = {"error": "critical", "warning": "warning", "info": "info"}
    pd_body: dict[str, Any] = {
        "routing_key": routing_key,
        "event_action": "trigger",
        "payload": {
            "summary": title,
            "severity": severity_map.get(payload["severity"], "critical"),
            "source": "AutoFlowOps",
            "custom_details": {
                "message": body,
                "alert_id": payload["alert_id"],
                "source_type": payload.get("source_type", ""),
                "source_id": payload.get("source_id", ""),
            },
        },
    }
    dedup_key_template = config.get("dedup_key_template")
    if dedup_key_template:
        pd_body["dedup_key"] = dedup_key_template.format_map(payload)
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(url, json=pd_body)
        response.raise_for_status()


_OPSGENIE_PRIORITY_MAP = {"error": "P2", "warning": "P3", "info": "P5"}


async def _send_opsgenie(config: dict[str, Any], payload: dict[str, str]) -> None:
    api_key = str(config["api_key"])
    region = str(config.get("region") or "us")
    base_url = (
        "https://api.eu.opsgenie.com/v2/alerts"
        if region == "eu"
        else "https://api.opsgenie.com/v2/alerts"
    )
    _check_http_target(base_url)
    title = payload.get("rendered_title") or payload["title"]
    body = payload.get("rendered_body") or payload["message"]
    priority = (
        config.get("priority") or _OPSGENIE_PRIORITY_MAP.get(payload["severity"], "P3")
    )
    og_body: dict[str, Any] = {
        "message": title,
        "description": body,
        "source": "AutoFlowOps",
        "alias": f"autoflowops-{payload['alert_id']}",
        "priority": priority,
        "tags": [payload["severity"]],
    }
    responders = config.get("responders")
    if responders:
        og_body["responders"] = responders
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            base_url,
            json=og_body,
            headers={"Authorization": f"GenieKey {api_key}"},
        )
        response.raise_for_status()


async def _send_smtp(config: dict[str, Any], payload: dict[str, str]) -> None:
    await asyncio.to_thread(_send_smtp_sync, config, payload)


def _send_smtp_sync(config: dict[str, Any], payload: dict[str, str]) -> None:
    title = payload.get("rendered_title") or payload["title"]
    body = payload.get("rendered_body") or payload["message"]
    message = EmailMessage()
    message["Subject"] = (
        f"[AutoFlowOps] {payload['severity'].upper()}: {title}"
    )
    message["From"] = str(config["from_email"])
    message["To"] = str(config["to_email"])
    message.set_content(
        "\n".join(
            [
                title,
                "",
                f"Severity: {payload['severity']}",
                f"Message: {body}",
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
        if len(value) > 4:  # skip short strings to avoid false positives
            masked = masked.replace(value, _MASK)
    return masked[:500]


# Re-export dump_channel_config for use in API layer
__all__ = [
    "channel_to_read",
    "dispatch_alert_notifications",
    "dump_channel_config",
    "load_channel_config",
    "mask_channel_config",
    "send_channel_notification",
]


def _log_json(obj: Any) -> str:
    return json.dumps(obj)

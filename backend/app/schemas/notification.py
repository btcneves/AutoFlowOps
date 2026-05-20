import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

NotificationType = Literal[
    "discord_webhook",
    "slack_webhook",
    "telegram_message",
    "smtp_email",
    "custom_webhook",
]
NotificationStatus = Literal["active", "paused"]


class NotificationChannelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: NotificationType
    config: dict[str, Any]
    status: NotificationStatus = "active"

    @model_validator(mode="after")
    def validate_config(self) -> "NotificationChannelCreate":
        _validate_channel_config(self.type, self.config)
        return self


class NotificationChannelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: NotificationType | None = None
    config: dict[str, Any] | None = None
    status: NotificationStatus | None = None

    @model_validator(mode="after")
    def validate_config(self) -> "NotificationChannelUpdate":
        if self.config is not None:
            if self.type is None:
                raise ValueError("type is required when updating config")
            _validate_channel_config(self.type, self.config)
        return self


class NotificationChannelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: str
    status: str
    config_masked: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_tested_at: datetime | None


class NotificationDeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: uuid.UUID | None
    channel_id: uuid.UUID | None
    channel_name: str
    channel_type: str
    status: str
    error_message: str | None
    sent_at: datetime | None
    created_at: datetime


class NotificationTestResult(BaseModel):
    channel: NotificationChannelRead
    delivery: NotificationDeliveryRead


def _require(config: dict[str, Any], key: str) -> None:
    value = config.get(key)
    if value is None or value == "":
        raise ValueError(f"{key} is required")


def _validate_channel_config(channel_type: str, config: dict[str, Any]) -> None:
    if channel_type == "discord_webhook":
        _require(config, "webhook_url")
    elif channel_type == "slack_webhook":
        _require(config, "webhook_url")
    elif channel_type == "telegram_message":
        _require(config, "bot_token")
        _require(config, "chat_id")
    elif channel_type == "smtp_email":
        for key in ("host", "port", "from_email", "to_email"):
            _require(config, key)
        port = int(config["port"])
        if port < 1 or port > 65535:
            raise ValueError("port must be between 1 and 65535")
    elif channel_type == "custom_webhook":
        _require(config, "url")
        method = str(config.get("method", "POST")).upper()
        if method != "POST":
            raise ValueError("custom webhook method must be POST")
        headers = config.get("headers", {})
        if headers is not None and not isinstance(headers, dict):
            raise ValueError("headers must be an object")
    else:
        raise ValueError("unsupported notification channel type")

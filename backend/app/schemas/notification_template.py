import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TemplateSeverity = Literal["error", "warning", "info"]


class NotificationTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    severity_filter: TemplateSeverity | None = None
    title_template: str = Field(
        default="{title}", min_length=1, max_length=500
    )
    body_template: str = Field(
        default="{title}\n\nSeverity: {severity}\n{message}", min_length=1
    )
    is_default: bool = False


class NotificationTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    severity_filter: TemplateSeverity | None = None
    title_template: str | None = Field(default=None, min_length=1, max_length=500)
    body_template: str | None = Field(default=None, min_length=1)
    is_default: bool | None = None


class NotificationTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    severity_filter: str | None
    title_template: str
    body_template: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

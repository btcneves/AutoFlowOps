import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    type: Literal["http"] = "http"
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    url: str = Field(min_length=1)
    headers: dict[str, str] | None = None
    body: str | None = None
    schedule_type: Literal["manual", "interval", "cron"] = "manual"
    schedule_expression: str | None = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_count: int = Field(default=0, ge=0, le=10)
    retry_delay_seconds: int = Field(default=60, ge=1)
    alert_on_failure: bool = True


class JobUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] | None = None
    url: str | None = Field(default=None, min_length=1)
    headers: dict[str, str] | None = None
    body: str | None = None
    schedule_type: Literal["manual", "interval", "cron"] | None = None
    schedule_expression: str | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    retry_count: int | None = Field(default=None, ge=0, le=10)
    retry_delay_seconds: int | None = Field(default=None, ge=1)
    alert_on_failure: bool | None = None
    status: Literal["active", "paused"] | None = None


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    type: str
    status: str
    schedule_type: str
    schedule_expression: str | None
    method: str | None
    url: str | None
    headers_masked: dict[str, str] | None
    timeout_seconds: int
    retry_count: int
    retry_delay_seconds: int
    alert_on_failure: bool
    created_at: datetime
    updated_at: datetime
    last_run_at: datetime | None
    next_run_at: datetime | None

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AlertRuleConditionType = Literal[
    "http_status_gte",
    "duration_ms_gte",
    "response_body_contains",
    "consecutive_failures_gte",
]

AlertRuleSeverity = Literal["error", "warning", "info"]


class AlertRuleCreate(BaseModel):
    condition_type: AlertRuleConditionType
    condition_value: str = Field(min_length=1, max_length=500)
    severity: AlertRuleSeverity = "warning"
    message: str | None = Field(default=None, max_length=255)
    is_enabled: bool = True

    @model_validator(mode="after")
    def validate_condition_value(self) -> "AlertRuleCreate":
        validate_alert_rule_condition_value(
            self.condition_type, self.condition_value
        )
        return self


class AlertRuleUpdate(BaseModel):
    condition_type: AlertRuleConditionType | None = None
    condition_value: str | None = Field(default=None, min_length=1, max_length=500)
    severity: AlertRuleSeverity | None = None
    message: str | None = Field(default=None, max_length=255)
    is_enabled: bool | None = None


class AlertRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    condition_type: AlertRuleConditionType
    condition_value: str
    severity: AlertRuleSeverity
    message: str | None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


def validate_alert_rule_condition_value(
    condition_type: AlertRuleConditionType,
    condition_value: str,
) -> None:
    if condition_type in {
        "http_status_gte",
        "duration_ms_gte",
        "consecutive_failures_gte",
    }:
        try:
            value = int(condition_value)
        except ValueError as exc:
            raise ValueError("condition_value must be an integer") from exc
        if condition_type == "http_status_gte" and not 100 <= value <= 599:
            raise ValueError("condition_value must be an HTTP status from 100 to 599")
        if condition_type == "duration_ms_gte" and value < 1:
            raise ValueError("condition_value must be greater than 0")
        if condition_type == "consecutive_failures_gte" and value < 1:
            raise ValueError("condition_value must be greater than 0")
